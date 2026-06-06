from src.security.scannerInterface import FileScannerInterface
from src.shared.customExceptions import ValidationException

_EICAR_SIGNATURE = b"X5O!P%@AP[4\\PZX54(P^)7CC)7}$EICAR-STANDARD-ANTIVIRUS-TEST-FILE!$H+H*"

_EXECUTABLE_MAGIC: tuple[bytes, ...] = (
    b"MZ",
    b"\x7fELF",
    b"#!",
)


class DangerousContentScanner(FileScannerInterface):
    def scan(self, file_bytes: bytes, filename: str) -> None:
        if _EICAR_SIGNATURE in file_bytes:
            raise ValidationException(
                "Dangerous file content detected",
                details={"reason": "eicar_signature", "filename": filename},
            )

        header = file_bytes[:4]
        for magic in _EXECUTABLE_MAGIC:
            if header[: len(magic)] == magic:
                raise ValidationException(
                    "Dangerous file content detected",
                    details={"reason": "executable_magic_bytes", "filename": filename},
                )
