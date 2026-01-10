# Prompt Chaining Doc Agent

## Project Overview
This project demonstrates a prompt chaining system for turning unstructured document text into verified, structured artifacts. Single-prompt systems fail because they must extract facts, structure them, summarize, and validate in one pass, which hides intermediate reasoning, makes errors hard to isolate, and blends extraction with invention.

## Why Prompt Chaining
Agent separation assigns one responsibility per step, reducing cross-task interference and making errors attributable to a specific stage. Inspectable intermediate outputs provide checkpoints so engineers can test, diff, and audit each transformation rather than trusting a single opaque response.

## System Architecture
Four agents run in sequence:
- Extractor: pulls atomic facts from raw text.
- Structurer: organizes facts into a hierarchical outline.
- Summarizer: generates a concise executive summary from the outline.
- Validator: checks all outputs for consistency and unsupported claims.
Data flows strictly left-to-right: document text -> Extractor -> facts.json -> Structurer -> outline.json -> Summarizer -> executive_summary.md, while the Validator reads all artifacts to produce validation_report.json and trace.json.

## Inputs and Outputs
Input: unstructured document text.
Outputs:
- facts.json
- outline.json
- executive_summary.md
- validation_report.json
- trace.json

## Success Criteria
- Clear, verifiable outputs.
- No hallucinated facts.
- Each agent independently testable.

## Explicit Out of Scope
- OCR
- Vector databases
- UI
- External orchestration frameworks