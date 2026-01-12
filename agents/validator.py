"""Validator agent: check outputs for consistency and unsupported claims."""
from __future__ import annotations

import json
from pathlib import Path

from jsonschema import validate

from llm_client import chat_completion, get_client_from_env_and_config

ROOT_DIR = Path(__file__).resolve().parents[1]
PROMPT_PATH = ROOT_DIR / "prompts" / "validate.txt"
SCHEMA_PATH = ROOT_DIR / "schemas" / "validation.schema.json"


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
                    "{\"coverage_score\":0,\"unsupported_claims\":[],\"missing_topics\":[],\"issues\":[]} only.\n\n"
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


def _normalize_validation(data: dict) -> dict:
    coverage_score = data.get("coverage_score")
    if not isinstance(coverage_score, (int, float)):
        coverage_score = 0
    coverage_score = max(0, min(100, float(coverage_score)))

    unsupported_claims = _clean_list(data.get("unsupported_claims", []))
    missing_topics = _clean_list(data.get("missing_topics", []))
    issues = _clean_list(data.get("issues", []))

    return {
        "coverage_score": coverage_score,
        "unsupported_claims": unsupported_claims,
        "missing_topics": missing_topics,
        "issues": issues,
    }


def run_validator(facts: dict, outline: dict, summary: dict, config: dict) -> dict:
    """Validate outputs for coverage and unsupported statements."""
    prompt = _load_prompt()
    client = get_client_from_env_and_config(config)

    payload = {
        "facts": facts,
        "outline": outline,
        "summary": summary,
    }
    messages = [
        {"role": "system", "content": prompt},
        {"role": "user", "content": json.dumps(payload, indent=2)},
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
        raise ValueError("Validator output is not a JSON object.")

    validation = _normalize_validation(data)
    validate(instance=validation, schema=_load_schema())
    return validation
