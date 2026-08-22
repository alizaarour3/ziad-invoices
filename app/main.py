from __future__ import annotations

import hashlib
import csv
import io
import json
import logging
import mimetypes
import os
import re
import sqlite3
import tempfile
from datetime import datetime, timedelta, timezone
from decimal import Decimal, ROUND_HALF_UP
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Annotated, Any
from urllib.parse import quote, unquote
from uuid import uuid4

from fastapi import Depends, FastAPI, Header, HTTPException, Query, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import FileResponse, JSONResponse, StreamingResponse
from starlette.background import BackgroundTask
from fastapi.staticfiles import StaticFiles

from .auth import CurrentUser, authenticate, get_bearer_token, get_current_user, logout, require
from .db import DBConnection, Record, audit, connect, ensure_user_page_permissions, init_db, transaction
from .schemas import (
    AdvanceCreateRequest,
    AdvancePaymentCreateRequest,
    AdvanceUpdateRequest,
    AttachmentNotesRequest,
    ChangePasswordRequest,
    DeleteRequest,
    DocumentCreateRequest,
    DocumentUpdateRequest,
    LoginRequest,
    LoanCreateRequest,
    LoanPaymentCreateRequest,
    LoanUpdateRequest,
    PagePermissionsUpdateRequest,
    PrintRequest,
    SetupAdminRequest,
    UserCreateRequest,
    UserUpdateRequest,
)
from .security import hash_password, utc_iso, verify_password
from .services.pdf_service import arabic_rendering_status, build_print_bundle, printing_status
from .services.backup_service import APP_VERSION, create_backup, database_integrity, template_integrity
from .services.storage_service import StorageError, storage
from .settings import DATA_DIR, GENERATED_DIR, MAX_ATTACHMENT_BYTES, STATIC_DIR

logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(_: FastAPI):
    init_db()
    yield


app = FastAPI(
    title="Ziad Documents",
    version=APP_VERSION,
    docs_url=None,
    redoc_url=None,
    openapi_url=None,
    lifespan=lifespan,
)


@app.middleware("http")
async def security_headers(request: Request, call_next):
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "SAMEORIGIN"
    response.headers["Referrer-Policy"] = "no-referrer"
    response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
    response.headers["Content-Security-Policy"] = (
        "default-src 'self'; img-src 'self' data: blob:; style-src 'self' 'unsafe-inline'; "
        "script-src 'self'; connect-src 'self'; frame-src 'self' blob:; object-src 'self' blob:; base-uri 'self'"
    )
    if request.url.scheme == "https" or request.headers.get("x-forwarded-proto") == "https":
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
    if request.url.path.startswith("/api/"):
        response.headers["Cache-Control"] = "no-store"
    return response


@app.exception_handler(RequestValidationError)
async def validation_error_handler(_: Request, exc: RequestValidationError):
    errors = exc.errors()
    first = errors[0] if errors else {}
    location = [str(part) for part in first.get("loc", ()) if str(part) not in {"body", "query", "path"}]
    field_key = location[-1] if location else ""
    field_labels = {
        "type_code": "نوع المستند",
        "status": "حالة المستند",
        "fields": "حقول المستند",
        "confirmation": "عبارة التأكيد",
        "username": "اسم المستخدم",
        "password": "كلمة المرور",
        "full_name": "الاسم الكامل",
        "role": "الصلاحية",
        "page_keys": "صلاحيات الصفحات",
        "borrower_name": "الاسم الثلاثي",
        "principal_amount": "مبلغ القرض",
        "months_total": "عدد أشهر التسديد",
        "minimum_payment": "الحد الأدنى للتسديد",
        "amount": "مبلغ التسديد",
        "notes": "الملاحظات",
        "person_name": "الاسم الثلاثي",
        "advance_month": "الشهر",
    }
    label = field_labels.get(field_key, field_key)
    detail = "البيانات المدخلة غير صحيحة"
    if label:
        detail = f"البيانات المدخلة غير صحيحة في حقل «{label}»"
    return JSONResponse(status_code=422, content={"detail": detail, "errors": errors})


async def database_integrity_error_handler(_: Request, exc: Exception):
    message = str(exc).lower()
    detail = "تعذر حفظ البيانات بسبب تعارض في قاعدة البيانات"
    if "users_username" in message or "users.username" in message or "username" in message:
        detail = "اسم المستخدم مستخدم مسبقاً"
    return JSONResponse(status_code=409, content={"detail": detail})


app.add_exception_handler(sqlite3.IntegrityError, database_integrity_error_handler)
try:
    import psycopg
except ImportError:
    psycopg = None
if psycopg is not None:
    app.add_exception_handler(psycopg.IntegrityError, database_integrity_error_handler)


def _user_dict(row: Record) -> dict[str, Any]:
    return {
        "id": row["id"],
        "full_name": row["full_name"],
        "username": row["username"],
        "role": row["role"],
        "is_active": bool(row["is_active"]),
        "must_change_password": bool(row["must_change_password"]),
        "created_at": row["created_at"],
        "updated_at": row["updated_at"],
        "last_login_at": row["last_login_at"],
    }



def _money_to_minor(value: float | int | str | Decimal) -> int:
    try:
        decimal_value = Decimal(str(value)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    except Exception as exc:
        raise HTTPException(status_code=422, detail="المبلغ المدخل غير صحيح") from exc
    minor = int(decimal_value * 100)
    if minor <= 0:
        raise HTTPException(status_code=422, detail="يجب أن يكون المبلغ أكبر من صفر")
    return minor


def _minor_to_money(value: int) -> str:
    amount = (Decimal(int(value)) / Decimal(100)).quantize(Decimal("0.01"))
    return format(amount, ".2f")


def _loan_page_access(conn: DBConnection, user: CurrentUser) -> None:
    _require_page_access(conn, user, "loans")


def _loan_dict(conn: DBConnection, row: Record, *, include_payments: bool = False) -> dict[str, Any]:
    payment_count = int(row["payment_count"]) if "payment_count" in row.keys() else int(
        conn.execute("SELECT COUNT(*) AS count FROM loan_payments WHERE loan_id=?", (row["id"],)).fetchone()["count"]
    )
    paid_minor = int(row["principal_amount_minor"]) - int(row["remaining_amount_minor"])
    remaining_months = 0 if int(row["remaining_amount_minor"]) == 0 else max(int(row["months_total"]) - payment_count, 0)
    result: dict[str, Any] = {
        "id": int(row["id"]),
        "borrower_name": row["borrower_name"],
        "principal_amount": _minor_to_money(int(row["principal_amount_minor"])),
        "months_total": int(row["months_total"]),
        "minimum_payment": _minor_to_money(int(row["minimum_payment_minor"])),
        "remaining_amount": _minor_to_money(int(row["remaining_amount_minor"])),
        "paid_amount": _minor_to_money(paid_minor),
        "payment_count": payment_count,
        "remaining_months": remaining_months,
        "status": "paid" if int(row["remaining_amount_minor"]) == 0 else "active",
        "created_by": int(row["created_by"]),
        "created_by_name": row["created_by_name"] if "created_by_name" in row.keys() else None,
        "updated_by": int(row["updated_by"]),
        "updated_by_name": row["updated_by_name"] if "updated_by_name" in row.keys() else None,
        "created_at": row["created_at"],
        "updated_at": row["updated_at"],
    }
    if include_payments:
        payments = conn.execute(
            """
            SELECT p.*, u.full_name AS paid_by_name
            FROM loan_payments p JOIN users u ON u.id=p.paid_by
            WHERE p.loan_id=? ORDER BY p.id DESC
            """,
            (row["id"],),
        ).fetchall()
        result["payments"] = [
            {
                "id": int(item["id"]),
                "amount": _minor_to_money(int(item["amount_minor"])),
                "remaining_amount_after": _minor_to_money(int(item["remaining_amount_minor_after"])),
                "months_remaining_after": int(item["months_remaining_after"]),
                "notes": item["notes"],
                "paid_by": int(item["paid_by"]),
                "paid_by_name": item["paid_by_name"],
                "paid_at": item["paid_at"],
            }
            for item in payments
        ]
    return result


LOAN_SELECT = """
SELECT l.*, creator.full_name AS created_by_name, updater.full_name AS updated_by_name,
       (SELECT COUNT(*) FROM loan_payments p WHERE p.loan_id=l.id) AS payment_count
FROM loans l
JOIN users creator ON creator.id=l.created_by
JOIN users updater ON updater.id=l.updated_by
"""


def _advance_page_access(conn: DBConnection, user: CurrentUser) -> None:
    _require_page_access(conn, user, "advances")


def _advance_dict(conn: DBConnection, row: Record, *, include_payments: bool = False) -> dict[str, Any]:
    payment_count = int(row["payment_count"]) if "payment_count" in row.keys() else int(
        conn.execute("SELECT COUNT(*) AS count FROM advance_payments WHERE advance_id=?", (row["id"],)).fetchone()["count"]
    )
    paid_minor = int(row["amount_minor"]) - int(row["remaining_amount_minor"])
    result: dict[str, Any] = {
        "id": int(row["id"]),
        "person_name": row["person_name"],
        "amount": _minor_to_money(int(row["amount_minor"])),
        "notes": row["notes"],
        "advance_month": row["advance_month"],
        "remaining_amount": _minor_to_money(int(row["remaining_amount_minor"])),
        "paid_amount": _minor_to_money(paid_minor),
        "payment_count": payment_count,
        "status": "paid" if int(row["remaining_amount_minor"]) == 0 else "active",
        "created_by": int(row["created_by"]),
        "created_by_name": row["created_by_name"] if "created_by_name" in row.keys() else None,
        "updated_by": int(row["updated_by"]),
        "updated_by_name": row["updated_by_name"] if "updated_by_name" in row.keys() else None,
        "created_at": row["created_at"],
        "updated_at": row["updated_at"],
    }
    if include_payments:
        payments = conn.execute(
            """
            SELECT p.*, u.full_name AS paid_by_name
            FROM advance_payments p JOIN users u ON u.id=p.paid_by
            WHERE p.advance_id=? ORDER BY p.id DESC
            """,
            (row["id"],),
        ).fetchall()
        result["payments"] = [
            {
                "id": int(item["id"]),
                "amount": _minor_to_money(int(item["amount_minor"])),
                "remaining_amount_after": _minor_to_money(int(item["remaining_amount_minor_after"])),
                "notes": item["notes"],
                "paid_by": int(item["paid_by"]),
                "paid_by_name": item["paid_by_name"],
                "paid_at": item["paid_at"],
            }
            for item in payments
        ]
    return result


ADVANCE_SELECT = """
SELECT a.*, creator.full_name AS created_by_name, updater.full_name AS updated_by_name,
       (SELECT COUNT(*) FROM advance_payments p WHERE p.advance_id=a.id) AS payment_count
FROM advances a
JOIN users creator ON creator.id=a.created_by
JOIN users updater ON updater.id=a.updated_by
"""

def _managed_pages(conn: DBConnection) -> list[dict[str, str]]:
    pages: list[dict[str, str]] = [
        {"key": "dashboard", "name_ar": "الداشبورد", "category": "عام"},
        {"key": "loans", "name_ar": "قروض", "category": "المالية"},
        {"key": "advances", "name_ar": "سلف", "category": "المالية"},
    ]
    rows = conn.execute("SELECT code, name_ar FROM document_types WHERE is_active=1 ORDER BY id").fetchall()
    pages.extend(
        {"key": f"documents.{row['code']}", "name_ar": row["name_ar"], "category": "النماذج"}
        for row in rows
    )
    return pages


def _allowed_page_keys(conn: DBConnection, user_id: int, role: str) -> list[str]:
    if role == "admin":
        return [item["key"] for item in _managed_pages(conn)]
    ensure_user_page_permissions(conn, user_id)
    rows = conn.execute(
        "SELECT page_key FROM user_page_permissions WHERE user_id=? AND can_view=1 ORDER BY page_key",
        (user_id,),
    ).fetchall()
    return [str(row["page_key"]) for row in rows]


def _can_view_page(conn: DBConnection, user: CurrentUser, page_key: str) -> bool:
    if user.role == "admin":
        return True
    ensure_user_page_permissions(conn, user.id)
    row = conn.execute(
        "SELECT can_view FROM user_page_permissions WHERE user_id=? AND page_key=?",
        (user.id, page_key),
    ).fetchone()
    return bool(row and row["can_view"])


def _require_page_access(conn: DBConnection, user: CurrentUser, page_key: str) -> None:
    if not _can_view_page(conn, user, page_key):
        raise HTTPException(status_code=403, detail="ليس لديك صلاحية لعرض هذه الصفحة")


def _document_page_key(type_code: str) -> str:
    return f"documents.{str(type_code).upper()}"


def _allowed_document_codes(conn: DBConnection, user: CurrentUser) -> list[str]:
    rows = conn.execute("SELECT code FROM document_types WHERE is_active=1 ORDER BY id").fetchall()
    codes = [str(row["code"]) for row in rows]
    if user.role == "admin":
        return codes
    return [code for code in codes if _can_view_page(conn, user, _document_page_key(code))]


def _require_document_code_access(conn: DBConnection, user: CurrentUser, type_code: str) -> None:
    _require_page_access(conn, user, _document_page_key(type_code))


def _document_type_code(conn: DBConnection, document_id: int) -> str:
    row = conn.execute(
        "SELECT dt.code FROM documents d JOIN document_types dt ON dt.id=d.document_type_id WHERE d.id=?",
        (document_id,),
    ).fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="المستند غير موجود")
    return str(row["code"])


def _require_document_access(conn: DBConnection, user: CurrentUser, document_id: int) -> str:
    type_code = _document_type_code(conn, document_id)
    _require_document_code_access(conn, user, type_code)
    return type_code


def _require_attachment_access(conn: DBConnection, user: CurrentUser, attachment_id: int) -> Record:
    row = conn.execute(
        """
        SELECT a.*, dt.code AS type_code
        FROM attachments a
        JOIN documents d ON d.id=a.document_id
        JOIN document_types dt ON dt.id=d.document_type_id
        WHERE a.id=?
        """,
        (attachment_id,),
    ).fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="المرفق غير موجود")
    _require_document_code_access(conn, user, str(row["type_code"]))
    return row


def _auth_user_payload(conn: DBConnection, *, user_id: int, full_name: str, username: str, role: str) -> dict[str, Any]:
    return {
        "id": user_id,
        "full_name": full_name,
        "username": username,
        "role": role,
        "page_permissions": _allowed_page_keys(conn, user_id, role),
    }


def _load_type(conn: DBConnection, code: str) -> Record:
    row = conn.execute("SELECT * FROM document_types WHERE code=? AND is_active=1", (code,)).fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="نوع المستند غير موجود")
    return row


def _safe_fields(type_row: Record, fields: dict[str, Any], document_number: str) -> dict[str, Any]:
    config = json.loads(type_row["config_json"])
    allowed = {field["key"]: field for field in config["fields"]}
    clean: dict[str, Any] = {"document_number": document_number}
    for key, value in fields.items():
        if key not in allowed or key == "document_number":
            continue
        field_type = allowed[key].get("type", "text")
        if field_type == "checkbox":
            clean[key] = bool(value)
            continue
        if value is None:
            clean[key] = ""
            continue
        text = str(value)
        if len(text) > 5000:
            raise HTTPException(status_code=422, detail=f"قيمة الحقل {allowed[key]['label_ar']} طويلة جداً")
        clean[key] = text
    return clean


def _attachment_dict(row: Record) -> dict[str, Any]:
    return {
        "id": row["id"],
        "document_id": row["document_id"],
        "original_name": row["original_name"],
        "mime_type": row["mime_type"],
        "size_bytes": row["size_bytes"],
        "sha256": row["sha256"],
        "notes": row["notes"],
        "print_order": row["print_order"],
        "uploaded_by": row["uploaded_by"],
        "uploader_name": row["uploader_name"] if "uploader_name" in row.keys() else None,
        "created_at": row["created_at"],
        "preview_url": f"/api/attachments/{row['id']}/file",
        "download_url": f"/api/attachments/{row['id']}/file?download=1",
    }


def _document_dict(conn: DBConnection, row: Record, include_attachments: bool = False) -> dict[str, Any]:
    type_config = json.loads(row["config_json"])
    fields = json.loads(row["field_values_json"])
    result = {
        "id": row["id"],
        "document_number": row["document_number"],
        "status": row["status"],
        "fields": fields,
        "created_by": row["created_by"],
        "created_by_name": row["created_by_name"],
        "updated_by": row["updated_by"],
        "updated_by_name": row["updated_by_name"],
        "created_at": row["created_at"],
        "updated_at": row["updated_at"],
        "print_count": row["print_count"],
        "revision": row["revision"],
        "type": {
            "id": row["document_type_id"],
            "code": row["type_code"],
            "name_ar": row["type_name_ar"],
            "name_en": row["type_name_en"],
            "image_url": f"/templates/{row['image_filename']}",
            "config": type_config,
        },
        "attachment_count": row["attachment_count"] if "attachment_count" in row.keys() else 0,
    }
    if include_attachments:
        attachments = conn.execute(
            """
            SELECT a.*, u.full_name AS uploader_name
            FROM attachments a JOIN users u ON u.id=a.uploaded_by
            WHERE a.document_id=? ORDER BY a.print_order, a.id
            """,
            (row["id"],),
        ).fetchall()
        result["attachments"] = [_attachment_dict(item) for item in attachments]
    return result


DOCUMENT_SELECT = """
SELECT d.*, dt.code AS type_code, dt.name_ar AS type_name_ar, dt.name_en AS type_name_en,
       dt.image_filename, dt.config_json,
       creator.full_name AS created_by_name, updater.full_name AS updated_by_name,
       (SELECT COUNT(*) FROM attachments a WHERE a.document_id=d.id) AS attachment_count
FROM documents d
JOIN document_types dt ON dt.id=d.document_type_id
JOIN users creator ON creator.id=d.created_by
JOIN users updater ON updater.id=d.updated_by
"""


@app.get("/api/health")
def health():
    return {"ok": True, "version": APP_VERSION, "arabic_rendering": arabic_rendering_status(), "printing": printing_status()}


@app.get("/api/setup/status")
def setup_status():
    conn = connect()
    try:
        count = conn.execute("SELECT COUNT(*) AS count FROM users").fetchone()["count"]
        return {"needs_setup": count == 0}
    finally:
        conn.close()


@app.post("/api/setup/admin", status_code=201)
def setup_admin(payload: SetupAdminRequest):
    conn = connect()
    try:
        with transaction(conn, immediate=True):
            count = conn.execute("SELECT COUNT(*) AS count FROM users").fetchone()["count"]
            if count:
                raise HTTPException(status_code=409, detail="تم إعداد النظام مسبقاً")
            salt, password_hash = hash_password(payload.password)
            now = utc_iso()
            cursor = conn.execute(
                """
                INSERT INTO users(full_name, username, password_salt, password_hash, role, created_at, updated_at)
                VALUES(?,?,?,?, 'admin', ?, ?)
                """,
                (payload.full_name.strip(), payload.username.strip(), salt, password_hash, now, now),
            )
            audit(conn, user_id=cursor.lastrowid, action="system.setup", entity_type="user", entity_id=cursor.lastrowid)
        return {"ok": True}
    finally:
        conn.close()


@app.post("/api/auth/login")
def login(payload: LoginRequest):
    token, user = authenticate(payload.username, payload.password)
    conn = connect()
    try:
        user["page_permissions"] = _allowed_page_keys(conn, int(user["id"]), str(user["role"]))
        return {"token": token, "user": user}
    finally:
        conn.close()


@app.post("/api/auth/change-password")
def change_password(
    payload: ChangePasswordRequest,
    user: Annotated[CurrentUser, Depends(get_current_user)],
):
    conn = connect()
    try:
        row = conn.execute("SELECT password_salt, password_hash FROM users WHERE id=?", (user.id,)).fetchone()
        if not row or not verify_password(payload.current_password, row["password_salt"], row["password_hash"]):
            raise HTTPException(status_code=422, detail="كلمة المرور الحالية غير صحيحة")
        salt, digest = hash_password(payload.new_password)
        now = utc_iso()
        with transaction(conn, immediate=True):
            conn.execute(
                "UPDATE users SET password_salt=?, password_hash=?, must_change_password=0, updated_at=? WHERE id=?",
                (salt, digest, now, user.id),
            )
            conn.execute("DELETE FROM sessions WHERE user_id=?", (user.id,))
            audit(conn, user_id=user.id, action="auth.password_changed", entity_type="user", entity_id=user.id)
        return {"ok": True, "message": "تم تغيير كلمة المرور. يرجى تسجيل الدخول من جديد"}
    finally:
        conn.close()


@app.post("/api/auth/logout")
def logout_endpoint(
    user: Annotated[CurrentUser, Depends(get_current_user)],
    token: Annotated[str, Depends(get_bearer_token)],
):
    logout(token, user.id)
    return {"ok": True}


@app.get("/api/auth/me")
def me(user: Annotated[CurrentUser, Depends(get_current_user)]):
    conn = connect()
    try:
        return _auth_user_payload(
            conn, user_id=user.id, full_name=user.full_name, username=user.username, role=user.role
        )
    finally:
        conn.close()


@app.get("/api/document-types")
def document_types(user: Annotated[CurrentUser, Depends(require("documents.read"))]):
    conn = connect()
    try:
        allowed_codes = _allowed_document_codes(conn, user)
        if not allowed_codes:
            return []
        placeholders = ",".join("?" for _ in allowed_codes)
        rows = conn.execute(
            f"SELECT * FROM document_types WHERE is_active=1 AND code IN ({placeholders}) ORDER BY id",
            allowed_codes,
        ).fetchall()
        return [
            {
                "id": row["id"],
                "code": row["code"],
                "name_ar": row["name_ar"],
                "name_en": row["name_en"],
                "prefix": row["prefix"],
                "image_url": f"/templates/{row['image_filename']}",
                "config": json.loads(row["config_json"]),
            }
            for row in rows
        ]
    finally:
        conn.close()


@app.get("/api/dashboard")
def dashboard(user: Annotated[CurrentUser, Depends(require("documents.read"))]):
    conn = connect()
    try:
        _require_page_access(conn, user, "dashboard")
        allowed_codes = _allowed_document_codes(conn, user)
        today = datetime.now(timezone.utc).date()
        arabic_days = ["الإثنين", "الثلاثاء", "الأربعاء", "الخميس", "الجمعة", "السبت", "الأحد"]

        if allowed_codes:
            placeholders = ",".join("?" for _ in allowed_codes)
            type_rows = conn.execute(
                f"""
                SELECT
                    dt.code,
                    dt.name_ar,
                    COUNT(d.id) AS count,
                    SUM(CASE WHEN d.status='saved' THEN 1 ELSE 0 END) AS saved_count,
                    SUM(CASE WHEN d.status='draft' THEN 1 ELSE 0 END) AS draft_count
                FROM document_types dt
                LEFT JOIN documents d ON d.document_type_id=dt.id
                WHERE dt.is_active=1 AND dt.code IN ({placeholders})
                GROUP BY dt.id, dt.code, dt.name_ar
                ORDER BY dt.id
                """,
                allowed_codes,
            ).fetchall()
            recent = conn.execute(
                DOCUMENT_SELECT + f" WHERE dt.code IN ({placeholders}) ORDER BY d.updated_at DESC LIMIT 8",
                allowed_codes,
            ).fetchall()
            totals = conn.execute(
                f"""
                SELECT
                    COUNT(*) AS total_documents,
                    SUM(CASE WHEN d.status='saved' THEN 1 ELSE 0 END) AS saved_documents,
                    SUM(CASE WHEN d.status='draft' THEN 1 ELSE 0 END) AS draft_documents,
                    COALESCE(SUM(d.print_count),0) AS printed_total
                FROM documents d
                JOIN document_types dt ON dt.id=d.document_type_id
                WHERE dt.code IN ({placeholders})
                """,
                allowed_codes,
            ).fetchone()
            today_count = conn.execute(
                f"""SELECT COUNT(*) AS count FROM documents d
                    JOIN document_types dt ON dt.id=d.document_type_id
                    WHERE dt.code IN ({placeholders}) AND substr(d.created_at,1,10)=?""",
                [*allowed_codes, today.isoformat()],
            ).fetchone()["count"]
            attachment_count = conn.execute(
                f"""SELECT COUNT(*) AS count FROM attachments a
                    JOIN documents d ON d.id=a.document_id
                    JOIN document_types dt ON dt.id=d.document_type_id
                    WHERE dt.code IN ({placeholders})""",
                allowed_codes,
            ).fetchone()["count"]
            activity_rows = conn.execute(
                f"""
                SELECT substr(d.created_at,1,10) AS day, COUNT(*) AS count
                FROM documents d
                JOIN document_types dt ON dt.id=d.document_type_id
                WHERE dt.code IN ({placeholders}) AND substr(d.created_at,1,10) >= ?
                GROUP BY substr(d.created_at,1,10)
                """,
                [*allowed_codes, (today - timedelta(days=6)).isoformat()],
            ).fetchall()
        else:
            type_rows = []
            recent = []
            totals = {"total_documents": 0, "saved_documents": 0, "draft_documents": 0, "printed_total": 0}
            today_count = 0
            attachment_count = 0
            activity_rows = []

        activity_map = {row["day"]: int(row["count"] or 0) for row in activity_rows}
        weekly_activity = []
        for offset in range(6, -1, -1):
            day = today - timedelta(days=offset)
            weekly_activity.append({
                "date": day.isoformat(),
                "label": arabic_days[day.weekday()],
                "count": activity_map.get(day.isoformat(), 0),
            })
        return {
            "total_documents": int(totals["total_documents"] or 0),
            "saved_documents": int(totals["saved_documents"] or 0),
            "draft_documents": int(totals["draft_documents"] or 0),
            "printed_total": int(totals["printed_total"] or 0),
            "today_documents": int(today_count or 0),
            "total_attachments": int(attachment_count or 0),
            "weekly_activity": weekly_activity,
            "types": [
                {
                    "code": row["code"],
                    "name_ar": row["name_ar"],
                    "count": int(row["count"] or 0),
                    "saved_count": int(row["saved_count"] or 0),
                    "draft_count": int(row["draft_count"] or 0),
                }
                for row in type_rows
            ],
            "recent": [_document_dict(conn, row) for row in recent],
        }
    finally:
        conn.close()


@app.get("/api/documents")
def list_documents(
    user: Annotated[CurrentUser, Depends(require("documents.read"))],
    type_code: str | None = Query(default=None, max_length=8),
    q: str | None = Query(default=None, max_length=200),
    status_filter: str | None = Query(default=None, alias="status"),
    limit: int = Query(default=100, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
):
    conn = connect()
    try:
        where: list[str] = []
        params: list[Any] = []
        allowed_codes = _allowed_document_codes(conn, user)
        if type_code:
            normalized_type = type_code.upper()
            _require_document_code_access(conn, user, normalized_type)
            where.append("dt.code=?")
            params.append(normalized_type)
        elif user.role != "admin":
            if not allowed_codes:
                return []
            placeholders = ",".join("?" for _ in allowed_codes)
            where.append(f"dt.code IN ({placeholders})")
            params.extend(allowed_codes)
        if q:
            where.append("(d.document_number LIKE ? OR d.field_values_json LIKE ?)")
            term = f"%{q.strip()}%"
            params.extend([term, term])
        if status_filter in {"draft", "saved"}:
            where.append("d.status=?")
            params.append(status_filter)
        sql = DOCUMENT_SELECT
        if where:
            sql += " WHERE " + " AND ".join(where)
        sql += " ORDER BY d.created_at DESC LIMIT ? OFFSET ?"
        params.extend([limit, offset])
        rows = conn.execute(sql, params).fetchall()
        return [_document_dict(conn, row) for row in rows]
    finally:
        conn.close()


@app.get("/api/reports/documents.csv")
def export_documents_csv(
    user: Annotated[CurrentUser, Depends(require("documents.read"))],
    type_code: str | None = Query(default=None, max_length=8),
    q: str | None = Query(default=None, max_length=200),
    status_filter: str | None = Query(default=None, alias="status"),
):
    """Export a UTF-8 BOM CSV report that opens correctly in Arabic Excel."""
    conn = connect()
    try:
        where: list[str] = []
        params: list[Any] = []
        allowed_codes = _allowed_document_codes(conn, user)
        if type_code:
            normalized_type = type_code.upper()
            _require_document_code_access(conn, user, normalized_type)
            where.append("dt.code=?")
            params.append(normalized_type)
        elif user.role != "admin":
            if not allowed_codes:
                return []
            placeholders = ",".join("?" for _ in allowed_codes)
            where.append(f"dt.code IN ({placeholders})")
            params.extend(allowed_codes)
        if q:
            where.append("(d.document_number LIKE ? OR d.field_values_json LIKE ?)")
            term = f"%{q.strip()}%"
            params.extend([term, term])
        if status_filter in {"draft", "saved"}:
            where.append("d.status=?")
            params.append(status_filter)
        sql = DOCUMENT_SELECT
        if where:
            sql += " WHERE " + " AND ".join(where)
        sql += " ORDER BY d.created_at DESC"
        rows = conn.execute(sql, params).fetchall()
        out = io.StringIO()
        writer = csv.writer(out)
        writer.writerow(["رقم المستند", "نوع المستند", "الحالة", "المنشئ", "تاريخ الإنشاء", "آخر تعديل", "عدد المرفقات", "عدد مرات الطباعة", "البيانات"])
        for row in rows:
            fields = json.loads(row["field_values_json"])
            summary = " | ".join(f"{k}: {v}" for k, v in fields.items() if k != "document_number" and str(v).strip())
            writer.writerow([row["document_number"], row["type_name_ar"], row["status"], row["created_by_name"], row["created_at"], row["updated_at"], row["attachment_count"], row["print_count"], summary])
        payload = "\ufeff" + out.getvalue()
        filename = f"ziad-documents-{utc_iso()[:10]}.csv"
        return StreamingResponse(iter([payload.encode("utf-8")]), media_type="text/csv; charset=utf-8", headers={"Content-Disposition": f'attachment; filename="{filename}"', "Cache-Control": "no-store"})
    finally:
        conn.close()


@app.post("/api/documents", status_code=201)
def create_document(
    payload: DocumentCreateRequest,
    user: Annotated[CurrentUser, Depends(require("documents.create"))],
):
    conn = connect()
    try:
        _require_document_code_access(conn, user, payload.type_code)
        with transaction(conn, immediate=True):
            type_row = _load_type(conn, payload.type_code)
            sequence_sql = "SELECT next_value FROM number_sequences WHERE document_type_id=?"
            if conn.is_postgres:
                sequence_sql += " FOR UPDATE"
            sequence = conn.execute(sequence_sql, (type_row["id"],)).fetchone()
            next_value = int(sequence["next_value"])
            document_number = f"{type_row['prefix']}-{next_value:06d}"
            conn.execute(
                "UPDATE number_sequences SET next_value=? WHERE document_type_id=?",
                (next_value + 1, type_row["id"]),
            )
            fields = _safe_fields(type_row, payload.fields, document_number)
            now = utc_iso()
            fields_json = json.dumps(fields, ensure_ascii=False, separators=(",", ":"))
            cursor = conn.execute(
                """
                INSERT INTO documents(document_type_id, document_number, status, field_values_json,
                                      created_by, updated_by, created_at, updated_at)
                VALUES(?,?,?,?,?,?,?,?)
                """,
                (type_row["id"], document_number, payload.status, fields_json, user.id, user.id, now, now),
            )
            document_id = cursor.lastrowid
            conn.execute(
                "INSERT INTO document_revisions(document_id, revision, field_values_json, changed_by, changed_at) VALUES(?,1,?,?,?)",
                (document_id, fields_json, user.id, now),
            )
            audit(
                conn,
                user_id=user.id,
                action="document.create",
                entity_type="document",
                entity_id=document_id,
                details={"document_number": document_number, "type": payload.type_code},
            )
        row = conn.execute(DOCUMENT_SELECT + " WHERE d.id=?", (document_id,)).fetchone()
        return _document_dict(conn, row, include_attachments=True)
    finally:
        conn.close()


@app.get("/api/documents/{document_id}")
def get_document(
    document_id: int,
    user: Annotated[CurrentUser, Depends(require("documents.read"))],
):
    conn = connect()
    try:
        row = conn.execute(DOCUMENT_SELECT + " WHERE d.id=?", (document_id,)).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="المستند غير موجود")
        _require_document_code_access(conn, user, str(row["type_code"]))
        return _document_dict(conn, row, include_attachments=True)
    finally:
        conn.close()


@app.put("/api/documents/{document_id}")
def update_document(
    document_id: int,
    payload: DocumentUpdateRequest,
    user: Annotated[CurrentUser, Depends(require("documents.update"))],
):
    conn = connect()
    try:
        _require_document_access(conn, user, document_id)
        with transaction(conn, immediate=True):
            row = conn.execute(
                "SELECT d.*, dt.* FROM documents d JOIN document_types dt ON dt.id=d.document_type_id WHERE d.id=?",
                (document_id,),
            ).fetchone()
            if not row:
                raise HTTPException(status_code=404, detail="المستند غير موجود")
            fields = _safe_fields(row, payload.fields, row["document_number"])
            fields_json = json.dumps(fields, ensure_ascii=False, separators=(",", ":"))
            revision = int(row["revision"]) + 1
            now = utc_iso()
            conn.execute(
                "UPDATE documents SET status=?, field_values_json=?, updated_by=?, updated_at=?, revision=? WHERE id=?",
                (payload.status, fields_json, user.id, now, revision, document_id),
            )
            conn.execute(
                "INSERT INTO document_revisions(document_id, revision, field_values_json, changed_by, changed_at) VALUES(?,?,?,?,?)",
                (document_id, revision, fields_json, user.id, now),
            )
            audit(
                conn,
                user_id=user.id,
                action="document.update",
                entity_type="document",
                entity_id=document_id,
                details={"document_number": row["document_number"], "revision": revision},
            )
        updated = conn.execute(DOCUMENT_SELECT + " WHERE d.id=?", (document_id,)).fetchone()
        return _document_dict(conn, updated, include_attachments=True)
    finally:
        conn.close()


@app.delete("/api/documents/{document_id}/permanent")
def delete_document_permanent(
    document_id: int,
    payload: DeleteRequest,
    user: Annotated[CurrentUser, Depends(require("documents.delete"))],
):
    if payload.confirmation.strip() != "حذف نهائي":
        raise HTTPException(status_code=422, detail="اكتب عبارة حذف نهائي للتأكيد")
    conn = connect()
    stored_files: list[str] = []
    try:
        _require_document_access(conn, user, document_id)
        with transaction(conn, immediate=True):
            row = conn.execute("SELECT document_number FROM documents WHERE id=?", (document_id,)).fetchone()
            if not row:
                raise HTTPException(status_code=404, detail="المستند غير موجود")
            stored_files = [item["stored_name"] for item in conn.execute("SELECT stored_name FROM attachments WHERE document_id=?", (document_id,)).fetchall()]
            audit(
                conn,
                user_id=user.id,
                action="document.delete_permanent",
                entity_type="document",
                entity_id=document_id,
                details={"document_number": row["document_number"]},
            )
            conn.execute("DELETE FROM documents WHERE id=?", (document_id,))
        storage_warnings: list[str] = []
        for stored_name in stored_files:
            try:
                storage.delete(stored_name)
            except Exception as exc:
                storage_warnings.append(str(exc))
        return {"ok": True, "storage_warnings": storage_warnings}
    finally:
        conn.close()


@app.get("/api/documents/{document_id}/revisions")
def document_revisions(
    document_id: int,
    user: Annotated[CurrentUser, Depends(require("documents.read"))],
):
    conn = connect()
    try:
        _require_document_access(conn, user, document_id)
        rows = conn.execute(
            """
            SELECT r.*, u.full_name AS changed_by_name
            FROM document_revisions r JOIN users u ON u.id=r.changed_by
            WHERE r.document_id=? ORDER BY r.revision DESC
            """,
            (document_id,),
        ).fetchall()
        return [
            {
                "revision": row["revision"],
                "fields": json.loads(row["field_values_json"]),
                "changed_by": row["changed_by"],
                "changed_by_name": row["changed_by_name"],
                "changed_at": row["changed_at"],
            }
            for row in rows
        ]
    finally:
        conn.close()


def _safe_filename(raw_name: str) -> str:
    name = Path(unquote(raw_name)).name.replace("\x00", "").strip()
    name = re.sub(r"[\r\n\t]", " ", name)
    if not name or name in {".", ".."}:
        name = "attachment.bin"
    return name[:240]


@app.post("/api/documents/{document_id}/attachments", status_code=201)
async def upload_attachment(
    document_id: int,
    request: Request,
    user: Annotated[CurrentUser, Depends(require("attachments.create"))],
    x_file_name: Annotated[str | None, Header()] = None,
    x_file_notes: Annotated[str | None, Header()] = None,
):
    if not x_file_name:
        raise HTTPException(status_code=422, detail="اسم الملف مفقود")
    content_length = request.headers.get("content-length")
    if content_length and int(content_length) > MAX_ATTACHMENT_BYTES:
        raise HTTPException(status_code=413, detail="حجم الملف أكبر من الحد المسموح")

    conn = connect()
    temp_path: Path | None = None
    uploaded_object: str | None = None
    try:
        _require_document_access(conn, user, document_id)
        original_name = _safe_filename(x_file_name)
        suffix = Path(original_name).suffix.lower()[:12]
        stored_name = f"attachments/{document_id}/{uuid4().hex}{suffix}"
        file_descriptor, temp_name = tempfile.mkstemp(prefix="ziad-upload-", suffix=suffix, dir=DATA_DIR)
        os.close(file_descriptor)
        temp_path = Path(temp_name)
        digest = hashlib.sha256()
        size = 0
        with temp_path.open("wb") as handle:
            async for chunk in request.stream():
                size += len(chunk)
                if size > MAX_ATTACHMENT_BYTES:
                    raise HTTPException(status_code=413, detail="حجم الملف أكبر من الحد المسموح")
                digest.update(chunk)
                handle.write(chunk)
        if size == 0:
            raise HTTPException(status_code=422, detail="الملف فارغ")

        mime_type = request.headers.get("content-type") or mimetypes.guess_type(original_name)[0] or "application/octet-stream"
        storage.put_file(stored_name, temp_path, mime_type)
        uploaded_object = stored_name
        now = utc_iso()
        with transaction(conn, immediate=True):
            order = conn.execute(
                "SELECT COALESCE(MAX(print_order), -1) + 1 AS next_order FROM attachments WHERE document_id=?",
                (document_id,),
            ).fetchone()["next_order"]
            cursor = conn.execute(
                """
                INSERT INTO attachments(document_id, original_name, stored_name, mime_type, size_bytes, sha256,
                                        notes, print_order, uploaded_by, created_at)
                VALUES(?,?,?,?,?,?,?,?,?,?)
                """,
                (
                    document_id,
                    original_name,
                    stored_name,
                    mime_type,
                    size,
                    digest.hexdigest(),
                    (x_file_notes or "")[:1000],
                    order,
                    user.id,
                    now,
                ),
            )
            attachment_id = cursor.lastrowid
            audit(
                conn,
                user_id=user.id,
                action="attachment.upload",
                entity_type="attachment",
                entity_id=attachment_id,
                details={"document_id": document_id, "name": original_name, "size": size},
            )
        row = conn.execute(
            "SELECT a.*, u.full_name AS uploader_name FROM attachments a JOIN users u ON u.id=a.uploaded_by WHERE a.id=?",
            (attachment_id,),
        ).fetchone()
        return _attachment_dict(row)
    except StorageError as exc:
        raise HTTPException(status_code=502, detail=f"تعذر حفظ المرفق في التخزين السحابي: {exc}") from exc
    except Exception:
        if uploaded_object:
            try:
                storage.delete(uploaded_object)
            except Exception:
                pass
        raise
    finally:
        if temp_path:
            temp_path.unlink(missing_ok=True)
        conn.close()


@app.put("/api/attachments/{attachment_id}")
def update_attachment(
    attachment_id: int,
    payload: AttachmentNotesRequest,
    user: Annotated[CurrentUser, Depends(require("attachments.create"))],
):
    conn = connect()
    try:
        with transaction(conn, immediate=True):
            row = _require_attachment_access(conn, user, attachment_id)
            conn.execute(
                "UPDATE attachments SET notes=?, print_order=? WHERE id=?",
                (payload.notes.strip(), payload.print_order, attachment_id),
            )
            audit(conn, user_id=user.id, action="attachment.update", entity_type="attachment", entity_id=attachment_id)
        return {"ok": True}
    finally:
        conn.close()


@app.get("/api/attachments/{attachment_id}/file")
def attachment_file(
    attachment_id: int,
    user: Annotated[CurrentUser, Depends(require("documents.read"))],
    download: bool = False,
):
    conn = connect()
    try:
        row = _require_attachment_access(conn, user, attachment_id)
        suffix = Path(row["original_name"]).suffix[:12]
        temp_path = GENERATED_DIR / f"download-{attachment_id}-{uuid4().hex}{suffix}"
        try:
            storage.download_to(row["stored_name"], temp_path)
        except FileNotFoundError as exc:
            raise HTTPException(status_code=410, detail="ملف المرفق غير موجود في التخزين") from exc
        except StorageError as exc:
            raise HTTPException(status_code=502, detail=f"تعذر قراءة المرفق من التخزين: {exc}") from exc
        disposition = "attachment" if download else "inline"
        encoded = quote(row["original_name"])
        headers = {"Content-Disposition": f"{disposition}; filename*=UTF-8''{encoded}"}
        return FileResponse(
            temp_path,
            media_type=row["mime_type"],
            headers=headers,
            background=BackgroundTask(temp_path.unlink, missing_ok=True),
        )
    finally:
        conn.close()


@app.delete("/api/attachments/{attachment_id}")
def delete_attachment(
    attachment_id: int,
    user: Annotated[CurrentUser, Depends(require("attachments.delete"))],
):
    conn = connect()
    stored_name: str | None = None
    try:
        with transaction(conn, immediate=True):
            row = _require_attachment_access(conn, user, attachment_id)
            stored_name = row["stored_name"]
            audit(
                conn,
                user_id=user.id,
                action="attachment.delete",
                entity_type="attachment",
                entity_id=attachment_id,
                details={"document_id": row["document_id"], "name": row["original_name"]},
            )
            conn.execute("DELETE FROM attachments WHERE id=?", (attachment_id,))
        storage_warning = None
        if stored_name:
            try:
                storage.delete(stored_name)
            except Exception as exc:
                storage_warning = str(exc)
        return {"ok": True, "storage_warning": storage_warning}
    finally:
        conn.close()


@app.post("/api/documents/{document_id}/print")
def print_document(
    document_id: int,
    payload: PrintRequest,
    user: Annotated[CurrentUser, Depends(require("documents.print"))],
):
    conn = connect()
    try:
        row = conn.execute(DOCUMENT_SELECT + " WHERE d.id=?", (document_id,)).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="المستند غير موجود")
        _require_document_code_access(conn, user, str(row["type_code"]))
        selected: list[Record] = []
        if payload.attachment_ids:
            placeholders = ",".join("?" for _ in payload.attachment_ids)
            selected = conn.execute(
                f"SELECT * FROM attachments WHERE document_id=? AND id IN ({placeholders}) ORDER BY print_order, id",
                [document_id, *payload.attachment_ids],
            ).fetchall()
            found_ids = {item["id"] for item in selected}
            if found_ids != set(payload.attachment_ids):
                raise HTTPException(status_code=422, detail="بعض المرفقات المحددة لا تتبع هذا المستند")
        template = json.loads(row["config_json"])
        values = json.loads(row["field_values_json"])
        with tempfile.TemporaryDirectory(prefix="ziad-print-", dir=DATA_DIR) as temp_dir:
            prepared_attachments: list[dict[str, Any]] = []
            for item in selected:
                suffix = Path(item["original_name"]).suffix[:12]
                local_path = Path(temp_dir) / f"{item['id']}{suffix}"
                try:
                    storage.download_to(item["stored_name"], local_path)
                except FileNotFoundError as exc:
                    raise HTTPException(status_code=410, detail=f"المرفق {item['original_name']} غير موجود في التخزين") from exc
                except StorageError as exc:
                    raise HTTPException(status_code=502, detail=f"تعذر تجهيز المرفقات للطباعة: {exc}") from exc
                attachment_data = dict(item)
                attachment_data["local_path"] = str(local_path)
                prepared_attachments.append(attachment_data)
            try:
                pdf_path = build_print_bundle(
                    document_id=document_id,
                    revision=row["revision"],
                    template=template,
                    values=values,
                    attachments=prepared_attachments,
                )
            except Exception as exc:
                logger.exception(
                    "Document print failed: id=%s number=%s type=%s",
                    document_id,
                    row["document_number"],
                    row["type_code"],
                )
                raise HTTPException(
                    status_code=503,
                    detail="تعذر تجهيز ملف الطباعة على الخادم. تم تشغيل مسار الطباعة الاحتياطي أيضاً ولم ينجح. حاول مرة أخرى، وإذا استمر الخطأ راجع سجل Render للطباعة.",
                ) from exc
        with transaction(conn, immediate=True):
            conn.execute("UPDATE documents SET print_count=print_count+1 WHERE id=?", (document_id,))
            audit(
                conn,
                user_id=user.id,
                action="document.print_export",
                entity_type="document",
                entity_id=document_id,
                details={"document_number": row["document_number"], "attachment_ids": payload.attachment_ids},
            )
        filename = f"{row['document_number']}.pdf"
        headers = {"Content-Disposition": f"inline; filename={filename}"}
        return FileResponse(pdf_path, media_type="application/pdf", filename=filename, headers=headers)
    finally:
        conn.close()



@app.get("/api/loans")
def list_loans(
    user: Annotated[CurrentUser, Depends(require("documents.read"))],
    q: str = Query(default="", max_length=160),
    status: str | None = Query(default=None, pattern=r"^(active|paid)$"),
):
    conn = connect()
    try:
        _loan_page_access(conn, user)
        where: list[str] = []
        params: list[Any] = []
        if q.strip():
            where.append("l.borrower_name LIKE ?")
            params.append(f"%{q.strip()}%")
        if status == "active":
            where.append("l.remaining_amount_minor > 0")
        elif status == "paid":
            where.append("l.remaining_amount_minor = 0")
        sql = LOAN_SELECT
        if where:
            sql += " WHERE " + " AND ".join(where)
        sql += " ORDER BY l.updated_at DESC, l.id DESC"
        rows = conn.execute(sql, params).fetchall()
        return [_loan_dict(conn, row) for row in rows]
    finally:
        conn.close()


@app.post("/api/loans", status_code=201)
def create_loan(
    payload: LoanCreateRequest,
    user: Annotated[CurrentUser, Depends(require("documents.create"))],
):
    conn = connect()
    try:
        _loan_page_access(conn, user)
        principal = _money_to_minor(payload.principal_amount)
        minimum = _money_to_minor(payload.minimum_payment)
        if minimum > principal:
            raise HTTPException(status_code=422, detail="الحد الأدنى للتسديد لا يمكن أن يكون أكبر من مبلغ القرض")
        now = utc_iso()
        with transaction(conn, immediate=True):
            cursor = conn.execute(
                """
                INSERT INTO loans(borrower_name, principal_amount_minor, months_total, minimum_payment_minor,
                                  remaining_amount_minor, created_by, updated_by, created_at, updated_at)
                VALUES(?,?,?,?,?,?,?,?,?)
                """,
                (payload.borrower_name, principal, payload.months_total, minimum, principal, user.id, user.id, now, now),
            )
            loan_id = int(cursor.lastrowid)
            audit(
                conn,
                user_id=user.id,
                action="loan.create",
                entity_type="loan",
                entity_id=loan_id,
                details={"borrower_name": payload.borrower_name, "principal_amount": _minor_to_money(principal)},
            )
        row = conn.execute(LOAN_SELECT + " WHERE l.id=?", (loan_id,)).fetchone()
        return _loan_dict(conn, row, include_payments=True)
    finally:
        conn.close()


@app.get("/api/loans/{loan_id}")
def get_loan(
    loan_id: int,
    user: Annotated[CurrentUser, Depends(require("documents.read"))],
):
    conn = connect()
    try:
        _loan_page_access(conn, user)
        row = conn.execute(LOAN_SELECT + " WHERE l.id=?", (loan_id,)).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="القرض غير موجود")
        return _loan_dict(conn, row, include_payments=True)
    finally:
        conn.close()


@app.put("/api/loans/{loan_id}")
def update_loan(
    loan_id: int,
    payload: LoanUpdateRequest,
    user: Annotated[CurrentUser, Depends(require("documents.update"))],
):
    conn = connect()
    try:
        _loan_page_access(conn, user)
        principal = _money_to_minor(payload.principal_amount)
        minimum = _money_to_minor(payload.minimum_payment)
        with transaction(conn, immediate=True):
            lock_sql = "SELECT * FROM loans WHERE id=?" + (" FOR UPDATE" if conn.is_postgres else "")
            current = conn.execute(lock_sql, (loan_id,)).fetchone()
            if not current:
                raise HTTPException(status_code=404, detail="القرض غير موجود")
            payment_stats = conn.execute(
                "SELECT COUNT(*) AS count, COALESCE(SUM(amount_minor),0) AS paid FROM loan_payments WHERE loan_id=?",
                (loan_id,),
            ).fetchone()
            payment_count = int(payment_stats["count"] or 0)
            paid_minor = int(payment_stats["paid"] or 0)
            if principal < paid_minor:
                raise HTTPException(status_code=422, detail="مبلغ القرض الجديد لا يمكن أن يكون أقل من المبلغ المسدد")
            if payload.months_total < payment_count and principal > paid_minor:
                raise HTTPException(status_code=422, detail="عدد أشهر التسديد لا يمكن أن يكون أقل من عدد عمليات التسديد المنفذة")
            remaining = principal - paid_minor
            if remaining > 0 and minimum > principal:
                raise HTTPException(status_code=422, detail="الحد الأدنى للتسديد لا يمكن أن يكون أكبر من مبلغ القرض")
            now = utc_iso()
            conn.execute(
                """
                UPDATE loans SET borrower_name=?, principal_amount_minor=?, months_total=?, minimum_payment_minor=?,
                                 remaining_amount_minor=?, updated_by=?, updated_at=? WHERE id=?
                """,
                (payload.borrower_name, principal, payload.months_total, minimum, remaining, user.id, now, loan_id),
            )
            audit(
                conn,
                user_id=user.id,
                action="loan.update",
                entity_type="loan",
                entity_id=loan_id,
                details={"borrower_name": payload.borrower_name, "principal_amount": _minor_to_money(principal)},
            )
        row = conn.execute(LOAN_SELECT + " WHERE l.id=?", (loan_id,)).fetchone()
        return _loan_dict(conn, row, include_payments=True)
    finally:
        conn.close()


@app.post("/api/loans/{loan_id}/payments", status_code=201)
def create_loan_payment(
    loan_id: int,
    payload: LoanPaymentCreateRequest,
    user: Annotated[CurrentUser, Depends(require("documents.update"))],
):
    conn = connect()
    try:
        _loan_page_access(conn, user)
        amount = _money_to_minor(payload.amount)
        with transaction(conn, immediate=True):
            lock_sql = "SELECT * FROM loans WHERE id=?" + (" FOR UPDATE" if conn.is_postgres else "")
            loan = conn.execute(lock_sql, (loan_id,)).fetchone()
            if not loan:
                raise HTTPException(status_code=404, detail="القرض غير موجود")
            remaining = int(loan["remaining_amount_minor"])
            if remaining <= 0:
                raise HTTPException(status_code=409, detail="تم تسديد هذا القرض بالكامل")
            if amount > remaining:
                raise HTTPException(status_code=422, detail="مبلغ التسديد أكبر من المبلغ المتبقي")
            minimum = int(loan["minimum_payment_minor"])
            # The final payment may equal the exact remaining balance even when that balance is below the configured minimum.
            if amount < minimum and amount != remaining:
                raise HTTPException(
                    status_code=422,
                    detail=f"لا يمكن تسديد مبلغ أقل من الحد الأدنى {_minor_to_money(minimum)}",
                )
            payment_count = int(conn.execute("SELECT COUNT(*) AS count FROM loan_payments WHERE loan_id=?", (loan_id,)).fetchone()["count"])
            remaining_after = remaining - amount
            months_remaining_after = 0 if remaining_after == 0 else max(int(loan["months_total"]) - (payment_count + 1), 0)
            now = utc_iso()
            cursor = conn.execute(
                """
                INSERT INTO loan_payments(loan_id, amount_minor, remaining_amount_minor_after,
                                          months_remaining_after, notes, paid_by, paid_at)
                VALUES(?,?,?,?,?,?,?)
                """,
                (loan_id, amount, remaining_after, months_remaining_after, payload.notes.strip(), user.id, now),
            )
            conn.execute(
                "UPDATE loans SET remaining_amount_minor=?, updated_by=?, updated_at=? WHERE id=?",
                (remaining_after, user.id, now, loan_id),
            )
            audit(
                conn,
                user_id=user.id,
                action="loan.payment",
                entity_type="loan",
                entity_id=loan_id,
                details={
                    "payment_id": int(cursor.lastrowid),
                    "amount": _minor_to_money(amount),
                    "remaining_amount": _minor_to_money(remaining_after),
                    "remaining_months": months_remaining_after,
                },
            )
        row = conn.execute(LOAN_SELECT + " WHERE l.id=?", (loan_id,)).fetchone()
        return _loan_dict(conn, row, include_payments=True)
    finally:
        conn.close()


@app.delete("/api/loans/{loan_id}/permanent")
def delete_loan_permanent(
    loan_id: int,
    payload: DeleteRequest,
    user: Annotated[CurrentUser, Depends(require("documents.delete"))],
):
    if payload.confirmation.strip() != "حذف نهائي":
        raise HTTPException(status_code=422, detail="اكتب عبارة حذف نهائي للتأكيد")
    conn = connect()
    try:
        _loan_page_access(conn, user)
        with transaction(conn, immediate=True):
            row = conn.execute("SELECT * FROM loans WHERE id=?", (loan_id,)).fetchone()
            if not row:
                raise HTTPException(status_code=404, detail="القرض غير موجود")
            audit(
                conn,
                user_id=user.id,
                action="loan.delete_permanent",
                entity_type="loan",
                entity_id=loan_id,
                details={"borrower_name": row["borrower_name"]},
            )
            conn.execute("DELETE FROM loans WHERE id=?", (loan_id,))
        return {"ok": True}
    finally:
        conn.close()


@app.get("/api/advances")
def list_advances(
    user: Annotated[CurrentUser, Depends(require("documents.read"))],
    q: str = Query(default="", max_length=160),
    status: str | None = Query(default=None, pattern=r"^(active|paid)$"),
):
    conn = connect()
    try:
        _advance_page_access(conn, user)
        where: list[str] = []
        params: list[Any] = []
        if q.strip():
            where.append("(a.person_name LIKE ? OR a.notes LIKE ? OR a.advance_month LIKE ?)")
            term = f"%{q.strip()}%"
            params.extend([term, term, term])
        if status == "active":
            where.append("a.remaining_amount_minor > 0")
        elif status == "paid":
            where.append("a.remaining_amount_minor = 0")
        sql = ADVANCE_SELECT
        if where:
            sql += " WHERE " + " AND ".join(where)
        sql += " ORDER BY a.advance_month DESC, a.updated_at DESC, a.id DESC"
        rows = conn.execute(sql, params).fetchall()
        return [_advance_dict(conn, row) for row in rows]
    finally:
        conn.close()


@app.post("/api/advances", status_code=201)
def create_advance(
    payload: AdvanceCreateRequest,
    user: Annotated[CurrentUser, Depends(require("documents.create"))],
):
    conn = connect()
    try:
        _advance_page_access(conn, user)
        amount = _money_to_minor(payload.amount)
        now = utc_iso()
        with transaction(conn, immediate=True):
            cursor = conn.execute(
                """
                INSERT INTO advances(person_name, amount_minor, notes, advance_month, remaining_amount_minor,
                                     created_by, updated_by, created_at, updated_at)
                VALUES(?,?,?,?,?,?,?,?,?)
                """,
                (payload.person_name, amount, payload.notes.strip(), payload.advance_month, amount, user.id, user.id, now, now),
            )
            advance_id = int(cursor.lastrowid)
            audit(
                conn,
                user_id=user.id,
                action="advance.create",
                entity_type="advance",
                entity_id=advance_id,
                details={"person_name": payload.person_name, "amount": _minor_to_money(amount), "month": payload.advance_month},
            )
        row = conn.execute(ADVANCE_SELECT + " WHERE a.id=?", (advance_id,)).fetchone()
        return _advance_dict(conn, row, include_payments=True)
    finally:
        conn.close()


@app.get("/api/advances/{advance_id}")
def get_advance(
    advance_id: int,
    user: Annotated[CurrentUser, Depends(require("documents.read"))],
):
    conn = connect()
    try:
        _advance_page_access(conn, user)
        row = conn.execute(ADVANCE_SELECT + " WHERE a.id=?", (advance_id,)).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="السلفة غير موجودة")
        return _advance_dict(conn, row, include_payments=True)
    finally:
        conn.close()


@app.put("/api/advances/{advance_id}")
def update_advance(
    advance_id: int,
    payload: AdvanceUpdateRequest,
    user: Annotated[CurrentUser, Depends(require("documents.update"))],
):
    conn = connect()
    try:
        _advance_page_access(conn, user)
        amount = _money_to_minor(payload.amount)
        with transaction(conn, immediate=True):
            lock_sql = "SELECT * FROM advances WHERE id=?" + (" FOR UPDATE" if conn.is_postgres else "")
            current = conn.execute(lock_sql, (advance_id,)).fetchone()
            if not current:
                raise HTTPException(status_code=404, detail="السلفة غير موجودة")
            payment_stats = conn.execute(
                "SELECT COALESCE(SUM(amount_minor),0) AS paid FROM advance_payments WHERE advance_id=?",
                (advance_id,),
            ).fetchone()
            paid_minor = int(payment_stats["paid"] or 0)
            if amount < paid_minor:
                raise HTTPException(status_code=422, detail="مبلغ السلفة الجديد لا يمكن أن يكون أقل من المبلغ المسدد")
            remaining = amount - paid_minor
            now = utc_iso()
            conn.execute(
                """
                UPDATE advances SET person_name=?, amount_minor=?, notes=?, advance_month=?,
                                    remaining_amount_minor=?, updated_by=?, updated_at=? WHERE id=?
                """,
                (payload.person_name, amount, payload.notes.strip(), payload.advance_month, remaining, user.id, now, advance_id),
            )
            audit(
                conn,
                user_id=user.id,
                action="advance.update",
                entity_type="advance",
                entity_id=advance_id,
                details={"person_name": payload.person_name, "amount": _minor_to_money(amount), "month": payload.advance_month},
            )
        row = conn.execute(ADVANCE_SELECT + " WHERE a.id=?", (advance_id,)).fetchone()
        return _advance_dict(conn, row, include_payments=True)
    finally:
        conn.close()


@app.post("/api/advances/{advance_id}/payments", status_code=201)
def create_advance_payment(
    advance_id: int,
    payload: AdvancePaymentCreateRequest,
    user: Annotated[CurrentUser, Depends(require("documents.update"))],
):
    conn = connect()
    try:
        _advance_page_access(conn, user)
        amount = _money_to_minor(payload.amount)
        with transaction(conn, immediate=True):
            lock_sql = "SELECT * FROM advances WHERE id=?" + (" FOR UPDATE" if conn.is_postgres else "")
            advance = conn.execute(lock_sql, (advance_id,)).fetchone()
            if not advance:
                raise HTTPException(status_code=404, detail="السلفة غير موجودة")
            remaining = int(advance["remaining_amount_minor"])
            if remaining <= 0:
                raise HTTPException(status_code=409, detail="تم تسديد هذه السلفة بالكامل")
            if amount > remaining:
                raise HTTPException(status_code=422, detail="مبلغ التسديد أكبر من المبلغ المتبقي")
            remaining_after = remaining - amount
            now = utc_iso()
            conn.execute(
                """
                INSERT INTO advance_payments(advance_id, amount_minor, remaining_amount_minor_after, notes, paid_by, paid_at)
                VALUES(?,?,?,?,?,?)
                """,
                (advance_id, amount, remaining_after, payload.notes.strip(), user.id, now),
            )
            conn.execute(
                "UPDATE advances SET remaining_amount_minor=?, updated_by=?, updated_at=? WHERE id=?",
                (remaining_after, user.id, now, advance_id),
            )
            audit(
                conn,
                user_id=user.id,
                action="advance.payment",
                entity_type="advance",
                entity_id=advance_id,
                details={"amount": _minor_to_money(amount), "remaining": _minor_to_money(remaining_after)},
            )
        row = conn.execute(ADVANCE_SELECT + " WHERE a.id=?", (advance_id,)).fetchone()
        return _advance_dict(conn, row, include_payments=True)
    finally:
        conn.close()


@app.delete("/api/advances/{advance_id}/permanent")
def delete_advance_permanent(
    advance_id: int,
    payload: DeleteRequest,
    user: Annotated[CurrentUser, Depends(require("documents.delete"))],
):
    if payload.confirmation.strip() != "حذف نهائي":
        raise HTTPException(status_code=422, detail="عبارة التأكيد غير صحيحة")
    conn = connect()
    try:
        _advance_page_access(conn, user)
        with transaction(conn, immediate=True):
            row = conn.execute("SELECT * FROM advances WHERE id=?", (advance_id,)).fetchone()
            if not row:
                raise HTTPException(status_code=404, detail="السلفة غير موجودة")
            audit(
                conn,
                user_id=user.id,
                action="advance.delete_permanent",
                entity_type="advance",
                entity_id=advance_id,
                details={"person_name": row["person_name"], "amount": _minor_to_money(int(row["amount_minor"]))},
            )
            conn.execute("DELETE FROM advances WHERE id=?", (advance_id,))
        return {"ok": True}
    finally:
        conn.close()


@app.get("/api/users")
def list_users(_: Annotated[CurrentUser, Depends(require("users.manage"))]):
    conn = connect()
    try:
        rows = conn.execute("SELECT * FROM users ORDER BY created_at DESC").fetchall()
        return [_user_dict(row) for row in rows]
    finally:
        conn.close()


@app.post("/api/users", status_code=201)
def create_user(
    payload: UserCreateRequest,
    current: Annotated[CurrentUser, Depends(require("users.manage"))],
):
    conn = connect()
    try:
        salt, password_hash = hash_password(payload.password)
        now = utc_iso()
        with transaction(conn, immediate=True):
            cursor = conn.execute(
                """
                INSERT INTO users(full_name, username, password_salt, password_hash, role, created_at, updated_at)
                VALUES(?,?,?,?,?,?,?)
                """,
                (payload.full_name.strip(), payload.username.strip(), salt, password_hash, payload.role, now, now),
            )
            ensure_user_page_permissions(conn, int(cursor.lastrowid))
            audit(
                conn,
                user_id=current.id,
                action="user.create",
                entity_type="user",
                entity_id=cursor.lastrowid,
                details={"username": payload.username.strip(), "role": payload.role},
            )
        row = conn.execute("SELECT * FROM users WHERE id=?", (cursor.lastrowid,)).fetchone()
        return _user_dict(row)
    finally:
        conn.close()


@app.put("/api/users/{user_id}")
def update_user(
    user_id: int,
    payload: UserUpdateRequest,
    current: Annotated[CurrentUser, Depends(require("users.manage"))],
):
    conn = connect()
    try:
        with transaction(conn, immediate=True):
            row = conn.execute("SELECT * FROM users WHERE id=?", (user_id,)).fetchone()
            if not row:
                raise HTTPException(status_code=404, detail="المستخدم غير موجود")
            if row["role"] == "admin" and (payload.role != "admin" or not payload.is_active):
                admin_count = conn.execute("SELECT COUNT(*) AS count FROM users WHERE role='admin' AND is_active=1").fetchone()["count"]
                if admin_count <= 1:
                    raise HTTPException(status_code=409, detail="لا يمكن تعطيل أو تغيير صلاحية آخر مدير فعال")
            now = utc_iso()
            if payload.password:
                salt, password_hash = hash_password(payload.password)
                conn.execute(
                    "UPDATE users SET full_name=?, role=?, is_active=?, password_salt=?, password_hash=?, updated_at=? WHERE id=?",
                    (payload.full_name.strip(), payload.role, int(payload.is_active), salt, password_hash, now, user_id),
                )
                conn.execute("DELETE FROM sessions WHERE user_id=?", (user_id,))
            else:
                conn.execute(
                    "UPDATE users SET full_name=?, role=?, is_active=?, updated_at=? WHERE id=?",
                    (payload.full_name.strip(), payload.role, int(payload.is_active), now, user_id),
                )
                if not payload.is_active:
                    conn.execute("DELETE FROM sessions WHERE user_id=?", (user_id,))
            ensure_user_page_permissions(conn, user_id)
            audit(
                conn,
                user_id=current.id,
                action="user.update",
                entity_type="user",
                entity_id=user_id,
                details={"role": payload.role, "is_active": payload.is_active, "password_changed": bool(payload.password)},
            )
        updated = conn.execute("SELECT * FROM users WHERE id=?", (user_id,)).fetchone()
        return _user_dict(updated)
    finally:
        conn.close()


@app.get("/api/permissions")
def permissions_matrix(_: Annotated[CurrentUser, Depends(require("users.manage"))]):
    conn = connect()
    try:
        pages = _managed_pages(conn)
        page_keys = [item["key"] for item in pages]
        users = conn.execute("SELECT * FROM users ORDER BY created_at DESC").fetchall()
        result_users = []
        for row in users:
            if row["role"] == "admin":
                allowed = list(page_keys)
            else:
                ensure_user_page_permissions(conn, int(row["id"]))
                allowed = _allowed_page_keys(conn, int(row["id"]), str(row["role"]))
            item = _user_dict(row)
            item["page_permissions"] = allowed
            result_users.append(item)
        return {"pages": pages, "users": result_users}
    finally:
        conn.close()


@app.put("/api/permissions/users/{user_id}")
def update_page_permissions(
    user_id: int,
    payload: PagePermissionsUpdateRequest,
    current: Annotated[CurrentUser, Depends(require("users.manage"))],
):
    conn = connect()
    try:
        with transaction(conn, immediate=True):
            target = conn.execute("SELECT * FROM users WHERE id=?", (user_id,)).fetchone()
            if not target:
                raise HTTPException(status_code=404, detail="المستخدم غير موجود")
            if target["role"] == "admin":
                raise HTTPException(status_code=422, detail="مدير النظام يمتلك جميع الصفحات تلقائياً")
            pages = _managed_pages(conn)
            valid_keys = {item["key"] for item in pages}
            requested = set(payload.page_keys)
            unknown = requested - valid_keys
            if unknown:
                raise HTTPException(status_code=422, detail="توجد صفحة غير معروفة ضمن الصلاحيات المطلوبة")
            ensure_user_page_permissions(conn, user_id)
            now = utc_iso()
            for page_key in valid_keys:
                conn.execute(
                    """
                    INSERT INTO user_page_permissions(user_id, page_key, can_view, updated_at, updated_by)
                    VALUES(?,?,?,?,?)
                    ON CONFLICT(user_id,page_key) DO UPDATE SET
                        can_view=excluded.can_view, updated_at=excluded.updated_at, updated_by=excluded.updated_by
                    """,
                    (user_id, page_key, int(page_key in requested), now, current.id),
                )
            audit(
                conn,
                user_id=current.id,
                action="permission.update",
                entity_type="user",
                entity_id=user_id,
                details={"page_keys": sorted(requested)},
            )
        return {"ok": True, "user_id": user_id, "page_permissions": sorted(requested)}
    finally:
        conn.close()


@app.get("/api/audit")
def audit_log(
    _: Annotated[CurrentUser, Depends(require("audit.read"))],
    limit: int = Query(default=100, ge=1, le=500),
):
    conn = connect()
    try:
        rows = conn.execute(
            """
            SELECT a.*, u.full_name AS user_name
            FROM audit_logs a LEFT JOIN users u ON u.id=a.user_id
            ORDER BY a.created_at DESC LIMIT ?
            """,
            (limit,),
        ).fetchall()
        return [
            {
                "id": row["id"],
                "user_id": row["user_id"],
                "user_name": row["user_name"],
                "action": row["action"],
                "entity_type": row["entity_type"],
                "entity_id": row["entity_id"],
                "details": json.loads(row["details_json"]),
                "created_at": row["created_at"],
            }
            for row in rows
        ]
    finally:
        conn.close()


@app.get("/api/system/status")
def system_status(_: Annotated[CurrentUser, Depends(require("system.manage"))]):
    conn = connect()
    try:
        counts = {
            "users": conn.execute("SELECT COUNT(*) FROM users").fetchone()[0],
            "documents": conn.execute("SELECT COUNT(*) FROM documents").fetchone()[0],
            "attachments": conn.execute("SELECT COUNT(*) FROM attachments").fetchone()[0],
            "loans": conn.execute("SELECT COUNT(*) FROM loans").fetchone()[0],
            "loan_payments": conn.execute("SELECT COUNT(*) FROM loan_payments").fetchone()[0],
        }
        attachment_bytes = conn.execute("SELECT COALESCE(SUM(size_bytes),0) FROM attachments").fetchone()[0]
    finally:
        conn.close()
    return {
        "version": APP_VERSION,
        "database": database_integrity(),
        "storage": storage.status(),
        "arabic_rendering": arabic_rendering_status(),
        "printing": printing_status(),
        "templates": template_integrity(),
        "counts": counts,
        "attachment_bytes": attachment_bytes,
    }


@app.post("/api/system/backup")
def download_backup(current: Annotated[CurrentUser, Depends(require("system.manage"))]):
    backup_path = create_backup()
    conn = connect()
    try:
        audit(
            conn,
            user_id=current.id,
            action="system.backup",
            entity_type="system",
            details={"filename": backup_path.name, "size_bytes": backup_path.stat().st_size},
        )
    finally:
        conn.close()
    return FileResponse(
        backup_path,
        media_type="application/zip",
        filename=backup_path.name,
        headers={"Cache-Control": "no-store"},
    )


# Static application is mounted last so every /api route has priority.
app.mount("/", StaticFiles(directory=STATIC_DIR, html=True), name="static")
