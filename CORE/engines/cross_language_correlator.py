"""
ACR-QA Feature 9 — Cross-Language Vulnerability Correlator
Inspired by: CHARON (CISPA/NDSS) — cross-language vulnerability detection.

Detects vulnerability chains that span Python backend code and
Jinja2/HTML templates or JS frontend files in the same project.

Correlation types detected:
    TEMPLATE_INJECTION  — Python route passes unsanitized data to template
    SQLI_TO_TEMPLATE    — SQL injection in DAO, result rendered in template
    XSS_CHAIN           — Python XSS finding + matching template renders same var
    ROUTE_JS_CHAIN      — Python route finding + JS file in same feature directory

Each correlation groups 2+ findings into a CorrelationGroup with a combined
severity and a chain description for the developer.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

# Template decorator patterns for Python web frameworks
_TEMPLATE_DECORATORS = re.compile(
    r"""@(?:template|render_template|aiohttp_jinja2\.template)\s*\(\s*['"]([^'"]+)['"]\s*\)""",
    re.MULTILINE,
)
_RENDER_TEMPLATE_CALLS = re.compile(
    r"""render_template\s*\(\s*['"]([^'"]+)['"]\s*""",
    re.MULTILINE,
)

# Jinja2 unsafe output: {{ var }} is escaped, {%- raw or |safe is XSS risk
_JINJA2_UNSAFE = re.compile(r"""\|\s*safe\b|Markup\s*\(|autoescape\s*=\s*False""")
_JINJA2_VAR = re.compile(r"""\{\{\s*(\w+)""")

# SQL injection patterns in Python DAO files
_SQLI_PATTERNS = re.compile(
    r"""(?:execute|query)\s*\(\s*(?:f['"]|['"][^'"]*%\s*[({]|['"][^'"]*\+)""",
    re.MULTILINE,
)
_SQLI_STRING_FORMAT = re.compile(
    r"""['"]\s*%\s*\{|%\s*\(\w+\)\s*s.*%\s*\{""",
    re.MULTILINE,
)


@dataclass
class CorrelationGroup:
    """A group of findings that form a cross-language vulnerability chain."""

    correlation_type: str  # TEMPLATE_INJECTION | SQLI_TO_TEMPLATE | XSS_CHAIN | ROUTE_JS_CHAIN
    chain_description: str  # Human-readable description of the chain
    python_findings: list[dict] = field(default_factory=list)
    template_findings: list[dict] = field(default_factory=list)
    js_findings: list[dict] = field(default_factory=list)
    template_file: str = ""  # Template file involved in the chain
    combined_severity: str = "medium"
    confidence_boost: int = 15  # Correlated findings get confidence boost

    @property
    def all_findings(self) -> list[dict]:
        return self.python_findings + self.template_findings + self.js_findings

    @property
    def finding_count(self) -> int:
        return len(self.all_findings)

    def to_dict(self) -> dict[str, Any]:
        return {
            "correlation_type": self.correlation_type,
            "chain_description": self.chain_description,
            "combined_severity": self.combined_severity,
            "confidence_boost": self.confidence_boost,
            "finding_count": self.finding_count,
            "template_file": self.template_file,
            "python_findings": len(self.python_findings),
            "template_findings": len(self.template_findings),
            "js_findings": len(self.js_findings),
        }


class CrossLanguageCorrelator:
    """
    Correlates findings across Python, Jinja2/HTML template, and JS files
    to detect multi-layer vulnerability chains.

    Supports: aiohttp + aiohttp_jinja2, Flask + Jinja2, Django templates.
    """

    SUPPORTED_TEMPLATE_EXTENSIONS = {".jinja2", ".j2", ".html", ".htm"}
    SECURITY_RULE_PREFIXES = ("SECURITY-", "HARDCODE-", "CUSTOM-", "CRYPTO-")

    def __init__(self, project_dir: str):
        self.project_dir = Path(project_dir)
        self._template_map: dict[str, Path] | None = None
        self._route_template_map: dict[str, list[str]] | None = None

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def correlate(self, findings: list[dict]) -> list[CorrelationGroup]:
        """
        Find cross-language correlation groups in a list of findings.
        Returns list of CorrelationGroup objects (may be empty).
        """
        if not findings:
            return []

        py_findings = [f for f in findings if self._is_python(f)]
        tmpl_findings = [f for f in findings if self._is_template(f)]
        js_findings = [f for f in findings if self._is_js(f)]

        groups: list[CorrelationGroup] = []

        # Correlation 1: SQL injection in DAO → template rendering user data
        groups.extend(self._correlate_sqli_to_template(py_findings, tmpl_findings))

        # Correlation 2: Python XSS finding + template with |safe filter
        groups.extend(self._correlate_xss_chain(py_findings, tmpl_findings))

        # Correlation 3: Python route security finding + JS in same feature dir
        groups.extend(self._correlate_route_js(py_findings, js_findings))

        # Correlation 4: Scan template files directly for unsafe patterns
        groups.extend(self._correlate_template_injection(py_findings))

        return groups

    def enrich_findings(self, findings: list[dict]) -> tuple[list[dict], list[CorrelationGroup]]:
        """
        Run correlation and add metadata to findings that are part of a chain.
        Returns (enriched_findings, correlation_groups).
        """
        groups = self.correlate(findings)

        # Tag each finding that belongs to a correlation group
        finding_ids_in_chain: dict[int, CorrelationGroup] = {}
        for group in groups:
            for f in group.all_findings:
                finding_ids_in_chain[id(f)] = group

        for f in findings:
            if id(f) in finding_ids_in_chain:
                group = finding_ids_in_chain[id(f)]
                f["cross_language_correlation"] = group.correlation_type
                f["correlation_chain"] = group.chain_description
                f["correlation_severity"] = group.combined_severity
                # Boost confidence for correlated findings
                if "confidence_score" in f and f["confidence_score"] is not None:
                    f["confidence_score"] = min(100, f["confidence_score"] + group.confidence_boost)

        return findings, groups

    def scan_project(self) -> list[CorrelationGroup]:
        """
        Scan the project directory directly for cross-language patterns
        without requiring pre-existing findings. Useful for standalone analysis.
        """
        synthetic_findings = self._build_synthetic_findings()
        return self.correlate(synthetic_findings)

    # ------------------------------------------------------------------
    # Correlation detectors
    # ------------------------------------------------------------------

    def _correlate_sqli_to_template(self, py_findings: list[dict], tmpl_findings: list[dict]) -> list[CorrelationGroup]:
        """Detect: SQL injection in DAO + route renders result in template."""
        groups = []
        sqli_findings = [
            f
            for f in py_findings
            if f.get("canonical_rule_id", "") in ("SECURITY-027", "SECURITY-061", "SECURITY-029", "SECURITY-030")
            or "sql" in f.get("message", "").lower()
        ]
        if not sqli_findings:
            return []

        route_template_map = self._build_route_template_map()

        for sqli_f in sqli_findings:
            file_path = sqli_f.get("file_path", sqli_f.get("file", ""))
            # Find templates rendered by routes in the same module
            related_templates = self._find_related_templates(file_path, route_template_map)

            if related_templates:
                groups.append(
                    CorrelationGroup(
                        correlation_type="SQLI_TO_TEMPLATE",
                        chain_description=(
                            f"SQL injection in {Path(file_path).name} — "
                            f"query result rendered in {', '.join(related_templates)}. "
                            f"Unsanitized DB data may reach template output."
                        ),
                        python_findings=[sqli_f],
                        template_file=related_templates[0],
                        combined_severity="high",
                        confidence_boost=20,
                    )
                )

        return groups

    def _correlate_xss_chain(self, py_findings: list[dict], tmpl_findings: list[dict]) -> list[CorrelationGroup]:
        """Detect: Python XSS finding + template using |safe or Markup()."""
        groups = []
        xss_findings = [
            f
            for f in py_findings
            if f.get("canonical_rule_id", "") in ("SECURITY-045", "SECURITY-031", "SECURITY-033")
            or "xss" in f.get("message", "").lower()
            or "render_template_string" in f.get("message", "").lower()
        ]

        # Scan templates for unsafe output patterns
        unsafe_templates = self._find_unsafe_templates()

        if xss_findings and unsafe_templates:
            for xss_f in xss_findings:
                groups.append(
                    CorrelationGroup(
                        correlation_type="XSS_CHAIN",
                        chain_description=(
                            "XSS risk in Python code + template uses |safe filter or Markup(). "
                            "User data may bypass HTML escaping."
                        ),
                        python_findings=[xss_f],
                        template_file=unsafe_templates[0] if unsafe_templates else "",
                        combined_severity="high",
                        confidence_boost=15,
                    )
                )

        return groups

    def _correlate_route_js(self, py_findings: list[dict], js_findings: list[dict]) -> list[CorrelationGroup]:
        """Detect: Python security finding + JS file in same feature directory."""
        groups = []
        security_py = [
            f
            for f in py_findings
            if any(f.get("canonical_rule_id", "").startswith(p) for p in self.SECURITY_RULE_PREFIXES)
        ]

        if not security_py or not js_findings:
            return []

        # Group by directory
        py_dirs = {Path(f.get("file_path", f.get("file", ""))).parent for f in security_py}
        js_dirs = {Path(f.get("file_path", f.get("file", ""))).parent for f in js_findings}

        shared_dirs = py_dirs & js_dirs
        for shared_dir in shared_dirs:
            py_in_dir = [f for f in security_py if Path(f.get("file_path", f.get("file", ""))).parent == shared_dir]
            js_in_dir = [f for f in js_findings if Path(f.get("file_path", f.get("file", ""))).parent == shared_dir]
            if py_in_dir and js_in_dir:
                groups.append(
                    CorrelationGroup(
                        correlation_type="ROUTE_JS_CHAIN",
                        chain_description=(
                            f"Security findings in both Python and JS code in {shared_dir.name}/. "
                            f"Review data flow between backend and frontend."
                        ),
                        python_findings=py_in_dir,
                        js_findings=js_in_dir,
                        combined_severity="high",
                        confidence_boost=10,
                    )
                )

        return groups

    def _correlate_template_injection(self, py_findings: list[dict]) -> list[CorrelationGroup]:
        """
        Scan template files directly for unsafe patterns even without
        pre-existing template findings.
        """
        groups = []
        unsafe_templates = self._find_unsafe_templates()

        security_py = [
            f
            for f in py_findings
            if any(f.get("canonical_rule_id", "").startswith(p) for p in self.SECURITY_RULE_PREFIXES)
        ]

        for tmpl in unsafe_templates:
            if security_py:
                groups.append(
                    CorrelationGroup(
                        correlation_type="TEMPLATE_INJECTION",
                        chain_description=(
                            f"Template {Path(tmpl).name} uses unsafe output (|safe or Markup). "
                            f"Combined with backend security findings, XSS risk is elevated."
                        ),
                        python_findings=security_py[:3],
                        template_file=tmpl,
                        combined_severity="high",
                        confidence_boost=15,
                    )
                )

        return groups

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _build_route_template_map(self) -> dict[str, list[str]]:
        """Build map of Python file → list of templates it renders."""
        if self._route_template_map is not None:
            return self._route_template_map

        route_map: dict[str, list[str]] = {}

        for py_file in self.project_dir.rglob("*.py"):
            if any(excl in py_file.parts for excl in ("__pycache__", ".venv", "venv")):
                continue
            try:
                text = py_file.read_text(encoding="utf-8", errors="replace")
            except OSError:
                continue

            templates: list[str] = []
            for m in _TEMPLATE_DECORATORS.finditer(text):
                templates.append(m.group(1))
            for m in _RENDER_TEMPLATE_CALLS.finditer(text):
                templates.append(m.group(1))

            if templates:
                route_map[str(py_file)] = templates

        self._route_template_map = route_map
        return route_map

    def _find_related_templates(self, file_path: str, route_template_map: dict[str, list[str]]) -> list[str]:
        """
        Find templates rendered by routes in the same project module.
        Looks at same dir, parent dir, and sibling dirs to handle
        DAO/view separation (e.g. dao/student.py + views.py both in sqli/).
        """
        file_path_obj = Path(file_path)
        file_dir = file_path_obj.parent
        # Check same dir + parent + grandparent
        search_dirs = {file_dir, file_dir.parent, file_dir.parent.parent}
        related: list[str] = []

        for py_file, templates in route_template_map.items():
            py_dir = Path(py_file).parent
            # Match if route file is in the same module tree
            if py_dir in search_dirs or file_dir in {py_dir, py_dir.parent}:
                related.extend(templates)

        return list(set(related))

    def _find_unsafe_templates(self) -> list[str]:
        """
        Find template files that use unsafe output patterns (|safe, Markup())
        OR Python files that disable autoescaping (autoescape=False).
        """
        unsafe: list[str] = []

        # Check template files for |safe and Markup()
        for ext in self.SUPPORTED_TEMPLATE_EXTENSIONS:
            for tmpl_file in self.project_dir.rglob(f"*{ext}"):
                if any(excl in tmpl_file.parts for excl in ("__pycache__", ".venv", "node_modules")):
                    continue
                try:
                    text = tmpl_file.read_text(encoding="utf-8", errors="replace")
                    if _JINJA2_UNSAFE.search(text):
                        unsafe.append(str(tmpl_file))
                except OSError:
                    continue

        # Also check Python files for autoescape=False (global XSS risk)
        for py_file in self.project_dir.rglob("*.py"):
            if any(excl in py_file.parts for excl in ("__pycache__", ".venv", "venv")):
                continue
            try:
                text = py_file.read_text(encoding="utf-8", errors="replace")
                if re.search(r"autoescape\s*=\s*False", text):
                    # Use the Python file path as the "unsafe template" indicator
                    unsafe.append(str(py_file))
            except OSError:
                continue

        return list(set(unsafe))

    def _build_synthetic_findings(self) -> list[dict]:
        """
        Build synthetic findings by scanning Python files for known
        vulnerability patterns. Used by scan_project().
        """
        findings: list[dict] = []

        for py_file in self.project_dir.rglob("*.py"):
            if any(excl in py_file.parts for excl in ("__pycache__", ".venv", "venv", "test")):
                continue
            try:
                text = py_file.read_text(encoding="utf-8", errors="replace")
            except OSError:
                continue

            # Detect SQL injection via string formatting
            for m in _SQLI_STRING_FORMAT.finditer(text):
                line_no = text[: m.start()].count("\n") + 1
                findings.append(
                    {
                        "canonical_rule_id": "SECURITY-027",
                        "canonical_severity": "high",
                        "category": "security",
                        "file": str(py_file),
                        "line_number": line_no,
                        "line": line_no,
                        "message": "SQL injection via string formatting",
                        "tool": "cross-language-correlator",
                        "language": "python",
                    }
                )

        return findings

    @staticmethod
    def _is_python(finding: dict) -> bool:
        lang = finding.get("language", "")
        file_path = finding.get("file_path", finding.get("file", ""))
        return lang == "python" or file_path.endswith(".py")

    @staticmethod
    def _is_template(finding: dict) -> bool:
        file_path = finding.get("file_path", finding.get("file", ""))
        return any(file_path.endswith(ext) for ext in (".jinja2", ".j2", ".html", ".htm"))

    @staticmethod
    def _is_js(finding: dict) -> bool:
        lang = finding.get("language", "")
        file_path = finding.get("file_path", finding.get("file", ""))
        return lang in ("javascript", "typescript") or any(
            file_path.endswith(ext) for ext in (".js", ".ts", ".jsx", ".tsx")
        )
