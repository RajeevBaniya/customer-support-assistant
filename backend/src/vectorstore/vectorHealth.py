import asyncio
from typing import Any

from src.core.appEnvironment import AppEnvironment
from src.embeddings.huggingfaceEmbedding import model_is_cached


async def vector_health(settings: AppEnvironment) -> dict[str, Any]:
    model_name = settings.resolved_embedding_model
    bundle: dict[str, Any] = {
        "pinecone_configured": settings.pinecone_configured(),
        "pinecone_reachable": False,
        "embedding_batch_size": settings.embedding_batch_size,
        "embedding_model": model_name,
        "embedding_model_cached": model_is_cached(model_name),
        "embedding_provider_ready": True,
    }
    if not settings.pinecone_configured():
        return bundle

    def _ping() -> bool:
        from src.vectorstore.pineconeStore import build_pinecone_store

        build_pinecone_store(settings)
        return True

    try:
        bundle["pinecone_reachable"] = await asyncio.to_thread(_ping)
    except Exception:
        bundle["pinecone_reachable"] = False
    return bundle
