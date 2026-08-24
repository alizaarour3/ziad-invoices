from __future__ import annotations

import hashlib
import json
import sqlite3
import tempfile
import zipfile
from datetime import datetime, timezone
from pathlib import Path

from ..db import connect
from ..settings import BACKUPS_DIR, DATABASE_BACKEND, DB_PATH, PROJECT_DIR, TEMPLATES_DIR
from .storage_service import storage

APP_VERSION = "3.3.34"


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def database_integrity() -> dict:
    conn = connect()
    try:
        if conn.is_postgres:
            result = conn.execute("SELECT 1 AS ok").fetchone()["ok"]
            version = conn.execute("SELECT current_database() AS database_name").fetchone()["database_name"]
            return {"ok": result == 1, "message": "connected", "backend": "postgres", "database": version}
        result = conn.execute("PRAGMA integrity_check").fetchone()[0]
        return {"ok": result == "ok", "message": result, "backend": "sqlite"}
    except Exception as exc:
        return {"ok": False, "message": str(exc), "backend": DATABASE_BACKEND}
    finally:
        conn.close()


def _read_hash_manifest(filename: str) -> dict[str, str]:
    expected: dict[str, str] = {}
    hashes_file = PROJECT_DIR / filename
    if not hashes_file.exists():
        return expected
    for line in hashes_file.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        checksum, relative = line.split(maxsplit=1)
        expected[relative.lstrip("* ").replace("\\", "/")] = checksum
    return expected


def template_integrity() -> list[dict]:
    manifests = {
        "A4 production": _read_hash_manifest("TEMPLATE_HASHES.sha256"),
        "Original preserved": _read_hash_manifest("ORIGINAL_TEMPLATE_HASHES.sha256"),
        "Official PDF sources": _read_hash_manifest("PDF_TEMPLATE_HASHES.sha256"),
        "Exact HTML templates": _read_hash_manifest("HTML_TEMPLATE_HASHES.sha256"),
    }
    results: list[dict] = []
    for category, expected in manifests.items():
        for relative, wanted in sorted(expected.items()):
            path = PROJECT_DIR / relative
            if not path.exists():
                results.append({"filename": relative, "sha256": "", "ok": False, "category": category})
                continue
            actual = _sha256(path)
            results.append({"filename": relative, "sha256": actual, "ok": wanted == actual, "category": category})
    return results


def _sqlite_snapshot(destination: Path) -> None:
    source = sqlite3.connect(str(DB_PATH), timeout=30)
    target = sqlite3.connect(str(destination))
    try:
        source.backup(target)
    finally:
        target.close()
        source.close()


def _postgres_json_export(destination: Path) -> None:
    table_names = [
        "schema_meta",
        "users",
        "user_page_permissions",
        "document_types",
        "number_sequences",
        "documents",
        "document_revisions",
        "attachments",
        "loans",
        "loan_payments",
        "advances",
        "advance_payments",
        "audit_logs",
        "settings",
    ]
    conn = connect()
    try:
        payload: dict[str, list[dict]] = {}
        for table in table_names:
            rows = conn.execute(f"SELECT * FROM {table}").fetchall()
            payload[table] = [dict(row) for row in rows]
        destination.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    finally:
        conn.close()


def _attachment_rows() -> list[dict]:
    conn = connect()
    try:
        return [dict(row) for row in conn.execute("SELECT id, original_name, stored_name, mime_type, size_bytes, sha256 FROM attachments ORDER BY id").fetchall()]
    finally:
        conn.close()


def create_backup() -> Path:
    BACKUPS_DIR.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    output = BACKUPS_DIR / f"ziad-invoices-backup-{timestamp}.zip"

    with tempfile.TemporaryDirectory(prefix="ziad-backup-") as temp_dir_name:
        temp_dir = Path(temp_dir_name)
        files: list[tuple[Path, str]] = []
        if DATABASE_BACKEND == "postgres":
            database_export = temp_dir / "postgres-export.json"
            _postgres_json_export(database_export)
            files.append((database_export, "database/postgres-export.json"))
        else:
            snapshot = temp_dir / "ziad_documents.sqlite3"
            _sqlite_snapshot(snapshot)
            files.append((snapshot, "database/ziad_documents.sqlite3"))

        for attachment in _attachment_rows():
            suffix = Path(attachment["original_name"]).suffix[:12]
            local_copy = temp_dir / "attachments" / f"{attachment['id']}{suffix}"
            storage.download_to(attachment["stored_name"], local_copy)
            files.append((local_copy, f"attachments/{attachment['id']}/{attachment['original_name']}"))

        files += [(path, path.relative_to(PROJECT_DIR).as_posix()) for path in TEMPLATES_DIR.rglob("*.docx")]
        files += [(path, path.relative_to(PROJECT_DIR).as_posix()) for path in TEMPLATES_DIR.rglob("*.pdf")]
        static_templates = PROJECT_DIR / "app" / "static" / "templates"
        files += [(path, path.relative_to(PROJECT_DIR).as_posix()) for path in static_templates.glob("*.png")]
        html_templates = PROJECT_DIR / "app" / "static" / "form-templates"
        files += [(path, path.relative_to(PROJECT_DIR).as_posix()) for path in html_templates.glob("*.html")]
        config = PROJECT_DIR / "config" / "templates.json"
        files.append((config, "config/templates.json"))
        for hash_name in ("TEMPLATE_HASHES.sha256", "ORIGINAL_TEMPLATE_HASHES.sha256", "PDF_TEMPLATE_HASHES.sha256", "HTML_TEMPLATE_HASHES.sha256"):
            hash_path = PROJECT_DIR / hash_name
            if hash_path.exists():
                files.append((hash_path, hash_name))

        manifest = {
            "application": "Ziad Invoices Professional",
            "version": APP_VERSION,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "database_backend": DATABASE_BACKEND,
            "storage_backend": storage.backend,
            "files": [
                {"path": archive_name, "size": path.stat().st_size, "sha256": _sha256(path)}
                for path, archive_name in files
            ],
        }
        with zipfile.ZipFile(output, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=6) as archive:
            for path, archive_name in files:
                archive.write(path, archive_name)
            archive.writestr("manifest.json", json.dumps(manifest, ensure_ascii=False, indent=2))
    return output
