"""Shared data contract for the whole pipeline.

These Pydantic models are the *interfaces* between stages. Defining them up front
(Step 1) lets each later step be built and tested in isolation: it just has to
produce/consume these types. Fields may gain detail as we go, but the shape here
is the backbone.

Flow of types:
    ingestion  -> Document (raw text + source blocks)
    segmentation -> list[Clause]   (one per document)
    alignment  -> list[AlignedPair]  (deterministic matching)
    comparison -> ComparisonResult   (LLM explanation + risk, per pair)
"""

from __future__ import annotations

from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


# --------------------------------------------------------------------------- #
# Ingestion (Step 2)
# --------------------------------------------------------------------------- #
class SourceBlock(BaseModel):
    """A contiguous chunk of text as extracted from the file, with provenance.

    Provenance (page, char offsets) is what lets every later finding trace back
    to exact source text — a hard requirement of this tool.
    """

    text: str
    page: Optional[int] = None          # 1-based page number, if applicable
    start_char: int = 0                 # offset within the document's full text
    end_char: int = 0
    from_ocr: bool = False              # True if this text came from OCR (lower trust)


class Document(BaseModel):
    """A fully ingested document: full text plus the blocks it was built from."""

    name: str                           # original filename / label
    full_text: str
    blocks: list[SourceBlock] = Field(default_factory=list)
    used_ocr: bool = False              # did any part of this doc require OCR?


# --------------------------------------------------------------------------- #
# Segmentation (Step 3)
# --------------------------------------------------------------------------- #
class Clause(BaseModel):
    """A comparable unit of a document (a clause / numbered section / paragraph)."""

    doc_name: str
    index: int                          # order within its document
    heading: Optional[str] = None       # e.g. "12. Confidentiality", if detected
    text: str
    start_char: int = 0                 # offsets back into Document.full_text
    end_char: int = 0
    from_ocr: bool = False


# --------------------------------------------------------------------------- #
# Alignment (Step 4)
# --------------------------------------------------------------------------- #
class MatchMethod(str, Enum):
    EXACT = "exact"                     # identical text
    FUZZY = "fuzzy"                     # high fuzzy-match score
    EMBEDDING = "embedding"             # matched via semantic similarity
    UNMATCHED = "unmatched"             # no counterpart found


class ChangeType(str, Enum):
    UNCHANGED = "unchanged"
    MODIFIED = "modified"               # matched pair with differing text
    ADDED = "added"                     # only in document B
    REMOVED = "removed"                 # only in document A


class AlignedPair(BaseModel):
    """One row of the comparison: an A-clause matched to a B-clause (either may be
    None for added/removed). Produced deterministically — no LLM involved yet."""

    clause_a: Optional[Clause] = None
    clause_b: Optional[Clause] = None
    method: MatchMethod = MatchMethod.UNMATCHED
    similarity: float = 0.0             # 0..1, how confident the deterministic match is
    change_type: ChangeType = ChangeType.UNCHANGED


# --------------------------------------------------------------------------- #
# Comparison + risk (Step 5)
# --------------------------------------------------------------------------- #
class RiskLevel(str, Enum):
    NONE = "none"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class ComparisonResult(BaseModel):
    """LLM output for a single matched pair. Always grounded in source text.

    `uncertain` makes the tool's own doubt explicit, per the design principle that
    it must clearly show when it isn't sure.
    """

    pair_index: int                     # which AlignedPair this refers to
    summary: str                        # plain-language description of the change
    risk_level: RiskLevel = RiskLevel.NONE
    risk_rationale: Optional[str] = None
    # The exact source spans this judgement is based on (traceability).
    evidence_a: Optional[str] = None
    evidence_b: Optional[str] = None
    uncertain: bool = False             # model flags low confidence / ambiguity


class ClauseAssessment(BaseModel):
    """The LLM's raw output for one matched clause pair (Step 5).

    Kept separate from ComparisonResult: this is exactly what the model fills in,
    with all fields *required* (empty strings allowed) so it plays cleanly with
    structured-output schema generation. The comparator then wraps it into a
    ComparisonResult, adding the pair_index the model never sees.
    """

    summary: str
    risk_level: RiskLevel
    risk_rationale: str
    evidence_a: str        # exact quote from version A (or "" if none)
    evidence_b: str        # exact quote from version B (or "" if none)
    uncertain: bool


class ReviewReport(BaseModel):
    """The full artifact handed to the UI: every aligned pair + any LLM result."""

    doc_a: str
    doc_b: str
    pairs: list[AlignedPair] = Field(default_factory=list)
    comparisons: list[ComparisonResult] = Field(default_factory=list)
