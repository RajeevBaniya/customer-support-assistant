import asyncio
import threading
from typing import Any

import numpy as np
from sentence_transformers import SentenceTransformer

from src.core.appEnvironment import AppEnvironment
from src.embeddings.embeddingBatch import batch_texts
from src.embeddings.embeddingProvider import EmbeddingProvider

_lock = threading.Lock()
_models: dict[str, SentenceTransformer] = {}


def model_is_cached(model_name: str) -> bool:
    return model_name in _models


def _get_model(model_name: str) -> SentenceTransformer:
    with _lock:
        if model_name not in _models:
            _models[model_name] = SentenceTransformer(model_name)
        return _models[model_name]


class HuggingFaceEmbeddingProvider(EmbeddingProvider):
    def __init__(self, settings: AppEnvironment) -> None:
        self._name = settings.resolved_embedding_model

    async def encode_batch(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []

        def _encode(batch: list[str]) -> Any:
            model = _get_model(self._name)
            return model.encode(batch, normalize_embeddings=True)

        raw = await asyncio.to_thread(_encode, texts)
        arr = np.atleast_2d(np.asarray(raw, dtype=np.float32))
        return [arr[i].tolist() for i in range(arr.shape[0])]


async def embed_texts_batched(settings: AppEnvironment, texts: list[str]) -> list[list[float]]:
    provider = HuggingFaceEmbeddingProvider(settings)
    out: list[list[float]] = []
    for batch in batch_texts(texts, settings.embedding_batch_size):
        out.extend(await provider.encode_batch(batch))
    return out
