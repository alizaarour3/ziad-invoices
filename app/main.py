from __future__ import annotations

import hashlib
import csv
import io
import json
import mimetypes
import os
import re
import sqlite3
import tempfile
from datetime import datetime, timedelta, timezone
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
from .db import DBConnection, Record, audit, connect, init_db, transaction
from .schemas import (
    AttachmentNotesRequest,
    ChangePasswordRequest,
    DeleteRequest,
    DocumentCreateRequest,
    DocumentUpdateRequest,
    LoginRequest,
    PrintRequest,
    SetupAdminRequest,
    UserCreateRequest,
    UserUpdateRequest,
)
from .security import hash_password, utc_iso, verify_password
from .services.pdf_service import build_print_bundle
from .services.backup_service import APP_VERSION, create_backup, database_integrity, template_integrity
from .services.storage_service import StorageError, storage
from .settings import DATA_DIR, GENERATED_DIR, MAX_ATTACHMENT_BYTES, STATIC_DIR

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
    return {"ok": True, "version": APP_VERSION}


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
    return {"token": token, "user": user}


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
    return {"id": user.id, "full_name": user.full_name, "username": user.username, "role": user.role}


@app.get("/api/document-types")
def document_types(_: Annotated[CurrentUser, Depends(require("documents.read"))]):
    conn = connect()
    try:
        rows = conn.execute("SELECT * FROM document_types WHERE is_active=1 ORDER BY id").fetchall()
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
def dashboard(_: Annotated[CurrentUser, Depends(require("documents.read"))]):
    conn = connect()
    try:
        type_rows = conn.execute(
            """
            SELECT
                dt.code,
                dt.name_ar,
                COUNT(d.id) AS count,
                SUM(CASE WHEN d.status='saved' THEN 1 ELSE 0 END) AS saved_count,
                SUM(CASE WHEN d.status='draft' THEN 1 ELSE 0 END) AS draft_count
            FROM document_types dt
            LEFT JOIN documents d ON d.document_type_id=dt.id
            WHERE dt.is_active=1
            GROUP BY dt.id, dt.code, dt.name_ar
            ORDER BY dt.id
            """
        ).fetchall()
        recent = conn.execute(DOCUMENT_SELECT + " ORDER BY d.updated_at DESC LIMIT 8").fetchall()
        today = datetime.now(timezone.utc).date()
        totals = conn.execute(
            """
            SELECT
                COUNT(*) AS total_documents,
                SUM(CASE WHEN status='saved' THEN 1 ELSE 0 END) AS saved_documents,
                SUM(CASE WHEN status='draft' THEN 1 ELSE 0 END) AS draft_documents,
                COALESCE(SUM(print_count),0) AS printed_total
            FROM documents
            """
        ).fetchone()
        today_count = conn.execute(
            "SELECT COUNT(*) AS count FROM documents WHERE substr(created_at,1,10)=?",
            (today.isoformat(),),
        ).fetchone()["count"]
        attachment_count = conn.execute("SELECT COUNT(*) AS count FROM attachments").fetchone()["count"]
        activity_rows = conn.execute(
            """
            SELECT substr(created_at,1,10) AS day, COUNT(*) AS count
            FROM documents
            WHERE substr(created_at,1,10) >= ?
            GROUP BY substr(created_at,1,10)
            """,
            ((today - timedelta(days=6)).isoformat(),),
        ).fetchall()
        activity_map = {row["day"]: int(row["count"] or 0) for row in activity_rows}
        arabic_days = ["الإثنين", "الثلاثاء", "الأربعاء", "الخميس", "الجمعة", "السبت", "الأحد"]
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
    _: Annotated[CurrentUser, Depends(require("documents.read"))],
    type_code: str | None = Query(default=None, max_length=4),
    q: str | None = Query(default=None, max_length=200),
    status_filter: str | None = Query(default=None, alias="status"),
    limit: int = Query(default=100, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
):
    conn = connect()
    try:
        where: list[str] = []
        params: list[Any] = []
        if type_code:
            where.append("dt.code=?")
            params.append(type_code.upper())
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
    _: Annotated[CurrentUser, Depends(require("documents.read"))],
    type_code: str | None = Query(default=None, max_length=4),
    q: str | None = Query(default=None, max_length=200),
    status_filter: str | None = Query(default=None, alias="status"),
):
    """Export a UTF-8 BOM CSV report that opens correctly in Arabic Excel."""
    conn = connect()
    try:
        where: list[str] = []
        params: list[Any] = []
        if type_code:
            where.append("dt.code=?")
            params.append(type_code.upper())
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
    _: Annotated[CurrentUser, Depends(require("documents.read"))],
):
    conn = connect()
    try:
        row = conn.execute(DOCUMENT_SELECT + " WHERE d.id=?", (document_id,)).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="المستند غير موجود")
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
    _: Annotated[CurrentUser, Depends(require("documents.read"))],
):
    conn = connect()
    try:
        exists = conn.execute("SELECT id FROM documents WHERE id=?", (document_id,)).fetchone()
        if not exists:
            raise HTTPException(status_code=404, detail="المستند غير موجود")
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
        if not conn.execute("SELECT id FROM documents WHERE id=?", (document_id,)).fetchone():
            raise HTTPException(status_code=404, detail="المستند غير موجود")
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
            row = conn.execute("SELECT * FROM attachments WHERE id=?", (attachment_id,)).fetchone()
            if not row:
                raise HTTPException(status_code=404, detail="المرفق غير موجود")
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
    _: Annotated[CurrentUser, Depends(require("documents.read"))],
    download: bool = False,
):
    conn = connect()
    try:
        row = conn.execute("SELECT * FROM attachments WHERE id=?", (attachment_id,)).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="المرفق غير موجود")
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
            row = conn.execute("SELECT * FROM attachments WHERE id=?", (attachment_id,)).fetchone()
            if not row:
                raise HTTPException(status_code=404, detail="المرفق غير موجود")
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
            pdf_path = build_print_bundle(
                document_id=document_id,
                revision=row["revision"],
                template=template,
                values=values,
                attachments=prepared_attachments,
            )
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
        }
        attachment_bytes = conn.execute("SELECT COALESCE(SUM(size_bytes),0) FROM attachments").fetchone()[0]
    finally:
        conn.close()
    return {
        "version": APP_VERSION,
        "database": database_integrity(),
        "storage": storage.status(),
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
