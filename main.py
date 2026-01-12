from __future__ import annotations

import json
from pathlib import Path

import yaml
from jsonschema import validate

from agents.extractor import run_extractor
from agents.structurer import run_structurer
from agents.summarizer import run_summarizer
from agents.validator import run_validator

ROOT_DIR = Path(__file__).resolve().parent
SCHEMAS_DIR = ROOT_DIR / "schemas"
SAMPLE_DOC = ROOT_DIR / "sample_docs" / "sample.txt"
OUTPUTS_DIR = ROOT_DIR / "outputs"
CONFIG_PATH = ROOT_DIR / "config.yaml"


def load_schema(filename: str) -> dict:
    schema_path = SCHEMAS_DIR / filename
    return json.loads(schema_path.read_text(encoding="utf-8"))


def load_config() -> dict:
    return yaml.safe_load(CONFIG_PATH.read_text(encoding="utf-8")) or {}


def build_placeholders(
    doc_text: str,
    facts: dict | None = None,
    outline: dict | None = None,
    summary: dict | None = None,
    validation: dict | None = None,
) -> dict:
    facts_payload = facts or {
        "facts": [
            "Revenue is reported up 12% versus last quarter.",
            "Refunds spiked around week 6 after the quarter started.",
            "Onboarding flow shipped on 8/14 and support tickets dropped afterward.",
            "Customer churn is highest in the EU region.",
        ]
    }

    outline_payload = outline or {
        "title": "Q3 Launch Notes",
        "sections": [
            {
                "heading": "Performance and Operations",
                "bullets": [
                    "Revenue up 12% versus last quarter.",
                    "Refund spike around week 6 noted.",
                    "Vendor invoice #A19 flagged as late.",
                ],
            },
            {
                "heading": "Customer and Next Steps",
                "bullets": [
                    "Onboarding flow shipped on 8/14; support tickets dropped.",
                    "EU churn is highest; cause unclear.",
                    "Next review scheduled 9/30 with metrics and timeline.",
                ],
            },
        ],
    }

    summary_payload = summary or {
        "tldr": "Q3 performance improved but churn and refunds need investigation.",
        "key_points": [
            "Revenue increased 12% versus last quarter.",
            "Support tickets declined after the 8/14 onboarding update.",
            "EU churn is a current hotspot.",
        ],
        "risks": [
            "Refund spike may indicate product or policy issues.",
            "Potential late fee tied to vendor invoice #A19.",
        ],
        "recommendations": [
            "Audit refund policy and root causes.",
            "Investigate EU latency and pricing impact on churn.",
            "Tighten promo tracking before next review.",
        ],
    }

    validation_payload = validation or {
        "coverage_score": 92,
        "unsupported_claims": [],
        "missing_topics": [],
        "issues": [],
    }

    return {
        "facts": facts_payload,
        "outline": outline_payload,
        "summary": summary_payload,
        "validation": validation_payload,
        "source_excerpt": doc_text.strip()[:240],
    }


def validate_outputs(outputs: dict) -> None:
    schema_map = {
        "facts": "facts.schema.json",
        "outline": "outline.schema.json",
        "summary": "summary.schema.json",
        "validation": "validation.schema.json",
    }
    for key, schema_file in schema_map.items():
        schema = load_schema(schema_file)
        validate(instance=outputs[key], schema=schema)


def write_outputs(outputs: dict, raw_text: str) -> list[Path]:
    OUTPUTS_DIR.mkdir(parents=True, exist_ok=True)

    file_map = {
        "facts": OUTPUTS_DIR / "facts.json",
        "outline": OUTPUTS_DIR / "outline.json",
        "summary": OUTPUTS_DIR / "summary.json",
        "validation": OUTPUTS_DIR / "validation_report.json",
    }

    written = []
    for key, path in file_map.items():
        path.write_text(json.dumps(outputs[key], indent=2), encoding="utf-8")
        written.append(path)

    trace = {
        "raw_text": raw_text,
        "facts": outputs["facts"],
        "outline": outputs["outline"],
        "summary": outputs["summary"],
        "validation": outputs["validation"],
    }
    trace_path = OUTPUTS_DIR / "trace.json"
    trace_path.write_text(json.dumps(trace, indent=2), encoding="utf-8")
    written.append(trace_path)

    return written


def main() -> None:
    config = load_config()
    raw_text = SAMPLE_DOC.read_text(encoding="utf-8")

    facts = run_extractor(raw_text, config)
    outline = run_structurer(facts, config)
    summary = run_summarizer(outline, config)
    validation = run_validator(facts, outline, summary, config)
    outputs = build_placeholders(
        raw_text,
        facts=facts,
        outline=outline,
        summary=summary,
        validation=validation,
    )
    validate_outputs(outputs)
    written = write_outputs(outputs, raw_text)

    rel_paths = [str(path.relative_to(ROOT_DIR)) for path in written]
    print("Wrote: " + ", ".join(rel_paths))


if __name__ == "__main__":
    main()
