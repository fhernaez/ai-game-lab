#!/bin/sh
set -e

# Wait for the database to accept connections before proceeding.
if [ -n "$POSTGRES_HOST" ]; then
  python - "$POSTGRES_HOST" "${POSTGRES_PORT:-5432}" <<'PY'
import socket
import sys
import time

host, port = sys.argv[1], int(sys.argv[2])
for _ in range(120):
    try:
        socket.create_connection((host, port), timeout=2).close()
        sys.exit(0)
    except OSError:
        time.sleep(1)
sys.exit(1)
PY
fi

# Migrate (and optionally seed) unless explicitly disabled. The worker service sets
# RUN_MIGRATIONS=false so only the web service migrates on boot.
if [ "${RUN_MIGRATIONS:-true}" != "false" ]; then
  flask --app run.py db upgrade

  if [ "$SEED_ON_START" = "true" ]; then
    flask --app run.py seed
  fi
fi

exec "$@"
