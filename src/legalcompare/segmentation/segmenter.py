"""Step 3: split a Document into comparable Clause units.

Legal documents are already organised into numbered clauses ("1.", "2.3",
"Section 4", "ARTICLE V"). So segmentation is deterministic and simple: find
where each numbered clause starts, and cut the text there. No LLM, no guessing.

We keep character offsets into `Document.full_text` on every Clause, so a clause
can always be traced back to its exact source span (and, via the Document's
blocks, back to its page / OCR origin).
"""

from __future__ import annotations

import re

from ..config import get_config
from ..schemas import Clause, Document

# A clause "marker" at the start of a line:
#   12.        1.2.       Section 3        ARTICLE IV        Clause 5
# It must be followed by space/punctuation so we don't grab numbers that merely
# begin a line by accident. `^` is per-line (re.MULTILINE).
CLAUSE_START = re.compile(
    r"^[ \t]*"
    r"(?P<marker>"
    r"(?:ARTICLE|SECTION|CLAUSE)\s+[IVXLC\d]+"   # ARTICLE IV / Section 3
    r"|\d{1,3}(?:\.\d{1,3})*\.?"                  # 1   1.   12.3   1.2.3.
    r")"
    r"(?=[ \t.):\-])",                            # must be followed by space/punct
    re.IGNORECASE | re.MULTILINE,
)


def segment(doc: Document) -> list[Clause]:
    """Split a document into clauses, preserving offsets and headings."""
    cfg = get_config()["segmentation"]
    min_chars = cfg["min_clause_chars"]
    text = doc.full_text

    # 1) Find every clause-start position.
    starts = [m.start() for m in CLAUSE_START.finditer(text)]

    # 2) Make sure any preamble before the first marker becomes its own unit.
    if not starts or starts[0] != 0:
        starts = [0] + starts
    starts = sorted(set(starts))

    # 3) Slice the text between consecutive starts into raw (start, end) spans.
    spans: list[tuple[int, int]] = []
    for i, s in enumerate(starts):
        e = starts[i + 1] if i + 1 < len(starts) else len(text)
        if text[s:e].strip():
            spans.append((s, e))

    # 4) Merge fragments shorter than min_chars into the previous clause, so a
    #    stray short line doesn't become its own "clause" and skew alignment.
    merged: list[tuple[int, int]] = []
    for s, e in spans:
        chunk = text[s:e].strip()
        if merged and len(chunk) < min_chars:
            ps, _ = merged[-1]
            merged[-1] = (ps, e)
        else:
            merged.append((s, e))

    # 5) Build Clause objects with headings and OCR provenance.
    clauses: list[Clause] = []
    for idx, (s, e) in enumerate(merged):
        chunk = text[s:e].strip()
        clauses.append(
            Clause(
                doc_name=doc.name,
                index=idx,
                heading=_extract_heading(chunk),
                text=chunk,
                start_char=s,
                end_char=e,
                from_ocr=_span_from_ocr(doc, s, e),
            )
        )
    return clauses


def _extract_heading(chunk: str) -> str | None:
    """A short label for the clause: its marker + the rest of its first line,
    trimmed. Used for display/grouping only — comparison always uses full text."""
    first_line = chunk.splitlines()[0].strip() if chunk else ""
    if not first_line:
        return None
    if len(first_line) > 80:
        first_line = first_line[:80].rstrip() + "…"
    return first_line


def _span_from_ocr(doc: Document, start: int, end: int) -> bool:
    """True if any source block overlapping this span came from OCR."""
    return any(
        b.from_ocr and b.start_char < end and b.end_char > start for b in doc.blocks
    )
