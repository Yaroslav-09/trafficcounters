#!/usr/bin/env bash
# Build příkaz pro Render
set -o errexit

pip install -r requirements.txt
python manage.py collectstatic --noinput
python manage.py migrate --noinput
