"""Step 5: run the LLM over matched-and-changed pairs to explain + flag risk.

By design the LLM only ever sees pairs the deterministic layer already (a) matched
and (b) found to differ — i.e. change_type == MODIFIED. Identical (UNCHANGED)
pairs are skipped, and ADDED / REMOVED clauses are surfaced by the deterministic
layer and the UI without LLM interpretation. So every model call is a small,
focused, already-localised comparison — which is what keeps it reliable.
"""

from __future__ import annotations

from ..schemas import AlignedPair, ChangeType, ComparisonResult


def compare_pairs(pairs: list[AlignedPair]) -> list[ComparisonResult]:
    """Explain + risk-rate each MODIFIED pair via the LLM.

    Returns one ComparisonResult per MODIFIED pair, keyed by its index in `pairs`
    so the UI can line each assessment back up with its clauses.
    """
    from .llm_client import LLMClient  # deferred so no API key is needed unless we call out

    client: LLMClient | None = None
    results: list[ComparisonResult] = []

    for idx, pair in enumerate(pairs):
        if pair.change_type != ChangeType.MODIFIED or pair.clause_a is None or pair.clause_b is None:
            continue

        if client is None:
            client = LLMClient()  # construct lazily — only when there's real work to do

        assessment = client.assess_clause(pair.clause_a.text, pair.clause_b.text)
        results.append(
            ComparisonResult(
                pair_index=idx,
                summary=assessment.summary,
                risk_level=assessment.risk_level,
                risk_rationale=assessment.risk_rationale or None,
                evidence_a=assessment.evidence_a or None,
                evidence_b=assessment.evidence_b or None,
                uncertain=assessment.uncertain,
            )
        )

    return results
