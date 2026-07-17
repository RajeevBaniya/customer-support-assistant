import json
from pathlib import Path
from time import perf_counter
from typing import Any

from pydantic import BaseModel, Field

from src.ai.providerRegistry import ProviderRegistry
from src.core.appEnvironment import AppEnvironment
from src.observability.structuredLogger import get_logger
from src.planning.executionPlan import ExecutionPlan
from src.planning.queryRewriteModels import QueryRewriteResult
from src.runtimeContext.runtimeContext import RuntimeContext

logger = get_logger("planning.query_rewrite")

_PROMPTS_DIR = Path(__file__).resolve().parent.parent / "ai" / "prompts"


def _read_prompt(name: str) -> str:
    return (_PROMPTS_DIR / name).read_text(encoding="utf-8").strip()


class QueryRewriteAgentOutput(BaseModel):
    """Pydantic validation model for parsing the LLM query rewrite JSON output."""

    rewritten_query: str = Field(min_length=1)
    rewrite_performed: bool
    rewrite_reason: str = Field(min_length=1)
    detected_entities: list[str] = Field(default_factory=list)
    detected_acronyms: list[str] = Field(default_factory=list)
    expanded_terms: list[str] = Field(default_factory=list)
    retrieval_queries: list[str] = Field(default_factory=list)
    confidence: float = Field(ge=0.0, le=1.0)


class QueryRewriteAgent:
    """Intelligent query optimizer improving retrieval accuracy and resolving context."""

    def __init__(self, settings: AppEnvironment) -> None:
        self._settings = settings

    async def rewrite_query(
        self, query: str, context: RuntimeContext, plan: ExecutionPlan
    ) -> QueryRewriteResult:
        """Invokes rewrite LLM or applies deterministic fallback on error/config issues."""
        start_time = perf_counter()

        model = self._settings.query_rewrite_model
        api_key = self._settings.query_rewrite_api_key

        if not api_key or not str(api_key).strip():
            logger.warning(
                "query_rewrite_credentials_missing",
                reason="Query rewrite API key not configured",
            )
            return self._build_deterministic_fallback(
                query, {"fallback_reason": "credentials_missing"}
            )

        try:
            history_str = "None"
            if context.conversation and context.conversation.recent_messages:
                lines = [
                    f"{m.role}: {m.content}"
                    for m in context.conversation.recent_messages
                ]
                history_str = "\n".join(lines)

            system_prompt = _read_prompt("query_rewrite_system.txt")
            user_prompt = _read_prompt("query_rewrite_user.txt").format(
                query=query,
                history=history_str,
                complexity=plan.complexity,
                strategy=plan.strategy.concurrency,
            )

            provider_name, executor = ProviderRegistry.get_provider(model)
            timeout = float(self._settings.llm_timeout_seconds)

            text_response, usage = await executor.chat(
                self._settings,
                model=model,
                api_key=api_key,
                system=system_prompt,
                user=user_prompt,
                timeout_seconds=timeout,
            )

            raw_data = self._clean_and_parse_json(text_response)
            parsed = QueryRewriteAgentOutput.model_validate(raw_data)

            duration_ms = (perf_counter() - start_time) * 1000.0
            metadata = {
                "latency_ms": duration_ms,
                "confidence": parsed.confidence,
                "version": "1.0.0",
                "provider_used": provider_name,
                "model_used": model,
                "fallback_used": False,
            }

            final_query = parsed.rewritten_query.strip()
            if not parsed.rewrite_performed:
                final_query = query

            # If retrieval_queries is empty, ensure it contains at least final_query
            queries = parsed.retrieval_queries
            if not queries:
                queries = [final_query]

            return QueryRewriteResult(
                original_query=query,
                rewritten_query=final_query,
                rewrite_performed=parsed.rewrite_performed,
                rewrite_reason=parsed.rewrite_reason,
                detected_entities=parsed.detected_entities,
                detected_acronyms=parsed.detected_acronyms,
                expanded_terms=parsed.expanded_terms,
                retrieval_queries=queries,
                confidence=parsed.confidence,
                metadata=metadata,
            )

        except Exception as exc:
            logger.exception("query_rewrite_agent_failed", reason=str(exc))
            return self._build_deterministic_fallback(query, {"fallback_reason": str(exc)})

    def _build_deterministic_fallback(
        self, query: str, metadata: dict[str, Any]
    ) -> QueryRewriteResult:
        """Builds a safe fallback QueryRewriteResult returning the original query unmodified."""
        metadata.update(
            {
                "fallback_used": True,
                "version": "1.0.0",
            }
        )
        return QueryRewriteResult(
            original_query=query,
            rewritten_query=query,
            rewrite_performed=False,
            rewrite_reason="fallback_used",
            detected_entities=[],
            detected_acronyms=[],
            expanded_terms=[],
            retrieval_queries=[query],
            confidence=1.0,
            metadata=metadata,
        )

    def _clean_and_parse_json(self, text: str) -> dict[str, Any]:
        """Cleans and extracts JSON payload from markdown fences or raw output."""
        cleaned = text.strip()
        if cleaned.startswith("```"):
            lines = cleaned.splitlines()
            if lines[0].startswith("```"):
                lines = lines[1:]
            if lines and lines[-1].startswith("```"):
                lines = lines[:-1]
            cleaned = "\n".join(lines).strip()
        parsed = json.loads(cleaned)
        if not isinstance(parsed, dict):
            raise ValueError("LLM response did not parse as a JSON object")
        return parsed
