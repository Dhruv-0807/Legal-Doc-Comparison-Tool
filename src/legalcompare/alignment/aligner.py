"""Step 4: deterministically align clauses between document A and document B.

No LLM here — this is the "catch layer" whose job is to reliably find *which
clause matches which*, and what changed, before any interpretation happens.

Three matching signals, cheapest first:
  1. EXACT     — normalised text is identical            -> unchanged
  2. FUZZY     — high character/token overlap (rapidfuzz) -> caught small edits
  3. EMBEDDING — semantic similarity (see similarity.py)  -> caught heavy rewording

We score every A-clause against every B-clause, then match greedily: repeatedly
take the highest-scoring still-available pair that clears a threshold. Whatever is
left over is ADDED (only in B) or REMOVED (only in A). Greedy keeps it simple and
easy to explain; clause counts are small so it's plenty good for a POC.
"""

from __future__ import annotations

import re

from ..config import get_config
from ..schemas import AlignedPair, ChangeType, Clause, MatchMethod
from .similarity import similarity_matrix

_WS = re.compile(r"\s+")


def _normalize(text: str) -> str:
    """Lowercase + collapse whitespace, so trivial formatting differences don't
    count as changes when deciding 'exact match'."""
    return _WS.sub(" ", text.strip().lower())


def _fuzzy_ratio(a: str, b: str) -> float:
    """Character/token similarity in [0, 1]. rapidfuzz if present, else stdlib."""
    try:
        from rapidfuzz import fuzz

        return fuzz.token_sort_ratio(a, b) / 100.0
    except Exception:
        from difflib import SequenceMatcher

        return SequenceMatcher(None, a, b).ratio()


def align(clauses_a: list[Clause], clauses_b: list[Clause]) -> list[AlignedPair]:
    """Match clauses across the two documents and classify each as
    unchanged / modified / added / removed."""
    cfg = get_config()["alignment"]
    fuzzy_thr = cfg["fuzzy_match_threshold"] / 100.0
    emb_thr = cfg["embedding_match_threshold"]
    model_name = cfg["embedding_model"]

    # Semantic matrix once for all pairs (None if no backend available).
    sem = similarity_matrix(
        tuple(c.text for c in clauses_a),
        tuple(c.text for c in clauses_b),
        model_name,
    )

    # 1) Score every candidate pair and record which signal qualified it.
    candidates: list[tuple[float, int, int, MatchMethod]] = []
    for i, ca in enumerate(clauses_a):
        na = _normalize(ca.text)
        for j, cb in enumerate(clauses_b):
            if na == _normalize(cb.text):
                candidates.append((1.0, i, j, MatchMethod.EXACT))
                continue
            fuzzy = _fuzzy_ratio(ca.text, cb.text)
            semantic = sem[i][j] if sem is not None else 0.0
            if fuzzy >= fuzzy_thr:
                candidates.append((fuzzy, i, j, MatchMethod.FUZZY))
            elif semantic >= emb_thr:
                candidates.append((semantic, i, j, MatchMethod.EMBEDDING))

    # 2) Greedy assignment: best score first, each clause used at most once.
    candidates.sort(key=lambda t: t[0], reverse=True)
    used_a: set[int] = set()
    used_b: set[int] = set()
    matches: list[tuple[int, int, float, MatchMethod]] = []
    for score, i, j, method in candidates:
        if i in used_a or j in used_b:
            continue
        used_a.add(i)
        used_b.add(j)
        matches.append((i, j, score, method))

    # 3) Build the result. Walk A in order (matched or removed), then append the
    #    B-only clauses (added). Keeps the review roughly in document order.
    matched_by_a = {i: (j, score, method) for i, j, score, method in matches}
    pairs: list[AlignedPair] = []

    for i, ca in enumerate(clauses_a):
        if i in matched_by_a:
            j, score, method = matched_by_a[i]
            cb = clauses_b[j]
            unchanged = method == MatchMethod.EXACT
            pairs.append(
                AlignedPair(
                    clause_a=ca,
                    clause_b=cb,
                    method=method,
                    similarity=round(float(score), 4),
                    change_type=ChangeType.UNCHANGED if unchanged else ChangeType.MODIFIED,
                )
            )
        else:
            pairs.append(
                AlignedPair(
                    clause_a=ca,
                    clause_b=None,
                    method=MatchMethod.UNMATCHED,
                    similarity=0.0,
                    change_type=ChangeType.REMOVED,
                )
            )

    for j, cb in enumerate(clauses_b):
        if j not in used_b:
            pairs.append(
                AlignedPair(
                    clause_a=None,
                    clause_b=cb,
                    method=MatchMethod.UNMATCHED,
                    similarity=0.0,
                    change_type=ChangeType.ADDED,
                )
            )

    return pairs
