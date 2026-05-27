import asyncio
import io
from typing import Any, cast
from uuid import UUID

import cloudinary
import cloudinary.api
import cloudinary.uploader
import httpx
from cloudinary import utils

from src.core.appEnvironment import AppEnvironment
from src.storage.storageProvider import StorageProvider


class CloudinaryStorage(StorageProvider):
    def __init__(self, settings: AppEnvironment) -> None:
        self._settings = settings
        cloudinary.config(
            cloud_name=(settings.cloudinary_cloud_name or "").strip(),
            api_key=(settings.cloudinary_api_key or "").strip(),
            api_secret=(settings.cloudinary_api_secret or "").strip(),
            secure=True,
        )

    def _public_id(self, *, organization_id: UUID, document_id: UUID, stored_file_name: str) -> str:
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
        del content_type
        if not self._settings.cloudinary_configured():
            raise RuntimeError("cloudinary_not_configured")
        public_id = self._public_id(
            organization_id=organization_id,
            document_id=document_id,
            stored_file_name=stored_file_name,
        )

        def _upload() -> dict[str, object]:
            raw: Any = cloudinary.uploader.upload(
                io.BytesIO(data),
                public_id=public_id,
                resource_type="raw",
                overwrite=True,
                invalidate=True,
            )
            if not isinstance(raw, dict):
                raise RuntimeError("cloudinary_upload_bad_response")
            return cast(dict[str, object], raw)

        result = await asyncio.to_thread(_upload)
        pid = result.get("public_id")
        if not isinstance(pid, str) or not pid.strip():
            raise RuntimeError("cloudinary_upload_missing_public_id")
        return pid.strip()

    async def delete_file(self, *, organization_id: UUID, storage_path: str) -> None:
        del organization_id

        def _destroy() -> None:
            try:
                cloudinary.uploader.destroy(storage_path, resource_type="raw")
            except Exception:
                return

        await asyncio.to_thread(_destroy)

    async def get_file(self, *, organization_id: UUID, storage_path: str) -> bytes:
        del organization_id
        url, _opts = utils.cloudinary_url(storage_path, resource_type="raw", secure=True)
        timeout = httpx.Timeout(60.0)
        async with httpx.AsyncClient(timeout=timeout) as client:
            response = await client.get(url)
            response.raise_for_status()
            return response.content

    async def file_exists(self, *, organization_id: UUID, storage_path: str) -> bool:
        del organization_id

        def _exists() -> bool:
            try:
                cloudinary.api.resource(storage_path, resource_type="raw")
                return True
            except Exception:
                return False

        return await asyncio.to_thread(_exists)
