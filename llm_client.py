from __future__ import annotations

import os

from openai import OpenAI


def get_client_from_env_and_config(config: dict) -> OpenAI:
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise ValueError("OPENAI_API_KEY is not set.")

    return OpenAI(api_key=api_key)


def chat_completion(client: OpenAI, model: str, messages: list[dict], temperature: float, max_tokens: int) -> str:
    response = client.chat.completions.create(
        model=model,
        messages=messages,
        temperature=temperature,
        max_tokens=max_tokens,
    )

    message = response.choices[0].message
    return message.content or ""