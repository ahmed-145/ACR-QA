#!/usr/bin/env python3
"""
ACR-QA Go Language Adapter
Orchestrates Go-specific analysis tools:
  - gosec     : Security vulnerabilities (CWE-mapped)
  - staticcheck: Style, bugs, unused code
  - semgrep   : Custom security patterns (reuses existing semgrep install)

Rule mapping follows ACR-QA canonical ID scheme.
Requires: gosec >= 2.18, staticcheck >= 2023.1, Go >= 1.18
"""

from __future__ import annotations

import json
import logging
import os
import shutil
import subprocess
from pathlib import Path
from typing import Any

from CORE.adapters.base import LanguageAdapter
from CORE.engines.normalizer import CanonicalFinding

# ---------------------------------------------------------------------------
# Rule mappings
# ---------------------------------------------------------------------------

# gosec rule ID → ACR-QA canonical ID
GOSEC_RULE_MAPPING: dict[str, str] = {
    # Injection
    "G101": "HARDCODE-001",  # Hardcoded credentials
    "G102": "SECURITY-001",  # Bind to all interfaces
    "G103": "SECURITY-002",  # Use of unsafe package
    "G104": "SECURITY-003",  # Errors unhandled
    "G106": "SECURITY-004",  # SSH InsecureIgnoreHostKey
    "G107": "SECURITY-005",  # URL provided to HTTP request as taint input
    "G108": "SECURITY-006",  # Profiling endpoint auto-registered
    "G109": "SECURITY-007",  # Potential integer overflow
    "G110": "SECURITY-008",  # Potential DoS via decompression bomb
    "G111": "SECURITY-009",  # File path traversal
    "G112": "SECURITY-010",  # Vulnerable to slowloris attack
    "G114": "SECURITY-011",  # HTTP serve with no timeout
    "G201": "SECURITY-027",  # SQL query construction using format string
    "G202": "SECURITY-028",  # SQL query construction using string concat
    "G203": "SECURITY-029",  # Use of unescaped data in HTML templates
    "G204": "SECURITY-030",  # Subprocess launched with variable
    "G301": "SECURITY-031",  # Poor file permissions (mkdir)
    "G302": "SECURITY-032",  # Poor file permissions (chmod/OpenFile)
    "G303": "SECURITY-033",  # Creating tempfile using predictable path
    "G304": "SECURITY-034",  # File path provided as taint input
    "G305": "SECURITY-035",  # File traversal when extracting zip
    "G306": "SECURITY-036",  # Poor file permissions (WriteFile)
    "G401": "SECURITY-050",  # Use of weak crypto primitive (MD5/SHA1)
    "G402": "SECURITY-051",  # TLS InsecureSkipVerify
    "G403": "SECURITY-052",  # RSA key < 2048 bits
    "G404": "SECURITY-053",  # Weak random number source
    "G501": "SECURITY-054",  # Blocklisted import: crypto/md5
    "G502": "SECURITY-055",  # Blocklisted import: crypto/des
    "G503": "SECURITY-056",  # Blocklisted import: crypto/rc4
    "G504": "SECURITY-057",  # Blocklisted import: net/http/cgi
    "G505": "SECURITY-058",  # Blocklisted import: crypto/sha1
    "G601": "SECURITY-059",  # Implicit memory aliasing in for loop
}

# staticcheck rule ID → ACR-QA canonical ID
STATICCHECK_RULE_MAPPING: dict[str, str] = {
    # Simple/Correctness
    "SA1006": "STYLE-010",  # Printf with dynamic format, no args
    "SA1019": "STYLE-011",  # Use of deprecated identifier
    "SA4006": "VAR-001",  # Unused variable
    "SA4008": "VAR-002",  # Loop variable used after loop
    "SA4009": "VAR-003",  # Function argument overwritten before use
    "SA4010": "VAR-004",  # Unreachable code after return
    "SA4016": "VAR-005",  # Certain bitwise operations always zero
    "SA4017": "DEAD-001",  # Pure function whose result is discarded
    "SA4018": "DEAD-002",  # Self-assignment
    "SA5000": "SECURITY-060",  # Nil pointer dereference
    "SA5001": "SECURITY-061",  # Deferring close before checking error
    "SA9003": "DEAD-003",  # Empty body in if/else branch
    "S1000": "STYLE-012",  # Use plain channel send/receive
    "S1001": "STYLE-013",  # Replace loop with copy()
    "S1002": "STYLE-014",  # Omit comparison with boolean constant
    "S1003": "STYLE-015",  # Replace call to strings.Index with strings.Contains
    "S1016": "STYLE-016",  # Use a type conversion instead of struct literal
    "S1021": "STYLE-017",  # Merge variable declaration and assignment
    "S1023": "STYLE-021",  # Redundant return statement
    "S1025": "STYLE-022",  # Don't use fmt.Sprintf with a single string
    "S1031": "STYLE-023",  # Unnecessary nil check around range
    "S1039": "STYLE-024",  # Unnecessary use of fmt.Sprintf
    "ST1005": "STYLE-025",  # Incorrectly formatted error string
    "ST1006": "STYLE-026",  # Poorly chosen receiver name
    "U1000": "DEAD-004",  # Unused code
}

logger = logging.getLogger(__name__)


class GoAdapter(LanguageAdapter):
    """
    Go language adapter for ACR-QA.

    Tools:
        - gosec      : CWE-mapped security vulnerability scanner
        - staticcheck: Style, correctness, unused code
        - semgrep    : Custom Go security patterns (if rules present)

    Findings are normalized to ACR-QA CanonicalFinding format,
    deduped by (file, line, canonical_rule_id), and returned as dicts.
    """

    GOSEC_PATH = os.path.expanduser("~/.local/gopath/bin/gosec")
    STATICCHECK_PATH = os.path.expanduser("~/.local/gopath/bin/staticcheck")

    @property
    def language_name(self) -> str:
        return "Go"

    @property
    def file_extensions(self) -> list[str]:
        return [".go"]

    def get_tools(self) -> list[dict[str, Any]]:
        return [
            {
                "name": "gosec",
                "version": "2.18.2",
                "purpose": "CWE-mapped Go security vulnerability scanner",
                "check": self.GOSEC_PATH,
            },
            {
                "name": "staticcheck",
                "version": "2023.1.3",
                "purpose": "Go style, correctness, and unused code",
                "check": self.STATICCHECK_PATH,
            },
            {
                "name": "semgrep",
                "version": "any",
                "purpose": "Custom Go security patterns",
                "check": "semgrep",
            },
        ]

    def check_tools_available(self) -> dict[str, bool]:
        return {
            "gosec": os.path.isfile(self.GOSEC_PATH) and os.access(self.GOSEC_PATH, os.X_OK),
            "staticcheck": os.path.isfile(self.STATICCHECK_PATH) and os.access(self.STATICCHECK_PATH, os.X_OK),
            "semgrep": shutil.which("semgrep") is not None,
        }

    def run_tools(self, output_dir: str = "DATA/outputs") -> dict[str, Any]:
        """Run gosec + staticcheck against target_dir. Returns raw results dict."""
        Path(output_dir).mkdir(parents=True, exist_ok=True)
        results: dict[str, Any] = {
            "gosec": None,
            "staticcheck": [],
            "semgrep": {"results": []},
            "errors": [],
        }

        # ── gosec ──────────────────────────────────────────────────────
        if os.path.isfile(self.GOSEC_PATH):
            try:
                proc = subprocess.run(
                    [self.GOSEC_PATH, "-fmt", "json", "./..."],
                    cwd=str(self.target_dir),
                    capture_output=True,
                    text=True,
                    timeout=120,
                )
                # gosec exits non-zero when it finds issues — that's normal
                stdout = proc.stdout.strip()
                if stdout:
                    results["gosec"] = json.loads(stdout)
                    logger.info("gosec: %d issues found", len(results["gosec"].get("Issues", [])))
            except json.JSONDecodeError as e:
                results["errors"].append(f"gosec JSON parse error: {e}")
            except subprocess.TimeoutExpired:
                results["errors"].append("gosec timed out after 120s")
            except Exception as e:
                results["errors"].append(f"gosec error: {e}")
        else:
            results["errors"].append(f"gosec not found at {self.GOSEC_PATH}")

        # ── staticcheck ────────────────────────────────────────────────
        if os.path.isfile(self.STATICCHECK_PATH):
            try:
                proc = subprocess.run(
                    [self.STATICCHECK_PATH, "./..."],
                    cwd=str(self.target_dir),
                    capture_output=True,
                    text=True,
                    timeout=120,
                )
                lines = (proc.stdout + proc.stderr).strip().splitlines()
                results["staticcheck"] = [l for l in lines if l.strip()]
                logger.info("staticcheck: %d findings", len(results["staticcheck"]))
            except subprocess.TimeoutExpired:
                results["errors"].append("staticcheck timed out after 120s")
            except Exception as e:
                results["errors"].append(f"staticcheck error: {e}")
        else:
            results["errors"].append(f"staticcheck not found at {self.STATICCHECK_PATH}")

        # ── semgrep (optional) ─────────────────────────────────────────
        if shutil.which("semgrep"):
            try:
                # Use local rules if available, skip semgrep if not
                rules_path = Path(__file__).parent.parent / "TOOLS" / "semgrep" / "go-rules.yml"
                if not rules_path.exists():
                    logger.info("No Go semgrep rules found at %s — skipping", rules_path)
                else:
                    proc = subprocess.run(
                        [
                            "semgrep",
                            "--config",
                            str(rules_path),
                            "--lang",
                            "go",
                            "--json",
                            "--quiet",
                            str(self.target_dir),
                        ],
                        capture_output=True,
                        text=True,
                        timeout=60,
                    )
                    if proc.stdout.strip():
                        results["semgrep"] = json.loads(proc.stdout)
                        logger.info("semgrep go: %d findings", len(results["semgrep"].get("results", [])))
            except Exception as e:
                results["errors"].append(f"semgrep error: {e}")

        return results

    # ------------------------------------------------------------------
    # Normalization
    # ------------------------------------------------------------------

    def normalize_gosec(self, gosec_data: dict) -> list[CanonicalFinding]:
        """Convert gosec JSON output to CanonicalFindings."""
        findings: list[CanonicalFinding] = []
        for issue in gosec_data.get("Issues", []):
            rule_id = issue.get("rule_id", "")
            canonical_rule_id = GOSEC_RULE_MAPPING.get(rule_id, f"CUSTOM-GO-{rule_id}")
            sev_raw = issue.get("severity", "MEDIUM").upper()
            severity = {"HIGH": "high", "MEDIUM": "medium", "LOW": "low"}.get(sev_raw, "medium")
            cwe_data = issue.get("cwe", {})
            cwe_id = str(cwe_data.get("id", "")) if isinstance(cwe_data, dict) else ""
            finding = CanonicalFinding.create(
                canonical_rule_id=canonical_rule_id,
                rule_id=rule_id,
                message=issue.get("details", ""),
                file=issue.get("file", "unknown"),
                line=int(str(issue.get("line", 0)).split("-")[0]),
                column=int(str(issue.get("column", 0)).split("-")[0]),
                severity=severity,
                category=self._infer_category(canonical_rule_id),
                tool_name="gosec",
                tool_output=issue,
            )
            # Preserve native gosec severity — RULE_SEVERITY uses Python-centric mappings
            # that don't correctly reflect Go-specific rule semantics.
            # Also expose CWE ID at top-level tool_raw for direct access.
            finding = finding.model_copy(
                update={
                    "severity": severity,
                    "tool_raw": {**finding.tool_raw, "cwe_id": cwe_id},
                }
            )
            findings.append(finding)
        return findings

    def normalize_staticcheck(self, lines: list[str]) -> list[CanonicalFinding]:
        """
        Convert staticcheck text output to CanonicalFindings.
        Format: file.go:line:col: SA1006 message
        """
        findings: list[CanonicalFinding] = []
        import re

        pattern = re.compile(r"^(.+?):(\d+):(\d+):\s+(.+?)\s+\((\w+)\)$")
        for line in lines:
            m = pattern.match(line.strip())
            if not m:
                continue
            file_path, lineno, col, message, rule_id = m.groups()
            canonical_rule_id = STATICCHECK_RULE_MAPPING.get(rule_id, f"CUSTOM-GO-{rule_id}")
            # Infer severity from rule prefix
            if rule_id.startswith("SA5") or rule_id.startswith("SA9"):
                severity = "medium"
            elif rule_id.startswith("SA4") or rule_id.startswith("U"):
                severity = "low"
            else:
                severity = "low"
            findings.append(
                CanonicalFinding.create(
                    canonical_rule_id=canonical_rule_id,
                    rule_id=rule_id,
                    message=message,
                    file=file_path,
                    line=int(lineno),
                    column=int(col),
                    severity=severity,
                    category=self._infer_category(canonical_rule_id),
                    tool_name="staticcheck",
                    tool_output={"raw_line": line},
                )
            )
        return findings

    def get_all_findings(self, results: dict[str, Any]) -> list[CanonicalFinding]:
        """
        Normalize all tool results into a unified deduplicated CanonicalFinding list.
        """
        all_findings: list[CanonicalFinding] = []

        if results.get("gosec"):
            gosec_findings = self.normalize_gosec(results["gosec"])
            all_findings.extend(gosec_findings)
            logger.info("gosec normalized: %d findings", len(gosec_findings))

        if results.get("staticcheck"):
            sc_findings = self.normalize_staticcheck(results["staticcheck"])
            all_findings.extend(sc_findings)
            logger.info("staticcheck normalized: %d findings", len(sc_findings))

        # Deduplicate by (file, line, column, canonical_rule_id)
        seen: set[tuple[str, int, int, str]] = set()
        deduped: list[CanonicalFinding] = []
        for f in all_findings:
            key = (f.file, f.line, f.column, f.canonical_rule_id)
            if key not in seen:
                seen.add(key)
                deduped.append(f)

        removed = len(all_findings) - len(deduped)
        if removed:
            logger.info("Go deduplication removed %d duplicates", removed)

        return deduped

    def get_rule_mappings(self) -> dict[str, str]:
        combined = {}
        combined.update(GOSEC_RULE_MAPPING)
        combined.update(STATICCHECK_RULE_MAPPING)
        return combined

    @staticmethod
    def detect_language(target_dir: str) -> str:
        """Return 'go' if directory contains .go files, else 'unknown'."""
        target = Path(target_dir)
        go_files = list(target.rglob("*.go"))
        if go_files:
            return "go"
        return "unknown"

    @staticmethod
    def _infer_category(canonical_id: str) -> str:
        prefix_map = {
            "SECURITY": "security",
            "HARDCODE": "security",
            "CUSTOM": "security",
            "VAR": "dead-code",
            "DEAD": "dead-code",
            "STYLE": "style",
        }
        for prefix, category in prefix_map.items():
            if canonical_id.startswith(prefix):
                return category
        return "best-practice"
