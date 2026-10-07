# WhatsApp AI Assistant

Python service for multilingual replies through Meta's official WhatsApp Cloud API.
It replaces the former WhatsApp Web screen automation. Incoming text is checked,
deduplicated, and queued; a separate worker handles conversations and sends replies.

## Quick start

1. Copy `.env.example` to `.env` and set a long random `WHATSAPP_VERIFY_TOKEN` and
   `ADMIN_API_TOKEN`. Configure the Meta app secret and Cloud API access token in
   `.env`; set `APP_ENV=production` for production.
2. Start Docker Desktop. Start local Ollama and pull the model in `.env`, or choose
   the OpenAI provider and add an API key.
3. Run `docker compose up --build -d`. Compose starts PostgreSQL and Redis, applies
   Alembic migrations, and then launches the API and worker.
4. Open `http://localhost:8000/admin/setup`, enter the admin token, WhatsApp
   Business display number, and Meta Phone Number ID, then save. The ID is available
   in Meta's WhatsApp API setup. The setup page does not store API secrets.
5. Configure the public HTTPS webhook and subscribe to `messages` as described
   below. Open `http://localhost:8000/health`; readiness is `ok` when Redis,
   PostgreSQL, and a WhatsApp number are configured.
6. For local messages, set `ENABLE_DEV_SIMULATOR=true` and send a test message with
   `python get.py --sender 9779800000000 "Namaste, k xa?"`.

For direct host development, install dependencies with `python -m pip install -r
requirements-dev.txt`, run `alembic upgrade head`, then start `uvicorn app.main:app
--reload` and `python -m app.worker` in separate terminals.

## WhatsApp setup

The number must be connected to Meta's WhatsApp Cloud API; entering an ordinary
WhatsApp number alone cannot receive automated replies. Expose
`/webhooks/whatsapp` over HTTPS, configure the callback and matching verify token
in Meta, and subscribe to `messages`. The endpoint verifies Meta's request
signature when `WHATSAPP_APP_SECRET` is configured and requires it in production.
Incoming webhook events are matched against the configured Phone Number ID. The
worker sends a reply to the inbound sender from that business number using the
configured Graph API version. Provide an approved template for any business-initiated
messages; this application currently only sends replies to inbound text events.

Meta's current [Business Messaging Policy](https://business.whatsapp.com/policy/)
defines the customer-service window and template requirements. The official
[WhatsApp Cloud API message collection](https://www.postman.com/meta/whatsapp-business-platform/folder/13382743-ba8d099d-007e-4b52-b9f2-3cf3c60e4fbc)
documents the phone-number `/messages` endpoint used by this service.

## User controls

- `/stop` and `/pause`: stop automatic replies. `/start` or `/resume`: continue.
- `/remember <preference>`: explicitly save a non-sensitive preference.
- `/memories`: review saved memories. `/forget`: remove memories. `/forget-all`:
  remove saved history and memories for the conversation.
- `/human` or `/handoff`: pause the bot and flag the conversation for staff review.
  There is no live staff notification configured yet.

## API and operations

See [API.md](API.md), [DATABASE.md](DATABASE.md), [SECURITY.md](SECURITY.md),
[DEPLOYMENT.md](DEPLOYMENT.md), and [TROUBLESHOOTING.md](TROUBLESHOOTING.md).
Run `pytest -q`, `ruff check .`, `ruff format --check .`, `mypy app`, and
`pip-audit` to verify the installed environment. Unit tests also run with
`python -m unittest discover -s tests -v` without pytest.

The current implementation handles text only. External search/weather tools,
media processing, live human notification, a web admin dashboard, and multi-instance
production hardening still need work. Inactive conversations are removed after the
configured retention period. See
[BUILD_REPORT.md](BUILD_REPORT.md) for implementation and verification status.
