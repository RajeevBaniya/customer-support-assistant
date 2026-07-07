from uuid import UUID

from src.vectorstore.vectorMetadata import chunk_vector_id


def test_chunk_vector_id_format() -> None:
    org = UUID("00000000-0000-4000-8000-000000000001")
    doc = UUID("00000000-0000-4000-8000-000000000002")
    vid = chunk_vector_id(org, doc, 7)
    assert vid == f"org:{org}:doc:{doc}:chunk:7"
