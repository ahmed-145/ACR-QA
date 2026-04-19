"""
ACR-QA Confidence Scorer — Feature 5
Assigns a 0-100 confidence score to every finding based on multiple signals.

Score interpretation:
    90-100  Very high — well-known vulnerability pattern, multiple tools agree
    70-89   High — strong rule match, security category
    50-69   Medium — single tool, design/style category
    30-49   Low — heuristic rule, low severity
    0-29    Very low — unknown rule, no context

Signals used (weighted):
    1. Severity          — high=40, medium=25, low=10
    2. Category          — security=20, design=10, best-practice=5, style=0
    3. Tool reliability  — bandit/semgrep=15, ruff=8, vulture=5, radon=5
    4. Rule specificity  — known rule=10, CUSTOM-=5, unmapped=0
    5. Fix validated     — validated fix exists=10, failed=0
    6. Multi-tool agree  — same file+line flagged by 2+ tools: +5 bonus (applied externally)
"""

from __future__ import annotations

from typing import Any

# Per-signal weights (must sum to 100 for a "perfect" finding)
_SEVERITY_SCORE = {"high": 40, "medium": 25, "low": 10, "critical": 40}
_CATEGORY_SCORE = {
    "security": 20,
    "design": 10,
    "best-practice": 5,
    "dead-code": 5,
    "duplication": 5,
    "style": 0,
}
_TOOL_SCORE = {
    "bandit": 15,
    "semgrep": 15,
    "secrets": 15,
    "cbom": 12,
    "sca": 12,
    "eslint": 10,
    "ruff": 8,
    "vulture": 5,
    "radon": 5,
    "jscpd": 3,
    "npm-audit": 12,
}
_RULE_BONUS = 10  # rule is in the known registry
_CUSTOM_BONUS = 5  # CUSTOM- rule (Semgrep custom, somewhat known)
_FIX_BONUS = 10  # AI fix passed linter validation


class ConfidenceScorer:
    """
    Computes a 0-100 integer confidence score for a canonical finding.
    Higher score = higher confidence that this is a true positive.
    """

    def __init__(self, known_rule_ids: set[str] | None = None):
        """
        Args:
            known_rule_ids: Set of canonical rule IDs in the registry.
                            If None, loads from SeverityScorer.RULE_SEVERITY.
        """
        if known_rule_ids is not None:
            self._known = known_rule_ids
        else:
            try:
                from CORE.engines.severity_scorer import SeverityScorer

                self._known = set(SeverityScorer.RULE_SEVERITY.keys())
            except Exception:
                self._known = set()

    def score(self, finding: dict[str, Any], fix_validated: bool | None = None) -> int:
        """
        Compute confidence score for a single finding.

        Args:
            finding: Canonical finding dict with at least:
                     canonical_severity, category, tool, canonical_rule_id
            fix_validated: True if AI fix passed linter validation (Feature 1).
                           Pass None if unknown.

        Returns:
            Integer 0-100.
        """
        total = 0

        # Signal 1: Severity
        sev = finding.get("canonical_severity", finding.get("severity", "low")).lower()
        total += _SEVERITY_SCORE.get(sev, 10)

        # Signal 2: Category
        cat = finding.get("category", "style").lower()
        total += _CATEGORY_SCORE.get(cat, 0)

        # Signal 3: Tool reliability
        tool = finding.get("tool", "").lower()
        # tool_raw may have a nested tool_name
        if not tool:
            tool = finding.get("tool_raw", {}).get("tool_name", "") if isinstance(finding.get("tool_raw"), dict) else ""
        total += _TOOL_SCORE.get(tool, 5)

        # Signal 4: Rule specificity
        rule_id = finding.get("canonical_rule_id", finding.get("rule_id", ""))
        if rule_id in self._known:
            total += _RULE_BONUS
        elif rule_id.startswith("CUSTOM-"):
            total += _CUSTOM_BONUS

        # Signal 5: Fix validated
        if fix_validated is True:
            total += _FIX_BONUS

        # Clamp to 0-100
        return max(0, min(100, total))

    def score_batch(self, findings: list[dict[str, Any]]) -> list[int]:
        """Score a list of findings. Returns list of integers in same order."""
        return [self.score(f) for f in findings]

    @staticmethod
    def label(score: int) -> str:
        """Human-readable label for a confidence score."""
        if score >= 90:
            return "very high"
        if score >= 70:
            return "high"
        if score >= 50:
            return "medium"
        if score >= 30:
            return "low"
        return "very low"


def compute_confidence(finding: dict[str, Any], fix_validated: bool | None = None) -> int:
    """Convenience function — score a single finding without instantiating scorer."""
    return ConfidenceScorer().score(finding, fix_validated=fix_validated)
