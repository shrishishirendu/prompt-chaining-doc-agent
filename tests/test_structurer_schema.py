import json
import os
from pathlib import Path

import pytest
import yaml
from jsonschema import validate

from agents.structurer import run_structurer

ROOT_DIR = Path(__file__).resolve().parents[1]
SCHEMA_PATH = ROOT_DIR / "schemas" / "outline.schema.json"
CONFIG_PATH = ROOT_DIR / "config.yaml"


def load_schema() -> dict:
    return json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))


def load_config() -> dict:
    return yaml.safe_load(CONFIG_PATH.read_text(encoding="utf-8")) or {}


def test_structurer_output_matches_schema() -> None:
    if not os.getenv("OPENAI_API_KEY"):
        pytest.skip("OPENAI_API_KEY not set.")

    config = load_config()
    facts = {
        "facts": [
            "Revenue was up 12% versus last quarter.",
            "Refunds spiked around week 6.",
            "Customer churn is highest in the EU region.",
        ]
    }
    outline = run_structurer(facts, config)

    validate(instance=outline, schema=load_schema())
    assert outline["sections"]
