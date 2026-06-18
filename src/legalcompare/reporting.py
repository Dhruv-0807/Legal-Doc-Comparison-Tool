"""Presentation helpers for the review UI — pure functions, no Streamlit import.

Kept separate from ui/app.py so the display logic (word-level diffing, change
counts, colour mapping) can be unit-tested without a running Streamlit server.
"""

from __future__ import annotations

import difflib
import html
import re

from .schemas import ChangeType, ReviewReport, RiskLevel

# Colours for the four change types and the four risk levels (UI styling only).
CHANGE_COLOR = {
    ChangeType.UNCHANGED: "#f5f5f5",
    ChangeType.MODIFIED: "#fff3cd",   # amber
    ChangeType.ADDED: "#d4edda",      # green
    ChangeType.REMOVED: "#f8d7da",    # red
}
RISK_COLOR = {
    RiskLevel.NONE: "#6c757d",
    RiskLevel.LOW: "#0d6efd",
    RiskLevel.MEDIUM: "#fd7e14",
    RiskLevel.HIGH: "#dc3545",
}

_WORD = re.compile(r"\S+\s*")


def change_counts(report: ReviewReport) -> dict[str, int]:
    """Tally pairs by change type — feeds the summary bar at the top of the UI."""
    counts = {ct.value: 0 for ct in ChangeType}
    for pair in report.pairs:
        counts[pair.change_type.value] += 1
    return counts


def inline_diff(text_a: str, text_b: str) -> tuple[str, str]:
    """Word-level diff of two clause versions, returned as two HTML strings.

    Deleted words are marked in the A column, inserted words in the B column, so a
    reviewer sees *exactly* what changed inside a modified clause — not just that
    it changed. All text is HTML-escaped first (clauses are untrusted input).
    """
    a_words = _WORD.findall(text_a)
    b_words = _WORD.findall(text_b)
    matcher = difflib.SequenceMatcher(a=a_words, b=b_words, autojunk=False)

    a_out: list[str] = []
    b_out: list[str] = []
    for tag, i1, i2, j1, j2 in matcher.get_opcodes():
        a_seg = html.escape("".join(a_words[i1:i2]))
        b_seg = html.escape("".join(b_words[j1:j2]))
        if tag == "equal":
            a_out.append(a_seg)
            b_out.append(b_seg)
        elif tag == "delete":
            a_out.append(f'<span style="background:#f5b7b1;text-decoration:line-through">{a_seg}</span>')
        elif tag == "insert":
            b_out.append(f'<span style="background:#abebc6">{b_seg}</span>')
        elif tag == "replace":
            a_out.append(f'<span style="background:#f5b7b1;text-decoration:line-through">{a_seg}</span>')
            b_out.append(f'<span style="background:#abebc6">{b_seg}</span>')

    return "".join(a_out), "".join(b_out)
