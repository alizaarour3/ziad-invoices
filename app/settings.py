from __future__ import annotations

import os
from pathlib import Path

PROJECT_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = Path(os.environ.get("ZIAD_DATA_DIR", PROJECT_DIR / "data")).resolve()
DB_PATH = DATA_DIR / "ziad_documents.sqlite3"
DATABASE_URL = os.environ.get("DATABASE_URL", "").strip()
DATABASE_BACKEND = "postgres" if DATABASE_URL.startswith(("postgres://", "postgresql://")) else "sqlite"

ATTACHMENTS_DIR = DATA_DIR / "attachments"
GENERATED_DIR = DATA_DIR / "generated"
BACKUPS_DIR = DATA_DIR / "backups"
STATIC_DIR = PROJECT_DIR / "app" / "static"
TEMPLATES_DIR = PROJECT_DIR / "templates"
TEMPLATE_CONFIG_PATH = PROJECT_DIR / "config" / "templates.json"

MAX_ATTACHMENT_BYTES = int(os.environ.get("ZIAD_MAX_ATTACHMENT_BYTES", 100 * 1024 * 1024))
SESSION_HOURS = int(os.environ.get("ZIAD_SESSION_HOURS", 24))
HOST = os.environ.get("HOST", os.environ.get("ZIAD_HOST", "127.0.0.1"))
PORT = int(os.environ.get("PORT", os.environ.get("ZIAD_PORT", "8765")))

STORAGE_BACKEND = os.environ.get("ZIAD_STORAGE_BACKEND", "supabase" if os.environ.get("SUPABASE_URL") else "local").strip().lower()
SUPABASE_URL = os.environ.get("SUPABASE_URL", "").rstrip("/")
SUPABASE_SERVICE_ROLE_KEY = os.environ.get("SUPABASE_SERVICE_ROLE_KEY", "")
SUPABASE_STORAGE_BUCKET = os.environ.get("SUPABASE_STORAGE_BUCKET", "ziad-invoices")

for directory in (DATA_DIR, ATTACHMENTS_DIR, GENERATED_DIR, BACKUPS_DIR):
    directory.mkdir(parents=True, exist_ok=True)
