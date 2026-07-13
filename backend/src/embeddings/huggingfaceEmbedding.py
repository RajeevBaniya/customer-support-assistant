"""HuggingFace sentence-transformers embedding provider implementation."""

import asyncio
import threading
from time import perf_counter
from typing import Any

import numpy as np
from sentence_transformers import SentenceTransformer

from src.core.appEnvironment import AppEnvironment
from src.embeddings.embeddingProvider import EmbeddingProvider
from src.observability.structuredLogger import get_logger

logger = get_logger("embeddings.pipeline")

_lock = threading.Lock()
_models: dict[str, SentenceTransformer] = {}


def model_is_cached(model_name: str) -> bool:
    """Check if the sentence-transformer model instance is cached in memory."""
    return model_name in _models


def _get_model(model_name: str) -> SentenceTransformer:
    """Thread-safe retrieval of cached sentence-transformer models."""
    with _lock:
        if model_name not in _models:
            _models[model_name] = SentenceTransformer(model_name)
        return _models[model_name]


class HuggingFaceEmbeddingProvider(EmbeddingProvider):
    """Concrete sentence-transformers embedding provider."""

    def __init__(self, settings: AppEnvironment) -> None:
        import os
        self._name = settings.resolved_embedding_model
        self._api_key = settings.huggingface_api_key
        if self._api_key and str(self._api_key).strip():
            os.environ["HF_TOKEN"] = str(self._api_key).strip()

    async def encode_batch(self, texts: list[str]) -> list[list[float]]:
        """Generate vectors for a single batch of text strings."""
        if not texts:
            return []

        def _encode(batch: list[str]) -> Any:
            model = _get_model(self._name)
            return model.encode(batch, normalize_embeddings=True)

        raw_embeddings = await asyncio.to_thread(_encode, texts)
        embeddings_array = np.atleast_2d(np.asarray(raw_embeddings, dtype=np.float32))
        return [embeddings_array[index].tolist() for index in range(embeddings_array.shape[0])]


async def embed_texts_batched(
    settings: AppEnvironment, texts: list[str]
) -> list[list[float]]:
    """Encode texts batched with configured retries, exponential backoffs, and latency logging."""
    if not texts:
        return []

    provider = HuggingFaceEmbeddingProvider(settings)
    embedded_vectors: list[list[float]] = []

    batch_size = settings.embedding_batch_size
    max_retries = settings.embedding_max_retries
    retry_delay = settings.embedding_retry_delay_seconds
    timeout = settings.embedding_timeout_seconds

    batches = [texts[index : index + batch_size] for index in range(0, len(texts), batch_size)]

    logger.info(
        "embedding_pipeline_started",
        total_texts=len(texts),
        batch_size=batch_size,
        total_batches=len(batches),
        model=settings.resolved_embedding_model,
    )

    total_latency = 0.0
    for batch_index, batch in enumerate(batches):
        batch_start_time = perf_counter()
        success = False
        last_exception = None

        for attempt in range(1, max_retries + 1):
            try:
                vectors = await asyncio.wait_for(
                    provider.encode_batch(batch),
                    timeout=timeout,
                )
                embedded_vectors.extend(vectors)
                success = True
                latency = perf_counter() - batch_start_time
                total_latency += latency

                logger.info(
                    "embedding_batch_processed",
                    batch_index=batch_index,
                    batch_size=len(batch),
                    latency_seconds=round(latency, 4),
                    attempt=attempt,
                    vector_dimension=len(vectors[0]) if vectors else 0,
                )
                break
            except Exception as exception:
                last_exception = exception
                backoff_delay = retry_delay * (2 ** (attempt - 1))
                logger.warning(
                    "embedding_batch_attempt_failed",
                    batch_index=batch_index,
                    attempt=attempt,
                    error=str(exception),
                    next_retry_delay_seconds=round(backoff_delay, 2),
                )
                if attempt < max_retries:
                    await asyncio.sleep(backoff_delay)

        if not success:
            logger.error(
                "embedding_batch_failed_persistently",
                batch_index=batch_index,
                total_attempts=max_retries,
                error=str(last_exception),
            )
            if last_exception:
                raise last_exception
            raise RuntimeError(f"batch_{batch_index}_embedding_failed")

    logger.info(
        "embedding_pipeline_completed",
        total_vectors_generated=len(embedded_vectors),
        total_latency_seconds=round(total_latency, 4),
    )
    return embedded_vectors
