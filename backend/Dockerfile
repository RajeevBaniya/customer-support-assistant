FROM python:3.12-slim AS builder

WORKDIR /build

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

RUN apt-get update \
    && apt-get install -y --no-install-recommends build-essential \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --upgrade pip \
    && pip wheel --no-cache-dir --wheel-dir /wheels -r requirements.txt


FROM python:3.12-slim AS runtime

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    HF_HOME=/app/.cache/huggingface \
    TRANSFORMERS_CACHE=/app/.cache/huggingface \
    SENTENCE_TRANSFORMERS_HOME=/app/.cache/sentence-transformers

RUN apt-get update \
    && apt-get install -y --no-install-recommends tini \
    && rm -rf /var/lib/apt/lists/* \
    && groupadd --system recallstack \
    && useradd --system --gid recallstack --home-dir /app recallstack \
    && mkdir -p /app/.cache/huggingface /app/.cache/sentence-transformers \
    && chown -R recallstack:recallstack /app

COPY --from=builder /wheels /wheels
COPY requirements.txt .
RUN pip install --upgrade pip \
    && pip install --no-cache-dir /wheels/* \
    && rm -rf /wheels

COPY alembic.ini .
COPY alembic ./alembic
COPY src ./src
COPY docker ./docker

RUN chmod +x docker/api-entrypoint.sh docker/celery-entrypoint.sh docker/migrate-entrypoint.sh \
    && chown -R recallstack:recallstack /app

USER recallstack

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=45s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/live', timeout=4)"

ENTRYPOINT ["/usr/bin/tini", "--"]
CMD ["docker/api-entrypoint.sh"]
