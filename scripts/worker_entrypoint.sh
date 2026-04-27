#!/bin/bash

# Run hardware check to get recommended concurrency
CONCURRENCY=$(python scripts/check_hardware.py | grep "Recommended Celery Concurrency:" | awk '{print $4}')

if [ -z "$CONCURRENCY" ]; then
  CONCURRENCY=1
fi

echo "Starting Celery with concurrency: $CONCURRENCY"

exec celery -A src.worker.celery_app worker --loglevel=info --concurrency=$CONCURRENCY
