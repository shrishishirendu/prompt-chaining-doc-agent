import os
import json
from pathlib import Path

import pytest
import yaml
from jsonschema import validate

from agents.extractor import run_extractor

ROOT_DIR = Path(__file__).resolve().parents[1]
SCHEMA_PATH = ROOT_DIR / "schemas" / "facts.schema.json"
SAMPLE_DOC = ROOT_DIR / "sample_docs" / "sample.txt"
CONFIG_PATH = ROOT_DIR / "config.yaml"


def load_schema() -> dict:
    return json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))


def load_config() -> dict:
    return yaml.safe_load(CONFIG_PATH.read_text(encoding="utf-8")) or {}


def test_extractor_output_matches_schema() -> None:
    if not os.getenv("OPENAI_API_KEY"):
        pytest.skip("OPENAI_API_KEY not set.")

    config = load_config()
    raw_text = SAMPLE_DOC.read_text(encoding="utf-8")
    facts = run_extractor(raw_text, config)

    validate(instance=facts, schema=load_schema())
    assert len(facts["facts"]) >= 3