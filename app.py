from __future__ import annotations

import json
import os
from pathlib import Path

import streamlit as st
import yaml
from jsonschema import validate

from agents.extractor import run_extractor
from agents.structurer import run_structurer
from agents.summarizer import run_summarizer
from agents.validator import run_validator

ROOT_DIR = Path(__file__).resolve().parent
SCHEMAS_DIR = ROOT_DIR / "schemas"
OUTPUTS_DIR = ROOT_DIR / "outputs"
CONFIG_PATH = ROOT_DIR / "config.yaml"
SAMPLE_DOC = ROOT_DIR / "sample_docs" / "sample.txt"


def load_schema(filename: str) -> dict:
    return json.loads((SCHEMAS_DIR / filename).read_text(encoding="utf-8"))


def load_config() -> dict:
    return yaml.safe_load(CONFIG_PATH.read_text(encoding="utf-8")) or {}


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


def load_sample_text() -> str:
    return SAMPLE_DOC.read_text(encoding="utf-8")


def init_state() -> None:
    if "doc_text" not in st.session_state:
        st.session_state.doc_text = load_sample_text()
    if "results" not in st.session_state:
        st.session_state.results = None
    if "error" not in st.session_state:
        st.session_state.error = None


def render_styles() -> None:
    st.markdown(
        """
        <style>
        @import url('https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@400;500;700&display=swap');
        html, body, [class*="css"]  {
            font-family: "Space Grotesk", "Segoe UI", Arial, sans-serif;
            color: #1b1f24;
        }
        .app-bg {
            background: radial-gradient(circle at 10% 10%, #fff4d6 0%, #f3f6ff 40%, #f8fafc 100%);
            padding: 1.5rem 1.5rem 0.5rem 1.5rem;
            border-radius: 18px;
            border: 1px solid #e7ebf3;
            box-shadow: 0 12px 40px rgba(20, 30, 60, 0.08);
        }
        .chain-grid {
            display: grid;
            grid-template-columns: repeat(4, 1fr);
            gap: 0.75rem;
            margin-top: 0.75rem;
        }
        .chain-card {
            background: #ffffff;
            border: 1px solid #e5e7ef;
            border-radius: 14px;
            padding: 0.9rem;
            box-shadow: 0 10px 26px rgba(20, 30, 60, 0.06);
        }
        .chain-card.active {
            border-color: #2563eb;
            box-shadow: 0 14px 34px rgba(37, 99, 235, 0.18);
            background: linear-gradient(135deg, #e0edff 0%, #ffffff 65%);
        }
        .chain-title {
            font-weight: 700;
            font-size: 0.95rem;
            color: #0f172a;
            margin-bottom: 0.35rem;
        }
        .chain-desc {
            font-size: 0.85rem;
            color: #475569;
        }
        .pill {
            display: inline-block;
            padding: 0.2rem 0.6rem;
            border-radius: 999px;
            background: #0f172a;
            color: #f8fafc;
            font-size: 0.75rem;
            letter-spacing: 0.04em;
            text-transform: uppercase;
        }
        .section-header {
            font-weight: 700;
            font-size: 1.1rem;
            margin: 1rem 0 0.4rem 0;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def render_chain(container: st.delta_generator.DeltaGenerator, active: str | None) -> None:
    def card(title: str, desc: str, key: str) -> str:
        active_class = "active" if active == key else ""
        return (
            f'<div class="chain-card {active_class}">'
            f'<div class="chain-title">{title}</div>'
            f'<div class="chain-desc">{desc}</div>'
            "</div>"
        )

    container.markdown(
        f"""
        <div class="chain-grid">
          {card("Extractor", "Atomic facts from messy text.", "extractor")}
          {card("Structurer", "Outline built from facts.", "structurer")}
          {card("Summarizer", "Executive summary artifacts.", "summarizer")}
          {card("Validator", "Coverage and support checks.", "validator")}
        </div>
        """,
        unsafe_allow_html=True,
    )


def run_pipeline(doc_text: str, chain_container: st.delta_generator.DeltaGenerator) -> dict:
    config = load_config()
    render_chain(chain_container, "extractor")
    facts = run_extractor(doc_text, config)
    render_chain(chain_container, "structurer")
    outline = run_structurer(facts, config)
    render_chain(chain_container, "summarizer")
    summary = run_summarizer(outline, config)
    render_chain(chain_container, "validator")
    validation = run_validator(facts, outline, summary, config)

    outputs = {
        "facts": facts,
        "outline": outline,
        "summary": summary,
        "validation": validation,
    }
    validate_outputs(outputs)
    write_outputs(outputs, doc_text)
    return outputs


def main() -> None:
    st.set_page_config(page_title="Prompt Chaining Demo", page_icon="🧩", layout="wide")
    render_styles()
    init_state()

    st.markdown('<div class="app-bg">', unsafe_allow_html=True)
    st.markdown("## Prompt Chaining Demo")
    st.markdown(
        "Run the pipeline end-to-end: extract facts, structure them, summarize, and validate."
    )

    if not os.getenv("OPENAI_API_KEY"):
        st.warning("OPENAI_API_KEY is not set. Add it to `.env` to enable runs.")

    st.markdown('<span class="pill">Chain</span>', unsafe_allow_html=True)
    chain_container = st.empty()
    render_chain(chain_container, None)

    col_input, col_controls = st.columns([3, 1])
    with col_input:
        st.markdown('<div class="section-header">Input</div>', unsafe_allow_html=True)
        st.text_area(
            "Document text",
            key="doc_text",
            height=240,
        )
    with col_controls:
        st.markdown('<div class="section-header">Run</div>', unsafe_allow_html=True)
        if st.button("Run pipeline", use_container_width=True):
            try:
                with st.spinner("Running prompt chain..."):
                    st.session_state.results = run_pipeline(
                        st.session_state.doc_text,
                        chain_container,
                    )
                    st.session_state.error = None
            except Exception as exc:
                st.session_state.error = str(exc)
                st.session_state.results = None

        if st.button("Load sample", use_container_width=True):
            st.session_state.doc_text = load_sample_text()

    if st.session_state.error:
        st.error(st.session_state.error)

    results = st.session_state.results
    if results:
        st.markdown('<div class="section-header">Outputs</div>', unsafe_allow_html=True)
        tabs = st.tabs(["facts.json", "outline.json", "summary.json", "validation_report.json", "trace.json"])
        tabs[0].json(results["facts"])
        tabs[1].json(results["outline"])
        tabs[2].json(results["summary"])
        tabs[3].json(results["validation"])
        tabs[4].json(
            {
                "raw_text": st.session_state.doc_text,
                "facts": results["facts"],
                "outline": results["outline"],
                "summary": results["summary"],
                "validation": results["validation"],
            }
        )

        st.caption("Saved to outputs/ as JSON artifacts.")

    st.markdown("</div>", unsafe_allow_html=True)


if __name__ == "__main__":
    main()
