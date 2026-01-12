import json
import os
from pathlib import Path

import pytest
import yaml
from jsonschema import validate

from agents.validator import run_validator

ROOT_DIR = Path(__file__).resolve().parents[1]
SCHEMA_PATH = ROOT_DIR / "schemas" / "validation.schema.json"
CONFIG_PATH = ROOT_DIR / "config.yaml"


def load_schema() -> dict:
    return json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))


def load_config() -> dict:
    return yaml.safe_load(CONFIG_PATH.read_text(encoding="utf-8")) or {}


def test_validator_output_matches_schema() -> None:
    if not os.getenv("OPENAI_API_KEY"):
        pytest.skip("OPENAI_API_KEY not set.")

    config = load_config()
    facts = {
        "facts": [
            "Revenue was up 12% versus last quarter.",
            "Refunds spiked around week 6.",
        ]
    }
    outline = {
        "title": "Q3 Launch Notes",
        "sections": [
            {
                "heading": "Performance",
                "bullets": [
                    "Revenue was up 12% versus last quarter.",
                    "Refunds spiked around week 6.",
                ],
            }
        ],
    }
    summary = {
        "tldr": "Revenue improved but refunds need review.",
        "key_points": ["Revenue up 12%."],
        "risks": ["Refund spike could indicate product issues."],
        "recommendations": ["Investigate refund causes."],
    }
    validation = run_validator(facts, outline, summary, config)

    validate(instance=validation, schema=load_schema())
