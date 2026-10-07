# Build report

## Implemented

- Replaced desktop WhatsApp Web automation with an official Meta Cloud API service.
- FastAPI health and webhook routes, subscription handshake, HMAC validation,
  malformed-event handling, body bounds, and per-sender Redis rate limiting.
- Timestamp-gated free-form replies that are dropped when outside WhatsApp's
  24-hour customer-service window; no unapproved template fallback.
- Atomic message-ID deduplication and Redis Streams consumer group with abandoned
  delivery recovery, bounded retry, dead-letter stream, and fallback response.
- PostgreSQL conversation/message/memory models and Alembic initial migration.
- Ollama/OpenAI provider switch, bounded history/input/output, language cues for
  English, Nepali, Hindi, and Maithili/code-switching, plus concise response policy.
- Explicit `/remember`, `/memories`, `/forget`, `/forget-all`, pause/resume/stop,
  and handoff flags. Control acknowledgements use the saved conversation language.
- Admin conversation deletion and scheduled deletion of inactive conversations
  (30-day default, configurable).
- Password-protected admin routes, development simulator that does not send
  WhatsApp messages, restricted calculator, and local timezone lookup.
- Admin setup page to save the WhatsApp Business display number and Meta Phone
  Number ID. Webhook events are matched to that ID, and replies are sent from it.
- Dockerfile, Compose stack, setup/test scripts, CI workflow, project documentation,
  and OpenCode commands/roles.

## Requires configuration

- `.env` values for Meta API credentials, provider, database/Redis, verification
  and admin tokens; the business display number and Phone Number ID are saved via
  `/admin/setup`.
- Public HTTPS callback URL and `messages` subscription configured in Meta.
- Docker engine and Ollama/model or OpenAI account. No external credentials were
  available for a live integration test.

## Not implemented / production follow-up

- Media processing, live staff notification for handoff, web search/weather, message
  summarization, metrics/dashboard, and full
  multi-instance reliability/security review.
- Conversation messages are stored in PostgreSQL for context and deleted with the
  conversation after configured inactivity. Validate this policy and backups before
  handling real customer data.
- Consent is represented by inbound user initiation and `/stop`; a configurable
  consent ledger and support for approved business-initiated templates are not built.
- Full Meta policy validation and production delivery windows have not been tested.

## Verification performed

- `python -m unittest discover -s tests -v` using the bundled runtime: **7 tests passed**,
  including incoming WhatsApp Phone Number ID parsing.
- `ruff check .`: **passed**.
- `ruff format --check .`: **passed** after formatting.
- Python syntax parsing: **passed** for repository source files.
- `git diff --check`: **passed**.
- `docker compose config --quiet`: **passed** (using `.env.example` for validation).
- `pytest`, `mypy`, and `pip-audit` could not be run: pytest/mypy are unavailable in
  the bundled Python and package downloads fail because PyPI DNS is unavailable.
- Docker engine is not running; PostgreSQL, Redis, Ollama, and Meta API operations
  were not exercised. Compose, migration execution, and end-to-end flow remain
  unverified in this environment.

## Versions and files

The Docker image uses Python 3.12; dependency ranges are in `pyproject.toml`,
`requirements.txt`, and `requirements-dev.txt`. The Meta Graph API default is
`v26.0`, configurable via `WHATSAPP_API_VERSION`.

Added the FastAPI application, migration, tests, deployment/docs, scripts, and
OpenCode project files; updated `mani.py`, `get.py`, dependency files, and Compose;
replaced the old standalone OpenAI example with a configured provider smoke test.
