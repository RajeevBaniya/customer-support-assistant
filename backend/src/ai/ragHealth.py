from src.core.appEnvironment import AppEnvironment
from src.retrieval.retrievalHealth import retrieval_health


async def rag_health(settings: AppEnvironment) -> dict[str, object]:
    r = await retrieval_health(settings)
    groq_key = bool(settings.groq_api_key and str(settings.groq_api_key).strip())
    gem_key = bool(settings.gemini_api_key and str(settings.gemini_api_key).strip())
    return {
        "active_llm_provider": settings.active_llm_provider,
        "groq_ready": groq_key,
        "gemini_ready": gem_key,
        "retrieval_ready": bool(r.get("vector_search_ready")),
        "prompt_templates_ready": True,
    }
