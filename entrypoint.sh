#!/bin/sh
set -eu

echo "START MIGRATIONS"
python manage.py migrate --noinput
echo "MIGRATIONS DONE"

echo "START COLLECTSTATIC IN BACKGROUND"
(
  python manage.py collectstatic --noinput \
    && echo "COLLECTSTATIC DONE" \
    || echo "COLLECTSTATIC FAILED"
) &

echo "START DAPHNE"

exec daphne \
    -b 0.0.0.0 \
    -p 8000 \
    src.core.asgi:application