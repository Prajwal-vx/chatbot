# Troubleshooting

- **Health is degraded:** check PostgreSQL/Redis availability and database
  migrations (`alembic upgrade head`).
- **Meta cannot verify the callback:** expose `/webhooks/whatsapp` over HTTPS and
  match the configured verify token exactly.
- **Webhook returns 401:** configure the matching Meta app secret and send the
  exact `X-Hub-Signature-256` header.
- **Worker retries then dead-letters:** inspect service availability and credentials;
  dead-letter payloads are in Redis stream `whatsapp:dead-letter`.
- **Ollama unavailable in Compose:** use `http://host.docker.internal:11434/v1` on
  Docker Desktop, ensure Ollama is running, and pull the configured model.
- **OpenAI provider error:** set `AI_PROVIDER=openai`, `OPENAI_API_KEY`, and a model
  name available to the account.
