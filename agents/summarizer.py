"""Summarizer agent: generate an executive summary from the outline."""
from __future__ import annotations

import json
from pathlib import Path

from jsonschema import validate

from llm_client import chat_completion, get_client_from_env_and_config

ROOT_DIR = Path(__file__).resolve().parents[1]
PROMPT_PATH = ROOT_DIR / "prompts" / "summarize.txt"
SCHEMA_PATH = ROOT_DIR / "schemas" / "summary.schema.json"


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
                    "Fix this into valid JSON with shape "
                    "{\"tldr\":\"...\",\"key_points\":[...],\"risks\":[...],\"recommendations\":[...]} only.\n\n"
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


def _clean_list(values: list) -> list[str]:
    cleaned = []
    seen = set()
    for value in values:
        if not isinstance(value, str):
            continue
        text = value.strip()
        if not text or text in seen:
            continue
        cleaned.append(text)
        seen.add(text)
    return cleaned


def _normalize_summary(data: dict) -> dict:
    tldr = data.get("tldr", "")
    if not isinstance(tldr, str):
        tldr = ""
    tldr = tldr.strip()

    key_points = _clean_list(data.get("key_points", []))
    risks = _clean_list(data.get("risks", []))
    recommendations = _clean_list(data.get("recommendations", []))

    return {
        "tldr": tldr,
        "key_points": key_points,
        "risks": risks,
        "recommendations": recommendations,
    }


def run_summarizer(outline: dict, config: dict) -> dict:
    """Summarize the outline for executive consumption."""
    prompt = _load_prompt()
    client = get_client_from_env_and_config(config)

    messages = [
        {"role": "system", "content": prompt},
        {"role": "user", "content": json.dumps(outline, indent=2)},
    ]

    raw = chat_completion(
        client=client,
        model=config.get("model", "gpt-4.1-mini"),
        messages=messages,
        temperature=config.get("temperature", 0.2),
        max_tokens=config.get("max_tokens", 1200),
    )

    data = _parse_json_or_repair(raw, config)
    if not isinstance(data, dict):
        raise ValueError("Summarizer output is not a JSON object.")

    summary = _normalize_summary(data)
    validate(instance=summary, schema=_load_schema())
    return summary
