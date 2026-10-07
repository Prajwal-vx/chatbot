# Deployment

1. Provision PostgreSQL, Redis, a model provider, and a publicly reachable HTTPS
   ingress. Use managed secrets rather than committing `.env`.
2. Create `.env` from `.env.example`; supply Meta credentials and a strong admin
   token. Verify that the configured Graph API version is enabled for the Meta app.
3. Run `docker compose up --build -d`. Compose migrates PostgreSQL before starting
   the API and worker. The default Ollama URL in Compose targets the host machine;
   for production, point `OLLAMA_BASE_URL` at the actual model service.
4. Open `https://<host>/admin/setup` and save the WhatsApp Business display number
   and Meta Phone Number ID. The number must already be connected to WhatsApp Cloud
   API. Keep the access token, app secret, and verification token in managed server
   secrets; the setup page does not store them.
5. Configure the Meta callback URL as `https://<host>/webhooks/whatsapp`, use the
   same verification token, and subscribe to `messages`.
6. Check `/health`, then test with a Meta test number and a permitted recipient.

The worker refuses free-form messages when the inbound timestamp is missing or the
customer-service window has expired. Approved template sends outside that window
must be implemented separately if the product needs them. Check the latest
[WhatsApp Business Messaging Policy](https://business.whatsapp.com/policy/) before
launch because Meta can update messaging rules and template restrictions.

Production still requires TLS, firewall restrictions for admin routes, database
retention and backup policy, monitoring/alerts, and operational staff procedures
for handoff/dead-letter review. Compose is for development and a small single-host
deployment, not a high-availability topology.
