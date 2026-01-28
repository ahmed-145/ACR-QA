"""
Universal Finding Normalizer for ACR-QA v2.0
Converts tool-specific outputs to canonical schema
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))


import uuid
import json
from typing import Dict, Any, List, Optional
from pathlib import Path
from pydantic import BaseModel, ConfigDict, Field, field_validator

# Universal Rule Mapping: Tool-specific → Canonical
RULE_MAPPING = {
    # Ruff rules → Universal IDs
    "F401": "IMPORT-001",  # Unused import
    "F841": "VAR-001",  # Unused variable
    "PLR0913": "SOLID-001",  # Too many parameters
    "B006": "PATTERN-001",  # Mutable default argument
    "E501": "STYLE-001",  # Line too long
    "D100": "STYLE-002",  # Missing docstring (module)
    "D101": "STYLE-002",  # Missing docstring (class)
    "D102": "STYLE-002",  # Missing docstring (method)
    "D103": "STYLE-002",  # Missing docstring (function)
    "N801": "NAMING-001",  # Bad class name
    "N802": "NAMING-001",  # Bad function name
    "N803": "NAMING-001",  # Bad argument name
    "N806": "NAMING-001",  # Bad variable name
    # Semgrep rules → Universal IDs
    "dangerous-eval-usage": "SECURITY-001",
    "mutable-default-argument": "PATTERN-001",
    # Vulture → Universal IDs
    "unused-code": "DEAD-001",
    "unused-import": "IMPORT-001",
    "unused-variable": "VAR-001",
    "unused-function": "DEAD-001",
    "unused-class": "DEAD-001",
    # jscpd → Universal IDs
    # Radon → Universal IDs
    "high-complexity": "COMPLEXITY-001",
    "code-duplication": "DUP-001",
    # Bandit security rules → Universal IDs
    "B101": "SECURITY-002",  # assert used
    "B102": "SECURITY-001",  # exec used
    "B103": "SECURITY-003",  # set_bad_file_permissions
    "B104": "SECURITY-004",  # hardcoded_bind_all_interfaces
    "B105": "SECURITY-005",  # hardcoded_password_string
    "B106": "SECURITY-005",  # hardcoded_password_funcarg
    "B107": "SECURITY-005",  # hardcoded_password_default
    # Ruff additional rules
    "E722": "EXCEPT-001",  # Bare except
    "B001": "EXCEPT-001",  # Bare except (flake8-bugbear)
    "ASYNC100": "ASYNC-001",  # Async function no await
    "ASYNC101": "ASYNC-001",  # Async function open call
    "ANN001": "TYPE-001",  # Missing type annotation for argument
    "ANN002": "TYPE-001",  # Missing type annotation for *args
    "ANN003": "TYPE-001",  # Missing type annotation for **kwargs
    "ANN201": "TYPE-001",  # Missing return type annotation
    "S105": "HARDCODE-001",  # Hardcoded password (flake8-bandit)
    "B108": "SECURITY-006",  # hardcoded_tmp_directory
    "B110": "SECURITY-007",  # try_except_pass
    "B112": "SECURITY-007",  # try_except_continue
    "B301": "SECURITY-008",  # pickle usage
    "B302": "SECURITY-008",  # marshal usage
    "B303": "SECURITY-009",  # md5 usage (weak hash)
    "B304": "SECURITY-010",  # des usage (weak cipher)
    "B305": "SECURITY-010",  # cipher usage
    "B306": "SECURITY-011",  # mktemp usage
    "B307": "SECURITY-001",  # eval usage
    "B308": "SECURITY-012",  # mark_safe usage
    "B324": "SECURITY-009",  # hashlib weak hash
    "B501": "SECURITY-013",  # request_with_no_cert_validation
    "B502": "SECURITY-014",  # ssl_with_bad_version
    "B503": "SECURITY-015",  # ssl_with_bad_defaults
    "B504": "SECURITY-016",  # ssl_with_no_version
    "B505": "SECURITY-017",  # weak_cryptographic_key
    "B506": "SECURITY-018",  # yaml_load
    "B507": "SECURITY-019",  # ssh_no_host_key_verification
    "B601": "SECURITY-020",  # paramiko_calls
    "B602": "SECURITY-021",  # subprocess_popen_with_shell
    "B603": "SECURITY-022",  # subprocess_without_shell
    "B604": "SECURITY-023",  # any_other_function_with_shell
    "B605": "SECURITY-024",  # start_process_with_a_shell
    "B606": "SECURITY-025",  # start_process_with_no_shell
    "B607": "SECURITY-026",  # start_process_with_partial_path
    "B608": "SECURITY-027",  # hardcoded_sql_expressions
    "B609": "SECURITY-028",  # linux_commands_wildcard_injection
    "B610": "SECURITY-029",  # django_extra_used
    "B611": "SECURITY-030",  # django_rawsql_used
    "B701": "SECURITY-031",  # jinja2_autoescape_false
    "B702": "SECURITY-032",  # use_of_mako_templates
    "B703": "SECURITY-033",  # django_mark_safe
}

# Severity Mapping: Tool-specific → Canonical (high/medium/low)
SEVERITY_MAPPING = {
    "error": "high",
    "warning": "medium",
    "info": "low",
    # Semgrep
    "ERROR": "high",
    "WARNING": "medium",
    "INFO": "low",
}

# Category Mapping
CATEGORY_MAPPING = {
    "security": "security",
    "best-practice": "best-practice",
    "style-or-practice": "style",
    "style": "style",
    "dead-code": "dead-code",
    "duplication": "duplication",
    "design": "design",
}


class CanonicalFinding(BaseModel):
    """Universal finding format following ACR-QA canonical schema with Pydantic validation"""

    # Core fields
    finding_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    canonical_rule_id: str
    original_rule_id: str
    severity: str
    category: str
    file: str
    line: int
    column: int = 0
    language: str
    message: str

    # Evidence
    evidence: Dict[str, Any] = Field(
        default_factory=lambda: {
            "snippet": "",
            "context_before": [],
            "context_after": [],
        }
    )

    # Tool metadata
    tool_raw: Dict[str, Any]

    # Original severity for audit trail
    original_severity: str = ""

    # Pydantic v2 configuration (replaces deprecated class Config)
    model_config = ConfigDict(arbitrary_types_allowed=True)

    @field_validator("severity")
    @classmethod
    def validate_severity(cls, v: str) -> str:
        """Validate severity is one of: high, medium, low"""
        valid_severities = {"high", "medium", "low"}
        v_lower = v.lower()
        if v_lower not in valid_severities:
            raise ValueError(
                f"Invalid severity '{v}'. Must be one of: {', '.join(valid_severities)}"
            )
        return v_lower

    @field_validator("category")
    @classmethod
    def validate_category(cls, v: str) -> str:
        """Validate category is one of the known categories"""
        valid_categories = {
            "security",
            "best-practice",
            "style",
            "dead-code",
            "duplication",
            "design",
        }
        if v not in valid_categories:
            # Log warning but allow custom categories
            print(
                f"Warning: Unknown category '{v}'. Valid categories: {', '.join(valid_categories)}"
            )
        return v

    @classmethod
    def create(
        cls,
        rule_id: str,
        file: str,
        line: int,
        severity: str,
        category: str,
        message: str,
        tool_name: str,
        tool_output: Dict[str, Any],
        column: int = 0,
    ) -> "CanonicalFinding":
        """
        Factory method to create a CanonicalFinding with intelligent severity scoring.

        This method:
        1. Maps tool-specific rule IDs to canonical IDs
        2. Detects language from file extension
        3. Applies intelligent severity scoring
        4. Returns validated Pydantic model
        """
        # Map to canonical rule ID
        canonical_rule_id = RULE_MAPPING.get(rule_id, f"CUSTOM-{rule_id}")

        # Map to canonical category
        canonical_category = CATEGORY_MAPPING.get(category, category)

        # Detect language
        ext = Path(file).suffix.lower()
        language_map = {
            ".py": "python",
            ".js": "javascript",
            ".ts": "typescript",
            ".java": "java",
            ".cpp": "cpp",
            ".c": "c",
            ".go": "go",
            ".rs": "rust",
            ".rb": "ruby",
            ".php": "php",
            ".sh": "shell",
        }
        language = language_map.get(ext, "unknown")

        # Build tool metadata
        tool_raw = {
            "tool_name": tool_name,
            "original_rule_id": rule_id,
            "original_severity": severity,
            "original_output": tool_output,
        }

        # Apply intelligent severity scoring
        from CORE.engines.severity_scorer import SeverityScorer

        scorer = SeverityScorer()

        # Build finding dict for scoring
        finding_dict = {
            "canonical_rule_id": canonical_rule_id,
            "message": message,
            "category": canonical_category,
            "tool_raw": tool_raw,
        }

        # Score severity intelligently
        scored_severity = scorer.score(canonical_rule_id, finding_dict)

        # Create and validate the Pydantic model
        try:
            finding = cls(
                canonical_rule_id=canonical_rule_id,
                original_rule_id=rule_id,
                severity=scored_severity,
                original_severity=severity,
                category=canonical_category,
                file=file,
                line=line,
                column=column,
                language=language,
                message=message,
                tool_raw=tool_raw,
            )
            return finding
        except Exception as e:
            # Log validation error but don't crash
            print(f"ERROR: Pydantic validation failed for finding: {e}")
            print(f"  Rule: {canonical_rule_id}, File: {file}:{line}")
            raise

    def extract_evidence(self, context_lines: int = 3) -> None:
        """Extract code snippet and context"""
        try:
            from CORE.utils.code_extractor import extract_code_snippet

            # Get snippet with context
            full_snippet = extract_code_snippet(self.file, self.line, context_lines)

            # Parse snippet into parts
            lines = full_snippet.split("\n")

            context_before = []
            context_after = []
            snippet = ""

            for line in lines:
                if ">>>" in line:
                    # This is the issue line
                    snippet = line.split("|", 1)[1].strip() if "|" in line else line
                elif "|" in line:
                    line_num_str, code = line.split("|", 1)
                    line_num = int(line_num_str.strip())

                    if line_num < self.line:
                        context_before.append(code.rstrip())
                    elif line_num > self.line:
                        context_after.append(code.rstrip())

            self.evidence = {
                "snippet": snippet,
                "context_before": context_before[-3:]
                if context_before
                else [],  # Last 3
                "context_after": context_after[:3] if context_after else [],  # First 3
            }

        except Exception as e:
            # Fallback: just use the message
            self.evidence = {
                "snippet": f"# Line {self.line}",
                "context_before": [],
                "context_after": [],
            }

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization (uses Pydantic's model_dump)"""
        return self.model_dump()


def normalize_ruff(ruff_json: List[Dict]) -> List[CanonicalFinding]:
    """Convert Ruff findings to canonical format"""
    findings = []

    for item in ruff_json:
        finding = CanonicalFinding.create(
            rule_id=item.get("code", "UNKNOWN"),
            file=item.get("filename", "unknown"),
            line=item.get("location", {}).get("row", 0),
            column=item.get("location", {}).get("column", 0),
            severity="warning",  # Ruff doesn't specify severity
            category="style",
            message=item.get("message", ""),
            tool_name="ruff",
            tool_output=item,
        )
        finding.extract_evidence()
        findings.append(finding)

    return findings


def normalize_semgrep(semgrep_json: Dict) -> List[CanonicalFinding]:
    """Convert Semgrep findings to canonical format"""
    findings = []

    results = semgrep_json.get("results", [])

    for item in results:
        # Extract rule ID from check_id (e.g., "services.semgrep.dangerous-eval-usage")
        check_id = item.get("check_id", "")
        rule_id = check_id.split(".")[-1] if "." in check_id else check_id

        finding = CanonicalFinding.create(
            rule_id=rule_id,
            file=item.get("path", "unknown"),
            line=item.get("start", {}).get("line", 0),
            column=item.get("start", {}).get("col", 0),
            severity=item.get("extra", {}).get("severity", "WARNING"),
            category=item.get("extra", {})
            .get("metadata", {})
            .get("category", "security"),
            message=item.get("extra", {}).get("message", ""),
            tool_name="semgrep",
            tool_output=item,
        )
        finding.extract_evidence()
        findings.append(finding)

    return findings


def normalize_vulture(vulture_txt: str) -> List[CanonicalFinding]:
    """Convert Vulture text output to canonical format"""
    findings = []

    for line in vulture_txt.strip().split("\n"):
        if not line or line.startswith("#"):
            continue

        # Format: filepath:line: message (confidence%)
        parts = line.split(":", 2)
        if len(parts) < 3:
            continue

        filepath = parts[0].strip()
        try:
            lineno = int(parts[1].strip())
        except ValueError:
            lineno = 0

        message = parts[2].strip()

        # Determine rule type from message
        rule_id = "unused-code"
        if "import" in message.lower():
            rule_id = "unused-import"
        elif "variable" in message.lower():
            rule_id = "unused-variable"
        elif "function" in message.lower():
            rule_id = "unused-function"
        elif "class" in message.lower():
            rule_id = "unused-class"

        finding = CanonicalFinding.create(
            rule_id=rule_id,
            file=filepath,
            line=lineno,
            column=0,
            severity="info",
            category="dead-code",
            message=message,
            tool_name="vulture",
            tool_output={"raw_line": line},
        )
        finding.extract_evidence()
        findings.append(finding)

    return findings


def normalize_jscpd(jscpd_json: Dict) -> List[CanonicalFinding]:
    """Convert jscpd findings to canonical format"""
    findings = []

    duplicates = jscpd_json.get("duplicates", [])

    for dup in duplicates:
        first_file = dup.get("firstFile", {})
        second_file = dup.get("secondFile", {})

        message = (
            f"Duplicate code block: {dup.get('lines', 0)} lines, "
            f"{dup.get('tokens', 0)} tokens. "
            f"Also found in {second_file.get('name', 'unknown')} "
            f"at line {second_file.get('start', 0)}"
        )

        finding = CanonicalFinding.create(
            rule_id="code-duplication",
            file=first_file.get("name", "unknown"),
            line=first_file.get("start", 0),
            column=0,
            severity="info",
            category="duplication",
            message=message,
            tool_name="jscpd",
            tool_output=dup,
        )
        finding.extract_evidence()
        findings.append(finding)

    return findings


def normalize_radon(radon_json: Dict) -> List[CanonicalFinding]:
    """Convert Radon complexity findings to canonical format"""
    findings = []

    # Radon output format: {filename: [function_data]}
    for filepath, functions in radon_json.items():
        if not isinstance(functions, list):
            continue

        for func in functions:
            # Only flag high complexity (> 10)
            complexity = func.get("complexity", 0)

            if complexity > 10:
                # Determine severity based on complexity
                if complexity > 20:
                    severity = "high"
                elif complexity > 15:
                    severity = "medium"
                else:
                    severity = "low"

                message = (
                    f"Function '{func.get('name', 'unknown')}' has cyclomatic complexity of {complexity}. "
                    f"High complexity makes code hard to test and maintain. "
                    f"Consider refactoring into smaller functions."
                )

                finding = CanonicalFinding.create(
                    rule_id="high-complexity",
                    file=filepath,
                    line=func.get("lineno", 0),
                    column=func.get("col_offset", 0),
                    severity=severity,
                    category="design",
                    message=message,
                    tool_name="radon",
                    tool_output=func,
                )
                finding.extract_evidence()
                findings.append(finding)

    return findings


def normalize_all(outputs_dir: str = "outputs") -> List[CanonicalFinding]:
    """
    Load and normalize all tool outputs from directory

    Args:
        outputs_dir: Directory containing tool output files

    Returns:
        List of CanonicalFinding objects
    """
    all_findings = []
    outputs_path = Path(outputs_dir)

    # Load and normalize Ruff
    ruff_file = outputs_path / "ruff.json"
    if ruff_file.exists():
        try:
            with open(ruff_file) as f:
                content = f.read().strip()
                if content:  # Only parse if not empty
                    ruff_data = json.loads(content)
                    all_findings.extend(normalize_ruff(ruff_data))
                    print(
                        f"  Normalized {len(normalize_ruff(ruff_data))} Ruff findings"
                    )
        except json.JSONDecodeError:
            print(f"  Warning: Could not parse {ruff_file}")
        except Exception as e:
            print(f"  Error processing Ruff: {e}")

    # Load and normalize Semgrep
    semgrep_file = outputs_path / "semgrep.json"
    if semgrep_file.exists():
        try:
            with open(semgrep_file) as f:
                semgrep_data = json.load(f)
                semgrep_findings = normalize_semgrep(semgrep_data)
                all_findings.extend(semgrep_findings)
                print(f"  Normalized {len(semgrep_findings)} Semgrep findings")
        except Exception as e:
            print(f"  Error processing Semgrep: {e}")

    # Load and normalize Vulture
    vulture_file = outputs_path / "vulture.txt"
    if vulture_file.exists():
        try:
            with open(vulture_file) as f:
                vulture_data = f.read()
                vulture_findings = normalize_vulture(vulture_data)
                all_findings.extend(vulture_findings)
                print(f"  Normalized {len(vulture_findings)} Vulture findings")
        except Exception as e:
            print(f"  Error processing Vulture: {e}")

    # Load and normalize jscpd
    jscpd_file = outputs_path / "jscpd.json"
    if jscpd_file.exists():
        try:
            with open(jscpd_file) as f:
                jscpd_data = json.load(f)
                jscpd_findings = normalize_jscpd(jscpd_data)
                all_findings.extend(jscpd_findings)
                print(f"  Normalized {len(jscpd_findings)} jscpd findings")
        except Exception as e:
            print(f"  Error processing jscpd: {e}")

    # Load and normalize Radon
    radon_file = outputs_path / "radon.json"
    if radon_file.exists():
        try:
            with open(radon_file) as f:
                radon_data = json.load(f)
                radon_findings = normalize_radon(radon_data)
                all_findings.extend(radon_findings)
                print(f"  Normalized {len(radon_findings)} Radon findings")
        except Exception as e:
            print(f"  Error processing Radon: {e}")

    # Load and normalize Bandit
    bandit_file = outputs_path / "bandit.json"
    if bandit_file.exists():
        try:
            with open(bandit_file) as f:
                bandit_data = json.load(f)
                bandit_findings = normalize_bandit(bandit_data)
                all_findings.extend(bandit_findings)
                print(f"  Normalized {len(bandit_findings)} Bandit findings")
        except Exception as e:
            print(f"  Error processing Bandit: {e}")

    print(f"\n  Total canonical findings: {len(all_findings)}")
    return all_findings


def normalize_bandit(bandit_json: Dict) -> List[CanonicalFinding]:
    """Convert Bandit security findings to canonical format"""
    findings = []

    # Bandit severity mapping
    BANDIT_SEVERITY = {"HIGH": "high", "MEDIUM": "medium", "LOW": "low"}

    results = bandit_json.get("results", [])

    for item in results:
        # Extract test ID (e.g., B101, B608)
        test_id = item.get("test_id", "UNKNOWN")

        finding = CanonicalFinding.create(
            rule_id=test_id,
            file=item.get("filename", "unknown"),
            line=item.get("line_number", 0),
            column=item.get("col_offset", 0),
            severity=BANDIT_SEVERITY.get(item.get("issue_severity", "LOW"), "low"),
            category="security",
            message=f"{item.get('issue_text', '')} (Confidence: {item.get('issue_confidence', 'UNKNOWN')})",
            tool_name="bandit",
            tool_output=item,
        )
        finding.extract_evidence()
        findings.append(finding)

    return findings


if __name__ == "__main__":
    # Test normalization
    print("Testing normalizer...")
    findings = normalize_all()

    if findings:
        print(f"\nSample canonical finding:")
        print(json.dumps(findings[0].to_dict(), indent=2))
