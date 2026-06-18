"""Step 7: accuracy check for the DETERMINISTIC layer (terminal version).

Runs the pipeline (no LLM — no API key needed) over every eval pair and compares
detected changes to the recorded ground truth. Scoring logic lives in
legalcompare.evaluation so the UI's Accuracy tab uses the exact same code.

Two metrics:
  * Strict     — exact (type, clause): precision / recall / F1.
  * Detection  — of all real changes, how many we flagged at all (catching > typing).

Run:  python eval/run_eval.py
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from legalcompare.evaluation import evaluate_all  # noqa: E402

EVAL_DIR = ROOT / "data" / "eval"


def main() -> None:
    if not EVAL_DIR.exists() or not any(EVAL_DIR.glob("*/ground_truth.json")):
        print("No eval pairs found. Run:  python scripts/make_eval_set.py")
        return

    result = evaluate_all(EVAL_DIR)
    for p in result["pairs"]:
        print(f"\n=== {p['name']} ===")
        print(f"  ground-truth changes: {p['gt_count']} | tool flagged: {p['pred_count']}")
        print(f"  exact correct: {len(p['correct'])}   missed: {len(p['missed'])}   "
              f"false alarms: {len(p['false_alarms'])}")
        print(f"  changes detected at all (any type): {p['detected']}/{p['total_changes']}")
        for typ, key in p["missed"]:
            print(f"    MISSED   [{typ}] {key[:70]}...")
        for typ, key in p["false_alarms"]:
            print(f"    FALSE +  [{typ}] {key[:70]}...")

    o = result["overall"]
    print("\n" + "=" * 50)
    print("OVERALL (deterministic layer)")
    print(f"  Exact precision: {o['precision']:.0%}   recall: {o['recall']:.0%}   F1: {o['f1']:.0%}")
    print(f"  Change-detection recall (caught at all): {o['detection_recall']:.0%} "
          f"({o['total_detected']}/{o['total_changes']})")
    print("=" * 50)


if __name__ == "__main__":
    main()
