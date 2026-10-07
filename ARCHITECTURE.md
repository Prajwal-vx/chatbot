# Architecture

```text
WhatsApp Cloud API -> FastAPI webhook -> Redis Stream -> worker
                                                   |-> PostgreSQL history/memory
                                                   |-> Ollama or OpenAI
                                                   `-> Meta Cloud API send endpoint
```

The webhook returns after signature checks and atomic deduplication/queue
insertion. Redis consumer groups allow recovery of messages abandoned by crashes.
PostgreSQL stores conversation history and explicit memories. User controls and
deterministic tools run before model generation. The local simulator uses the same
conversation engine but never calls the WhatsApp sender.

Unsupported incoming media types and status events are ignored. No WhatsApp Web or
browser automation exists in the supported request path.
