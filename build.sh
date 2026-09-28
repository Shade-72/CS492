#!/usr/bin/env bash
# Render's build command for this service. Configure it in the dashboard
# (or via render.yaml, already set up below) as:
#   ./build.sh
set -o errexit

pip install -r requirements.txt

python manage.py collectstatic --no-input
python manage.py migrate
