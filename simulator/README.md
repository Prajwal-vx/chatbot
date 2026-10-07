# Local message simulator

Set `ENABLE_DEV_SIMULATOR=true`, set `ADMIN_API_TOKEN`, start the API, and apply
the database migration. Then run:

```powershell
python get.py --sender 9779800000000 "Namaste, k xa?"
```

The development route stores simulated conversation turns and returns an AI reply.
It never sends a WhatsApp message and is unavailable in production.
