# Security notes

- WhatsApp traffic uses the official Meta Cloud API only. The old desktop UI
  automation was removed.
- Configure `WHATSAPP_APP_SECRET`; production refuses inbound webhooks when the
  secret is missing and validates `X-Hub-Signature-256` against the exact body.
- Keep `.env` out of source control. Rotate tokens if they are exposed. Do not put
  credentials or personal data into logs.
- Admin and simulator routes require a bearer token. Use a long random
  `ADMIN_API_TOKEN`, TLS at the reverse proxy, and restrict admin access by network.
- Inbound bodies, message lengths, context, output, and per-sender message rate are
  bounded. The Redis stream uses consumer groups, retries, and a dead-letter stream.
- Rate-limit keys expire after one minute. Incoming/retry streams are bounded by
  length; dead-letter entries keep only message IDs and a hashed sender, not message
  bodies. Configure Redis persistence and backups for deployment recovery needs.
- Long-term memory is only created by an explicit `/remember` command. The service
  rejects obvious passwords, codes, financial details, and secrets; `/memories` and
  `/forget` let the user review/delete memories.
- `/stop` and `/pause` disable automatic replies; `/start` and `/resume` re-enable.
- Free-form replies are sent only for timestamped inbound events still inside the
  24-hour customer-service window. Older/retried events are dropped; approved
  template messaging is not implemented.
- `/human` pauses the assistant and records a handoff request. Staff notification is
  not configured yet, so the user is told that explicitly.
- Message history is stored in PostgreSQL for conversation context. Inactive
  conversations, messages, and memories are deleted after `MESSAGE_RETENTION_DAYS`
  (30 by default); users can send `/forget-all`, and admins can delete a conversation.
  Configure database backups and test restore/deletion behavior before production.
- Tool execution is restricted to a small AST-validated arithmetic calculator and
  local timezone lookup. No arbitrary shell, file, or network tool is exposed.
- Deployment still needs a security review, reverse-proxy TLS, admin network policy,
  database credentials and backup policy, and verification against a Meta test app.
