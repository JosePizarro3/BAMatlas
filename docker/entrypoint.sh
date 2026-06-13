#!/bin/sh
set -eu

# Keep container startup predictable for BAM IT: apply schema changes and
# collect static assets before the web process starts serving traffic.
python manage.py migrate --noinput
python manage.py collectstatic --noinput

if [ "${1:-}" = "gunicorn" ]; then
  shift
  set -- gunicorn \
    --bind "0.0.0.0:${PORT:-8000}" \
    --workers "${WEB_CONCURRENCY:-2}" \
    --access-logfile - \
    --error-logfile - \
    "$@"
fi

exec "$@"
