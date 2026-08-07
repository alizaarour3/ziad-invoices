from __future__ import annotations

import argparse
import os
import sqlite3
import sys
from pathlib import Path
from typing import Any, Callable

# DATABASE_URL and the Supabase variables must be set before this script starts.
if not os.environ.get("DATABASE_URL", "").startswith(("postgres://", "postgresql://")):
    raise SystemExit("Set DATABASE_URL to the Supabase PostgreSQL Session pooler URI before running this script.")
if not os.environ.get("SUPABASE_URL") or not os.environ.get("SUPABASE_SERVICE_ROLE_KEY"):
    raise SystemExit("Set SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY before running this script.")
os.environ.setdefault("ZIAD_STORAGE_BACKEND", "supabase")

PROJECT_DIR = Path(__file__).resolve().parents[1]
if str(PROJECT_DIR) not in sys.path:
    sys.path.insert(0, str(PROJECT_DIR))

from app.db import connect, init_db, transaction  # noqa: E402
from app.services.storage_service import storage  # noqa: E402


def rows_from(source: sqlite3.Connection, table: str) -> list[dict[str, Any]]:
    try:
        return [dict(row) for row in source.execute(f"SELECT * FROM {table}").fetchall()]
    except sqlite3.OperationalError:
        return []


def insert_row(target, table: str, row: dict[str, Any], conflict_column: str) -> None:
    columns = list(row.keys())
    placeholders = ",".join("?" for _ in columns)
    sql = (
        f"INSERT INTO {table} ({','.join(columns)}) VALUES ({placeholders}) "
        f"ON CONFLICT({conflict_column}) DO NOTHING"
    )
    target.execute(sql, tuple(row[column] for column in columns))


def main() -> int:
    parser = argparse.ArgumentParser(description="Migrate Ziad Invoices SQLite data and attachments to Supabase.")
    parser.add_argument("--sqlite", type=Path, required=True, help="Path to ziad_documents.sqlite3")
    parser.add_argument("--attachments", type=Path, required=True, help="Path to the old data/attachments folder")
    parser.add_argument("--allow-nonempty", action="store_true", help="Allow migration into a database that already contains users/documents")
    args = parser.parse_args()

    sqlite_path = args.sqlite.resolve()
    attachments_dir = args.attachments.resolve()
    if not sqlite_path.exists():
        raise SystemExit(f"SQLite database not found: {sqlite_path}")
    if not attachments_dir.exists():
        raise SystemExit(f"Attachments directory not found: {attachments_dir}")

    source = sqlite3.connect(str(sqlite_path))
    source.row_factory = sqlite3.Row
    init_db()
    target = connect()
    try:
        existing_users = target.execute("SELECT COUNT(*) AS count FROM users").fetchone()["count"]
        existing_documents = target.execute("SELECT COUNT(*) AS count FROM documents").fetchone()["count"]
        if (existing_users or existing_documents) and not args.allow_nonempty:
            raise SystemExit(
                "The Supabase database is not empty. Run against an empty project or pass --allow-nonempty only after taking a backup."
            )

        source_types = {row["id"]: row["code"] for row in source.execute("SELECT id, code FROM document_types").fetchall()}
        target_types = {row["code"]: row["id"] for row in target.execute("SELECT id, code FROM document_types").fetchall()}
        type_id_map = {source_id: target_types[code] for source_id, code in source_types.items() if code in target_types}

        users = rows_from(source, "users")
        documents = rows_from(source, "documents")
        revisions = rows_from(source, "document_revisions")
        attachments = rows_from(source, "attachments")
        audit_logs = rows_from(source, "audit_logs")
        settings = rows_from(source, "settings")
        schema_meta = rows_from(source, "schema_meta")
        sequences = rows_from(source, "number_sequences")

        print(f"Users: {len(users)}")
        print(f"Documents: {len(documents)}")
        print(f"Attachments: {len(attachments)}")

        # Upload attachment objects first. Database inserts happen only after every file is available.
        for index, attachment in enumerate(attachments, start=1):
            old_name = attachment["stored_name"]
            candidates = [
                attachments_dir / old_name,
                attachments_dir / Path(old_name).name,
                attachments_dir.parent / old_name,
            ]
            source_file = next((candidate for candidate in candidates if candidate.is_file()), None)
            if source_file is None:
                searched = ", ".join(str(candidate) for candidate in candidates)
                raise SystemExit(f"Attachment file missing. Searched: {searched}")
            object_name = old_name if "/" in old_name else f"attachments/{attachment['document_id']}/{old_name}"
            storage.put_file(object_name, source_file, attachment.get("mime_type") or "application/octet-stream")
            attachment["stored_name"] = object_name
            print(f"Uploaded attachment {index}/{len(attachments)}: {attachment['original_name']}")

        with transaction(target):
            for row in users:
                # Old releases may not contain the lockout columns.
                row.setdefault("failed_login_count", 0)
                row.setdefault("locked_until", None)
                insert_row(target, "users", row, "id")

            for row in sequences:
                source_type_id = row["document_type_id"]
                if source_type_id not in type_id_map:
                    continue
                row["document_type_id"] = type_id_map[source_type_id]
                insert_row(target, "number_sequences", row, "document_type_id")
                target.execute(
                    "UPDATE number_sequences SET next_value=? WHERE document_type_id=?",
                    (row["next_value"], row["document_type_id"]),
                )

            for row in documents:
                row["document_type_id"] = type_id_map[row["document_type_id"]]
                insert_row(target, "documents", row, "id")
            for row in revisions:
                insert_row(target, "document_revisions", row, "id")
            for row in attachments:
                insert_row(target, "attachments", row, "id")
            for row in audit_logs:
                insert_row(target, "audit_logs", row, "id")
            for row in settings:
                insert_row(target, "settings", row, "key")
            for row in schema_meta:
                insert_row(target, "schema_meta", row, "key")

            for table in ("users", "documents", "document_revisions", "attachments", "audit_logs"):
                target.execute(
                    f"SELECT setval(pg_get_serial_sequence('{table}','id'), COALESCE(MAX(id), 1), MAX(id) IS NOT NULL) FROM {table}"
                )

        print("Migration completed successfully.")
        print("Open the Render application, sign in with the same local administrator credentials, and verify the counts.")
        return 0
    finally:
        target.close()
        source.close()


if __name__ == "__main__":
    raise SystemExit(main())
