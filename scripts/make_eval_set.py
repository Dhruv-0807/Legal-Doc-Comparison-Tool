"""Step 7: generate A/B contract pairs from templates with a KNOWN change list.

For each template we hold a "version A" (generic, public-style boilerplate) and an
explicit edit script (keep / modify / remove per clause, plus additions and an
optional reordering). Applying the script produces "version B" AND a recorded
ground-truth list of exactly what changed. That ground truth is the answer key the
accuracy check (eval/run_eval.py) scores the tool against.

Run:  python scripts/make_eval_set.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

import docx  # noqa: E402

EVAL_DIR = ROOT / "data" / "eval"


def build_pair(a_clauses, actions, additions, b_order):
    """Apply the edit script -> (b_clauses, changes, unchanged_keys).

    actions[i] is "keep", "remove", or ("modify", new_text) for a_clauses[i].
    b_order lists the ORIGINAL indices of kept clauses in the order they appear in
    B (this is how we model reordering). Additions are appended after.
    Change keys are the *original A text* for modified/removed and the *new text*
    for additions — exactly what the evaluator can match against.
    """
    kept: dict[int, str] = {}
    changes: list[dict] = []
    unchanged: list[str] = []

    for i, act in enumerate(actions):
        if act == "keep":
            kept[i] = a_clauses[i]
            unchanged.append(a_clauses[i])
        elif act == "remove":
            changes.append({"type": "removed", "key": a_clauses[i]})
        elif isinstance(act, tuple) and act[0] == "modify":
            kept[i] = act[1]
            changes.append({"type": "modified", "key": a_clauses[i]})
        else:
            raise ValueError(f"bad action: {act!r}")

    for new in additions:
        changes.append({"type": "added", "key": new})

    b_clauses = [kept[i] for i in b_order] + list(additions)
    return b_clauses, changes, unchanged


def _write_docx(path: Path, clauses: list[str]) -> None:
    d = docx.Document()
    for c in clauses:
        d.add_paragraph(c)
    d.save(str(path))


def make(name, a_clauses, actions, additions, b_order):
    b_clauses, changes, unchanged = build_pair(a_clauses, actions, additions, b_order)
    out = EVAL_DIR / name
    out.mkdir(parents=True, exist_ok=True)
    _write_docx(out / "version_A.docx", a_clauses)
    _write_docx(out / "version_B.docx", b_clauses)
    gt = {
        "doc_a": "version_A.docx",
        "doc_b": "version_B.docx",
        "changes": changes,
        "unchanged": unchanged,
    }
    (out / "ground_truth.json").write_text(json.dumps(gt, indent=2), encoding="utf-8")
    n = {"modified": 0, "added": 0, "removed": 0}
    for c in changes:
        n[c["type"]] += 1
    print(f"  {name}: {len(a_clauses)} clauses -> {len(b_clauses)} | "
          f"{n['modified']} modified, {n['added']} added, {n['removed']} removed, "
          f"{len(unchanged)} unchanged")


# --------------------------------------------------------------------------- #
# Template 1 — Mutual NDA
# --------------------------------------------------------------------------- #
NDA = [
    "1. Confidentiality. Each party shall keep the other party's Confidential "
    "Information strictly confidential and shall not disclose it to any third party.",
    "2. Term. This Agreement commences on the Effective Date and continues for "
    "twelve (12) months unless terminated earlier in accordance with its terms.",
    "3. Governing Law. This Agreement shall be governed by and construed in "
    "accordance with the laws of Singapore.",
    "4. Assignment. Neither party may assign this Agreement without the prior "
    "written consent of the other party.",
]
NDA_ACTIONS = [
    ("modify", "1. Confidentiality. Neither party shall disclose the other's "
               "Confidential Information to any third party and shall keep it strictly secret."),  # reworded -> embedding
    ("modify", "2. Term. This Agreement commences on the Effective Date and continues for "
               "twenty-four (24) months unless terminated earlier in accordance with its terms."),  # value -> fuzzy
    "keep",      # Governing Law unchanged...
    "remove",    # Assignment removed
]
NDA_ADD = [
    "5. Indemnification. Each party shall indemnify the other against losses "
    "arising from its breach of this Agreement.",
]
NDA_BORDER = [2, 0, 1]  # B puts Governing Law first (reorder), then Conf, Term


# --------------------------------------------------------------------------- #
# Template 2 — Services Agreement
# --------------------------------------------------------------------------- #
SVC = [
    "1. Scope of Services. The Provider shall perform the services described in "
    "the attached Statement of Work.",
    "2. Fees. The Client shall pay the Provider a fee of ten thousand dollars "
    "($10,000) for the services.",
    "3. Payment Terms. The Client shall pay each invoice within thirty (30) days "
    "of the invoice date.",
    "4. Limitation of Liability. The Provider's total liability under this "
    "Agreement shall not exceed the fees paid by the Client.",
    "5. Governing Law. This Agreement shall be governed by the laws of Singapore.",
    "6. Confidentiality. Each party shall keep the other's confidential "
    "information confidential during and after the term of this Agreement.",
]
SVC_ACTIONS = [
    "keep",      # Scope unchanged
    ("modify", "2. Fees. The Client shall pay the Provider a fee of fifteen thousand "
               "dollars ($15,000) for the services."),  # value -> fuzzy
    ("modify", "3. Payment Terms. The Client shall pay each invoice within forty-five "
               "(45) days of the invoice date."),  # value -> fuzzy
    ("modify", "4. Limitation of Liability. Neither party shall be liable for any "
               "indirect or consequential damages, and the Provider's aggregate liability "
               "shall not exceed two times the total fees paid under this Agreement."),  # reworded + cap change -> embedding, risky
    "keep",      # Governing Law unchanged
    "remove",    # Confidentiality removed
]
SVC_ADD = [
    "7. Termination. Either party may terminate this Agreement for convenience on "
    "thirty (30) days' written notice.",
]
SVC_BORDER = [4, 0, 1, 2, 3]  # Governing Law moved to front


def main() -> None:
    print("Generating evaluation pairs with known changes:")
    make("nda", NDA, NDA_ACTIONS, NDA_ADD, NDA_BORDER)
    make("services", SVC, SVC_ACTIONS, SVC_ADD, SVC_BORDER)
    print(f"\nWrote eval pairs to: {EVAL_DIR}")
    print("Run the accuracy check with:  python eval/run_eval.py")


if __name__ == "__main__":
    main()
