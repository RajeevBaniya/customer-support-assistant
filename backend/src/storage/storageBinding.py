import asyncio

import cloudinary
import cloudinary.api

from src.core.appEnvironment import AppEnvironment
from src.storage.cloudinaryStorage import CloudinaryStorage
from src.storage.storageProvider import StorageProvider


def _configure_cloudinary(settings: AppEnvironment) -> None:
    cloudinary.config(
        cloud_name=(settings.cloudinary_cloud_name or "").strip(),
        api_key=(settings.cloudinary_api_key or "").strip(),
        api_secret=(settings.cloudinary_api_secret or "").strip(),
        secure=True,
    )


async def storage_health(settings: AppEnvironment) -> dict[str, object]:
    configured = settings.cloudinary_configured()
    if not configured:
        return {
            "provider": "cloudinary",
            "ready": False,
            "writable": False,
            "cloudinary_configured": False,
        }

    def _ping() -> bool:
        try:
            _configure_cloudinary(settings)
            cloudinary.api.ping()
            return True
        except Exception:
            return False

    ok = await asyncio.to_thread(_ping)
    return {
        "provider": "cloudinary",
        "ready": ok,
        "writable": ok,
        "cloudinary_configured": configured,
        "cloud_name_set": bool((settings.cloudinary_cloud_name or "").strip()),
    }


def storage_provider_for(settings: AppEnvironment) -> StorageProvider:
    return CloudinaryStorage(settings)
