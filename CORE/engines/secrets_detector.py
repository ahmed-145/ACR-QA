#!/usr/bin/env python3
"""
ACR-QA Secrets Detector
Pattern-based detection of hardcoded secrets, API keys, passwords, and tokens
"""

import re
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).parent.parent.parent))


class SecretsDetector:
    """
    Detect hardcoded secrets in source code using regex patterns.

    Detects:
    - API keys (AWS, Google, GitHub, Slack, etc.)
    - Passwords and tokens
    - Private keys (RSA, SSH, PGP)
    - JWT tokens
    - Database connection strings with credentials
    - Generic high-entropy strings in assignments
    """

    # Secret patterns: (name, regex, severity, description)
    PATTERNS = [
        # AWS
        (
            "AWS Access Key",
            r"(?:AKIA|ASIA)[A-Z0-9]{16}",
            "high",
            "AWS Access Key ID detected",
        ),
        (
            "AWS Secret Key",
            r'(?i)aws[_\-]?secret[_\-]?(?:access)?[_\-]?key\s*[=:]\s*["\']?([A-Za-z0-9/+=]{40})',
            "high",
            "AWS Secret Access Key detected",
        ),
        # Google
        (
            "Google API Key",
            r"AIza[A-Za-z0-9\-_]{35}",
            "high",
            "Google API Key detected",
        ),
        (
            "Google OAuth",
            r"[0-9]+-[a-z0-9_]{32}\.apps\.googleusercontent\.com",
            "high",
            "Google OAuth client ID detected",
        ),
        # GitHub
        (
            "GitHub Token",
            r"(?:ghp|gho|ghu|ghs|ghr)_[A-Za-z0-9_]{36,}",
            "high",
            "GitHub personal access token detected",
        ),
        (
            "GitHub OAuth",
            r'(?i)github[_\-]?(?:oauth|token|secret)\s*[=:]\s*["\']?([a-f0-9]{40})',
            "high",
            "GitHub OAuth secret detected",
        ),
        # Generic API Keys
        (
            "API Key Assignment",
            r'(?i)(?:api[_\-]?key|apikey|api_secret)\s*[=:]\s*["\']([A-Za-z0-9\-_]{20,})["\']',
            "high",
            "Hardcoded API key detected",
        ),
        # Passwords
        (
            "Password Assignment",
            r'(?i)(?:password|passwd|pwd|pass)\s*[=:]\s*["\']([^"\']{6,})["\']',
            "high",
            "Hardcoded password detected",
        ),
        (
            "Database URL with Password",
            r"(?i)(?:postgres|mysql|mongodb|redis)://[^:]+:([^@]+)@",
            "high",
            "Database connection string with embedded password",
        ),
        # Tokens
        (
            "Bearer Token",
            r"(?i)bearer\s+[A-Za-z0-9\-_\.]{20,}",
            "high",
            "Hardcoded bearer token detected",
        ),
        (
            "JWT Token",
            r"eyJ[A-Za-z0-9\-_]+\.eyJ[A-Za-z0-9\-_]+\.[A-Za-z0-9\-_]+",
            "high",
            "Hardcoded JWT token detected",
        ),
        (
            "Auth Token",
            r'(?i)(?:auth[_\-]?token|access[_\-]?token|secret[_\-]?token)\s*[=:]\s*["\']([A-Za-z0-9\-_\.]{20,})["\']',
            "high",
            "Hardcoded authentication token detected",
        ),
        # Private Keys
        (
            "RSA Private Key",
            r"-----BEGIN (?:RSA )?PRIVATE KEY-----",
            "high",
            "RSA private key detected in source code",
        ),
        (
            "SSH Private Key",
            r"-----BEGIN OPENSSH PRIVATE KEY-----",
            "high",
            "SSH private key detected in source code",
        ),
        (
            "PGP Private Key",
            r"-----BEGIN PGP PRIVATE KEY BLOCK-----",
            "high",
            "PGP private key detected in source code",
        ),
        # Slack
        (
            "Slack Token",
            r"xox[bpors]-[0-9]{10,13}-[a-zA-Z0-9-]{20,}",
            "high",
            "Slack API token detected",
        ),
        (
            "Slack Webhook",
            r"https://hooks\.slack\.com/services/T[A-Z0-9]+/B[A-Z0-9]+/[A-Za-z0-9]+",
            "medium",
            "Slack webhook URL detected",
        ),
        # Generic secrets
        (
            "Secret Assignment",
            r'(?i)(?:secret|private[_\-]?key|encryption[_\-]?key)\s*[=:]\s*["\']([A-Za-z0-9\-_\.]{16,})["\']',
            "medium",
            "Hardcoded secret value detected",
        ),
        # Stripe
        (
            "Stripe Key",
            r"(?:sk|pk)_(?:live|test)_[A-Za-z0-9]{24,}",
            "high",
            "Stripe API key detected",
        ),
        # SendGrid
        (
            "SendGrid Key",
            r"SG\.[A-Za-z0-9\-_]{22}\.[A-Za-z0-9\-_]{43}",
            "high",
            "SendGrid API key detected",
        ),
        # Twilio
        ("Twilio Key", r"SK[a-f0-9]{32}", "medium", "Twilio API key detected"),
    ]

    # Files/directories to skip
    SKIP_PATTERNS = [
        r"\.git/",
        r"__pycache__/",
        r"\.venv/",
        r"venv/",
        r"node_modules/",
        r"\.env\.example",
        r"\.env\.sample",
        r".*\.pyc$",
        r".*\.lock$",
        r".*\.min\.js$",
    ]

    # File extensions to scan
    SCAN_EXTENSIONS = {
        ".py",
        ".js",
        ".ts",
        ".java",
        ".go",
        ".rb",
        ".php",
        ".yml",
        ".yaml",
        ".json",
        ".toml",
        ".cfg",
        ".ini",
        ".env",
        ".sh",
        ".bash",
        ".conf",
        ".config",
    }

    def __init__(self):
        self.compiled_patterns = [
            (name, re.compile(pattern), severity, desc) for name, pattern, severity, desc in self.PATTERNS
        ]
        self.skip_compiled = [re.compile(p) for p in self.SKIP_PATTERNS]

    def scan_file(self, filepath: str) -> list[dict[str, Any]]:
        """
        Scan a single file for secrets.

        Returns:
            List of detected secrets with location and details
        """
        results = []

        try:
            with open(filepath, encoding="utf-8", errors="replace") as f:
                lines = f.readlines()
        except Exception:
            return []

        for line_num, line in enumerate(lines, 1):
            # Skip comment-only lines (likely documentation/examples)
            stripped = line.strip()
            if stripped.startswith("#") and "TODO" not in stripped:
                continue

            for name, pattern, severity, desc in self.compiled_patterns:
                match = pattern.search(line)
                if match:
                    # Avoid false positives from env var references
                    if re.search(r"os\.(?:getenv|environ)", line):
                        continue
                    if re.search(r"(?:\.env|environment|config\.get)", line, re.IGNORECASE):
                        continue

                    # Mask the actual secret value
                    secret_value = match.group(0)
                    if len(secret_value) > 8:
                        masked = secret_value[:4] + "*" * (len(secret_value) - 8) + secret_value[-4:]
                    else:
                        masked = "****"

                    results.append(
                        {
                            "type": name,
                            "file": filepath,
                            "line": line_num,
                            "severity": severity,
                            "description": desc,
                            "masked_value": masked,
                            "canonical_rule_id": "SECRET-001",
                            "category": "security",
                            "message": f"{desc} at line {line_num}: {masked}",
                        }
                    )

        return results

    def scan_directory(self, directory: str) -> dict[str, Any]:
        """
        Scan an entire directory for secrets.

        Args:
            directory: Path to directory

        Returns:
            Dict with results summary and per-file findings
        """
        dir_path = Path(directory)
        all_findings = []
        files_scanned = 0

        for filepath in dir_path.rglob("*"):
            if not filepath.is_file():
                continue

            # Check extension
            if filepath.suffix not in self.SCAN_EXTENSIONS:
                continue

            # Check skip patterns
            rel_path = str(filepath)
            if any(p.search(rel_path) for p in self.skip_compiled):
                continue

            files_scanned += 1
            findings = self.scan_file(str(filepath))
            all_findings.extend(findings)

        # Summary
        severity_counts = {"high": 0, "medium": 0, "low": 0}
        for f in all_findings:
            severity_counts[f["severity"]] = severity_counts.get(f["severity"], 0) + 1

        types_found = set(f["type"] for f in all_findings)

        return {
            "directory": directory,
            "files_scanned": files_scanned,
            "total_secrets": len(all_findings),
            "severity_breakdown": severity_counts,
            "secret_types_found": list(types_found),
            "findings": all_findings,
        }

    def to_canonical_findings(self, findings: list[dict]) -> list[dict]:
        """Convert findings to canonical format for database storage."""
        canonical = []
        for f in findings:
            canonical.append(
                {
                    "canonical_rule_id": "SECRET-001",
                    "original_rule_id": f["type"],
                    "severity": f["severity"],
                    "category": "security",
                    "file": f["file"],
                    "line": f["line"],
                    "message": f["message"],
                    "tool_name": "secrets-detector",
                }
            )
        return canonical


if __name__ == "__main__":
    detector = SecretsDetector()

    target = sys.argv[1] if len(sys.argv) > 1 else "."

    if Path(target).is_file():
        findings = detector.scan_file(target)
        print(f"\n🔐 Secrets scan: {target}")
        print(f"   Found: {len(findings)} potential secrets")
        for f in findings:
            print(f"   🔴 Line {f['line']}: {f['type']} — {f['masked_value']}")
    else:
        results = detector.scan_directory(target)
        print(f"\n🔐 Secrets Scan Results: {target}")
        print(f"   Files scanned: {results['files_scanned']}")
        print(f"   Secrets found: {results['total_secrets']}")
        print(f"   Breakdown: {results['severity_breakdown']}")
        if results["secret_types_found"]:
            print(f"   Types: {', '.join(results['secret_types_found'])}")
        for f in results["findings"][:10]:
            print(f"   🔴 {f['file']}:{f['line']} — {f['type']}: {f['masked_value']}")
