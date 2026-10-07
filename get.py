"""Command-line client for the local, non-WhatsApp development simulator."""

import argparse
import sys

import httpx

from app.config import get_settings


def main() -> None:
    parser = argparse.ArgumentParser(description="Send a message to the local assistant simulator")
    parser.add_argument("text", help="message text to simulate")
    parser.add_argument(
        "--sender", required=True, help="test sender number in international digits"
    )
    parser.add_argument("--url", default="http://127.0.0.1:8000")
    args = parser.parse_args()
    token = get_settings().admin_api_token.get_secret_value()
    if not token:
        raise SystemExit("Set ADMIN_API_TOKEN in .env first")
    try:
        response = httpx.post(
            f"{args.url.rstrip('/')}/dev/messages",
            headers={"Authorization": f"Bearer {token}"},
            json={"sender": args.sender, "text": args.text},
            timeout=60.0,
        )
        response.raise_for_status()
    except httpx.HTTPError as exc:
        print(f"Simulator request failed: {type(exc).__name__}", file=sys.stderr)
        raise SystemExit(1) from exc
    print(response.json()["reply"])


if __name__ == "__main__":
    main()
