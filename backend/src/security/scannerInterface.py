from abc import ABC, abstractmethod


class FileScannerInterface(ABC):
    @abstractmethod
    def scan(self, file_bytes: bytes, filename: str) -> None:
        """Inspect file bytes for dangerous content.

        Raises ValidationException if the content is considered unsafe.
        Implementations must be synchronous and must not modify the bytes.
        """
