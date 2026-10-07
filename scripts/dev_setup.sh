#!/usr/bin/env sh
set -eu
if [ ! -f .env ]; then
  cp .env.example .env
  echo "Created .env. Set ADMIN_API_TOKEN and WHATSAPP_VERIFY_TOKEN before continuing."
fi
python -m pip install -r requirements-dev.txt
docker compose up -d postgres redis
python -m alembic upgrade head
