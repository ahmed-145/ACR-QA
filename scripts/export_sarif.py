#!/usr/bin/env python3
"""
ACR-QA SARIF Export
Exports findings in SARIF v2.1.0 format for GitHub Security tab integration.
SARIF = Static Analysis Results Interchange Format (OASIS standard)
"""

import json
import logging
import sys
import uuid
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import argparse

from CORE import __version__
from DATABASE.database import Database

logger = logging.getLogger(__name__)


def generate_sarif(run_id=None, output_file=None, confirmed_only: bool = False):
    """Export a DB run's findings as SARIF v2.1.0 (thin wrapper over build_sarif)."""
    db = Database()
    if not run_id:
        runs = db.get_analysis_runs(limit=1)
        if not runs:
            logger.error("❌ No analysis runs found.")
            return None
        run_id = runs[0]["id"]
    findings = db.get_findings(run_id)
    if not findings:
        logger.error(f"⚠️  No findings for run {run_id}")
        return None
    return build_sarif(findings, output_file=output_file, confirmed_only=confirmed_only, run_id=run_id)


def build_sarif(findings, output_file=None, confirmed_only: bool = False, run_id="latest"):
    """Build a SARIF v2.1.0 file from a findings list — DB-free and field-tolerant.

    Accepts both DB rows (``file_path``/``line_number``) and in-memory
    CanonicalFindings (``file``/``line``), so the CLI can emit SARIF standalone
    without a database. Returns the written path, or None if there are no findings.
    """
    if not findings:
        return None

    # Build SARIF structure
    sarif = {
        "$schema": "https://raw.githubusercontent.com/oasis-tcs/sarif-spec/master/Schemata/sarif-schema-2.1.0.json",
        "version": "2.1.0",
        "runs": [
            {
                "tool": {
                    "driver": {
                        "name": "ACR-QA",
                        "version": __version__,
                        "informationUri": "https://github.com/ahmed-145/ACR-QA",
                        "semanticVersion": __version__,
                        "rules": [],
                    }
                },
                "results": [],
                "invocations": [
                    {
                        "executionSuccessful": True,
                        "startTimeUtc": datetime.utcnow().isoformat() + "Z",
                    }
                ],
            }
        ],
    }

    # Track unique rules for the rules array
    seen_rules = {}
    results = []

    severity_map = {
        "high": "error",
        "medium": "warning",
        "low": "note",
    }

    category_to_tag = {
        "security": ["security", "vulnerability"],
        "best-practice": ["maintainability", "best-practice"],
        "style": ["style", "readability"],
        "dead-code": ["maintainability", "dead-code"],
        "duplication": ["maintainability", "duplication"],
        "complexity": ["maintainability", "complexity"],
        "design": ["design", "architecture"],
        "performance": ["performance"],
    }

    # --confirmed-only: export only Confirmed Tier findings (96.4% precision gate)
    # Ideal for GHAS / GitHub Security tab — zero noise upload
    if confirmed_only:
        from CORE.engines.confirmed_tier import ConfirmedTierEngine as _CTEngine

        _ct = _CTEngine()
        before = len(findings)
        findings = [
            f
            for f in findings
            if _ct.classify({**f, "file": f.get("file_path") or f.get("file", "")}).in_confirmed_tier
        ]
        logger.info(f"   Confirmed-only filter: {before} → {len(findings)} findings")

    for f in findings:
        rule_id = f.get("rule_id", f.get("canonical_rule_id", "UNKNOWN"))
        category = f.get("category", "unknown")
        severity = f.get("severity", "medium").lower()

        # Add rule if not seen
        if rule_id not in seen_rules:
            rule_entry = {
                "id": rule_id,
                "shortDescription": {"text": f.get("message", rule_id)[:200]},
                "fullDescription": {"text": f.get("message", rule_id)},
                "defaultConfiguration": {"level": severity_map.get(severity, "warning")},
                "properties": {"tags": category_to_tag.get(category, ["general"])},
                "helpUri": f"https://github.com/ACR-QA/rules/{rule_id}",
            }
            seen_rules[rule_id] = len(sarif["runs"][0]["tool"]["driver"]["rules"])
            sarif["runs"][0]["tool"]["driver"]["rules"].append(rule_entry)

        # Build result (field-tolerant: DB rows use file_path/line_number,
        # in-memory CanonicalFindings use file/line)
        file_path = f.get("file_path") or f.get("file") or "unknown"
        line = f.get("line_number") or f.get("line") or 1
        col = f.get("column_number") or f.get("column") or 1

        # Confirmed Tier classification
        from CORE.engines.confirmed_tier import ConfirmedTierEngine

        ct_finding = dict(f)
        ct_finding["file"] = file_path
        ct_result = ConfirmedTierEngine().classify(ct_finding)

        result = {
            "ruleId": rule_id,
            "ruleIndex": seen_rules[rule_id],
            "level": severity_map.get(severity, "warning"),
            "message": {"text": f.get("message", "Issue detected")},
            "locations": [
                {
                    "physicalLocation": {
                        "artifactLocation": {
                            "uri": file_path,
                            "uriBaseId": "%SRCROOT%",
                        },
                        "region": {
                            "startLine": max(line, 1),
                            "startColumn": max(col, 1),
                        },
                    }
                }
            ],
            "fingerprints": {
                "primaryLocationLineHash": str(uuid.uuid5(uuid.NAMESPACE_URL, f"{file_path}:{line}:{rule_id}"))
            },
            "properties": {
                "tool": f.get("tool", "unknown"),
                "category": category,
                "confidence_score": f.get("confidence_score"),
                # Confirmed Tier — the trust-layer signal for GHAS / merge gate consumers
                "acrqa/confirmed_tier": ct_result.in_confirmed_tier,
                "acrqa/confirmed_tier_signal": ct_result.reachability_signal,
                "acrqa/precision_context": "96.4% conservative precision gate" if ct_result.in_confirmed_tier else None,
            },
            # GHAS severity mapping: Confirmed Tier findings get highest precision tag
            **({"partialFingerprints": {"acrqa/confirmed": "true"}} if ct_result.in_confirmed_tier else {}),
        }

        results.append(result)

    sarif["runs"][0]["results"] = results

    # Write output
    if not output_file:
        output_file = f"DATA/outputs/acr-qa-run-{run_id}.sarif"

    Path(output_file).parent.mkdir(parents=True, exist_ok=True)
    with open(output_file, "w") as fp:
        json.dump(sarif, fp, indent=2)

    logger.info(f"✅ SARIF exported: {output_file}")
    logger.info(f"   Rules: {len(seen_rules)}")
    logger.info(f"   Results: {len(results)}")
    logger.info(f"\n   Upload to GitHub: gh api repos/OWNER/REPO/code-scanning/sarifs --input {output_file}")
    return output_file


def main():
    parser = argparse.ArgumentParser(description="ACR-QA SARIF Export")
    parser.add_argument("--run-id", type=int, help="Analysis run ID (default: latest)")
    parser.add_argument("--output", "-o", help="Output SARIF file path")
    parser.add_argument(
        "--confirmed-only",
        action="store_true",
        help="Export only Confirmed Tier findings (96.4%% precision gate). Recommended for GHAS uploads.",
    )
    args = parser.parse_args()

    generate_sarif(run_id=args.run_id, output_file=args.output, confirmed_only=args.confirmed_only)


if __name__ == "__main__":
    main()
