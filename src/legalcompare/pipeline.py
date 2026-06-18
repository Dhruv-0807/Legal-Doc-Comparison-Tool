"""End-to-end orchestration: file A + file B -> ReviewReport.

This is the spine that wires the four stages together. It is intentionally thin:
each stage lives in its own module and is filled in on its step. Keeping the
wiring here (and stable) means the UI and eval harness can call `compare_documents`
without caring how any single stage works internally.
"""

from __future__ import annotations

from .schemas import ReviewReport

# Imports are deferred inside the function so that importing this module doesn't
# require every heavy dependency (OCR, embeddings, LLM) to be installed yet.


def compare_documents(path_a: str, path_b: str, run_llm: bool = True) -> ReviewReport:
    """Compare two legal documents and return a review report.

    Stages (each implemented in its own step):
        2. ingest      -> Document
        3. segment     -> list[Clause]
        4. align       -> list[AlignedPair]   (deterministic)
        5. compare     -> list[ComparisonResult]  (LLM, matched pairs only)

    `run_llm=False` stops after the deterministic layer (no API key needed) — the
    report still has every clause aligned and every change classified, just no
    risk interpretation. The UI uses this so it works with or without a key.
    """
    from .ingestion.loader import load_document
    from .segmentation.segmenter import segment
    from .alignment.aligner import align
    from .comparison.comparator import compare_pairs

    doc_a = load_document(path_a)
    doc_b = load_document(path_b)

    clauses_a = segment(doc_a)
    clauses_b = segment(doc_b)

    pairs = align(clauses_a, clauses_b)
    comparisons = compare_pairs(pairs) if run_llm else []

    return ReviewReport(
        doc_a=doc_a.name,
        doc_b=doc_b.name,
        pairs=pairs,
        comparisons=comparisons,
    )
