"""Extractor agent: pull atomic, source-grounded facts from raw text."""
from __future__ import annotations

import json
from pathlib import Path

from jsonschema import validate

from llm_client import chat_completion, get_client_from_env_and_config

ROOT_DIR = Path(__file__).resolve().parents[1]
PROMPT_PATH = ROOT_DIR / "prompts" / "extract.txt"
SCHEMA_PATH = ROOT_DIR / "schemas" / "facts.schema.json"


def _load_prompt() -> str:
    return PROMPT_PATH.read_text(encoding="utf-8")


def _load_schema() -> dict:
    return json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))


def _parse_json_or_repair(raw_text: str, config: dict) -> dict:
    try:
        return json.loads(raw_text)
    except json.JSONDecodeError:
        client = get_client_from_env_and_config(config)
        repair_messages = [
            {
                "role": "system",
                "content": "Return valid JSON only. No markdown or explanation.",
            },
            {
                "role": "user",
                "content": (
                    "Fix this into valid JSON with shape {\"facts\":[...]} only.\n\n"
                    f"Content:\n{raw_text}"
                ),
            },
        ]
        repaired = chat_completion(
            client=client,
            model=config.get("model", "gpt-4.1-mini"),
            messages=repair_messages,
            temperature=0.0,
            max_tokens=config.get("max_tokens", 1200),
        )
        return json.loads(repaired)


def _normalize_facts(facts: list) -> list[str]:
    cleaned = []
    seen = set()
    for fact in facts:
        if not isinstance(fact, str):
            continue
        text = fact.strip()
        if not text:
            continue
        if len(text) > 140:
            text = text[:140]
        if text in seen:
            continue
        cleaned.append(text)
        seen.add(text)
    return cleaned


def run_extractor(text: str, config: dict) -> dict:
    """Extract atomic facts from unstructured text."""
    prompt = _load_prompt()
    client = get_client_from_env_and_config(config)

    messages = [
        {"role": "system", "content": prompt},
        {"role": "user", "content": text},
    ]

    raw = chat_completion(
        client=client,
        model=config.get("model", "gpt-4.1-mini"),
        messages=messages,
        temperature=config.get("temperature", 0.2),
        max_tokens=config.get("max_tokens", 1200),
    )

    data = _parse_json_or_repair(raw, config)
    if not isinstance(data, dict) or "facts" not in data:
        raise ValueError("Extractor output missing 'facts' key.")

    facts = _normalize_facts(data.get("facts", []))
    result = {"facts": facts}

    validate(instance=result, schema=_load_schema())
    return result