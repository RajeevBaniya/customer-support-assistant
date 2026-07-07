import pytest

from src.security.dangerousContentScanner import DangerousContentScanner
from src.shared.customExceptions import ValidationException

_EICAR = b"X5O!P%@AP[4\\PZX54(P^)7CC)7}$EICAR-STANDARD-ANTIVIRUS-TEST-FILE!$H+H*"
_CLEAN_PDF = b"%PDF-1.4 clean content here"
_PE_MAGIC = b"MZ\x90\x00\x03"
_ELF_MAGIC = b"\x7fELF\x02\x01\x01\x00"
_SHEBANG = b"#!/bin/bash\necho hi"


@pytest.fixture
def scanner() -> DangerousContentScanner:
    return DangerousContentScanner()


def test_eicar_signature_rejected(scanner):
    with pytest.raises(ValidationException) as exc_info:
        scanner.scan(_EICAR, "test.txt")
    assert "dangerous" in exc_info.value.message.lower()
    assert exc_info.value.details["reason"] == "eicar_signature"


def test_pe_executable_rejected(scanner):
    with pytest.raises(ValidationException) as exc_info:
        scanner.scan(_PE_MAGIC, "malware.pdf")
    assert exc_info.value.details["reason"] == "executable_magic_bytes"


def test_elf_executable_rejected(scanner):
    with pytest.raises(ValidationException) as exc_info:
        scanner.scan(_ELF_MAGIC, "payload.docx")
    assert exc_info.value.details["reason"] == "executable_magic_bytes"


def test_shebang_rejected(scanner):
    with pytest.raises(ValidationException) as exc_info:
        scanner.scan(_SHEBANG, "script.txt")
    assert exc_info.value.details["reason"] == "executable_magic_bytes"


def test_clean_pdf_passes(scanner):
    scanner.scan(_CLEAN_PDF, "report.pdf")


def test_empty_bytes_pass(scanner):
    scanner.scan(b"", "empty.txt")


def test_eicar_embedded_in_larger_file_rejected(scanner):
    padded = b"some prefix " + _EICAR + b" some suffix"
    with pytest.raises(ValidationException):
        scanner.scan(padded, "doc.txt")
