from __future__ import annotations

import asyncio
from uuid import UUID

from src.core.appEnvironment import AppEnvironment
from src.storage.storageProvider import StorageProvider


class SupabaseStorageProvider(StorageProvider):
    """Storage provider leveraging Supabase Storage buckets."""

    def __init__(self, settings: AppEnvironment) -> None:
        self._settings = settings
        url = settings.supabase_url
        key = settings.supabase_service_role_key
        bucket = settings.supabase_storage_bucket
        if not url or not key or not bucket:
            raise RuntimeError("supabase_not_configured")

        from supabase import create_client

        self._client = create_client(url, key)
        self._bucket = bucket

    def _storage_path(
        self, *, organization_id: UUID, document_id: UUID, stored_file_name: str
    ) -> str:
        return f"recallstack/{organization_id}/{document_id}/{stored_file_name}"

    async def upload_file(
        self,
        *,
        organization_id: UUID,
        document_id: UUID,
        stored_file_name: str,
        data: bytes,
        content_type: str,
    ) -> str:
        path = self._storage_path(
            organization_id=organization_id,
            document_id=document_id,
            stored_file_name=stored_file_name,
        )

        def _upload() -> None:
            self._client.storage.from_(self._bucket).upload(
                path=path,
                file=data,
                file_options={"content-type": content_type, "upsert": "true"},
            )

        try:
            await asyncio.to_thread(_upload)
        except Exception as exc:
            raise RuntimeError(f"supabase_upload_failed: {str(exc)}") from exc
        return path

    async def delete_file(self, *, organization_id: UUID, storage_path: str) -> None:
        del organization_id

        def _destroy() -> None:
            try:
                self._client.storage.from_(self._bucket).remove([storage_path])
            except Exception:
                return

        await asyncio.to_thread(_destroy)

    async def get_file(self, *, organization_id: UUID, storage_path: str) -> bytes:
        del organization_id

        def _download() -> bytes:
            return self._client.storage.from_(self._bucket).download(storage_path)

        try:
            return await asyncio.to_thread(_download)
        except Exception as exc:
            raise RuntimeError(f"supabase_download_failed: {str(exc)}") from exc

    async def file_exists(self, *, organization_id: UUID, storage_path: str) -> bool:
        del organization_id
        parts = storage_path.split("/")
        if len(parts) < 2:
            folder = ""
            filename = storage_path
        else:
            folder = "/".join(parts[:-1])
            filename = parts[-1]

        def _list() -> bool:
            try:
                res = self._client.storage.from_(self._bucket).list(
                    path=folder, options={"search": filename}
                )
                for item in res:
                    if isinstance(item, dict) and item.get("name") == filename:
                        return True
                    elif hasattr(item, "name") and item.name == filename:
                        return True
                return False
            except Exception:
                return False

        return await asyncio.to_thread(_list)
