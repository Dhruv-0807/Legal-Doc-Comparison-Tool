# Legal Document Comparison Tool (POC)

A proof-of-concept that compares two legal documents (contracts / agreements),
aligns comparable clauses even when wording or order differs, detects what
changed, and flags potential risk areas for a **human legal reviewer** in a
side-by-side interface.

> This tool **assists** review. It does not make legal decisions. Every flagged
> item traces back to exact source text, and the tool shows when it is uncertain.

## Core design principle

Alignment is done with **reliable, deterministic methods first**
(text diff + fuzzy matching + embedding similarity). The LLM is used **only on
already-matched clause pairs** to explain changes and flag risk. We prioritise
reliably catching *all* changes first, then layer risk interpretation on top.

This gives us two independent layers:

1. **Catch layer (deterministic):** finds and aligns every clause, surfaces every
   textual change. Reproducible, no model calls, auditable.
2. **Interpret layer (LLM):** explains and risk-rates the changes the catch layer
   found. Constrained to matched pairs, returns structured JSON, always cites
   source text.

## Build order (we build and explain one step at a time)

1. **Project setup + repo structure**  ← *you are here*
2. Document ingestion + OCR (PDF, Word, scanned)
3. Clause segmentation (split docs into comparable units)
4. Deterministic alignment (diff, fuzzy match, embeddings)
5. LLM comparison + risk flagging on matched clauses (structured JSON)
6. UI with risk/change highlights (side-by-side)
7. Evaluation set (edited public templates with known changes) + accuracy check

## Pipeline at a glance

```
              ingestion            segmentation          alignment              comparison
  file ──▶ text + blocks ──▶ list of clauses ──┐
                                               ├─▶ aligned clause pairs ──▶ change + risk JSON ──▶ UI
  file ──▶ text + blocks ──▶ list of clauses ──┘   (deterministic)          (LLM, per pair)
```

## Project layout

```
legal-doc-compare/
├── config.yaml              # tunable, non-secret settings (thresholds, model id, OCR opts)
├── .env.example             # secrets template (API keys) — copy to .env
├── requirements.txt
├── pyproject.toml           # makes `legalcompare` importable (pip install -e .)
├── run_app.py               # launches the Streamlit UI
├── src/legalcompare/
│   ├── config.py            # loads config.yaml + .env
│   ├── schemas.py           # Pydantic data contract shared across all stages
│   ├── pipeline.py          # wires the stages together end-to-end
│   ├── ingestion/           # Step 2: read PDF / Word / scanned (OCR)
│   ├── segmentation/        # Step 3: split a document into clauses
│   ├── alignment/           # Step 4: deterministic clause matching
│   └── comparison/          # Step 5: LLM change explanation + risk flagging
├── ui/app.py                # Step 6: side-by-side review interface
├── scripts/make_eval_set.py # Step 7: generate version pairs from public templates
├── eval/run_eval.py         # Step 7: accuracy check vs known changes
└── data/
    ├── templates/           # public legal templates (originals)
    ├── samples/             # generated A/B version pairs for manual testing
    └── eval/                # eval pairs + ground-truth change list
```

## Setup

```bash
python -m venv .venv
.venv\Scripts\activate          # Windows (PowerShell: .venv\Scripts\Activate.ps1)
pip install -r requirements.txt
pip install -e .                # makes `legalcompare` importable from anywhere

cp .env.example .env            # then add your API key
```

**OCR note:** scanned-PDF support needs the system binaries **Tesseract OCR** and
**Poppler** installed (the Python packages only wrap them). Setup details land in
Step 2. Text-based PDFs and Word files work without them.

## Run

```bash
python run_app.py               # Streamlit UI  (added in Step 6)
python scripts/make_eval_set.py # build sample/eval pairs (added in Step 7)
python eval/run_eval.py         # run accuracy check (added in Step 7)
```

## Status

Step 1 complete: repo structure, config, and shared data contract are in place.
Stage modules are stubs that raise `NotImplementedError` until their step.
