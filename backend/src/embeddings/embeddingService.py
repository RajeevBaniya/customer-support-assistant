from src.core.appEnvironment import AppEnvironment
from src.embeddings.huggingfaceEmbedding import embed_texts_batched


async def embed_document_chunks(settings: AppEnvironment, texts: list[str]) -> list[list[float]]:
    return await embed_texts_batched(settings, texts)


async def embed_query_text(settings: AppEnvironment, text: str) -> list[float]:
    vectors = await embed_texts_batched(settings, [text])
    if not vectors:
        raise RuntimeError("query_embedding_empty")
    return vectors[0]
