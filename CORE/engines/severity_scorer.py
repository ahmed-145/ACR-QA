"""
Severity Scoring Engine for ACR-QA v2.0
Maps canonical rule IDs to severity levels following PRD guidelines
"""

from typing import Any


class SeverityScorer:
    """
    Assigns severity based on canonical rule ID and context

    Severity Guidelines (from PRD):
    - HIGH: Security vulnerabilities, crashes, data loss risks
    - MEDIUM: Design smells, maintainability issues, performance problems
    - LOW: Style violations, minor best practices
    """

    # Canonical Rule ID → Base Severity Mapping
    RULE_SEVERITY = {
        # ══════════════════════════════════════════════
        # HIGH: Security vulnerabilities, crashes, data loss
        # ══════════════════════════════════════════════
        "SECURITY-001": "high",  # eval() / exec() usage
        "SECURITY-003": "high",  # set_bad_file_permissions
        "SECURITY-004": "high",  # hardcoded_bind_all_interfaces
        "SECURITY-005": "high",  # hardcoded_password (string/funcarg/default)
        "SECURITY-013": "high",  # request_with_no_cert_validation
        "SECURITY-020": "high",  # paramiko_calls
        "SECURITY-021": "high",  # subprocess_popen_with_shell=True
        "SECURITY-024": "high",  # start_process_with_a_shell
        "SECURITY-027": "high",  # ⚠️ SQL INJECTION (hardcoded_sql_expressions)
        "SECURITY-029": "high",  # django_extra_used
        "SECURITY-030": "high",  # django_rawsql_used
        "SECURITY-031": "high",  # jinja2_autoescape_false (XSS)
        "SECURITY-033": "high",  # django_mark_safe (XSS)
        "HARDCODE-001": "high",  # Hardcoded password (flake8-bandit)
        # ══════════════════════════════════════════════
        # MEDIUM: Risky patterns, weak crypto, design smells
        # ══════════════════════════════════════════════
        "SECURITY-008": "high",  # pickle / marshal usage (RCE risk via CWE-502)
        "SECURITY-009": "medium",  # ⚠️ MD5 / weak hash
        "SECURITY-010": "medium",  # DES / weak cipher
        "SECURITY-011": "medium",  # mktemp usage
        "SECURITY-012": "medium",  # mark_safe usage
        "SECURITY-014": "medium",  # ssl_with_bad_version
        "SECURITY-015": "medium",  # ssl_with_bad_defaults
        "SECURITY-016": "medium",  # ssl_with_no_version
        "SECURITY-017": "medium",  # weak_cryptographic_key
        "SECURITY-018": "high",  # yaml_load unsafe (arbitrary code exec via CWE-502)
        "SECURITY-019": "medium",  # ssh_no_host_key_verification
        "SECURITY-022": "medium",  # subprocess_without_shell
        "SECURITY-023": "medium",  # any_other_function_with_shell
        "SECURITY-025": "medium",  # start_process_with_no_shell
        "SECURITY-026": "medium",  # start_process_with_partial_path
        "SECURITY-028": "medium",  # linux_commands_wildcard_injection
        "SECURITY-032": "medium",  # use_of_mako_templates
        "SOLID-001": "medium",  # Too many parameters
        "COMPLEXITY-001": "medium",  # High cyclomatic complexity
        "DUP-001": "medium",  # Code duplication
        "PATTERN-001": "medium",  # Mutable default arguments
        "EXCEPT-001": "medium",  # Bare except
        # ══════════════════════════════════════════════
        # LOW: Style, minor issues, informational
        # ══════════════════════════════════════════════
        "SECURITY-002": "low",  # assert used (noisy — demoted from medium)
        "SECURITY-006": "low",  # hardcoded_tmp_directory
        "SECURITY-007": "low",  # try_except_pass / try_except_continue
        "DEAD-001": "low",  # Unused code (low unless large)
        "IMPORT-001": "low",  # Unused imports
        "IMPORT-002": "low",  # Import sorting
        "VAR-001": "low",  # Unused variables
        "STYLE-001": "low",  # Line too long
        "STYLE-002": "low",  # Missing docstring
        "STYLE-003": "low",  # Type union syntax (UP007)
        "STYLE-004": "low",  # Format specifiers (UP031)
        "STYLE-005": "low",  # Deprecated imports (UP035)
        "STYLE-006": "low",  # isinstance union (UP038)
        "STYLE-007": "low",  # print/pprint found
        "ERROR-001": "medium",  # Undefined name (F821) — real bug
        "ERROR-002": "low",  # Redefined unused name
        "EXCEPT-002": "low",  # raise without from
        "NAMING-001": "low",  # Bad naming
        "NAMING-002": "low",  # Dunder function naming
        "NAMING-003": "low",  # Import alias naming
        "TYPE-001": "low",  # Missing type annotation
        "TYPE-002": "low",  # TYPE_CHECKING block
        "ASYNC-001": "low",  # Async without await
        # ── Round 3 god-mode additions ──
        "STYLE-008": "low",  # Use builtin type for annotations
        "STYLE-009": "low",  # Use datetime.UTC alias
        "STYLE-010": "low",  # Use os module errors
        "STYLE-011": "low",  # Use f-string
        "NAMING-004": "low",  # First arg of classmethod should be cls
        "NAMING-005": "low",  # Exception name should end in Error
        "BEST-PRACTICE-001": "low",  # stacklevel in warnings.warn
        "BEST-PRACTICE-002": "low",  # zip() without strict=
        # ── Round 5 additions (Django, SQLAlchemy, aiohttp, black, Pillow) ──
        "STYLE-014": "low",  # UP041: Replace timeout=None form
        "STYLE-015": "low",  # UP030: Implicit positional format fields
        "STYLE-016": "low",  # B018: Useless expression / statement
        "BEST-PRACTICE-003": "low",  # B027: Empty method in abstract class
        "BEST-PRACTICE-004": "low",  # global statement usage
        "BEST-PRACTICE-005": "medium",  # open() without context manager (resource leak)
        "ASSERT-002": "low",  # B011: assert False — raise AssertionError() instead
        "SECURITY-049": "high",  # path-traversal (user-controlled path = file read/write risk)
        "SECURITY-050": "medium",  # B023: function defined in loop uses closure variable (logic bug)
        "BEST-PRACTICE-006": "low",  # B009: getattr with constant attribute string
        "SECURITY-034": "low",  # import pickle (informational)
        "SECURITY-035": "low",  # import subprocess (informational)
        "IMPORT-003": "medium",  # Wildcard import — can cause name collisions
        # ── JavaScript/TypeScript rules (Round 5+) ──
        "SECURITY-051": "high",  # ReDoS — catastrophic regex backtracking
        "SECURITY-052": "high",  # Dynamic require() — path traversal risk
        "SECURITY-053": "medium",  # Timing attack — non-constant time comparison
        "SECURITY-054": "medium",  # Buffer() without bounds / deprecated new Buffer()
        "SECURITY-055": "high",  # CSRF before method-override missing
        "SECURITY-056": "high",  # Object injection via obj[user_input]
        "SECURITY-057": "high",  # Prototype pollution via Object.assign(obj, req.body)
        "SECURITY-058": "high",  # NoSQL injection (MongoDB query w/ user input)
        "SECURITY-059": "high",  # npm audit critical/high CVE
        "SECURITY-060": "medium",  # npm audit moderate CVE
        "STYLE-017": "low",  # var instead of let/const
        "STYLE-018": "low",  # prefer const over let
        "ASYNC-002": "medium",  # Promise executor returns value (logic bug)
        "ASYNC-003": "low",  # async function with no await
        "VAR-002": "medium",  # Undefined variable reference
        "PATTERN-002": "low",  # == instead of === (type coercion risk)
        "BEST-PRACTICE-007": "medium",  # with() statement
        "IMPORT-004": "medium",  # Circular import
        # ══════════════════════════════════════════════
        # CUSTOM-xxx: Semgrep custom rules
        # ══════════════════════════════════════════════
        "CUSTOM-hardcoded-password": "high",  # Semgrep: hardcoded passwords
        "CUSTOM-shell-injection": "high",  # Semgrep: shell injection
        "CUSTOM-sql-injection": "high",  # Semgrep: SQL injection
        "CUSTOM-dangerous-eval-usage": "high",  # Semgrep: eval/exec
        "CUSTOM-command-injection": "high",  # Semgrep: command injection
        "CUSTOM-unsafe-pickle": "medium",  # Semgrep: pickle deserialization
        "CUSTOM-bare-except": "medium",  # Semgrep: bare except
        "CUSTOM-open-without-context-manager": "low",  # Semgrep: open() without 'with'
        "CUSTOM-assert-for-validation": "low",  # Semgrep: assert for validation
        "CUSTOM-print-in-production": "low",  # Semgrep: print statements
        "CUSTOM-too-many-parameters": "low",  # Semgrep: too many params (informational)
        "CUSTOM-global-variable": "low",  # Semgrep: global variable usage
        # ── Round 3 deep scan additions ──
        "SECURITY-036": "medium",  # TLS certificate verification disabled
        "SECURITY-037": "low",  # Standard pseudo-random (not for crypto)
        "SECURITY-038": "medium",  # Unsafe XML parsing (SAX)
        "SECURITY-039": "medium",  # Unsafe XML parsing (lxml)
        "SECURITY-040": "medium",  # FTP cleartext protocol
        "SECURITY-041": "low",  # import ftplib (informational)
        # ── New mappings (previously CUSTOM-*) ──
        "SECURITY-042": "medium",  # urllib_urlopen — SSRF risk
        "SECURITY-043": "medium",  # Unsafe XML parsing (ElementTree/SAX/pulldom)
        "SECURITY-044": "medium",  # Unsafe XML parsing (lxml)
        # ── New rules from precision/recall overhaul ──
        "SECURITY-045": "high",  # XSS via render_template_string (CWE-79)
        "SECURITY-046": "high",  # SSRF via requests with user-controlled URL (CWE-918)
        "SECURITY-047": "critical",  # JWT none algorithm — signature bypass (CWE-347)
        "SECURITY-048": "medium",  # Open redirect via user-controlled URL (CWE-601)
    }

    # Context-based severity adjustments
    COMPLEXITY_THRESHOLDS = {
        "high": 20,  # CC > 20 = high severity
        "medium": 10,  # CC > 10 = medium severity
        "low": 0,  # CC <= 10 = low severity
    }

    def __init__(self):
        pass

    def score(self, canonical_rule_id: str, finding_dict: dict[str, Any]) -> str:
        """
        Determine severity for a finding

        Args:
            canonical_rule_id: Canonical rule ID (e.g., "SECURITY-001")
            finding_dict: Full finding dictionary with context

        Returns:
            Severity string: "high", "medium", or "low"
        """
        # Get base severity from rule mapping
        # Default: any unmapped SECURITY-xxx rule → medium (not low!)
        if canonical_rule_id in self.RULE_SEVERITY:
            base_severity = self.RULE_SEVERITY[canonical_rule_id]
        elif canonical_rule_id.startswith("SECURITY-"):
            base_severity = "medium"
        elif canonical_rule_id.startswith("CUSTOM-"):
            # Keyword-based inference for unmapped CUSTOM rules
            base_severity = self._infer_custom_severity(canonical_rule_id)
        else:
            base_severity = "low"

        # Apply context-based adjustments
        severity = self._apply_context_adjustments(base_severity, canonical_rule_id, finding_dict)

        return severity

    def _infer_custom_severity(self, rule_id: str) -> str:
        """Infer severity for unmapped CUSTOM- rules based on keywords in rule ID."""
        rule_lower = rule_id.lower()

        # HIGH: security-critical keywords
        high_keywords = ["injection", "password", "secret", "xss", "rce", "eval", "exec", "command"]
        if any(kw in rule_lower for kw in high_keywords):
            return "high"

        # MEDIUM: risky pattern keywords
        medium_keywords = ["pickle", "ssl", "crypto", "yaml", "except", "marshal", "deserialization"]
        if any(kw in rule_lower for kw in medium_keywords):
            return "medium"

        # LOW: everything else
        return "low"

    def _apply_context_adjustments(self, base_severity: str, canonical_rule_id: str, finding: dict[str, Any]) -> str:
        """Apply context-specific severity adjustments"""

        # COMPLEXITY-001: Adjust based on actual complexity value
        if canonical_rule_id == "COMPLEXITY-001":
            complexity = self._extract_complexity(finding)

            if complexity and complexity > self.COMPLEXITY_THRESHOLDS["high"]:
                return "high"
            elif complexity and complexity > self.COMPLEXITY_THRESHOLDS["medium"]:
                return "medium"
            else:
                return "low"

        # DEAD-001: Large unused functions are medium priority
        if canonical_rule_id == "DEAD-001":
            message = finding.get("message", "").lower()

            # Check if it's a large unused class or function
            if "class" in message:
                return "medium"  # Unused classes = medium
            elif "function" in message and len(finding.get("evidence", {}).get("snippet", "")) > 100:
                return "medium"  # Large unused functions = medium

        # DUP-001: Large duplications are higher priority
        if canonical_rule_id == "DUP-001":
            tokens = self._extract_duplication_size(finding)

            if tokens and tokens > 200:
                return "high"  # Massive duplication = high
            elif tokens and tokens > 100:
                return "medium"

        # Default: use base severity
        return base_severity

    def _extract_complexity(self, finding: dict[str, Any]) -> int:
        """Extract cyclomatic complexity from Radon output"""
        try:
            raw_output = finding.get("tool_raw", {}).get("original_output", {})
            return raw_output.get("complexity", 0)
        except Exception:
            # Fallback: parse from message
            message = finding.get("message", "")
            if "complexity of " in message:
                try:
                    # Extract "complexity of 15" → 15
                    parts = message.split("complexity of ")
                    if len(parts) > 1:
                        complexity_str = parts[1].split(".")[0].split()[0]
                        return int(complexity_str)
                except Exception:
                    pass
            return 0

    def _extract_duplication_size(self, finding: dict[str, Any]) -> int:
        """Extract token count from duplication finding"""
        try:
            raw_output = finding.get("tool_raw", {}).get("original_output", {})
            return raw_output.get("tokens", 0)
        except Exception:
            # Fallback: parse from message
            message = finding.get("message", "")
            if "tokens" in message:
                try:
                    # Extract "50 tokens" → 50
                    parts = message.split("tokens")
                    if len(parts) > 0:
                        token_str = parts[0].split()[-1]
                        return int(token_str)
                except Exception:
                    pass
            return 0

    def get_severity_priority(self, severity: str) -> int:
        """
        Get numeric priority for sorting (lower = higher priority)
        Used for ordering PR comments and dashboard views
        """
        priority_map = {"high": 1, "medium": 2, "low": 3}
        return priority_map.get(severity, 99)


# Convenience function for quick scoring
def score_severity(canonical_rule_id: str, finding_dict: dict[str, Any]) -> str:
    """Quick severity scoring without instantiating scorer"""
    scorer = SeverityScorer()
    return scorer.score(canonical_rule_id, finding_dict)


# Test the scorer
if __name__ == "__main__":
    print("Testing Severity Scorer...\n")

    scorer = SeverityScorer()

    # Test cases
    test_cases = [
        {
            "name": "High Complexity (CC=25)",
            "rule_id": "COMPLEXITY-001",
            "finding": {
                "message": "Function has cyclomatic complexity of 25",
                "tool_raw": {"original_output": {"complexity": 25}},
            },
            "expected": "high",
        },
        {
            "name": "Medium Complexity (CC=15)",
            "rule_id": "COMPLEXITY-001",
            "finding": {
                "message": "Function has cyclomatic complexity of 15",
                "tool_raw": {"original_output": {"complexity": 15}},
            },
            "expected": "medium",
        },
        {
            "name": "Security Issue",
            "rule_id": "SECURITY-001",
            "finding": {"message": "Dangerous eval() usage"},
            "expected": "high",
        },
        {
            "name": "Too Many Parameters",
            "rule_id": "SOLID-001",
            "finding": {"message": "Function has 8 parameters"},
            "expected": "medium",
        },
        {
            "name": "Unused Import",
            "rule_id": "IMPORT-001",
            "finding": {"message": "Unused import: os"},
            "expected": "low",
        },
        {
            "name": "Large Duplication",
            "rule_id": "DUP-001",
            "finding": {
                "message": "Duplicate code: 250 tokens",
                "tool_raw": {"original_output": {"tokens": 250}},
            },
            "expected": "high",
        },
    ]

    passed = 0
    failed = 0

    for test in test_cases:
        result = scorer.score(test["rule_id"], test["finding"])  # type: ignore[arg-type]
        status = "✓" if result == test["expected"] else "✗"

        if result == test["expected"]:
            passed += 1
        else:
            failed += 1

        print(f"{status} {test['name']}")
        print(f"   Rule: {test['rule_id']}")
        print(f"   Expected: {test['expected']}, Got: {result}")
        print()

    print(f"Results: {passed} passed, {failed} failed")
