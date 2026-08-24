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
            return {"ok": bool(result), "backend": "postgres"}
        result = conn.execute("PRAGMA integrity_check").fetchone()[0]
        return {"ok": result == "ok", "backend": "sqlite", "result": result}
    finally:
        conn.close()


def _sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def template_integrity() -> list[dict]:
    manifest_path = PROJECT_DIR / "config" / "template_hashes.json"
    if not manifest_path.exists():
        return []
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    results = []
    for relative, expected in manifest.items():
        path = PROJECT_DIR / relative
        actual = _sha256(path) if path.exists() else ""
        results.append({"path": relative, "ok": actual == expected, "expected": expected, "actual": actual})
    return results


def create_backup() -> Path:
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
    output = BACKUPS_DIR / f"ziad-backup-{timestamp}.zip"
    output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="ziad-backup-") as temp_dir:
        temp = Path(temp_dir)
        if DATABASE_BACKEND == "sqlite" and DB_PATH.exists():
            db_copy = temp / DB_PATH.name
            source = sqlite3.connect(str(DB_PATH))
            target = sqlite3.connect(str(db_copy))
            try:
                source.backup(target)
            finally:
                target.close()
                source.close()
        manifest = {
            "app_version": APP_VERSION,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "database_backend": DATABASE_BACKEND,
            "template_integrity": template_integrity(),
        }
        (temp / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
        with zipfile.ZipFile(output, "w", compression=zipfile.ZIP_DEFLATED) as archive:
            for path in temp.rglob("*"):
                if path.is_file():
                    archive.write(path, path.relative_to(temp))
    return output
