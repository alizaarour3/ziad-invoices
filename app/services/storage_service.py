from __future__ import annotations

import shutil
from pathlib import Path
from urllib.parse import quote

import httpx

from ..settings import (
    ATTACHMENTS_DIR,
    STORAGE_BACKEND,
    SUPABASE_SERVICE_ROLE_KEY,
    SUPABASE_STORAGE_BUCKET,
    SUPABASE_URL,
)


class StorageError(RuntimeError):
    pass


class StorageService:
    def __init__(self) -> None:
        self.backend = STORAGE_BACKEND
        if self.backend not in {"local", "supabase"}:
            raise StorageError("ZIAD_STORAGE_BACKEND must be local or supabase")
        if self.backend == "supabase" and not (SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY):
            raise StorageError("Supabase Storage requires SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY")
        self._bucket_checked = False

    @property
    def is_cloud(self) -> bool:
        return self.backend == "supabase"

    def _headers(self) -> dict[str, str]:
        return {
            "apikey": SUPABASE_SERVICE_ROLE_KEY,
            "Authorization": f"Bearer {SUPABASE_SERVICE_ROLE_KEY}",
        }

    def _ensure_bucket(self) -> None:
        if not self.is_cloud or self._bucket_checked:
            return
        headers = self._headers()
        with httpx.Client(timeout=30.0) as client:
            response = client.get(
                f"{SUPABASE_URL}/storage/v1/bucket/{quote(SUPABASE_STORAGE_BUCKET, safe='')}",
                headers=headers,
            )
            if response.status_code == 404:
                response = client.post(
                    f"{SUPABASE_URL}/storage/v1/bucket",
                    headers={**headers, "Content-Type": "application/json"},
                    json={
                        "id": SUPABASE_STORAGE_BUCKET,
                        "name": SUPABASE_STORAGE_BUCKET,
                        "public": False,
                    },
                )
            if response.status_code not in {200, 201, 409}:
                raise StorageError(f"Could not access Supabase Storage bucket: {response.status_code} {response.text[:300]}")
        self._bucket_checked = True

    def put_file(self, object_name: str, source: Path, content_type: str) -> None:
        if self.backend == "local":
            destination = ATTACHMENTS_DIR / object_name
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, destination)
            return

        self._ensure_bucket()
        encoded_name = quote(object_name, safe="/")
        headers = {
            **self._headers(),
            "Content-Type": content_type or "application/octet-stream",
            "x-upsert": "false",
        }
        with source.open("rb") as handle, httpx.Client(timeout=httpx.Timeout(180.0, connect=30.0)) as client:
            response = client.post(
                f"{SUPABASE_URL}/storage/v1/object/{quote(SUPABASE_STORAGE_BUCKET, safe='')}/{encoded_name}",
                headers=headers,
                content=handle,
            )
        if response.status_code not in {200, 201}:
            raise StorageError(f"Supabase upload failed: {response.status_code} {response.text[:300]}")

    def read_bytes(self, object_name: str) -> bytes:
        if self.backend == "local":
            path = ATTACHMENTS_DIR / object_name
            if not path.exists():
                raise FileNotFoundError(object_name)
            return path.read_bytes()

        self._ensure_bucket()
        encoded_name = quote(object_name, safe="/")
        with httpx.Client(timeout=httpx.Timeout(180.0, connect=30.0)) as client:
            response = client.get(
                f"{SUPABASE_URL}/storage/v1/object/authenticated/{quote(SUPABASE_STORAGE_BUCKET, safe='')}/{encoded_name}",
                headers=self._headers(),
            )
        if response.status_code == 404:
            raise FileNotFoundError(object_name)
        if response.status_code != 200:
            raise StorageError(f"Supabase download failed: {response.status_code} {response.text[:300]}")
        return response.content

    def download_to(self, object_name: str, destination: Path) -> Path:
        destination.parent.mkdir(parents=True, exist_ok=True)
        if self.backend == "local":
            source = ATTACHMENTS_DIR / object_name
            if not source.exists():
                raise FileNotFoundError(object_name)
            shutil.copy2(source, destination)
            return destination

        self._ensure_bucket()
        encoded_name = quote(object_name, safe="/")
        with httpx.Client(timeout=httpx.Timeout(180.0, connect=30.0)) as client:
            with client.stream(
                "GET",
                f"{SUPABASE_URL}/storage/v1/object/authenticated/{quote(SUPABASE_STORAGE_BUCKET, safe='')}/{encoded_name}",
                headers=self._headers(),
            ) as response:
                if response.status_code == 404:
                    raise FileNotFoundError(object_name)
                if response.status_code != 200:
                    body = response.read().decode("utf-8", errors="replace")
                    raise StorageError(f"Supabase download failed: {response.status_code} {body[:300]}")
                with destination.open("wb") as handle:
                    for chunk in response.iter_bytes():
                        handle.write(chunk)
        return destination

    def delete(self, object_name: str) -> None:
        if self.backend == "local":
            path = ATTACHMENTS_DIR / object_name
            path.unlink(missing_ok=True)
            # Remove empty per-document folder when applicable.
            if path.parent != ATTACHMENTS_DIR:
                try:
                    path.parent.rmdir()
                except OSError:
                    pass
            return

        self._ensure_bucket()
        with httpx.Client(timeout=30.0) as client:
            response = client.request(
                "DELETE",
                f"{SUPABASE_URL}/storage/v1/object/{quote(SUPABASE_STORAGE_BUCKET, safe='')}",
                headers={**self._headers(), "Content-Type": "application/json"},
                json={"prefixes": [object_name]},
            )
        if response.status_code not in {200, 204, 404}:
            raise StorageError(f"Supabase delete failed: {response.status_code} {response.text[:300]}")

    def status(self) -> dict:
        if self.backend == "local":
            return {"backend": "local", "ok": True, "bucket": None}
        try:
            self._ensure_bucket()
            return {"backend": "supabase", "ok": True, "bucket": SUPABASE_STORAGE_BUCKET}
        except Exception as exc:  # Status page should report, not crash.
            return {"backend": "supabase", "ok": False, "bucket": SUPABASE_STORAGE_BUCKET, "message": str(exc)}


storage = StorageService()
