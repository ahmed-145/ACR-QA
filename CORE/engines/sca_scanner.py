#!/usr/bin/env python3
"""
ACR-QA SCA (Software Composition Analysis) Scanner
Scans dependencies for known vulnerabilities using pip-audit
"""

import json
import logging
import subprocess
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

logger = logging.getLogger(__name__)


class SCAScanner:
    """
    Software Composition Analysis scanner for dependency vulnerabilities.

    Uses pip-audit to identify known vulnerabilities in Python dependencies.
    Falls back to requirements.txt parsing if pip-audit is unavailable.
    """

    # Severity mapping from CVSS to canonical
    CVSS_SEVERITY = {
        "CRITICAL": "high",
        "HIGH": "high",
        "MODERATE": "medium",
        "MEDIUM": "medium",
        "LOW": "low",
        "UNKNOWN": "medium",
    }

    def __init__(self, project_dir: str = "."):
        self.project_dir = Path(project_dir)

    def scan(self) -> dict[str, Any]:
        """
        Run SCA scan on the project.

        Returns:
            Dict with vulnerabilities, stats, and findings
        """
        # Try pip-audit first
        vulnerabilities = self._run_pip_audit()

        if vulnerabilities is None:
            # Fallback: parse requirements and check against known issues
            vulnerabilities = self._scan_requirements()

        # Convert to canonical findings
        findings = self._to_canonical_findings(vulnerabilities)

        # Build summary
        severity_counts = {"high": 0, "medium": 0, "low": 0}
        for vuln in vulnerabilities:
            sev = self.CVSS_SEVERITY.get(vuln.get("severity", "UNKNOWN"), "medium")
            severity_counts[sev] = severity_counts.get(sev, 0) + 1

        return {
            "total_vulnerabilities": len(vulnerabilities),
            "severity_breakdown": severity_counts,
            "vulnerabilities": vulnerabilities,
            "findings": findings,
            "scanner": "pip-audit" if self._pip_audit_available() else "requirements-check",
        }

    def _pip_audit_available(self) -> bool:
        """Check if pip-audit is available."""
        try:
            result = subprocess.run(["pip-audit", "--version"], capture_output=True, text=True, timeout=10)
            return result.returncode == 0
        except (FileNotFoundError, subprocess.TimeoutExpired):
            return False

    def _run_pip_audit(self) -> list[dict] | None:
        """Run pip-audit and parse results."""
        if not self._pip_audit_available():
            return None

        # Find requirements file
        req_file = self._find_requirements()

        cmd = ["pip-audit", "--format=json", "--output=-"]
        if req_file:
            cmd.extend(["--requirement", str(req_file)])

        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=120,
                cwd=str(self.project_dir),
            )

            if result.stdout.strip():
                data = json.loads(result.stdout)
                return self._parse_pip_audit(data)
            return []
        except (subprocess.TimeoutExpired, json.JSONDecodeError, Exception) as e:
            logger.error(f"⚠️ pip-audit error: {e}")
            return None

    def _parse_pip_audit(self, data: dict) -> list[dict]:
        """Parse pip-audit JSON output."""
        vulnerabilities = []

        deps = data.get("dependencies", [])
        for dep in deps:
            for vuln in dep.get("vulns", []):
                vulnerabilities.append(
                    {
                        "package": dep.get("name", "unknown"),
                        "installed_version": dep.get("version", "unknown"),
                        "vulnerability_id": vuln.get("id", "UNKNOWN"),
                        "description": vuln.get("description", "No description"),
                        "fix_versions": vuln.get("fix_versions", []),
                        "severity": vuln.get("severity", "UNKNOWN"),
                        "aliases": vuln.get("aliases", []),
                    }
                )

        return vulnerabilities

    def _find_requirements(self) -> Path | None:
        """Find requirements file in project."""
        candidates = [
            "requirements.txt",
            "requirements/base.txt",
            "requirements/prod.txt",
            "requirements-prod.txt",
        ]

        for candidate in candidates:
            path = self.project_dir / candidate
            if path.exists():
                return path
        return None

    def _scan_requirements(self) -> list[dict]:
        """
        Fallback: parse requirements and check for known vulnerable patterns.
        This is a basic check — not a replacement for pip-audit.
        """
        req_file = self._find_requirements()
        if not req_file:
            return []

        vulnerabilities = []

        # Known vulnerable version patterns (simplified)
        KNOWN_VULNERABLE = {
            "requests": {
                "below": "2.31.0",
                "vuln": "CVE-2023-32681",
                "desc": "Unintended leak of Proxy-Authorization header",
            },
            "urllib3": {
                "below": "2.0.7",
                "vuln": "CVE-2023-45803",
                "desc": "Cookie header leak on redirect",
            },
            "flask": {
                "below": "2.3.2",
                "vuln": "CVE-2023-30861",
                "desc": "Session cookie security bypass",
            },
            "cryptography": {
                "below": "41.0.0",
                "vuln": "CVE-2023-38325",
                "desc": "X.509 certificate verification bypass",
            },
            "pillow": {
                "below": "10.0.1",
                "vuln": "CVE-2023-44271",
                "desc": "DoS via large TIFF file",
            },
            "django": {
                "below": "4.2.4",
                "vuln": "CVE-2023-41164",
                "desc": "Potential denial-of-service",
            },
            "pyyaml": {
                "below": "6.0.1",
                "vuln": "CVE-2020-14343",
                "desc": "Arbitrary code execution via yaml.load",
            },
        }

        try:
            with open(req_file) as f:
                for line in f:
                    line = line.strip()
                    if not line or line.startswith("#") or line.startswith("-"):
                        continue

                    # Parse package==version or package>=version
                    for sep in ["==", ">=", "~="]:
                        if sep in line:
                            pkg, version = line.split(sep, 1)
                            pkg = pkg.strip().lower()
                            version = version.strip().split(",")[0].split(";")[0].strip()

                            if pkg in KNOWN_VULNERABLE:
                                vuln_info = KNOWN_VULNERABLE[pkg]
                                if self._version_lt(version, vuln_info["below"]):
                                    vulnerabilities.append(
                                        {
                                            "package": pkg,
                                            "installed_version": version,
                                            "vulnerability_id": vuln_info["vuln"],
                                            "description": vuln_info["desc"],
                                            "fix_versions": [vuln_info["below"]],
                                            "severity": "HIGH",
                                        }
                                    )
                            break
        except Exception as e:
            logger.error(f"⚠️ Error scanning requirements: {e}")

        return vulnerabilities

    def _version_lt(self, v1: str, v2: str) -> bool:
        """Simple version comparison (a < b)."""
        try:
            parts1 = [int(x) for x in v1.split(".")]
            parts2 = [int(x) for x in v2.split(".")]
            return parts1 < parts2
        except (ValueError, AttributeError):
            return False

    def _to_canonical_findings(self, vulnerabilities: list[dict]) -> list[dict]:
        """Convert vulnerabilities to canonical finding dicts."""
        findings = []

        for vuln in vulnerabilities:
            sev = self.CVSS_SEVERITY.get(vuln.get("severity", "UNKNOWN"), "medium")
            fix_str = ", ".join(vuln.get("fix_versions", [])) or "No fix available"

            findings.append(
                {
                    "canonical_rule_id": "SCA-001",
                    "original_rule_id": vuln.get("vulnerability_id", "UNKNOWN"),
                    "severity": sev,
                    "category": "security",
                    "file": "requirements.txt",
                    "line": 0,
                    "message": (
                        f"Vulnerable dependency: {vuln['package']}=={vuln['installed_version']} "
                        f"({vuln['vulnerability_id']}). {vuln.get('description', '')}. "
                        f"Fix: upgrade to {fix_str}"
                    ),
                    "tool_name": "sca-scanner",
                }
            )

        return findings


if __name__ == "__main__":
    scanner = SCAScanner(project_dir=".")
    results = scanner.scan()

    logger.info("\n🔍 SCA Scan Results")
    logger.info(f"   Scanner: {results['scanner']}")
    logger.info(f"   Total vulnerabilities: {results['total_vulnerabilities']}")
    logger.info(f"   Breakdown: {results['severity_breakdown']}")

    for vuln in results["vulnerabilities"]:
        emoji = "🔴" if vuln.get("severity") in ("HIGH", "CRITICAL") else "🟡"
        logger.info(f"   {emoji} {vuln['package']}=={vuln['installed_version']}: {vuln['vulnerability_id']}")
        logger.info(f"      {vuln.get('description', 'N/A')}")
