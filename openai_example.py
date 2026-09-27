"""Optional OpenAI SDK example; importing this module makes no API request.

Set OPENAI_API_KEY in the environment before running this example. Keep API
keys out of source files and chat transcripts.
"""

import os

from openai import OpenAI


def main() -> None:
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        raise SystemExit("Set OPENAI_API_KEY in the environment first.")

    client = OpenAI(api_key=api_key, timeout=30.0, max_retries=2)
    completion = client.chat.completions.create(
        model="gpt-3.5-turbo",
        messages=[
            {"role": "system", "content": "Reply briefly and helpfully."},
            {"role": "user", "content": "Say hello."},
        ],
        max_tokens=100,
    )
    print(completion.choices[0].message.content or "")


if __name__ == "__main__":
    main()
