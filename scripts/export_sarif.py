#!/usr/bin/env python3
"""
ACR-QA SARIF Export
Exports findings in SARIF v2.1.0 format for GitHub Security tab integration.
SARIF = Static Analysis Results Interchange Format (OASIS standard)
"""

import json
import sys
import uuid
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import argparse

from DATABASE.database import Database


def generate_sarif(run_id=None, output_file=None):
    """
    Export analysis findings as a SARIF v2.1.0 JSON file.

    Args:
        run_id: Analysis run ID (None = latest)
        output_file: Output file path (None = auto-generate)
    """
    db = Database()

    # Get run info
    if not run_id:
        runs = db.get_analysis_runs(limit=1)
        if not runs:
            print("❌ No analysis runs found.")
            return None
        run_id = runs[0]["id"]

    findings = db.get_findings(run_id)
    if not findings:
        print(f"⚠️  No findings for run {run_id}")
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
                        "version": "2.4.0",
                        "informationUri": "https://github.com/ACR-QA",
                        "semanticVersion": "2.4.0",
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

        # Build result
        file_path = f.get("file_path", "unknown")
        line = f.get("line_number", 1)
        col = f.get("column_number", 1)

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
            },
        }

        results.append(result)

    sarif["runs"][0]["results"] = results

    # Write output
    if not output_file:
        output_file = f"DATA/outputs/acr-qa-run-{run_id}.sarif"

    Path(output_file).parent.mkdir(parents=True, exist_ok=True)
    with open(output_file, "w") as fp:
        json.dump(sarif, fp, indent=2)

    print(f"✅ SARIF exported: {output_file}")
    print(f"   Rules: {len(seen_rules)}")
    print(f"   Results: {len(results)}")
    print(f"\n   Upload to GitHub: gh api repos/OWNER/REPO/code-scanning/sarifs --input {output_file}")
    return output_file


def main():
    parser = argparse.ArgumentParser(description="ACR-QA SARIF Export")
    parser.add_argument("--run-id", type=int, help="Analysis run ID (default: latest)")
    parser.add_argument("--output", "-o", help="Output SARIF file path")
    args = parser.parse_args()

    generate_sarif(run_id=args.run_id, output_file=args.output)


if __name__ == "__main__":
    main()
