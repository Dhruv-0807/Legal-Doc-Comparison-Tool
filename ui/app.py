"""Step 6: Streamlit side-by-side review UI with change + risk highlights.

Layout: a summary bar (counts by change type), then one row per aligned clause
pair — document A on the left, document B on the right — colour-coded by change
type, with word-level diffs inside modified clauses and an expandable risk panel
when the AI step has run. Works with or without an API key (AI step is a toggle).
"""

from __future__ import annotations

import sys
import tempfile
from pathlib import Path

import streamlit as st

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from legalcompare.config import get_config  # noqa: E402
from legalcompare.pipeline import compare_documents  # noqa: E402
from legalcompare.reporting import (  # noqa: E402
    CHANGE_COLOR,
    RISK_COLOR,
    change_counts,
    inline_diff,
)
from legalcompare.schemas import ChangeType, ReviewReport  # noqa: E402

SUPPORTED = ("pdf", "docx", "txt", "md")


def _save_upload(upload) -> str:
    """Persist an uploaded file to a temp path the loaders can read by extension."""
    suffix = Path(upload.name).suffix
    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=suffix)
    tmp.write(upload.getvalue())
    tmp.close()
    return tmp.name


def _make_demo_pair() -> tuple[str, str]:
    """Write a small A/B contract pair with known changes, for a no-upload demo."""
    import docx

    out = ROOT / "data" / "samples" / "_ui_demo"
    out.mkdir(parents=True, exist_ok=True)
    a_clauses = [
        "1. Confidentiality. Each party shall keep the other party's Confidential "
        "Information strictly confidential and shall not disclose it to any third party.",
        "2. Term. This Agreement commences on the Effective Date and continues for "
        "twelve (12) months unless terminated earlier.",
        "3. Governing Law. This Agreement shall be governed by the laws of Singapore.",
        "4. Assignment. Neither party may assign this Agreement without prior written consent.",
    ]
    b_clauses = [
        "3. Governing Law. This Agreement shall be governed by the laws of Singapore.",
        "1. Confidentiality. Neither party shall disclose the other's Confidential "
        "Information to any third party and shall keep it strictly secret.",
        "2. Term. This Agreement commences on the Effective Date and continues for "
        "twenty-four (24) months unless terminated earlier.",
        "5. Indemnification. Each party shall indemnify the other against losses "
        "arising from its breach of this Agreement.",
    ]
    paths = []
    for name, clauses in (("nda_A.docx", a_clauses), ("nda_B.docx", b_clauses)):
        d = docx.Document()
        for c in clauses:
            d.add_paragraph(c)
        d.save(str(out / name))
        paths.append(str(out / name))
    return paths[0], paths[1]


def _clause_cell(pair_side, html_text: str | None, bg: str) -> str:
    """Render one side of a row as a coloured HTML cell."""
    if pair_side is None:
        body = "<em style='color:#999'>— no matching clause —</em>"
    else:
        ocr = " 🔍OCR" if pair_side.from_ocr else ""
        page = f" · p.{pair_side.page}" if getattr(pair_side, "page", None) else ""
        head = f"<div style='font-size:0.75em;color:#666'>{pair_side.doc_name}{page}{ocr}</div>"
        body = head + (html_text if html_text is not None else "")
    return (
        f"<div style='background:{bg};color:#1a1a1a;padding:8px 10px;"
        f"border-radius:6px;min-height:40px;font-size:0.9em'>{body}</div>"
    )


def _render_report(report: ReviewReport) -> None:
    counts = change_counts(report)
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Unchanged", counts["unchanged"])
    c2.metric("Modified", counts["modified"])
    c3.metric("Added", counts["added"])
    c4.metric("Removed", counts["removed"])
    st.divider()

    comparisons_by_pair = {c.pair_index: c for c in report.comparisons}

    for idx, pair in enumerate(report.pairs):
        bg = CHANGE_COLOR[pair.change_type]

        # Word-level diff inside modified clauses; plain (escaped) text otherwise.
        if pair.change_type == ChangeType.MODIFIED and pair.clause_a and pair.clause_b:
            html_a, html_b = inline_diff(pair.clause_a.text, pair.clause_b.text)
        else:
            import html as _html

            html_a = _html.escape(pair.clause_a.text) if pair.clause_a else None
            html_b = _html.escape(pair.clause_b.text) if pair.clause_b else None

        left, right = st.columns(2)
        tag = f"`{pair.change_type.value}` · matched by *{pair.method.value}*"
        if pair.similarity:
            tag += f" ({pair.similarity:.2f})"
        st.caption(f"Clause {idx + 1} — {tag}")
        left.markdown(_clause_cell(pair.clause_a, html_a, bg), unsafe_allow_html=True)
        right.markdown(_clause_cell(pair.clause_b, html_b, bg), unsafe_allow_html=True)

        result = comparisons_by_pair.get(idx)
        if result is not None:
            color = RISK_COLOR[result.risk_level]
            label = f"{'⚠️ ' if result.uncertain else ''}Risk: {result.risk_level.value.upper()}"
            with st.expander(f"AI assessment — {label}", expanded=result.risk_level.value in ("medium", "high")):
                st.markdown(
                    f"<span style='background:{color};color:white;padding:2px 8px;"
                    f"border-radius:10px;font-size:0.8em'>{result.risk_level.value.upper()}</span>",
                    unsafe_allow_html=True,
                )
                st.write(f"**What changed:** {result.summary}")
                if result.risk_rationale:
                    st.write(f"**Why it matters:** {result.risk_rationale}")
                if result.evidence_a or result.evidence_b:
                    st.caption("Evidence (exact source text):")
                    if result.evidence_a:
                        st.markdown(f"> A: {result.evidence_a}")
                    if result.evidence_b:
                        st.markdown(f"> B: {result.evidence_b}")
                if result.uncertain:
                    st.warning("The tool is uncertain about this assessment — review carefully.")
        st.write("")


def main() -> None:
    cfg = get_config()
    st.set_page_config(page_title=cfg["ui"]["title"], layout="wide")
    st.title(cfg["ui"]["title"])
    st.caption(
        "Aligns clauses across two contract versions (deterministically), then "
        "uses AI to explain changes and flag risk on the matched pairs. Assists a "
        "human reviewer — it does not make legal decisions."
    )

    has_key = bool(cfg["secrets"]["anthropic_api_key"])
    with st.sidebar:
        st.header("Documents")
        up_a = st.file_uploader("Version A (original)", type=SUPPORTED, key="a")
        up_b = st.file_uploader("Version B (revised)", type=SUPPORTED, key="b")
        run_llm = st.checkbox(
            "Run AI risk analysis", value=has_key, disabled=not has_key,
            help="Needs ANTHROPIC_API_KEY in .env. Off shows the deterministic layer only.",
        )
        if not has_key:
            st.info("No API key found — running the deterministic layer only (change detection).")
        compare_clicked = st.button("Compare", type="primary")
        demo_clicked = st.button("Load built-in demo pair")

    if demo_clicked:
        path_a, path_b = _make_demo_pair()
        st.session_state["report"] = compare_documents(path_a, path_b, run_llm=run_llm)
    elif compare_clicked:
        if not up_a or not up_b:
            st.error("Please upload both Version A and Version B.")
        else:
            with st.spinner("Aligning clauses and detecting changes…"):
                report = compare_documents(_save_upload(up_a), _save_upload(up_b), run_llm=run_llm)
            st.session_state["report"] = report

    if "report" in st.session_state:
        _render_report(st.session_state["report"])
    else:
        st.info("Upload two versions (or click *Load built-in demo pair*) and press **Compare**.")


if __name__ == "__main__":
    main()
