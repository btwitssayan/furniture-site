#!/usr/bin/env bash
# Render build command. Any non-zero exit fails the deploy.
set -o errexit

pip install -r requirements.txt

# Hashed + gzipped static files for WhiteNoise to serve.
python manage.py collectstatic --no-input

# Schema first, then the full-text index for any rows that arrived without it
# (a restored dump, a bulk load, anything that bypassed the post_save signals).
python manage.py migrate --no-input
python manage.py rebuild_search
