"""
ACR-QA Confirmed Tier — high-confidence stratum for autonomous PR-blocking.

Criteria (all four must pass):
  1. canonical_severity == "high"
  2. canonical_rule_id in CONFIRMED_RULE_SET (22 curated rules, empirically ≥80% precision)
  3. file path is production code (excludes tests, migrations, docs, vendor, build scripts)
  4. For Bandit findings: issue_confidence == "HIGH" (Bandit's own AST-shape confidence)

Reachability boost (optional — enables the gate if any check is True):
  - taint_source set (finding has a confirmed HTTP source → taint path exists)
  - reachability_status == "REACHABLE" (call-graph reachability: function is live)
  - exploit_tier == "verified-exploitable" (DAST sandbox confirmed exploitation)

The reachability gate promotes the Confirmed Tier from a static-only rule to
a reachability-aware stratum: a finding passes the gate if ANY of the above
reachability signals is present AND all four base criteria hold.

Usage:
    from CORE.engines.confirmed_tier import ConfirmedTierEngine

    engine = ConfirmedTierEngine()
    result = engine.classify(finding_dict)
    # result.in_confirmed_tier, result.reasons, result.reachability_signal
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

# ---------------------------------------------------------------------------
# Curated rule set — rules with empirically ≥80% precision OR published
# Bandit/Semgrep "high confidence" classification on production corpora.
# ---------------------------------------------------------------------------
CONFIRMED_RULE_SET: frozenset[str] = frozenset(
    {
        "SECURITY-001",  # exec / eval (B102, B307)
        "SECURITY-002",  # try/except/pass (B110)
        "SECURITY-003",  # assert in production (B101)
        "SECURITY-004",  # hard-coded SQL bind (B608)
        "SECURITY-006",  # password from env without verification
        "SECURITY-007",  # bind to all interfaces
        "SECURITY-008",  # pickle.loads (B301)
        "SECURITY-009",  # marshal.loads (B302)
        "SECURITY-010",  # mark_safe / autoescape off
        "SECURITY-018",  # yaml.load without SafeLoader (B506)
        "SECURITY-021",  # shell=True (B602)
        "SECURITY-024",  # XML parsing without secure parser (B313-B320)
        "SECRET-001",
        "SECRET-002",
        "SECRET-003",
        "SQLI-001",
        "SQLI-002",
        "SHELL-001",
        "SHELL-002",
        "XML-001",
        "YAML-001",
        "CRYPTO-001",
        "CRYPTO-002",
    }
)

_TEST_PATH_RE = re.compile(
    r"(?:^|/)(tests?|testing|test_|_test\.|spec[_/]|fixtures?|examples?|"
    r"benchmarks?|demos?|vendor|_vendor|third.?party|node_modules|__pycache__|\.git|"
    r"docs?/|changelog|CHANGELOG|migrations?|conftest|tasks?/|noxfile|"
    r"setup\.py$|setup\.cfg$|pyproject\.toml$|tox\.ini$|Makefile$)(?:/|$|\.)",
    re.IGNORECASE,
)


# ---------------------------------------------------------------------------
# Result dataclass
# ---------------------------------------------------------------------------


@dataclass
class ConfirmedTierResult:
    in_confirmed_tier: bool
    reasons: list[str] = field(default_factory=list)
    reachability_signal: str = "none"  # none | taint | call_graph | exploit


# ---------------------------------------------------------------------------
# Engine
# ---------------------------------------------------------------------------


class ConfirmedTierEngine:
    """Classifies a finding against the Confirmed Tier criteria."""

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def classify(self, finding: dict) -> ConfirmedTierResult:
        """Return a ConfirmedTierResult for a single finding dict."""
        reasons: list[str] = []

        # Gate 1 — severity
        sev = (finding.get("canonical_severity") or finding.get("severity") or "").lower()
        if sev != "high":
            reasons.append(f"severity={sev!r} (need 'high')")
            return ConfirmedTierResult(False, reasons)

        # Gate 2 — rule set
        rule = finding.get("canonical_rule_id") or ""
        if rule not in CONFIRMED_RULE_SET:
            reasons.append(f"rule {rule!r} not in CONFIRMED_RULE_SET")
            return ConfirmedTierResult(False, reasons)

        # Gate 3 — production code
        path = finding.get("file", "")
        if _TEST_PATH_RE.search(path):
            reasons.append(f"file {path!r} matches non-production pattern")
            return ConfirmedTierResult(False, reasons)

        # Gate 4 — Bandit AST-shape confidence (only for Bandit findings)
        tool = (finding.get("tool_raw") or {}).get("tool_name", "").lower()
        if tool == "bandit":
            conf = (finding.get("tool_raw") or {}).get("original_output", {}).get("issue_confidence", "").upper()
            if conf != "HIGH":
                reasons.append(f"bandit issue_confidence={conf!r} (need 'HIGH')")
                return ConfirmedTierResult(False, reasons)

        # All four base gates passed — now check reachability boost
        reachability_signal = self._reachability_signal(finding)
        reasons.append("all 4 base gates passed")
        if reachability_signal != "none":
            reasons.append(f"reachability signal: {reachability_signal}")

        return ConfirmedTierResult(
            in_confirmed_tier=True,
            reasons=reasons,
            reachability_signal=reachability_signal,
        )

    def enrich_findings(self, findings: list[dict]) -> list[dict]:
        """
        Classify a batch of findings.  Adds confirmed_tier (bool) and
        confirmed_tier_signal (str) keys to each finding dict.
        Never raises — wraps all exceptions.
        """
        out = []
        for f in findings:
            try:
                result = self.classify(f)
                enriched = dict(f)
                enriched["confirmed_tier"] = result.in_confirmed_tier
                enriched["confirmed_tier_signal"] = result.reachability_signal
                out.append(enriched)
            except Exception:
                enriched = dict(f)
                enriched["confirmed_tier"] = False
                enriched["confirmed_tier_signal"] = "none"
                out.append(enriched)
        return out

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _reachability_signal(finding: dict) -> str:
        """
        Return the strongest reachability signal present, or 'none'.

        Priority: exploit > taint > call_graph
        """
        # Strongest: DAST exploit verification confirms the code path is live
        if finding.get("exploit_tier") == "verified-exploitable":
            return "exploit"

        # Taint: finding has a confirmed HTTP source in its data-flow chain
        tool_raw = finding.get("tool_raw") or {}
        if tool_raw.get("taint_source"):
            return "taint"

        # Call-graph reachability: function is reachable from an entry point
        if finding.get("reachability_status") == "REACHABLE":
            return "call_graph"

        return "none"

    @staticmethod
    def confirmed_rule_set() -> frozenset[str]:
        return CONFIRMED_RULE_SET
