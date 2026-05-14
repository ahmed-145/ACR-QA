"""Heuristic confidence scoring for ACR-QA findings."""

from __future__ import annotations


def calculate_confidence(finding: dict) -> float:
    """Return a [0.0, 1.0] confidence score for a finding.

    Factors:
    - Rule citation in explanation: +0.2
    - Has explanation: +0.1
    - High severity: +0.1
    - Security category: +0.1
    - Baseline: 0.5
    """
    score = 0.5

    explanation = finding.get("explanation_text", "") or finding.get("explanation", "") or ""
    rule_id = finding.get("canonical_rule_id", "") or ""
    severity = finding.get("canonical_severity", "low")
    category = finding.get("category", "")

    if rule_id and rule_id in explanation:
        score += 0.2
    if explanation:
        score += 0.1
    if severity == "high":
        score += 0.1
    if category == "security":
        score += 0.1

    return min(1.0, round(score, 2))
