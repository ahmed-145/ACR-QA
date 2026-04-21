"""
ACR-QA Feature 8 — Dependency Reachability Checker
Determines whether a vulnerable npm package is directly used in source code
or only present as a transitive (indirect) dependency.

Reachability levels:
    DIRECT      — package is explicitly require()'d or import'd in source → high risk
    TRANSITIVE  — package is installed but never directly imported → lower real risk
    UNUSED      — package is in package.json but not found anywhere → likely safe
    UNKNOWN     — could not determine (no package.json or source files found)

Confidence score adjustments:
    DIRECT      →  0 (no change — finding stands as-is)
    TRANSITIVE  → -15 (real vulnerability but harder to exploit directly)
    UNUSED      → -25 (very unlikely to be exploitable)
    UNKNOWN     →  -5 (insufficient data)
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from pathlib import Path

# Regex patterns for detecting package imports in JS/TS source
_REQUIRE_PATTERN = re.compile(
    r"""require\s*\(\s*['"]([^'"./][^'"]*)['"]\s*\)""",
    re.MULTILINE,
)
_IMPORT_PATTERN = re.compile(
    r"""(?:import\s+.*?\s+from\s+|import\s+)['"]([^'"./][^'"]*)['"]\s*""",
    re.MULTILINE,
)

_EXCLUDE_DIRS = {
    "node_modules",
    ".git",
    "dist",
    "build",
    "coverage",
    ".nyc_output",
    "tmp",
    ".venv",
    "__pycache__",
}

_SOURCE_EXTENSIONS = {".js", ".ts", ".jsx", ".tsx", ".mjs", ".cjs"}


@dataclass
class ReachabilityResult:
    package_name: str
    level: str  # DIRECT | TRANSITIVE | UNUSED | UNKNOWN
    confidence_penalty: int  # 0, -15, -25, or -5
    direct_imports: list[str] = field(default_factory=list)  # files that directly import it
    in_package_json: bool = False
    in_dev_dependencies: bool = False

    @property
    def is_reachable(self) -> bool:
        return self.level == "DIRECT"

    def to_dict(self) -> dict:
        return {
            "reachability_level": self.level,
            "reachability_penalty": self.confidence_penalty,
            "reachability_direct_imports": self.direct_imports,
            "reachability_in_package_json": self.in_package_json,
            "reachability_in_dev_deps": self.in_dev_dependencies,
            "reachability_is_direct": self.is_reachable,
        }


class DependencyReachabilityChecker:
    """
    Checks whether vulnerable npm packages are actually used in source code.
    Works on any JS/TS project directory — no external tools required.
    """

    def __init__(self, project_dir: str):
        self.project_dir = Path(project_dir)
        self._pkg_cache: dict | None = None
        self._imports_cache: dict[str, set[str]] | None = None

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def check(self, package_name: str) -> ReachabilityResult:
        """
        Check reachability for a single package name.
        Results are cached — safe to call in a loop.
        """
        pkg_data = self._load_package_json()
        direct_deps = set(pkg_data.get("dependencies", {}).keys())
        dev_deps = set(pkg_data.get("devDependencies", {}).keys())
        all_declared = direct_deps | dev_deps

        in_pkg = package_name in all_declared
        in_dev = package_name in dev_deps

        # Scan source for direct imports
        imports_map = self._scan_imports()
        files_importing = imports_map.get(package_name, set())

        if files_importing:
            level = "DIRECT"
            penalty = 0
        elif in_pkg:
            level = "TRANSITIVE"
            penalty = -15
        else:
            # Not in package.json and not imported — truly unknown/transitive
            level = "TRANSITIVE"
            penalty = -15

        if not in_pkg and not files_importing:
            level = "UNKNOWN"
            penalty = -5

        return ReachabilityResult(
            package_name=package_name,
            level=level,
            confidence_penalty=penalty,
            direct_imports=sorted(files_importing),
            in_package_json=in_pkg,
            in_dev_dependencies=in_dev,
        )

    def check_batch(self, package_names: list[str]) -> dict[str, ReachabilityResult]:
        """Check multiple packages at once. Returns dict mapping name → result."""
        return {name: self.check(name) for name in package_names}

    def enrich_findings(self, findings: list[dict]) -> list[dict]:
        """
        Add reachability metadata to a list of npm audit findings.
        Only processes findings from the 'npm-audit' tool.
        Modifies findings in place and returns the list.
        """
        if not findings:
            return findings

        # Extract package names from npm audit findings
        for finding in findings:
            tool = finding.get("tool", finding.get("tool_raw", {}).get("tool_name", ""))
            if not isinstance(tool, str):
                tool = ""

            # Only process npm-audit findings
            if "npm" not in tool.lower() and finding.get("canonical_rule_id") not in ("SECURITY-059", "SECURITY-060"):
                continue

            # Extract package name from message
            # Message format: "Vulnerable dependency: pkg-name (high) — ..."
            pkg_name = self._extract_package_name(finding.get("message", ""))
            if not pkg_name:
                continue

            result = self.check(pkg_name)
            finding.update(result.to_dict())

            # Adjust confidence score if present
            if "confidence_score" in finding and finding["confidence_score"] is not None:
                original = finding["confidence_score"]
                finding["confidence_score"] = max(0, original + result.confidence_penalty)
                finding["reachability_confidence_adjustment"] = result.confidence_penalty

        return findings

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _load_package_json(self) -> dict:
        if self._pkg_cache is not None:
            return self._pkg_cache
        pkg_path = self.project_dir / "package.json"
        if not pkg_path.exists():
            self._pkg_cache = {}
            return self._pkg_cache
        try:
            with open(pkg_path) as f:
                self._pkg_cache = json.load(f)
        except (json.JSONDecodeError, OSError):
            self._pkg_cache = {}
        return self._pkg_cache

    def _scan_imports(self) -> dict[str, set[str]]:
        """
        Scan all JS/TS source files and build a map of package → set of files importing it.
        Result is cached after first call.
        """
        if self._imports_cache is not None:
            return self._imports_cache

        imports_map: dict[str, set[str]] = {}

        for path in self._iter_source_files():
            try:
                text = path.read_text(encoding="utf-8", errors="replace")
            except OSError:
                continue

            rel_path = str(path.relative_to(self.project_dir))

            # Find all require('pkg') calls
            for match in _REQUIRE_PATTERN.finditer(text):
                pkg = self._normalise_pkg_name(match.group(1))
                imports_map.setdefault(pkg, set()).add(rel_path)

            # Find all import ... from 'pkg' statements
            for match in _IMPORT_PATTERN.finditer(text):
                pkg = self._normalise_pkg_name(match.group(1))
                imports_map.setdefault(pkg, set()).add(rel_path)

        self._imports_cache = imports_map
        return imports_map

    def _iter_source_files(self):
        for path in self.project_dir.rglob("*"):
            if not path.is_file():
                continue
            if path.suffix not in _SOURCE_EXTENSIONS:
                continue

            # Check exclusions relative to project_dir to avoid ignoring /tmp
            rel_parts = path.relative_to(self.project_dir).parts
            if any(excl in rel_parts for excl in _EXCLUDE_DIRS):
                continue

            yield path

    @staticmethod
    def _normalise_pkg_name(raw: str) -> str:
        """
        Normalise package name — strip subpath imports.
        e.g. 'lodash/merge' → 'lodash', '@org/pkg/utils' → '@org/pkg'
        """
        raw = raw.strip()
        if raw.startswith("@"):
            # Scoped package: @org/name[/subpath]
            parts = raw.split("/")
            return "/".join(parts[:2])
        return raw.split("/")[0]

    @staticmethod
    def _extract_package_name(message: str) -> str | None:
        """
        Extract package name from npm audit finding message.
        Format: "Vulnerable dependency: pkg-name (severity) — ..."
        """
        match = re.search(r"Vulnerable dependency:\s+([^\s(]+)", message)
        if match:
            return match.group(1).split("==")[0].strip()
        return None
