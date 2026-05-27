from src.models.documentModel import Document
from src.schemas.retrievalSchemas import RetrievalChunkItem
from src.vectorstore.queryHit import VectorQueryHit


def build_chunk_item(
    *,
    hit: VectorQueryHit,
    similarity_score: float,
    document: Document,
) -> RetrievalChunkItem:
    sp = hit.metadata.get("source_page")
    source_page = int(sp) if sp is not None else None
    return RetrievalChunkItem(
        document_id=document.id,
        document_name=document.original_file_name,
        chunk_index=hit.chunk_index,
        source_page=source_page,
        similarity_score=round(similarity_score, 6),
        parser_type=document.parser_type,
        text=hit.text,
        upload_timestamp=document.created_at,
    )
