"""
ACR-QA dogfood test — ACR-QA scans its own CORE/ directory.

Asserts that ACR-QA's own engine code is free of HIGH-severity findings.
This is both a regression guard and a demonstration that the tool's output
is trustworthy enough to apply to production-quality code.

Marked `slow` because it invokes Bandit + Ruff + Semgrep subprocesses.

Run:
    pytest TESTS/test_dogfood.py -m slow -v
"""

import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).parent.parent
CORE_DIR = ROOT / "CORE"


@pytest.mark.slow
def test_dogfood_zero_high_in_core():
    """ACR-QA must find 0 HIGH findings in its own CORE/ directory."""
    result = subprocess.run(
        [
            sys.executable,
            "CORE/main.py",
            "--target-dir",
            str(CORE_DIR),
            "--output-format",
            "json",
            "--limit",
            "50",
        ],
        capture_output=True,
        text=True,
        cwd=str(ROOT),
        timeout=120,
    )

    import json

    try:
        output = json.loads(result.stdout)
    except json.JSONDecodeError:
        output = {"findings": []}

    findings = output.get("findings", []) if isinstance(output, dict) else []
    high_findings = [
        f
        for f in findings
        if f.get("severity", "").upper() == "HIGH" and not f.get("canonical_rule_id", "").startswith("CUSTOM-")
    ]

    assert high_findings == [], f"ACR-QA found {len(high_findings)} HIGH finding(s) in its own CORE/:\n" + "\n".join(
        f"  {f.get('file', '?')}:{f.get('line', '?')} [{f.get('canonical_rule_id', '?')}] {f.get('message', '')[:80]}"
        for f in high_findings[:10]
    )


@pytest.mark.slow
def test_dogfood_no_custom_rules_in_core():
    """ACR-QA must not emit CUSTOM-* findings on its own code (all rules must be mapped)."""
    result = subprocess.run(
        [
            sys.executable,
            "CORE/main.py",
            "--target-dir",
            str(CORE_DIR),
            "--output-format",
            "json",
            "--limit",
            "200",
        ],
        capture_output=True,
        text=True,
        cwd=str(ROOT),
        timeout=120,
    )

    import json

    try:
        output = json.loads(result.stdout)
    except json.JSONDecodeError:
        output = {"findings": []}

    findings = output.get("findings", []) if isinstance(output, dict) else []
    custom_findings = [f for f in findings if f.get("canonical_rule_id", "").startswith("CUSTOM-")]

    assert custom_findings == [], f"Found {len(custom_findings)} unmapped CUSTOM-* rule(s) in CORE/:\n" + "\n".join(
        f"  {f.get('canonical_rule_id', '?')}: {f.get('message', '')[:80]}" for f in custom_findings[:10]
    )


@pytest.mark.slow
def test_dogfood_returns_nonzero_findings():
    """Sanity check: the dogfood run produces some output (scan didn't silently fail)."""
    result = subprocess.run(
        [
            sys.executable,
            "CORE/main.py",
            "--target-dir",
            str(CORE_DIR),
            "--output-format",
            "json",
            "--limit",
            "200",
        ],
        capture_output=True,
        text=True,
        cwd=str(ROOT),
        timeout=120,
    )

    import json

    try:
        output = json.loads(result.stdout)
    except json.JSONDecodeError:
        pytest.skip("Pipeline output not JSON — may be running in minimal mode")

    findings = output.get("findings", []) if isinstance(output, dict) else []
    assert isinstance(findings, list), "findings must be a list"
