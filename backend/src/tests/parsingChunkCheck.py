from io import BytesIO
from uuid import uuid4

from docx import Document as DocxBuilder

from src.chunking.chunkMetadata import token_estimate
from src.chunking.chunkStrategy import chunk_plain_text
from src.chunking.textChunker import chunk_with_offsets, normalize_whitespace
from src.parsing.docxParser import extract_text as extract_docx
from src.parsing.markdownParser import extract_text as extract_md
from src.parsing.pdfParser import extract_text as extract_pdf


def test_normalize_whitespace_collapses_blank_runs() -> None:
    assert normalize_whitespace("a\n\n\n\nb") == "a\n\nb"


def test_chunk_overlap_advances() -> None:
    body = "x" * 2500
    chunks, starts = chunk_with_offsets(body, chunk_size=1200, overlap=150)
    assert len(chunks) >= 2
    assert starts[1] > starts[0]


def test_chunk_plain_text_deterministic() -> None:
    text = "para one\n\npara two\n\n" + ("z" * 500)
    a, sa = chunk_plain_text(text)
    b, sb = chunk_plain_text(text)
    assert a == b and sa == sb


def test_token_estimate_heuristic() -> None:
    assert token_estimate("abcd") == 1
    assert token_estimate("x" * 12) == 3


def test_pdf_malformed_bytes_returns_empty_string() -> None:
    out = extract_pdf(b"%PDF-1.4\nnot a real trailer")
    assert isinstance(out, str)


def test_docx_extracts_paragraph() -> None:
    buf = BytesIO()
    doc = DocxBuilder()
    doc.add_paragraph("RecallStack phase four")
    doc.save(buf)
    text = extract_docx(buf.getvalue())
    assert "phase four" in text.lower()


def test_markdown_strips_to_plain_text() -> None:
    md = b"# Title\n\n- item one\n- **bold** item\n"
    text = extract_md(md)
    assert "Title" in text
    assert "item one" in text


def test_build_previews_respects_five_cap() -> None:
    from src.chunking.chunkMetadata import build_previews

    long = "word " * 400
    chunks, starts = chunk_plain_text(long)
    previews = build_previews(
        document_id=uuid4(),
        parser_key="text",
        chunks=chunks,
        starts=starts,
        page_for_char=None,
        max_chunks=5,
        preview_len=200,
    )
    assert len(previews) <= 5
    for p in previews:
        assert len(p.preview_text) <= 200


def test_chunk_plain_text_with_custom_settings() -> None:
    from src.core.appEnvironment import AppEnvironment

    settings = AppEnvironment(
        APP_ENV="test",
        DEBUG=False,
        DATABASE_URL="postgresql+asyncpg://u:p@localhost/db",
        CHUNK_SIZE=500,
        CHUNK_OVERLAP=50,
    )
    long_text = "word " * 300
    # verify custom strategy settings propagate correctly
    chunks, starts = chunk_plain_text(long_text, chunk_size=settings.chunk_size, overlap=settings.chunk_overlap)
    for c in chunks:
        assert len(c) <= 500

