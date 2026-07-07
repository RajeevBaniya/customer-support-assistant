import pytest

from src.documents import mimeValidator, uploadSecurity
from src.shared.customExceptions import ValidationException


def test_mime_accepts_pdf() -> None:
    ext, mime = mimeValidator.validate_document_upload(
        original_file_name="report.pdf",
        declared_content_type="application/pdf",
        file_bytes=b"%PDF-1.4 minimal",
    )
    assert ext == ".pdf"
    assert mime == "application/pdf"


def test_mime_rejects_bad_extension() -> None:
    with pytest.raises(ValidationException):
        mimeValidator.validate_document_upload(
            original_file_name="x.exe",
            declared_content_type="application/pdf",
            file_bytes=b"%PDF-1.4",
        )


def test_upload_security_blocks_exe_name() -> None:
    with pytest.raises(ValidationException):
        uploadSecurity.assert_extension_not_blocked("setup.exe")


def test_normalize_filename_rejects_traversal() -> None:
    with pytest.raises(ValidationException):
        uploadSecurity.normalize_original_filename("../../etc/passwd")
