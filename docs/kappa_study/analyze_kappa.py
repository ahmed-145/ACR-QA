#!/usr/bin/env python3
"""Compute Fleiss' kappa from 5 rater CSV files.

Usage:
    python3 analyze_kappa.py submitted/rater1.csv submitted/rater2.csv ...

Each CSV must have columns: finding_id, label, confidence, note
Label must be one of: TP, FP, NEEDS_REVIEW

Outputs:
    - Per-item agreement matrix
    - Fleiss' kappa + 95% CI (bootstrap)
    - Suggested thesis sentence
"""

from __future__ import annotations

import csv
import sys
from pathlib import Path
from collections import defaultdict


LABELS = ("TP", "FP", "NEEDS_REVIEW")
N_BOOTSTRAP = 2000


def load_csv(path: str) -> dict[int, str]:
    """Return {finding_id: label} from a rater CSV."""
    ratings: dict[int, str] = {}
    with open(path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            fid = int(row["finding_id"])
            label = row["label"].strip().upper()
            if label not in LABELS:
                print(f"  WARNING {path}: finding {fid} has unknown label '{label}' — skipped")
                continue
            ratings[fid] = label
    return ratings


def fleiss_kappa(rating_matrix: list[list[int]]) -> float:
    """Compute Fleiss' κ from a subject × category count matrix.

    rating_matrix[i][j] = number of raters who assigned category j to subject i.
    """
    n_subjects = len(rating_matrix)
    n_categories = len(rating_matrix[0])
    n_raters = sum(rating_matrix[0])

    # p̄_j: proportion of all assignments to category j
    p_bar = [sum(rating_matrix[i][j] for i in range(n_subjects)) / (n_subjects * n_raters) for j in range(n_categories)]

    # P̄_i: proportion of agreeing pairs for subject i
    p_i = [(sum(c**2 for c in rating_matrix[i]) - n_raters) / (n_raters * (n_raters - 1)) for i in range(n_subjects)]

    P_bar = sum(p_i) / n_subjects
    P_e = sum(pj**2 for pj in p_bar)

    if P_e == 1.0:
        return 1.0
    return (P_bar - P_e) / (1.0 - P_e)


def bootstrap_ci(rating_matrix: list[list[int]], n: int = N_BOOTSTRAP, alpha: float = 0.05):
    """Bootstrap 95% CI for Fleiss' κ."""
    import random

    kappas = []
    for _ in range(n):
        sample = random.choices(rating_matrix, k=len(rating_matrix))
        kappas.append(fleiss_kappa(sample))
    kappas.sort()
    lo = kappas[int(alpha / 2 * n)]
    hi = kappas[int((1 - alpha / 2) * n)]
    return lo, hi


def interpret(kappa: float) -> str:
    if kappa >= 0.90:
        return "almost perfect"
    if kappa >= 0.78:
        return "substantial"
    if kappa >= 0.61:
        return "moderate"
    if kappa >= 0.41:
        return "fair"
    return "slight"


def main(csv_paths: list[str]) -> None:
    if len(csv_paths) < 2:
        print("Usage: analyze_kappa.py rater1.csv rater2.csv [rater3.csv ...]")
        sys.exit(1)

    print(f"\nLoading {len(csv_paths)} rater files...")
    all_ratings: list[dict[int, str]] = []
    for p in csv_paths:
        r = load_csv(p)
        print(f"  {Path(p).name}: {len(r)} ratings loaded")
        all_ratings.append(r)

    # Find common finding IDs
    common_ids = sorted(set.intersection(*[set(r.keys()) for r in all_ratings]))
    print(f"\nCommon findings across all raters: {len(common_ids)}")

    if len(common_ids) == 0:
        print("ERROR: No common finding IDs found.")
        sys.exit(1)

    # Build rating matrix (subjects × categories)
    label_to_idx = {lbl: i for i, lbl in enumerate(LABELS)}
    matrix: list[list[int]] = []
    for fid in common_ids:
        row = [0] * len(LABELS)
        for rater in all_ratings:
            lbl = rater.get(fid)
            if lbl and lbl in label_to_idx:
                row[label_to_idx[lbl]] += 1
        matrix.append(row)

    # Per-category distribution
    print("\nLabel distribution across all raters:")
    totals = [sum(matrix[i][j] for i in range(len(matrix))) for j in range(len(LABELS))]
    grand_total = sum(totals)
    for j, lbl in enumerate(LABELS):
        pct = 100 * totals[j] / grand_total if grand_total else 0
        print(f"  {lbl:15s}: {totals[j]:4d}  ({pct:.1f}%)")

    # Fleiss' kappa
    kappa = fleiss_kappa(matrix)
    lo, hi = bootstrap_ci(matrix)
    interp = interpret(kappa)

    print(f"\n{'='*50}")
    print(f"  Fleiss' κ = {kappa:.3f}  (95% CI [{lo:.3f}, {hi:.3f}])")
    print(f"  Interpretation: {interp} agreement")
    print(f"{'='*50}")

    # Agreement per finding
    disagreements = [
        (common_ids[i], matrix[i])
        for i in range(len(common_ids))
        if max(matrix[i]) < len(all_ratings)  # not unanimous
    ]
    print(f"\nDisagreements (non-unanimous): {len(disagreements)} / {len(common_ids)}")
    for fid, row in sorted(disagreements, key=lambda x: max(x[1]), reverse=False)[:10]:
        votes = ", ".join(f"{LABELS[j]}:{row[j]}" for j in range(len(LABELS)) if row[j] > 0)
        print(f"  Finding #{fid}: [{votes}]")

    # Thesis sentence
    print(f"\n📝 Thesis sentence:")
    print(
        f"Five independent raters classified {len(common_ids)} ACR-QA findings "
        f"as TP/FP/NEEDS_REVIEW following pre-registered instructions "
        f"(see `docs/kappa_study/RATING_INSTRUCTIONS.md`). "
        f"Fleiss' κ = {kappa:.3f} (95% CI [{lo:.3f}, {hi:.3f}]), "
        f"indicating {interp} agreement and supporting the reproducibility "
        f"of the ground-truth labels used in the evaluation."
    )


if __name__ == "__main__":
    main(sys.argv[1:])
