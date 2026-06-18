# ⚖️ Legal Document Comparison Tool

**Compare two versions of a contract, see exactly what changed, and get AI-flagged risk — with every finding traced back to the exact source text.**

A proof-of-concept built for the NTU **veNTUre** programme (with OCBC). It takes two legal documents (contracts / agreements), lines up comparable clauses even when the wording or order differs, detects what changed, and flags potential risk areas in a side-by-side review interface.

> It **assists** a human legal reviewer — it does **not** make legal decisions. Every flag points back to the source text, and the tool clearly shows when it is unsure.

---

## 💡 The core idea: deterministic first, AI second

A plain text diff fails on contracts — clauses get reordered and reworded, so it drowns the reviewer in false "changes." This tool works in two layers instead:

1. **Catch layer (no AI).** Split each document into clauses, then match them across the two versions using exact text, fuzzy similarity, and meaning-based embeddings. This reliably finds *every* change and is fully reproducible — run it twice, get the same answer.
2. **Interpret layer (AI).** Only the clauses that actually changed are sent to the LLM, one matched pair at a time, to explain the change and rate the risk — returning structured data with the exact quotes it based its judgement on.

So the AI never hunts through whole documents (where it would miss things or hallucinate). It only ever explains changes the reliable layer already found.

---

## ✨ Features

- **📄 Reads PDF, Word, and scanned documents** — text PDFs and `.docx` directly; scanned/image PDFs via OCR.
- **🧩 Clause-level matching** — aligns "Confidentiality" in A to "Confidentiality" in B even if it was reworded or moved.
- **🔍 Change detection** — labels every clause `unchanged` / `modified` / `added` / `removed`, with word-level highlights inside modified clauses.
- **⚠️ AI risk flagging** — for each changed clause: a plain-language summary, a risk level, the reasoning, the exact source quotes, and an "uncertain" flag.
- **🖥️ Side-by-side review UI** — colour-coded, with the AI risk panel and document provenance (page number, OCR origin).
- **📊 Accuracy harness** — generates test contract pairs with *known* changes and measures how many the engine catches.

---

## 🔁 How it works

```
            ingestion          segmentation        alignment              comparison
 file A ─▶ text + pages ─▶ list of clauses ─┐
                                            ├─▶ matched clause pairs ─▶ change + risk ─▶ UI
 file B ─▶ text + pages ─▶ list of clauses ─┘    (deterministic)        (AI, per pair)
```

---

## 📁 Project structure

```
legal-doc-compare/
├── config.yaml              # tunable settings (thresholds, model, OCR options)
├── .env.example             # secrets template (API key) — copy to .env
├── run_app.py               # launches the review UI
├── src/legalcompare/
│   ├── schemas.py           # the data types shared across every stage
│   ├── pipeline.py          # wires the stages together end-to-end
│   ├── ingestion/           # read PDF / Word / scanned (OCR)
│   ├── segmentation/        # split a document into clauses
│   ├── alignment/           # deterministic clause matching
│   ├── comparison/          # LLM change explanation + risk flagging
│   ├── reporting.py         # word-level diff + display helpers
│   └── evaluation.py        # accuracy scoring logic
├── ui/app.py                # Streamlit side-by-side interface
├── scripts/make_eval_set.py # generate test pairs with known changes
├── eval/run_eval.py         # run the accuracy check
└── data/eval/               # generated test pairs + answer keys
```

---

## 🚀 Quick start

### Prerequisites
- Python 3.10+
- An Anthropic API key (only needed for the AI risk step — change detection works without it)
- *For scanned PDFs only:* [Tesseract OCR](https://github.com/UB-Mannheim/tesseract/wiki) and [Poppler](https://github.com/oschwartz10612/poppler-windows) installed on your system

### Setup
```bash
python -m venv .venv
.venv\Scripts\activate            # Windows
pip install -r requirements.txt
pip install -e .                  # makes the legalcompare package importable

copy .env.example .env            # then add your ANTHROPIC_API_KEY (optional)
```

### Run the review UI
```bash
python run_app.py
```
Open http://localhost:8501, click **"Load built-in demo pair"** (or upload two documents), and press **Compare**. The AI risk panels appear when an API key is present.

### Run the accuracy check
```bash
python scripts/make_eval_set.py   # build the test pairs (once)
python eval/run_eval.py           # run the check and print scores
```

---

## ⚙️ Configuration

All tunable settings live in `config.yaml` (not in the code), so behaviour is easy to inspect and adjust:

- **alignment** — the match thresholds (fuzzy %, embedding similarity) and the local embedding model.
- **comparison** — the LLM model id and token limit.
- **ingestion** — OCR language and the "this page looks scanned" threshold.

The API key lives separately in `.env` (which is never committed).

---

## 📊 Evaluation

The accuracy check measures the **deterministic catch layer** — the part the design says must be reliable. `make_eval_set.py` takes a template, applies a *recorded* set of edits (reword / change / add / remove / reorder), and writes both the modified version and a ground-truth answer key. `run_eval.py` runs the engine and compares.

On the current controlled set (an NDA and a Services Agreement, 9 known changes), it caught **9/9 changes with no false positives**. This is an encouraging start, not a benchmark — the value is the *harness*, which lets you drop in real templates and grow the test set to make the number meaningful.

---

## ✅ Status — what works today

| Capability | Status |
|---|---|
| Ingestion (PDF text / Word / txt) | ✅ working |
| Clause segmentation | ✅ working |
| Deterministic alignment + change detection | ✅ working, evaluated |
| Side-by-side review UI | ✅ working |
| AI risk flagging | 🟡 implemented; needs an API key to run live |
| OCR for scanned PDFs | 🟡 implemented; needs Tesseract + Poppler installed to verify |
| Accuracy evaluation harness | ✅ working |

---

## 🎯 What makes this different

**❌ What it's not:** a plain text diff, or an AI asked to "find the differences" in two whole documents (unreliable, can't be traced).

**✅ What it is:** a tool that reliably catches *every* change with deterministic methods first, then uses AI only to explain and risk-rate the changes it found — with every judgement grounded in quoted source text and uncertainty made explicit.

---

## 🗺️ Roadmap

- [ ] Verify the OCR path on real scanned contracts
- [ ] Expand the evaluation set with real public templates and harder edits
- [ ] Tune match thresholds against the larger eval set
- [ ] Optionally extend AI risk flagging to added/removed clauses

---

*Proof of concept developed for the NTU veNTUre programme. Built to assist legal review, not replace it.*
