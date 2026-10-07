"""Compatibility entry point for the official WhatsApp Cloud API service.

The former desktop automation used WhatsApp Web. That integration has been
removed; use Meta's official Cloud API webhook and run the FastAPI service.
"""

from app.main import app

__all__ = ["app"]
