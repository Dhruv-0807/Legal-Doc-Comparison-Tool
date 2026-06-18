"""Step 7 (shared logic): score the deterministic layer against ground truth.

Extracted here so both the terminal script (eval/run_eval.py) and the UI's
Accuracy tab run the *same* scoring code — no duplication, no drift.
"""

from __future__ import annotations

import json
from pathlib import Path

from .pipeline import compare_documents
from .schemas import ChangeType, ReviewReport


def predicted_changes(report: ReviewReport) -> set[tuple[str, str]]:
    """The tool's detected changes as (type, key). Key is the A text for
    modified/removed and the B text for added — matching the ground-truth keys."""
    preds: set[tuple[str, str]] = set()
    for p in report.pairs:
        if p.change_type == ChangeType.MODIFIED and p.clause_a:
            preds.add(("modified", p.clause_a.text))
        elif p.change_type == ChangeType.REMOVED and p.clause_a:
            preds.add(("removed", p.clause_a.text))
        elif p.change_type == ChangeType.ADDED and p.clause_b:
            preds.add(("added", p.clause_b.text))
    return preds


def _detected_at_all(change: dict, pred: set[tuple[str, str]]) -> bool:
    key, t = change["key"], change["type"]
    if t in ("modified", "removed"):
        return ("modified", key) in pred or ("removed", key) in pred
    return ("added", key) in pred


def evaluate_pair(pair_dir: Path) -> dict:
    """Score one eval pair directory (must contain ground_truth.json)."""
    gt = json.loads((pair_dir / "ground_truth.json").read_text(encoding="utf-8"))
    report = compare_documents(
        str(pair_dir / gt["doc_a"]), str(pair_dir / gt["doc_b"]), run_llm=False
    )
    gt_set = {(c["type"], c["key"]) for c in gt["changes"]}
    pred = predicted_changes(report)
    detected = sum(_detected_at_all(c, pred) for c in gt["changes"])
    return {
        "name": pair_dir.name,
        "gt_count": len(gt_set),
        "pred_count": len(pred),
        "correct": sorted(gt_set & pred),
        "missed": sorted(gt_set - pred),
        "false_alarms": sorted(pred - gt_set),
        "detected": detected,
        "total_changes": len(gt["changes"]),
    }


def evaluate_all(eval_dir: Path) -> dict:
    """Score every eval pair and aggregate into overall metrics."""
    dirs = sorted(d for d in eval_dir.iterdir() if (d / "ground_truth.json").exists())
    pairs = [evaluate_pair(d) for d in dirs]

    tp = sum(len(p["correct"]) for p in pairs)
    fp = sum(len(p["false_alarms"]) for p in pairs)
    fn = sum(len(p["missed"]) for p in pairs)
    total_changes = sum(p["total_changes"] for p in pairs)
    total_detected = sum(p["detected"] for p in pairs)

    precision = tp / (tp + fp) if (tp + fp) else 0.0
    recall = tp / (tp + fn) if (tp + fn) else 0.0
    f1 = 2 * precision * recall / (precision + recall) if (precision + recall) else 0.0
    detection_recall = total_detected / total_changes if total_changes else 0.0

    return {
        "pairs": pairs,
        "overall": {
            "precision": precision,
            "recall": recall,
            "f1": f1,
            "detection_recall": detection_recall,
            "tp": tp, "fp": fp, "fn": fn,
            "total_changes": total_changes,
            "total_detected": total_detected,
        },
    }
