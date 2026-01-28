#!/usr/bin/env python3
"""
Evaluation Metrics Calculator for ACR-QA v2.0
Computes precision, recall, F1 score from labeled ground truth
"""

import sys
from pathlib import Path
from collections import defaultdict

sys.path.insert(0, str(Path(__file__).parent.parent))

from DATABASE.database import Database
import argparse


def compute_metrics(run_id=None, by_severity=False, by_category=False):
    """
    Compute evaluation metrics from ground truth labels

    Requires findings to be labeled with ground_truth column:
    - TP (True Positive): Correctly detected real issue
    - FP (False Positive): Incorrectly flagged as issue
    - TN (True Negative): Correctly ignored (rare in this context)
    - FN (False Negative): Missed real issue (requires manual analysis)

    Args:
        run_id: Specific run to evaluate (None = all runs)
        by_severity: Break down metrics by severity
        by_category: Break down metrics by category
    """
    db = Database()

    # Get findings
    if run_id:
        findings = db.get_findings_with_explanations(run_id)
        print(f"📊 Computing metrics for Run {run_id}...")
    else:
        # Get all findings from recent runs
        runs = db.get_recent_runs(limit=10)
        findings = []
        for run in runs:
            findings.extend(db.get_findings_with_explanations(run["id"]))
        print(f"📊 Computing metrics across {len(runs)} runs...")

    print(f"   Total findings: {len(findings)}")

    # Filter labeled findings
    labeled_findings = [f for f in findings if f.get("ground_truth")]

    if not labeled_findings:
        print("\n⚠️  No labeled findings found!")
        print("   To label findings:")
        print("   1. Use dashboard to mark false positives")
        print("   2. Or directly update database:")
        print("      UPDATE findings SET ground_truth='TP' WHERE id=X;")
        return None

    print(f"   Labeled findings: {len(labeled_findings)}")

    # Count labels
    tp = sum(1 for f in labeled_findings if f.get("ground_truth") == "TP")
    fp = sum(1 for f in labeled_findings if f.get("ground_truth") == "FP")
    tn = sum(1 for f in labeled_findings if f.get("ground_truth") == "TN")
    fn = sum(1 for f in labeled_findings if f.get("ground_truth") == "FN")

    # Calculate overall metrics
    precision = tp / (tp + fp) if (tp + fp) > 0 else 0
    recall = tp / (tp + fn) if (tp + fn) > 0 else 0
    f1 = (
        2 * (precision * recall) / (precision + recall)
        if (precision + recall) > 0
        else 0
    )

    # Print overall results
    print("\n" + "=" * 60)
    print("OVERALL METRICS")
    print("=" * 60)
    print(f"True Positives (TP):  {tp:4d}")
    print(f"False Positives (FP): {fp:4d}")
    print(f"False Negatives (FN): {fn:4d}")
    print(f"True Negatives (TN):  {tn:4d}")
    print("-" * 60)
    print(f"Precision: {precision:6.2%}  (TP / (TP + FP))")
    print(f"Recall:    {recall:6.2%}  (TP / (TP + FN))")
    print(f"F1 Score:  {f1:6.2%}  (2 * P * R / (P + R))")
    print("=" * 60)

    # Check targets
    print("\n🎯 Target Evaluation (from PRD):")
    precision_target = 0.70
    recall_target = 0.60

    if precision >= precision_target:
        print(f"✅ Precision {precision:.2%} >= {precision_target:.0%} target")
    else:
        print(
            f"❌ Precision {precision:.2%} < {precision_target:.0%} target (gap: {(precision_target - precision):.2%})"
        )

    if recall >= recall_target:
        print(f"✅ Recall {recall:.2%} >= {recall_target:.0%} target")
    else:
        print(
            f"⚠️  Recall {recall:.2%} < {recall_target:.0%} target (gap: {(recall_target - recall):.2%})"
        )

    # By severity breakdown
    if by_severity:
        print("\n" + "=" * 60)
        print("METRICS BY SEVERITY")
        print("=" * 60)

        by_sev = defaultdict(lambda: {"tp": 0, "fp": 0, "fn": 0})

        for f in labeled_findings:
            sev = f.get("canonical_severity", "low")  # Use canonical_severity
            gt = f.get("ground_truth")
            if gt == "TP":
                by_sev[sev]["tp"] += 1
            elif gt == "FP":
                by_sev[sev]["fp"] += 1
            elif gt == "FN":
                by_sev[sev]["fn"] += 1

        for sev in ["high", "medium", "low"]:  # Updated to canonical levels
            if sev in by_sev:
                s = by_sev[sev]
                tp_s = s["tp"]
                fp_s = s["fp"]
                fn_s = s["fn"]

                prec_s = tp_s / (tp_s + fp_s) if (tp_s + fp_s) > 0 else 0
                rec_s = tp_s / (tp_s + fn_s) if (tp_s + fn_s) > 0 else 0
                f1_s = (
                    2 * (prec_s * rec_s) / (prec_s + rec_s)
                    if (prec_s + rec_s) > 0
                    else 0
                )

                print(f"\n{sev.upper()}:")
                print(f"  TP: {tp_s:3d} | FP: {fp_s:3d} | FN: {fn_s:3d}")
                print(
                    f"  Precision: {prec_s:6.2%} | Recall: {rec_s:6.2%} | F1: {f1_s:6.2%}"
                )

    # By category breakdown
    if by_category:
        print("\n" + "=" * 60)
        print("METRICS BY CATEGORY")
        print("=" * 60)

        by_cat = defaultdict(lambda: {"tp": 0, "fp": 0, "fn": 0})

        for f in labeled_findings:
            cat = f["category"]
            gt = f.get("ground_truth")
            if gt == "TP":
                by_cat[cat]["tp"] += 1
            elif gt == "FP":
                by_cat[cat]["fp"] += 1
            elif gt == "FN":
                by_cat[cat]["fn"] += 1

        for cat, s in sorted(by_cat.items()):
            tp_c = s["tp"]
            fp_c = s["fp"]
            fn_c = s["fn"]

            prec_c = tp_c / (tp_c + fp_c) if (tp_c + fp_c) > 0 else 0
            rec_c = tp_c / (tp_c + fn_c) if (tp_c + fn_c) > 0 else 0
            f1_c = (
                2 * (prec_c * rec_c) / (prec_c + rec_c) if (prec_c + rec_c) > 0 else 0
            )

            print(f"\n{cat.upper()}:")
            print(f"  TP: {tp_c:3d} | FP: {fp_c:3d} | FN: {fn_c:3d}")
            print(
                f"  Precision: {prec_c:6.2%} | Recall: {rec_c:6.2%} | F1: {f1_c:6.2%}"
            )

    # Save results
    results = {
        "overall": {
            "true_positives": tp,
            "false_positives": fp,
            "false_negatives": fn,
            "true_negatives": tn,
            "precision": precision,
            "recall": recall,
            "f1_score": f1,
            "total_labeled": len(labeled_findings),
        }
    }

    output_file = Path("outputs") / "metrics_results.json"
    output_file.parent.mkdir(exist_ok=True)

    import json

    with open(output_file, "w") as f:
        json.dump(results, f, indent=2)

    print(f"\n💾 Results saved to: {output_file}")

    return results


def label_seeded_dataset():
    """
    Helper: Label the seeded dataset findings as TP
    (Since we intentionally created those issues)
    """
    print("🏷️  Labeling seeded dataset as True Positives...")

    db = Database()

    # Get all findings from seeded-repo files
    runs = db.get_recent_runs(limit=10)

    labeled_count = 0

    for run in runs:
        if "seeded-repo" in run["repo_name"]:
            findings = db.get_findings_with_explanations(run["id"])

            for f in findings:
                # Label as TP if from seeded files
                if (
                    "seeded-repo" in f["file_path"]
                    or "comprehensive-issues" in f["file_path"]
                ):
                    # Update ground truth using db.execute
                    db.execute(
                        """
                        UPDATE findings 
                        SET ground_truth = 'TP'
                        WHERE id = %s
                    """,
                        (f["id"],),
                    )
                    labeled_count += 1

    print(f"✅ Labeled {labeled_count} findings as True Positives")
    print("   Run: python3 scripts/compute_metrics.py")


def main():
    parser = argparse.ArgumentParser(description="Compute ACR-QA Evaluation Metrics")
    parser.add_argument("run_id", type=int, nargs="?", help="Specific run to evaluate")
    parser.add_argument(
        "--by-severity", action="store_true", help="Break down by severity"
    )
    parser.add_argument(
        "--by-category", action="store_true", help="Break down by category"
    )
    parser.add_argument(
        "--label-seeded", action="store_true", help="Auto-label seeded dataset as TP"
    )

    args = parser.parse_args()

    try:
        if args.label_seeded:
            label_seeded_dataset()
        else:
            compute_metrics(
                run_id=args.run_id,
                by_severity=args.by_severity,
                by_category=args.by_category,
            )
    except Exception as e:
        print(f"❌ Error computing metrics: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
