from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Annotated

from fastapi import Depends, Header, HTTPException, status

from .db import audit, connect, transaction
from .security import new_session_token, session_expiry, token_hash, utc_iso, verify_password
from .settings import SESSION_HOURS


@dataclass(frozen=True)
class CurrentUser:
    id: int
    full_name: str
    username: str
    role: str
    is_active: bool


ROLE_PERMISSIONS: dict[str, set[str]] = {
    "admin": {
        "documents.read",
        "documents.create",
        "documents.update",
        "documents.delete",
        "attachments.create",
        "attachments.delete",
        "documents.print",
        "users.manage",
        "audit.read",
        "system.manage",
    },
    "editor": {
        "documents.read",
        "documents.create",
        "documents.update",
        "attachments.create",
        "attachments.delete",
        "documents.print",
    },
    "viewer": {"documents.read", "documents.print"},
}


def authenticate(username: str, password: str) -> tuple[str, dict]:
    conn = connect()
    try:
        row = conn.execute(
            "SELECT * FROM users WHERE username=? COLLATE NOCASE",
            (username.strip(),),
        ).fetchone()
        now_dt = datetime.now(timezone.utc)
        if row and row["locked_until"]:
            locked_until = datetime.fromisoformat(row["locked_until"])
            if locked_until > now_dt:
                raise HTTPException(status_code=status.HTTP_423_LOCKED, detail="تم قفل الحساب مؤقتاً بعد محاولات دخول فاشلة")

        valid = bool(row and row["is_active"] and verify_password(password, row["password_salt"], row["password_hash"]))
        if not valid:
            with transaction(conn, immediate=True):
                if row:
                    failures = int(row["failed_login_count"] or 0) + 1
                    locked_until = None
                    if failures >= 5:
                        locked_until = (now_dt + timedelta(minutes=15)).isoformat()
                        failures = 0
                    conn.execute(
                        "UPDATE users SET failed_login_count=?, locked_until=?, updated_at=? WHERE id=?",
                        (failures, locked_until, utc_iso(), row["id"]),
                    )
                audit(
                    conn,
                    user_id=row["id"] if row else None,
                    action="auth.login_failed",
                    entity_type="user",
                    entity_id=row["id"] if row else username.strip(),
                    details={"username": username.strip()},
                )
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="اسم المستخدم أو كلمة المرور غير صحيحة")

        token = new_session_token()
        now = utc_iso()
        with transaction(conn, immediate=True):
            conn.execute(
                "INSERT INTO sessions(token_hash, user_id, expires_at, created_at) VALUES(?,?,?,?)",
                (token_hash(token), row["id"], session_expiry(SESSION_HOURS), now),
            )
            conn.execute(
                "UPDATE users SET last_login_at=?, updated_at=?, failed_login_count=0, locked_until=NULL WHERE id=?",
                (now, now, row["id"]),
            )
            audit(conn, user_id=row["id"], action="auth.login", entity_type="user", entity_id=row["id"])
        user = {
            "id": row["id"],
            "full_name": row["full_name"],
            "username": row["username"],
            "role": row["role"],
            "must_change_password": bool(row["must_change_password"]),
        }
        return token, user
    finally:
        conn.close()


def _extract_bearer(authorization: str | None) -> str:
    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="يجب تسجيل الدخول")
    token = authorization.split(" ", 1)[1].strip()
    if not token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="جلسة غير صالحة")
    return token


def get_current_user(authorization: Annotated[str | None, Header()] = None) -> CurrentUser:
    token = _extract_bearer(authorization)
    conn = connect()
    try:
        row = conn.execute(
            """
            SELECT u.id, u.full_name, u.username, u.role, u.is_active, s.expires_at
            FROM sessions s
            JOIN users u ON u.id=s.user_id
            WHERE s.token_hash=?
            """,
            (token_hash(token),),
        ).fetchone()
        if not row:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="انتهت الجلسة أو أنها غير صالحة")
        expires_at = datetime.fromisoformat(row["expires_at"])
        if expires_at <= datetime.now(timezone.utc) or not row["is_active"]:
            conn.execute("DELETE FROM sessions WHERE token_hash=?", (token_hash(token),))
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="انتهت الجلسة")
        return CurrentUser(
            id=row["id"],
            full_name=row["full_name"],
            username=row["username"],
            role=row["role"],
            is_active=bool(row["is_active"]),
        )
    finally:
        conn.close()


def require(permission: str):
    def dependency(user: Annotated[CurrentUser, Depends(get_current_user)]) -> CurrentUser:
        if permission not in ROLE_PERMISSIONS.get(user.role, set()):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="ليس لديك صلاحية لتنفيذ هذه العملية")
        return user

    return dependency


def logout(token: str, user_id: int) -> None:
    conn = connect()
    try:
        with transaction(conn, immediate=True):
            conn.execute("DELETE FROM sessions WHERE token_hash=?", (token_hash(token),))
            audit(conn, user_id=user_id, action="auth.logout", entity_type="user", entity_id=user_id)
    finally:
        conn.close()


def get_bearer_token(authorization: Annotated[str | None, Header()] = None) -> str:
    return _extract_bearer(authorization)
