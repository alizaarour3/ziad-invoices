from __future__ import annotations

import json
import re
import sqlite3
from collections.abc import Iterator, Mapping
from contextlib import contextmanager
from pathlib import Path
from typing import Any

from .security import utc_iso
from .settings import DATABASE_BACKEND, DATABASE_URL, DB_PATH, TEMPLATE_CONFIG_PATH

try:  # Optional in local-only installs; required by the cloud requirements file.
    import psycopg
    from psycopg.rows import dict_row
except ImportError:  # pragma: no cover - exercised only when PostgreSQL is requested without the driver.
    psycopg = None
    dict_row = None

SCHEMA_VERSION = 5

INTEGRITY_ERRORS: tuple[type[BaseException], ...] = (sqlite3.IntegrityError,)
if psycopg is not None:
    INTEGRITY_ERRORS = INTEGRITY_ERRORS + (psycopg.IntegrityError,)
_POSTGRES_ID_TABLES = {
    "users",
    "document_types",
    "documents",
    "document_revisions",
    "attachments",
    "audit_logs",
    "loans",
    "loan_payments",
}


class Record(Mapping[str, Any]):
    """Small row object compatible with the sqlite3.Row features used by the app."""

    def __init__(self, data: Mapping[str, Any] | sqlite3.Row):
        self._data = dict(data)
        self._keys = list(self._data.keys())

    def __getitem__(self, key: str | int) -> Any:
        if isinstance(key, int):
            return self._data[self._keys[key]]
        return self._data[key]

    def __iter__(self):
        return iter(self._data)

    def __len__(self) -> int:
        return len(self._data)

    def keys(self):
        return self._data.keys()

    def as_dict(self) -> dict[str, Any]:
        return dict(self._data)


class CursorResult:
    def __init__(self, cursor: Any, *, lastrowid: int | None = None):
        self._cursor = cursor
        self.lastrowid = lastrowid

    @staticmethod
    def _record(row: Any) -> Record | None:
        if row is None:
            return None
        if isinstance(row, Record):
            return row
        return Record(row)

    def fetchone(self) -> Record | None:
        return self._record(self._cursor.fetchone())

    def fetchall(self) -> list[Record]:
        return [Record(row) for row in self._cursor.fetchall()]


class DBConnection:
    def __init__(self, raw: Any, backend: str):
        self.raw = raw
        self.backend = backend

    @property
    def is_postgres(self) -> bool:
        return self.backend == "postgres"

    def _postgres_sql(self, sql: str) -> str:
        # The application intentionally uses qmark placeholders so the same SQL stays readable
        # for both SQLite and PostgreSQL. No SQL string in the project contains a literal '?'.
        converted = sql.replace("?", "%s")
        converted = converted.replace(" COLLATE NOCASE", "")
        converted = re.sub(r"\sLIKE\s", " ILIKE ", converted, flags=re.IGNORECASE)
        return converted

    def execute(self, sql: str, params: Any = ()) -> CursorResult:
        if self.backend == "sqlite":
            cursor = self.raw.execute(sql, tuple(params) if isinstance(params, list) else params)
            return CursorResult(cursor, lastrowid=cursor.lastrowid)

        converted = self._postgres_sql(sql)
        stripped = converted.strip()
        match = re.match(r"INSERT\s+INTO\s+([a-zA-Z_][a-zA-Z0-9_]*)", stripped, re.IGNORECASE)
        wants_id = bool(match and match.group(1).lower() in _POSTGRES_ID_TABLES and " RETURNING " not in stripped.upper())
        if wants_id:
            if stripped.endswith(";"):
                converted = stripped[:-1] + " RETURNING id;"
            else:
                converted = stripped + " RETURNING id"
        cursor = self.raw.cursor()
        cursor.execute(converted, tuple(params) if isinstance(params, list) else params)
        lastrowid = None
        if wants_id:
            returned = cursor.fetchone()
            if returned:
                lastrowid = int(returned["id"] if isinstance(returned, Mapping) else returned[0])
        return CursorResult(cursor, lastrowid=lastrowid)

    def close(self) -> None:
        self.raw.close()

    def commit(self) -> None:
        self.raw.commit()

    def rollback(self) -> None:
        self.raw.rollback()


def _connect_postgres() -> DBConnection:
    if psycopg is None:
        raise RuntimeError("DATABASE_URL is PostgreSQL but psycopg is not installed. Run pip install -r requirements.txt")
    url = DATABASE_URL
    if url.startswith("postgres://"):
        url = "postgresql://" + url[len("postgres://") :]
    kwargs: dict[str, Any] = {
        "autocommit": True,
        "row_factory": dict_row,
        "connect_timeout": 15,
        "application_name": "ziad-invoices",
    }
    # Supabase requires TLS. Local PostgreSQL remains usable without forcing SSL.
    if "sslmode=" not in url and not any(host in url for host in ("localhost", "127.0.0.1", "postgres:5432")):
        kwargs["sslmode"] = "require"
    raw = psycopg.connect(url, **kwargs)
    # Works with Supabase session and transaction poolers and avoids prepared-statement conflicts.
    raw.prepare_threshold = None
    return DBConnection(raw, "postgres")


def connect(db_path: Path | None = None) -> DBConnection:
    if DATABASE_BACKEND == "postgres" and db_path is None:
        return _connect_postgres()
    raw = sqlite3.connect(str(db_path or DB_PATH), timeout=30, isolation_level=None, check_same_thread=False)
    raw.row_factory = sqlite3.Row
    raw.execute("PRAGMA foreign_keys = ON")
    raw.execute("PRAGMA journal_mode = WAL")
    raw.execute("PRAGMA synchronous = NORMAL")
    raw.execute("PRAGMA busy_timeout = 30000")
    return DBConnection(raw, "sqlite")


@contextmanager
def transaction(conn: DBConnection, immediate: bool = False) -> Iterator[DBConnection]:
    conn.execute("BEGIN" if conn.is_postgres else ("BEGIN IMMEDIATE" if immediate else "BEGIN"))
    try:
        yield conn
    except Exception:
        conn.rollback()
        raise
    else:
        conn.commit()


SQLITE_SCHEMA = """
CREATE TABLE IF NOT EXISTS schema_meta (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    full_name TEXT NOT NULL,
    username TEXT NOT NULL UNIQUE COLLATE NOCASE,
    password_salt TEXT NOT NULL,
    password_hash TEXT NOT NULL,
    role TEXT NOT NULL CHECK (role IN ('admin','editor','viewer')),
    is_active INTEGER NOT NULL DEFAULT 1 CHECK (is_active IN (0,1)),
    must_change_password INTEGER NOT NULL DEFAULT 0 CHECK (must_change_password IN (0,1)),
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    last_login_at TEXT,
    failed_login_count INTEGER NOT NULL DEFAULT 0,
    locked_until TEXT
);

CREATE TABLE IF NOT EXISTS sessions (
    token_hash TEXT PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    expires_at TEXT NOT NULL,
    created_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_sessions_user_id ON sessions(user_id);
CREATE INDEX IF NOT EXISTS idx_sessions_expires_at ON sessions(expires_at);

CREATE TABLE IF NOT EXISTS user_page_permissions (
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    page_key TEXT NOT NULL,
    can_view INTEGER NOT NULL DEFAULT 1 CHECK (can_view IN (0,1)),
    updated_at TEXT NOT NULL,
    updated_by INTEGER REFERENCES users(id) ON DELETE SET NULL,
    PRIMARY KEY(user_id, page_key)
);
CREATE INDEX IF NOT EXISTS idx_user_page_permissions_page ON user_page_permissions(page_key, can_view);

CREATE TABLE IF NOT EXISTS document_types (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    code TEXT NOT NULL UNIQUE,
    name_ar TEXT NOT NULL,
    name_en TEXT NOT NULL,
    prefix TEXT NOT NULL,
    image_filename TEXT NOT NULL,
    docx_filename TEXT NOT NULL,
    config_json TEXT NOT NULL,
    is_active INTEGER NOT NULL DEFAULT 1 CHECK (is_active IN (0,1))
);

CREATE TABLE IF NOT EXISTS number_sequences (
    document_type_id INTEGER PRIMARY KEY REFERENCES document_types(id) ON DELETE CASCADE,
    next_value INTEGER NOT NULL DEFAULT 1 CHECK (next_value > 0)
);

CREATE TABLE IF NOT EXISTS documents (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    document_type_id INTEGER NOT NULL REFERENCES document_types(id),
    document_number TEXT NOT NULL UNIQUE,
    status TEXT NOT NULL DEFAULT 'saved' CHECK (status IN ('draft','saved')),
    field_values_json TEXT NOT NULL,
    created_by INTEGER NOT NULL REFERENCES users(id),
    updated_by INTEGER NOT NULL REFERENCES users(id),
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    print_count INTEGER NOT NULL DEFAULT 0,
    revision INTEGER NOT NULL DEFAULT 1
);
CREATE INDEX IF NOT EXISTS idx_documents_type ON documents(document_type_id);
CREATE INDEX IF NOT EXISTS idx_documents_created_at ON documents(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_documents_number ON documents(document_number);

CREATE TABLE IF NOT EXISTS document_revisions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    document_id INTEGER NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
    revision INTEGER NOT NULL,
    field_values_json TEXT NOT NULL,
    changed_by INTEGER NOT NULL REFERENCES users(id),
    changed_at TEXT NOT NULL,
    UNIQUE(document_id, revision)
);

CREATE TABLE IF NOT EXISTS attachments (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    document_id INTEGER NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
    original_name TEXT NOT NULL,
    stored_name TEXT NOT NULL UNIQUE,
    mime_type TEXT NOT NULL,
    size_bytes INTEGER NOT NULL,
    sha256 TEXT NOT NULL,
    notes TEXT NOT NULL DEFAULT '',
    print_order INTEGER NOT NULL DEFAULT 0,
    uploaded_by INTEGER NOT NULL REFERENCES users(id),
    created_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_attachments_document ON attachments(document_id, print_order, id);

CREATE TABLE IF NOT EXISTS loans (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    borrower_name TEXT NOT NULL,
    principal_amount_minor INTEGER NOT NULL CHECK (principal_amount_minor > 0),
    months_total INTEGER NOT NULL CHECK (months_total > 0),
    minimum_payment_minor INTEGER NOT NULL CHECK (minimum_payment_minor > 0),
    remaining_amount_minor INTEGER NOT NULL CHECK (remaining_amount_minor >= 0),
    created_by INTEGER NOT NULL REFERENCES users(id),
    updated_by INTEGER NOT NULL REFERENCES users(id),
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_loans_borrower_name ON loans(borrower_name);
CREATE INDEX IF NOT EXISTS idx_loans_remaining ON loans(remaining_amount_minor);
CREATE INDEX IF NOT EXISTS idx_loans_updated_at ON loans(updated_at DESC);

CREATE TABLE IF NOT EXISTS loan_payments (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    loan_id INTEGER NOT NULL REFERENCES loans(id) ON DELETE CASCADE,
    amount_minor INTEGER NOT NULL CHECK (amount_minor > 0),
    remaining_amount_minor_after INTEGER NOT NULL CHECK (remaining_amount_minor_after >= 0),
    months_remaining_after INTEGER NOT NULL CHECK (months_remaining_after >= 0),
    notes TEXT NOT NULL DEFAULT '',
    paid_by INTEGER NOT NULL REFERENCES users(id),
    paid_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_loan_payments_loan ON loan_payments(loan_id, id);
CREATE INDEX IF NOT EXISTS idx_loan_payments_paid_at ON loan_payments(paid_at DESC);

CREATE TABLE IF NOT EXISTS audit_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER REFERENCES users(id) ON DELETE SET NULL,
    action TEXT NOT NULL,
    entity_type TEXT NOT NULL,
    entity_id TEXT,
    details_json TEXT NOT NULL DEFAULT '{}',
    created_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_audit_created_at ON audit_logs(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_audit_entity ON audit_logs(entity_type, entity_id);

CREATE TABLE IF NOT EXISTS settings (
    key TEXT PRIMARY KEY,
    value_json TEXT NOT NULL,
    updated_at TEXT NOT NULL
);
"""

POSTGRES_SCHEMA_STATEMENTS = [
    """CREATE TABLE IF NOT EXISTS schema_meta (key TEXT PRIMARY KEY, value TEXT NOT NULL)""",
    """CREATE TABLE IF NOT EXISTS users (
        id BIGSERIAL PRIMARY KEY,
        full_name TEXT NOT NULL,
        username TEXT NOT NULL UNIQUE,
        password_salt TEXT NOT NULL,
        password_hash TEXT NOT NULL,
        role TEXT NOT NULL CHECK (role IN ('admin','editor','viewer')),
        is_active INTEGER NOT NULL DEFAULT 1 CHECK (is_active IN (0,1)),
        must_change_password INTEGER NOT NULL DEFAULT 0 CHECK (must_change_password IN (0,1)),
        created_at TEXT NOT NULL,
        updated_at TEXT NOT NULL,
        last_login_at TEXT,
        failed_login_count INTEGER NOT NULL DEFAULT 0,
        locked_until TEXT
    )""",
    """CREATE UNIQUE INDEX IF NOT EXISTS idx_users_username_lower ON users ((lower(username)))""",
    """CREATE TABLE IF NOT EXISTS sessions (
        token_hash TEXT PRIMARY KEY,
        user_id BIGINT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
        expires_at TEXT NOT NULL,
        created_at TEXT NOT NULL
    )""",
    "CREATE INDEX IF NOT EXISTS idx_sessions_user_id ON sessions(user_id)",
    "CREATE INDEX IF NOT EXISTS idx_sessions_expires_at ON sessions(expires_at)",
    """CREATE TABLE IF NOT EXISTS user_page_permissions (
        user_id BIGINT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
        page_key TEXT NOT NULL,
        can_view INTEGER NOT NULL DEFAULT 1 CHECK (can_view IN (0,1)),
        updated_at TEXT NOT NULL,
        updated_by BIGINT REFERENCES users(id) ON DELETE SET NULL,
        PRIMARY KEY(user_id, page_key)
    )""",
    "CREATE INDEX IF NOT EXISTS idx_user_page_permissions_page ON user_page_permissions(page_key, can_view)",
    """CREATE TABLE IF NOT EXISTS document_types (
        id BIGSERIAL PRIMARY KEY,
        code TEXT NOT NULL UNIQUE,
        name_ar TEXT NOT NULL,
        name_en TEXT NOT NULL,
        prefix TEXT NOT NULL,
        image_filename TEXT NOT NULL,
        docx_filename TEXT NOT NULL,
        config_json TEXT NOT NULL,
        is_active INTEGER NOT NULL DEFAULT 1 CHECK (is_active IN (0,1))
    )""",
    """CREATE TABLE IF NOT EXISTS number_sequences (
        document_type_id BIGINT PRIMARY KEY REFERENCES document_types(id) ON DELETE CASCADE,
        next_value BIGINT NOT NULL DEFAULT 1 CHECK (next_value > 0)
    )""",
    """CREATE TABLE IF NOT EXISTS documents (
        id BIGSERIAL PRIMARY KEY,
        document_type_id BIGINT NOT NULL REFERENCES document_types(id),
        document_number TEXT NOT NULL UNIQUE,
        status TEXT NOT NULL DEFAULT 'saved' CHECK (status IN ('draft','saved')),
        field_values_json TEXT NOT NULL,
        created_by BIGINT NOT NULL REFERENCES users(id),
        updated_by BIGINT NOT NULL REFERENCES users(id),
        created_at TEXT NOT NULL,
        updated_at TEXT NOT NULL,
        print_count INTEGER NOT NULL DEFAULT 0,
        revision INTEGER NOT NULL DEFAULT 1
    )""",
    "CREATE INDEX IF NOT EXISTS idx_documents_type ON documents(document_type_id)",
    "CREATE INDEX IF NOT EXISTS idx_documents_created_at ON documents(created_at DESC)",
    "CREATE INDEX IF NOT EXISTS idx_documents_number ON documents(document_number)",
    """CREATE TABLE IF NOT EXISTS document_revisions (
        id BIGSERIAL PRIMARY KEY,
        document_id BIGINT NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
        revision INTEGER NOT NULL,
        field_values_json TEXT NOT NULL,
        changed_by BIGINT NOT NULL REFERENCES users(id),
        changed_at TEXT NOT NULL,
        UNIQUE(document_id, revision)
    )""",
    """CREATE TABLE IF NOT EXISTS attachments (
        id BIGSERIAL PRIMARY KEY,
        document_id BIGINT NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
        original_name TEXT NOT NULL,
        stored_name TEXT NOT NULL UNIQUE,
        mime_type TEXT NOT NULL,
        size_bytes BIGINT NOT NULL,
        sha256 TEXT NOT NULL,
        notes TEXT NOT NULL DEFAULT '',
        print_order INTEGER NOT NULL DEFAULT 0,
        uploaded_by BIGINT NOT NULL REFERENCES users(id),
        created_at TEXT NOT NULL
    )""",
    "CREATE INDEX IF NOT EXISTS idx_attachments_document ON attachments(document_id, print_order, id)",

    """CREATE TABLE IF NOT EXISTS loans (
        id BIGSERIAL PRIMARY KEY,
        borrower_name TEXT NOT NULL,
        principal_amount_minor BIGINT NOT NULL CHECK (principal_amount_minor > 0),
        months_total INTEGER NOT NULL CHECK (months_total > 0),
        minimum_payment_minor BIGINT NOT NULL CHECK (minimum_payment_minor > 0),
        remaining_amount_minor BIGINT NOT NULL CHECK (remaining_amount_minor >= 0),
        created_by BIGINT NOT NULL REFERENCES users(id),
        updated_by BIGINT NOT NULL REFERENCES users(id),
        created_at TEXT NOT NULL,
        updated_at TEXT NOT NULL
    )""",
    "CREATE INDEX IF NOT EXISTS idx_loans_borrower_name ON loans(borrower_name)",
    "CREATE INDEX IF NOT EXISTS idx_loans_remaining ON loans(remaining_amount_minor)",
    "CREATE INDEX IF NOT EXISTS idx_loans_updated_at ON loans(updated_at DESC)",
    """CREATE TABLE IF NOT EXISTS loan_payments (
        id BIGSERIAL PRIMARY KEY,
        loan_id BIGINT NOT NULL REFERENCES loans(id) ON DELETE CASCADE,
        amount_minor BIGINT NOT NULL CHECK (amount_minor > 0),
        remaining_amount_minor_after BIGINT NOT NULL CHECK (remaining_amount_minor_after >= 0),
        months_remaining_after INTEGER NOT NULL CHECK (months_remaining_after >= 0),
        notes TEXT NOT NULL DEFAULT '',
        paid_by BIGINT NOT NULL REFERENCES users(id),
        paid_at TEXT NOT NULL
    )""",
    "CREATE INDEX IF NOT EXISTS idx_loan_payments_loan ON loan_payments(loan_id, id)",
    "CREATE INDEX IF NOT EXISTS idx_loan_payments_paid_at ON loan_payments(paid_at DESC)",
    """CREATE TABLE IF NOT EXISTS audit_logs (
        id BIGSERIAL PRIMARY KEY,
        user_id BIGINT REFERENCES users(id) ON DELETE SET NULL,
        action TEXT NOT NULL,
        entity_type TEXT NOT NULL,
        entity_id TEXT,
        details_json TEXT NOT NULL DEFAULT '{}',
        created_at TEXT NOT NULL
    )""",
    "CREATE INDEX IF NOT EXISTS idx_audit_created_at ON audit_logs(created_at DESC)",
    "CREATE INDEX IF NOT EXISTS idx_audit_entity ON audit_logs(entity_type, entity_id)",
    """CREATE TABLE IF NOT EXISTS settings (
        key TEXT PRIMARY KEY,
        value_json TEXT NOT NULL,
        updated_at TEXT NOT NULL
    )""",
]


def _run_sqlite_script(conn: DBConnection, script: str) -> None:
    conn.raw.executescript(script)


def init_db(db_path: Path | None = None) -> None:
    conn = connect(db_path)
    try:
        if conn.is_postgres:
            with transaction(conn):
                for statement in POSTGRES_SCHEMA_STATEMENTS:
                    conn.execute(statement)
                conn.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS failed_login_count INTEGER NOT NULL DEFAULT 0")
                conn.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS locked_until TEXT")
        else:
            _run_sqlite_script(conn, SQLITE_SCHEMA)
            user_columns = {row["name"] for row in conn.execute("PRAGMA table_info(users)").fetchall()}
            if "failed_login_count" not in user_columns:
                conn.execute("ALTER TABLE users ADD COLUMN failed_login_count INTEGER NOT NULL DEFAULT 0")
            if "locked_until" not in user_columns:
                conn.execute("ALTER TABLE users ADD COLUMN locked_until TEXT")

        conn.execute(
            "INSERT INTO schema_meta(key, value) VALUES('schema_version', ?) "
            "ON CONFLICT(key) DO UPDATE SET value=excluded.value",
            (str(SCHEMA_VERSION),),
        )
        _sync_document_types(conn)
        _sync_page_permissions(conn)
        conn.execute("DELETE FROM sessions WHERE expires_at <= ?", (utc_iso(),))
    finally:
        conn.close()


def _sync_document_types(conn: DBConnection) -> None:
    config = json.loads(TEMPLATE_CONFIG_PATH.read_text(encoding="utf-8"))
    for code, item in config.items():
        config_json = json.dumps(item, ensure_ascii=False, separators=(",", ":"))
        conn.execute(
            """
            INSERT INTO document_types(code, name_ar, name_en, prefix, image_filename, docx_filename, config_json)
            VALUES(?,?,?,?,?,?,?)
            ON CONFLICT(code) DO UPDATE SET
                name_ar=excluded.name_ar,
                name_en=excluded.name_en,
                prefix=excluded.prefix,
                image_filename=excluded.image_filename,
                docx_filename=excluded.docx_filename,
                config_json=excluded.config_json
            """,
            (
                code,
                item["name_ar"],
                item["name_en"],
                item["prefix"],
                item["image"],
                item["docx"],
                config_json,
            ),
        )
        type_id = conn.execute("SELECT id FROM document_types WHERE code=?", (code,)).fetchone()["id"]
        conn.execute(
            "INSERT INTO number_sequences(document_type_id, next_value) VALUES(?,1) "
            "ON CONFLICT(document_type_id) DO NOTHING",
            (type_id,),
        )


def permission_page_keys(conn: DBConnection) -> list[str]:
    rows = conn.execute("SELECT code FROM document_types WHERE is_active=1 ORDER BY id").fetchall()
    return ["dashboard", "loans", *[f"documents.{row['code']}" for row in rows]]


def ensure_user_page_permissions(conn: DBConnection, user_id: int) -> None:
    now = utc_iso()
    for page_key in permission_page_keys(conn):
        conn.execute(
            "INSERT INTO user_page_permissions(user_id, page_key, can_view, updated_at, updated_by) "
            "VALUES(?,?,1,?,NULL) ON CONFLICT(user_id,page_key) DO NOTHING",
            (user_id, page_key, now),
        )


def _sync_page_permissions(conn: DBConnection) -> None:
    rows = conn.execute("SELECT id FROM users").fetchall()
    for row in rows:
        ensure_user_page_permissions(conn, int(row["id"]))


def audit(
    conn: DBConnection,
    *,
    user_id: int | None,
    action: str,
    entity_type: str,
    entity_id: str | int | None = None,
    details: dict | None = None,
) -> None:
    conn.execute(
        "INSERT INTO audit_logs(user_id, action, entity_type, entity_id, details_json, created_at) VALUES(?,?,?,?,?,?)",
        (
            user_id,
            action,
            entity_type,
            None if entity_id is None else str(entity_id),
            json.dumps(details or {}, ensure_ascii=False, separators=(",", ":")),
            utc_iso(),
        ),
    )
