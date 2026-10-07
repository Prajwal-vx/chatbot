$ErrorActionPreference = "Stop"
if (-not (Test-Path -LiteralPath ".env")) {
    Copy-Item -LiteralPath ".env.example" -Destination ".env"
    Write-Host "Created .env. Set ADMIN_API_TOKEN and WHATSAPP_VERIFY_TOKEN before continuing."
}
python -m pip install -r requirements-dev.txt
docker compose up -d postgres redis
python -m alembic upgrade head
