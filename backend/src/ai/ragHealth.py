from src.core.appEnvironment import AppEnvironment
from src.retrieval.retrievalHealth import retrieval_health


async def rag_health(settings: AppEnvironment) -> dict[str, object]:
    r = await retrieval_health(settings)

    active = settings.active_llm_provider.strip().lower()
    fallback = settings.fallback_llm_provider.strip().lower()

    gen_key_exists = bool(settings.generation_api_key and str(settings.generation_api_key).strip())
    fb_key_exists = bool(
        settings.fallback_generation_api_key
        and str(settings.fallback_generation_api_key).strip()
    )

    groq_ready = False
    gemini_ready = False

    if active == "groq" and gen_key_exists:
        groq_ready = True
    elif active == "gemini" and gen_key_exists:
        gemini_ready = True

    if fallback == "groq" and fb_key_exists:
        groq_ready = True
    elif fallback == "gemini" and fb_key_exists:
        gemini_ready = True

    return {
        "active_llm_provider": settings.active_llm_provider,
        "groq_ready": groq_ready,
        "gemini_ready": gemini_ready,
        "retrieval_ready": bool(r.get("vector_search_ready")),
        "prompt_templates_ready": True,
    }
