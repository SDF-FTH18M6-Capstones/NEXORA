#!/bin/sh
# Container entrypoint. Set RUN_MIGRATIONS=1 on the host to apply
# `flask db upgrade` before the server starts (use it with ONE instance).
set -e

if [ "${RUN_MIGRATIONS:-0}" = "1" ]; then
  echo "Running database migrations..."
  flask --app app db upgrade
fi

exec gunicorn "app:create_app()" \
  --bind "0.0.0.0:${PORT:-10000}" \
  --workers "${WEB_CONCURRENCY:-2}" \
  --timeout 60 \
  --access-logfile - \
  --error-logfile -
