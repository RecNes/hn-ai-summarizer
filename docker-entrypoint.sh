#!/bin/bash
set -e

echo "[ENTRYPOINT] Starting HN-AI-Summerizer..."

# Run Alembic migrations
echo "[ENTRYPOINT] Running database migrations..."
alembic upgrade head
echo "[ENTRYPOINT] Migrations complete."

# Execute the main command (passed as arguments to this script)
exec "$@"