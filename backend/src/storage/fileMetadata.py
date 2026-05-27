import hashlib

from fastapi import UploadFile

from src.shared.customExceptions import ValidationException


async def read_upload_with_sha256(
    upload: UploadFile,
    *,
    max_bytes: int,
) -> tuple[bytes, str]:
    digest = hashlib.sha256()
    chunks: list[bytes] = []
    total = 0
    while True:
        piece = await upload.read(1024 * 1024)
        if not piece:
            break
        total += len(piece)
        if total > max_bytes:
            raise ValidationException(
                "File exceeds maximum upload size",
                details={"max_bytes": max_bytes},
            )
        digest.update(piece)
        chunks.append(piece)
    data = b"".join(chunks)
    return data, digest.hexdigest()
