# Implementation plan and status

## Architecture

Meta WhatsApp Cloud API posts webhooks to FastAPI. The API validates the handshake
and HMAC signature, parses text events, rate limits per sender, deduplicates message
IDs, and atomically pushes them into a Redis Stream. A consumer-group worker writes
conversation history to PostgreSQL, handles consent and memory commands, generates
a language-matched response through Ollama/OpenAI, and sends through Meta's Graph API.

## Phases

1. **Foundation — implemented:** settings, FastAPI, health, package metadata, Compose,
   Dockerfile, docs, structured entrypoint.
2. **WhatsApp webhook — implemented:** verification, HMAC, parsing, size bound,
   per-sender rate limit, atomic duplicate protection.
3. **WhatsApp sender — implemented:** authenticated official text-message endpoint.
4. **Queue and worker — implemented:** Redis streams, consumer group, reclaim,
   bounded retries, dead-letter stream, fallback response.
5. **Database — implemented:** conversations, messages, explicit memories, Alembic
   initial migration, bounded recent-history retrieval.
6. **AI and language — implemented:** Ollama/OpenAI adapter, basic script/romanized
   language cues, context/memory, token and character bounds.
7. **Privacy and operations — partly implemented:** `/stop`, `/pause`, `/start`,
   `/remember`, `/memories`, `/forget`, `/human`, admin API, simulator, basic tools.
8. **Remaining:** media, external search/weather, human notification, summarization,
   automatic data retention, metrics/dashboard, full security and live integration QA.

## Key files

- `app/main.py`: webhook, health, admin, and local simulator endpoints.
- `app/conversation_engine.py`: command handling and response orchestration.
- `app/models.py`, `app/database.py`, `alembic/`: PostgreSQL data model and migration.
- `app/queue.py`, `app/worker.py`: durable queue consumption and processing.
- `app/ai.py`, `app/language.py`: provider and language response cues.
- `app/whatsapp.py`, `app/whatsapp_client.py`: inbound/outbound Cloud API boundary.
- `app/tools/`: restricted calculator and local timezone lookup.
- `tests/`: fast unit tests; `docker-compose.yml` provides local infrastructure.

## Dependencies

Python 3.12 Docker image; FastAPI/Pydantic, SQLAlchemy 2 with psycopg 3, Alembic,
Redis, HTTPX, and OpenAI-compatible SDK. Supported version ranges are in
`pyproject.toml` and `requirements.txt`; lock resolution in a network-enabled build
before production deployment.

## Security and rollout

Use only the official Meta Cloud API. Protect tokens in deployment secrets, require
signature verification and TLS in production, restrict the bearer-protected admin
routes, and validate Meta policy/consent setup. Apply schema migrations before
launching API/worker, back up PostgreSQL, monitor Redis dead letters, and conduct a
separate security review before onboarding customers.
