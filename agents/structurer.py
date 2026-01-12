"""Structurer agent: organize extracted facts into a coherent outline."""
from __future__ import annotations

import json
from pathlib import Path

from jsonschema import validate

from llm_client import chat_completion, get_client_from_env_and_config

ROOT_DIR = Path(__file__).resolve().parents[1]
PROMPT_PATH = ROOT_DIR / "prompts" / "structure.txt"
SCHEMA_PATH = ROOT_DIR / "schemas" / "outline.schema.json"


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
                    "{\"title\":\"...\",\"sections\":[{\"heading\":\"...\",\"bullets\":[...]}]} only.\n\n"
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


def _normalize_outline(data: dict) -> dict:
    title = data.get("title")
    if not isinstance(title, str):
        title = ""
    title = title.strip()

    sections = []
    raw_sections = data.get("sections", [])
    if isinstance(raw_sections, list):
        for section in raw_sections:
            if not isinstance(section, dict):
                continue
            heading = section.get("heading", "")
            if not isinstance(heading, str):
                heading = ""
            heading = heading.strip()

            bullets = []
            seen = set()
            raw_bullets = section.get("bullets", [])
            if isinstance(raw_bullets, list):
                for bullet in raw_bullets:
                    if not isinstance(bullet, str):
                        continue
                    text = bullet.strip()
                    if not text or text in seen:
                        continue
                    bullets.append(text)
                    seen.add(text)

            if heading or bullets:
                sections.append({"heading": heading, "bullets": bullets})

    return {"title": title, "sections": sections}


def run_structurer(facts: dict, config: dict) -> dict:
    """Transform facts into a structured outline."""
    prompt = _load_prompt()
    client = get_client_from_env_and_config(config)

    messages = [
        {"role": "system", "content": prompt},
        {"role": "user", "content": json.dumps(facts, indent=2)},
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
        raise ValueError("Structurer output is not a JSON object.")

    outline = _normalize_outline(data)
    validate(instance=outline, schema=_load_schema())
    return outline
