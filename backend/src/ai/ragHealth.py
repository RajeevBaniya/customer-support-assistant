from src.ai.providerRegistry import ProviderRegistry
from src.core.appEnvironment import AppEnvironment
from src.retrieval.retrievalHealth import retrieval_health


async def rag_health(settings: AppEnvironment) -> dict[str, object]:
    r = await retrieval_health(settings)

    gen_key_exists = bool(settings.generation_api_key and str(settings.generation_api_key).strip())
    fb_key_exists = bool(
        settings.fallback_generation_api_key
        and str(settings.fallback_generation_api_key).strip()
    )

    groq_ready = False
    gemini_ready = False

    active_provider = "none"
    if settings.generation_model:
        try:
            active_provider, _ = ProviderRegistry.get_provider(settings.generation_model)
            if active_provider == "groq" and gen_key_exists:
                groq_ready = True
            elif active_provider == "gemini" and gen_key_exists:
                gemini_ready = True
        except Exception:
            pass

    if settings.fallback_generation_model:
        try:
            fb_provider, _ = ProviderRegistry.get_provider(settings.fallback_generation_model)
            if fb_provider == "groq" and fb_key_exists:
                groq_ready = True
            elif fb_provider == "gemini" and fb_key_exists:
                gemini_ready = True
        except Exception:
            pass

    return {
        "active_llm_provider": active_provider,
        "groq_ready": groq_ready,
        "gemini_ready": gemini_ready,
        "retrieval_ready": bool(r.get("vector_search_ready")),
        "prompt_templates_ready": True,
    }
