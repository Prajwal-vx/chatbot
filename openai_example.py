"""Generate one example reply through the configured provider."""

import asyncio

from app.ai import AIProvider
from app.config import get_settings


async def main() -> None:
    provider = AIProvider(get_settings())
    try:
        print(await provider.reply("Please greet me briefly in English."))
    finally:
        await provider.client.close()


if __name__ == "__main__":
    asyncio.run(main())
