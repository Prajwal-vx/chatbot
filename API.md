# API

## Public routes

- `GET /admin/setup`: setup page for the business display number and Meta Phone
  Number ID. The page itself is public; saving/loading requires the admin bearer token.
- `GET /health`: readiness status for PostgreSQL and Redis.
- `GET /webhooks/whatsapp`: Meta subscription handshake (`hub.mode`,
  `hub.verify_token`, and `hub.challenge`).
- `POST /webhooks/whatsapp`: validates the raw-body signature, parses inbound text,
  enforces a per-sender limit, deduplicates message IDs, and queues work.

## Admin routes

Send `Authorization: Bearer $ADMIN_API_TOKEN`:

- `GET /admin/settings/whatsapp`: load the saved business number configuration.
- `PUT /admin/settings/whatsapp`: save `{"display_number":"+...","phone_number_id":"..."}`.
- `GET /admin/conversations`: latest 200 conversation states (no message bodies).
- `GET /admin/conversations/{sender}/memories`: review saved memories.
- `DELETE /admin/conversations/{sender}/memories`: delete saved memories.
- `PATCH /admin/conversations/{sender}`: update `paused` and
  `handoff_requested` state.
- `DELETE /admin/conversations/{sender}`: delete the conversation, messages, and
  memories.

## Development simulator

`POST /dev/messages` accepts `{"sender":"9779800000000","text":"Namaste"}` and
returns a generated reply without sending a WhatsApp message. Enable it with
`ENABLE_DEV_SIMULATOR=true`; it is disabled in production and requires the admin
bearer token. It still stores the conversation in PostgreSQL.
