#!/bin/bash
set -e -x

    # Init database
    echo 'Applying migrations...'
    uv run --frozen --no-sync alembic upgrade head

# Init app
echo "Starting the FastAPI application..."
if [ "$ENVIRONMENT" = "local" ]; then
    uv run --frozen --no-sync fastapi dev app/main.py --host 0.0.0.0 --port 8000
else
    uv run --frozen --no-sync fastapi run app/main.py --host 0.0.0.0 --port 8000
fi
