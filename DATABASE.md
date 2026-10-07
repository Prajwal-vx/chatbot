# Database

PostgreSQL stores one conversation per WhatsApp sender, inbound and assistant
messages, and explicit user-approved memories. Message IDs are unique for safe
webhook redelivery. Conversation/message foreign keys cascade on account deletion.
The `whatsapp_numbers` table stores the configured business display number and
Meta Phone Number ID used to match inbound webhook events and send replies.

Apply schema changes with `alembic upgrade head`; the first migration is in
`alembic/versions/0001_initial_schema.py`; the WhatsApp number settings are added
by `alembic/versions/0002_whatsapp_number_settings.py`. Compose runs migrations
before starting the API or worker. Back up the database and test restores before
production. Message retention cleanup is still a required operational follow-up.
