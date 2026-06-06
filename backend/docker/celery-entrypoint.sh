#!/bin/sh
set -eu

exec celery -A src.jobs.celeryApp:celery_app worker \
  --loglevel="${CELERY_LOG_LEVEL:-info}" \
  --concurrency="${CELERY_CONCURRENCY:-2}" \
  --queues="${CELERY_QUEUES:-recallstack_default}" \
  --hostname="${CELERY_HOSTNAME:-recallstack-worker@%h}"
