#!/bin/sh
set -eu

exec uvicorn src.main:app \
  --host 0.0.0.0 \
  --port "${BACKEND_PORT:-8000}" \
  --timeout-graceful-shutdown 30 \
  --lifespan on
