import json
from pathlib import Path

from jsonschema import validate

import main

ROOT_DIR = Path(__file__).resolve().parents[1]
SCHEMAS_DIR = ROOT_DIR / "schemas"


def load_schema(filename: str) -> dict:
    return json.loads((SCHEMAS_DIR / filename).read_text(encoding="utf-8"))


def test_placeholder_outputs_match_schemas() -> None:
    outputs = main.build_placeholders("Sample text for testing.")

    validate(instance=outputs["facts"], schema=load_schema("facts.schema.json"))
    validate(instance=outputs["outline"], schema=load_schema("outline.schema.json"))
    validate(instance=outputs["summary"], schema=load_schema("summary.schema.json"))
    validate(instance=outputs["validation"], schema=load_schema("validation.schema.json"))