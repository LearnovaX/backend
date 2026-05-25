#!/bin/sh
set -eu

python manage.py migrate --noinput
python manage.py collectstatic --noinput

exec daphne \
    -b 0.0.0.0 \
    -p 8000 \
    src.core.asgi:application