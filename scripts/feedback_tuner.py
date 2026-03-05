#!/usr/bin/env python3
"""
ACR-QA Feedback-Driven Severity Tuner
Analyzes stored false-positive feedback to generate per-rule severity overrides.
This is a unique ACR-QA feature — no competitor does this.
"""

import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import argparse
import json

import yaml

from DATABASE.database import Database


def compute_fp_rates(run_id=None):
    """
    Compute per-rule false positive rates from stored feedback.

    Returns:
        Dict of { rule_id: { tp, fp, total, fp_rate, recommendation } }
    """
    db = Database()

    # Get all feedback entries
    try:
        feedback = db.execute(
            """
            SELECT f.canonical_rule_id, f.canonical_severity, f.category,
                   fb.is_false_positive, fb.is_helpful
            FROM findings f
            JOIN feedback fb ON fb.finding_id = f.id
            """,
            fetch=True,
        )
    except Exception as e:
        print(f"⚠️  Could not query feedback: {e}")
        print("   This script requires the feedback table to have data.")
        return {}

    if not feedback:
        print("ℹ️  No feedback data found. Mark some findings as FP first.")
        return {}

    # Aggregate by rule
    stats = defaultdict(
        lambda: {
            "tp": 0,
            "fp": 0,
            "total": 0,
            "severity": None,
            "category": None,
        }
    )

    for row in feedback:
        rule_id = row.get("canonical_rule_id", "UNKNOWN")
        is_fp = row.get("is_false_positive", False)

        stats[rule_id]["total"] += 1
        stats[rule_id]["severity"] = row.get("canonical_severity")
        stats[rule_id]["category"] = row.get("category")

        if is_fp:
            stats[rule_id]["fp"] += 1
        else:
            stats[rule_id]["tp"] += 1

    # Calculate FP rates and recommendations
    results = {}
    for rule_id, data in stats.items():
        fp_rate = data["fp"] / data["total"] if data["total"] > 0 else 0
        data["fp_rate"] = round(fp_rate, 3)

        # Recommendation logic
        if fp_rate >= 0.7 and data["total"] >= 3:
            data["recommendation"] = "DOWNGRADE"
            data["suggested_severity"] = "low"
        elif fp_rate >= 0.5 and data["total"] >= 5:
            data["recommendation"] = "DOWNGRADE"
            current = data["severity"]
            data["suggested_severity"] = "medium" if current == "high" else "low" if current == "medium" else "low"
        elif fp_rate <= 0.1 and data["total"] >= 3:
            data["recommendation"] = "KEEP"
            data["suggested_severity"] = data["severity"]
        else:
            data["recommendation"] = "MONITOR"
            data["suggested_severity"] = data["severity"]

        results[rule_id] = data

    return results


def generate_overrides(fp_rates, min_feedback=3):
    """
    Generate severity_overrides.yml from false positive rates.

    Args:
        fp_rates: Dict from compute_fp_rates()
        min_feedback: Minimum feedback entries to consider a rule

    Returns:
        Dict suitable for YAML dump
    """
    overrides = {}

    for rule_id, data in fp_rates.items():
        if data["total"] < min_feedback:
            continue

        if data["recommendation"] == "DOWNGRADE":
            overrides[rule_id] = {
                "severity": data["suggested_severity"],
                "reason": f"FP rate {data['fp_rate']*100:.0f}% ({data['fp']}/{data['total']} marked false positive)",
                "original_severity": data["severity"],
            }

    return overrides


def print_report(fp_rates):
    """Print a formatted report of per-rule FP rates."""
    if not fp_rates:
        return

    print("\n📊 ACR-QA Feedback Analysis Report")
    print("=" * 70)
    print(f"{'Rule ID':<18} {'Severity':<10} {'TP':>4} {'FP':>4} {'Total':>6} {'FP Rate':>8} {'Action':<12}")
    print("-" * 70)

    for rule_id, data in sorted(fp_rates.items(), key=lambda x: x[1]["fp_rate"], reverse=True):
        action_icon = {
            "DOWNGRADE": "⬇️ ",
            "KEEP": "✅",
            "MONITOR": "👁️ ",
        }.get(data["recommendation"], "❓")

        print(
            f"{rule_id:<18} {data['severity'] or '?':<10} "
            f"{data['tp']:>4} {data['fp']:>4} {data['total']:>6} "
            f"{data['fp_rate']*100:>6.1f}% {action_icon} {data['recommendation']:<10}"
        )

    # Summary
    total_fp = sum(d["fp"] for d in fp_rates.values())
    total_all = sum(d["total"] for d in fp_rates.values())
    overall_rate = total_fp / total_all if total_all > 0 else 0
    downgrade_count = sum(1 for d in fp_rates.values() if d["recommendation"] == "DOWNGRADE")

    print("-" * 70)
    print(f"Overall FP Rate: {overall_rate*100:.1f}% ({total_fp}/{total_all})")
    print(f"Rules to downgrade: {downgrade_count}")
    print()


def main():
    parser = argparse.ArgumentParser(description="ACR-QA Feedback-Driven Severity Tuner")
    parser.add_argument("--apply", action="store_true", help="Write severity_overrides.yml to config/")
    parser.add_argument("--min-feedback", type=int, default=3, help="Minimum feedback entries per rule (default: 3)")
    parser.add_argument("--output", "-o", default="config/severity_overrides.yml", help="Output file path")
    parser.add_argument("--format", "-f", choices=["report", "json", "yaml"], default="report", help="Output format")
    args = parser.parse_args()

    fp_rates = compute_fp_rates()

    if not fp_rates:
        return

    if args.format == "report":
        print_report(fp_rates)
    elif args.format == "json":
        print(json.dumps(fp_rates, indent=2, default=str))

    if args.apply:
        overrides = generate_overrides(fp_rates, min_feedback=args.min_feedback)

        if not overrides:
            print("ℹ️  No rules meet the threshold for downgrade.")
            return

        output_path = Path(args.output)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        with open(output_path, "w") as f:
            yaml.dump(
                {"severity_overrides": overrides},
                f,
                default_flow_style=False,
                sort_keys=True,
            )

        print(f"✅ Severity overrides written to {output_path}")
        print(f"   {len(overrides)} rules downgraded based on feedback data.")
    elif args.format == "yaml":
        overrides = generate_overrides(fp_rates, min_feedback=args.min_feedback)
        print(yaml.dump({"severity_overrides": overrides}, default_flow_style=False))


if __name__ == "__main__":
    main()
