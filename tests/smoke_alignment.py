"""Smoke test for Step 4 alignment: build two versions of a contract with KNOWN
changes (reword, reorder, value change, add, remove) and check the aligner labels
each correctly. No files needed — we construct Clause lists directly.

Run:  python tests/smoke_alignment.py
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from legalcompare.alignment.aligner import align  # noqa: E402
from legalcompare.alignment.similarity import active_backend  # noqa: E402
from legalcompare.schemas import Clause  # noqa: E402


def clause(doc: str, i: int, text: str) -> Clause:
    return Clause(doc_name=doc, index=i, heading=text[:30], text=text, start_char=0, end_char=len(text))


# Version A
A = [
    clause("A", 0, "1. Confidentiality. Each party shall keep the other party's Confidential "
                   "Information strictly confidential and shall not disclose it to any third party."),
    clause("A", 1, "2. Term. This Agreement commences on the Effective Date and continues for "
                   "twelve (12) months unless terminated earlier."),
    clause("A", 2, "3. Governing Law. This Agreement shall be governed by the laws of Singapore."),
    clause("A", 3, "4. Assignment. Neither party may assign this Agreement without prior written consent."),
]

# Version B: Governing Law moved to top (reorder, identical -> UNCHANGED);
# Confidentiality reworded (-> MODIFIED); Term 12 -> 24 months (-> MODIFIED);
# Assignment removed (-> REMOVED); Indemnification added (-> ADDED).
B = [
    clause("B", 0, "3. Governing Law. This Agreement shall be governed by the laws of Singapore."),
    clause("B", 1, "1. Confidentiality. Neither party shall disclose the other's Confidential "
                   "Information to any third party and shall keep it strictly secret."),
    clause("B", 2, "2. Term. This Agreement commences on the Effective Date and continues for "
                   "twenty-four (24) months unless terminated earlier."),
    clause("B", 3, "5. Indemnification. Each party shall indemnify the other against losses "
                   "arising from its breach of this Agreement."),
]


def main() -> None:
    print(f"Semantic backend: {active_backend()}\n")
    pairs = align(A, B)
    print(f"{'CHANGE':<10}{'METHOD':<11}{'SIM':<7}A -> B")
    print("-" * 70)
    for p in pairs:
        a = p.clause_a.heading if p.clause_a else "—"
        b = p.clause_b.heading if p.clause_b else "—"
        print(f"{p.change_type.value:<10}{p.method.value:<11}{p.similarity:<7}{a[:22]:<24} | {b[:22]}")


if __name__ == "__main__":
    main()
