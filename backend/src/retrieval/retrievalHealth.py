from typing import Any

from src.core.appEnvironment import AppEnvironment
from src.vectorstore.vectorHealth import vector_health


async def retrieval_health(settings: AppEnvironment) -> dict[str, Any]:
    vector_bundle = await vector_health(settings)
    configured = bool(vector_bundle.get("pinecone_configured"))
    reachable = bool(vector_bundle.get("pinecone_reachable"))
    ready = configured and reachable
    reranking_ready = True
    retrieval_pipeline_ready = bool(ready and reranking_ready)
    return {
        "retrieval_enabled": configured,
        "vector_search_ready": ready,
        "embedding_provider_ready": vector_bundle.get("embedding_provider_ready"),
        "embedding_model": vector_bundle.get("embedding_model"),
        "embedding_model_cached": vector_bundle.get("embedding_model_cached"),
        "embedding_model_alignment": True,
        "pinecone_query_ready": ready,
        "reranking_ready": reranking_ready,
        "retrieval_pipeline_ready": retrieval_pipeline_ready,
    }
