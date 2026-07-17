import asyncio

import cloudinary
import cloudinary.api

from src.core.appEnvironment import AppEnvironment
from src.storage.cloudinaryStorage import CloudinaryStorage
from src.storage.storageProvider import StorageProvider


async def storage_health(settings: AppEnvironment) -> dict[str, object]:
    if settings.enable_original_file_storage:
        url = settings.supabase_url
        key = settings.supabase_service_role_key
        bucket = settings.supabase_storage_bucket
        if not url or not key or not bucket:
            return {
                "provider": "supabase",
                "ready": False,
                "writable": False,
                "supabase_configured": False,
            }

        def _ping_supabase() -> bool:
            try:
                from supabase import create_client

                client = create_client(url, key)
                client.storage.from_(bucket).list(options={"limit": 1})
                return True
            except Exception:
                return False

        ok = await asyncio.to_thread(_ping_supabase)
        return {
            "provider": "supabase",
            "ready": ok,
            "writable": ok,
            "supabase_configured": True,
        }

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
    if settings.enable_original_file_storage:
        from src.storage.supabaseStorage import SupabaseStorageProvider

        return SupabaseStorageProvider(settings)
    return CloudinaryStorage(settings)
