#!/usr/bin/env python3
"""
ACR-QA JavaScript/TypeScript Language Adapter (v3.0).

Orchestrates JS/TS-specific analysis tools:
  - ESLint       : Style, best practices, security (eslint-plugin-security)
  - Semgrep      : Security patterns, OWASP, custom JS rules
  - npm audit    : Dependency vulnerability scan (SCA)
  - jscpd        : Code duplication detection (same as Python adapter)

Usage:
    adapter = JavaScriptAdapter(target_dir="/path/to/js-project")
    results = adapter.run_tools()
    findings = adapter.normalize_eslint(results["eslint"])
"""

import json
import logging
import os
import shutil
import subprocess
from pathlib import Path
from typing import Any

from CORE.adapters.base import LanguageAdapter
from CORE.engines.normalizer import CanonicalFinding

logger = logging.getLogger(__name__)

# ──────────────────────────────────────────────────────────────────────────────
# ESLint rule → canonical rule ID mapping
# Used by normalizer.py (merged at runtime via JS_RULE_MAPPING)
# ──────────────────────────────────────────────────────────────────────────────
JS_RULE_MAPPING: dict[str, str] = {
    # ── Security (eslint-plugin-security) ────────────────────────────────────
    "security/detect-eval-with-expression": "SECURITY-001",  # eval() with variable
    "security/detect-non-literal-regexp": "SECURITY-051",  # RegExp from user input (ReDoS)
    "security/detect-non-literal-require": "SECURITY-052",  # require() with variable (path traversal)
    "security/detect-possible-timing-attacks": "SECURITY-053",  # Timing-safe comparison omitted
    "security/detect-unsafe-regex": "SECURITY-051",  # Catastrophic backtracking regex
    "security/detect-buffer-noassert": "SECURITY-054",  # Buffer() without bounds check
    "security/detect-child-process": "SECURITY-021",  # child_process (command injection risk)
    "security/detect-disable-mustache-escape": "SECURITY-045",  # XSS via mustache disable
    "security/detect-new-buffer": "SECURITY-054",  # new Buffer() deprecated (use Buffer.from)
    "security/detect-no-csrf-before-method-override": "SECURITY-055",  # CSRF risk
    "security/detect-object-injection": "SECURITY-056",  # obj[user_input] injection
    "security/detect-pseudoRandomBytes": "SECURITY-037",  # Weak random (crypto.pseudoRandomBytes)
    # ── ESLint core: bugs & errors ────────────────────────────────────────────
    "no-eval": "SECURITY-001",  # eval() — same as SECURITY-001
    "no-implied-eval": "SECURITY-001",  # setTimeout("code") implicit eval
    "no-new-func": "SECURITY-001",  # new Function() — dynamic code exec
    "no-unused-vars": "VAR-001",  # Unused variable
    "no-undef": "VAR-002",  # Undefined variable reference
    "no-debugger": "DEAD-001",  # debugger statement left in code
    "no-console": "STYLE-007",  # console.log in production
    "no-var": "STYLE-017",  # Use let/const instead of var
    "prefer-const": "STYLE-018",  # Use const when not reassigned
    "eqeqeq": "PATTERN-002",  # Use === instead of ==
    "no-with": "BEST-PRACTICE-007",  # with() statement
    # ── ESLint: async / promises ─────────────────────────────────────────────
    "no-async-promise-executor": "ASYNC-001",
    "no-promise-executor-return": "ASYNC-002",
    "require-await": "ASYNC-003",  # async function with no await
    # ── ESLint: imports ───────────────────────────────────────────────────────
    "import/no-cycle": "IMPORT-004",  # Circular import
    "import/no-duplicates": "DUP-001",  # Duplicate imports
    # ── Semgrep JS rules (custom, defined in js-rules.yml) ───────────────────
    "js-eval-injection": "SECURITY-001",
    "express-cookie-session-no-secure": "SECURITY-060",
    "express-cookie-session-no-httponly": "SECURITY-060",
    # ── Hardcoded Secrets ──
    "express-session-hardcoded-secret": "HARDCODE-001",
    # ── Custom / Manually mapped (from v3) ──"SECURITY-045",
    "js-prototype-pollution": "SECURITY-057",
    "js-xss-innerhtml": "SECURITY-045",
    "js-xss-document-write": "SECURITY-045",
    "js-open-redirect": "SECURITY-048",
    "js-hardcoded-secret": "SECURITY-005",
    "js-sql-injection": "SECURITY-027",
    "js-nosql-injection": "SECURITY-058",
    "js-nosql-injection-mongodb": "SECURITY-058",
    "js-nosql-where-injection": "SECURITY-058",
    "js-ssrf-request": "SECURITY-065",
    "js-path-traversal": "SECURITY-049",
    "js-command-injection": "SECURITY-021",
    "js-insecure-random": "SECURITY-037",
    "js-jwt-none-algorithm": "SECURITY-047",
    "js-global-variable": "BEST-PRACTICE-004",
    "js-console-log": "STYLE-007",
    "js-unused-variable": "VAR-001",
    "js-complexity": "COMPLEXITY-001",
    # ── npm audit severity → canonical ────────────────────────────────────────
    "npm-audit-critical": "SECURITY-059",  # npm CVE critical
    "npm-audit-high": "SECURITY-059",  # npm CVE high
    "npm-audit-moderate": "SECURITY-060",  # npm CVE moderate
    # ── Taint analysis rules (js-taint-rules.yml) ─────────────────────────────
    "js-taint-sql-injection": "SECURITY-061",  # req.* → sequelize.query/db.query (SQLi)
    "js-taint-command-injection": "SECURITY-062",  # req.* → exec/spawn (cmd injection)
    "js-taint-eval-injection": "SECURITY-001",  # req.* → eval/Function (RCE)
    # ── XXE rules (js-xxe.yml) ────────────────────────────────────────────────
    "js-xxe-libxmljs-noent": "SECURITY-063",  # libxmljs with noent:true
    "js-xxe-libxmljs-variable": "SECURITY-063",  # libxmljs noent via variable
    "js-xxe-libxmljs": "SECURITY-063",  # libxmljs in js-rules.yml (pattern form)
    # ── EJS template XSS rules (js-ejs-xss.yml) ──────────────────────────────
    "js-ejs-unescaped-output": "SECURITY-064",  # <%- unescaped EJS output
    "js-ejs-innerHTML-template": "SECURITY-045",  # innerHTML in EJS template
    # ── Pattern-based SQLi / XXE rules (js-rules.yml) ─────────────────────────
    "js-sequelize-raw-query": "SECURITY-061",  # db.sequelize.query(var) — SQLi
}


class JavaScriptAdapter(LanguageAdapter):
    """
    JavaScript/TypeScript language adapter for ACR-QA.

    Runs ESLint, Semgrep (JS rules), and npm audit on a JS/TS project.
    Normalizes findings into the same CanonicalFinding format as the Python adapter.

    Tools required (auto-installed if missing via npx):
        - eslint + eslint-plugin-security
        - semgrep (system-installed)
        - jscpd (optional)

    npm audit runs automatically if package.json is found.
    """

    @property
    def language_name(self) -> str:
        """Return language name."""
        return "JavaScript/TypeScript"

    @property
    def file_extensions(self) -> list[str]:
        """Return supported file extensions."""
        return [".js", ".jsx", ".ts", ".tsx", ".mjs", ".cjs", ".ejs"]

    def get_tools(self) -> list[dict[str, Any]]:
        """Return list of tools used by this adapter."""
        return [
            {
                "name": "eslint",
                "purpose": "Style, best practices, security (eslint-plugin-security)",
                "check": "eslint",
                "requires_npm": True,
            },
            {
                "name": "semgrep",
                "purpose": "OWASP security patterns, custom JS rules",
                "check": "semgrep",
                "requires_npm": False,
            },
            {
                "name": "npm-audit",
                "purpose": "Dependency vulnerability scan (SCA)",
                "check": "npm",
                "requires_npm": False,
            },
            {
                "name": "jscpd",
                "purpose": "Code duplication detection",
                "check": "jscpd",
                "requires_npm": True,
            },
        ]

    def check_tools_available(self) -> dict[str, bool]:
        """Check which tools are installed."""
        return {
            "eslint": shutil.which("eslint") is not None,
            "semgrep": shutil.which("semgrep") is not None,
            "npm": shutil.which("npm") is not None,
            "npx": shutil.which("npx") is not None,
            "jscpd": shutil.which("jscpd") is not None,
        }

    def _get_js_files(self) -> list[Path]:
        """Return all JS/TS files in target_dir."""
        files: list[Path] = []
        for ext in self.file_extensions:
            files.extend(self.target_dir.rglob(f"*{ext}"))
        # Exclude node_modules, dist, build, vendor etc
        exclude = {
            "node_modules",
            "dist",
            "build",
            ".next",
            ".nuxt",
            "coverage",
            "__pycache__",
            "vendor",
            "bower_components",
            "min",
            "minified",
        }

        filtered_files: list[Path] = []
        for f in files:
            # Skip if file path contains excluded folder parts
            if any(part in exclude for part in f.parts):
                continue
            # Skip minified files
            if f.stem.endswith(".min"):
                continue

            filtered_files.append(f)

        return filtered_files

    def _has_package_json(self) -> bool:
        """Check if target_dir has a package.json (npm project)."""
        return (self.target_dir / "package.json").exists()

    def __init__(self, target_dir: str | Path):
        super().__init__(str(target_dir))
        # Ensure target_dir is always resolved to an absolute path
        # to avoid CWD issues across subprocess calls (ESLint, Semgrep).
        self.target_dir = Path(os.path.abspath(str(self.target_dir)))

    def run_tools(self, output_dir: str = "DATA/outputs") -> dict[str, Any]:
        """
        Run ESLint, Semgrep JS rules, and npm audit on the target directory.

        Returns dict with keys: eslint, semgrep, npm_audit, errors
        """
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)

        js_files = self._get_js_files()
        if not js_files:
            logger.warning("No JS/TS files found in %s", self.target_dir)
            return {"eslint": [], "semgrep": {}, "npm_audit": {}, "errors": ["No JS/TS files found"]}

        logger.info("Found %d JS/TS files to analyze", len(js_files))
        results: dict[str, Any] = {"eslint": [], "semgrep": {}, "npm_audit": {}, "errors": []}

        # Run ESLint
        eslint_output = output_path / "eslint.json"
        self._run_eslint(js_files, eslint_output, results)

        # Run Semgrep with JS rules
        semgrep_output = output_path / "semgrep_js.json"
        self._run_semgrep_js(semgrep_output, results)

        # Run npm audit (if package.json exists)
        if self._has_package_json():
            npm_output = output_path / "npm_audit.json"
            self._run_npm_audit(npm_output, results)

        return results

    def _run_eslint(
        self,
        js_files: list[Path],
        output_file: Path,
        results: dict[str, Any],
    ) -> None:
        """Run ESLint with security plugin on JS/TS files.

        ESLint v9/v10 (flat config) resolves eslint.config.mjs from the target
        directory. We write the config there temporarily, run eslint, then remove it.
        """
        config_content = self._get_eslint_config_content()
        target_config = self.target_dir / "eslint.config.mjs"
        config_existed = target_config.exists()

        # Use relative paths — eslint resolves config from target_dir
        rel_files: list[str] = []
        for f in js_files:
            try:
                rel_files.append(str(f.relative_to(self.target_dir)))
            except ValueError:
                rel_files.append(str(f))

        env_flat = {**__import__("os").environ, "ESLINT_USE_FLAT_CONFIG": "true"}

        try:
            if not config_existed:
                target_config.write_text(config_content)

            proc = subprocess.run(
                ["eslint", "--format", "json", *rel_files],
                capture_output=True,
                text=True,
                timeout=120,
                cwd=str(self.target_dir),
                env=env_flat,
            )
            raw = proc.stdout.strip() or "[]"
            # Strip any non-JSON prefix (ESLint can emit warnings before the array)
            bracket_pos = raw.find("[")
            if bracket_pos > 0:
                raw = raw[bracket_pos:]
            elif not raw.startswith("["):
                raw = "[]"
            eslint_data = json.loads(raw)
            results["eslint"] = eslint_data
            output_file.write_text(json.dumps(eslint_data))
            logger.info("ESLint: found results in %d file(s)", len(eslint_data))
        except subprocess.TimeoutExpired:
            results["errors"].append("ESLint timed out (120s)")
            logger.warning("ESLint timed out")
        except (json.JSONDecodeError, FileNotFoundError) as e:
            results["errors"].append(f"ESLint error: {e}")
            logger.warning("ESLint failed: %s", e)
        finally:
            if not config_existed and target_config.exists():
                target_config.unlink()

    def _get_eslint_config_content(self) -> str:
        """Return ESLint flat config content (eslint.config.mjs) for ESLint v9/v10.

        Generates a flat config that imports eslint-plugin-security from its global
        npm installation path and registers all security rules.
        """
        import subprocess as _sp

        npm_root = _sp.run(["npm", "root", "-g"], capture_output=True, text=True).stdout.strip()
        plugin_path = f"{npm_root}/eslint-plugin-security"

        has_ts = any(self.target_dir.rglob("*.ts")) or any(self.target_dir.rglob("*.tsx"))

        if has_ts:
            ts_parser_path = f"{npm_root}/@typescript-eslint/parser"
            ts_plugin_path = f"{npm_root}/@typescript-eslint/eslint-plugin"

            return f"""import securityPlugin from '{plugin_path}/index.js';
import tsParser from '{ts_parser_path}/dist/index.js';
import tsPlugin from '{ts_plugin_path}/dist/index.js';

export default [
  {{
    files: ['**/*.ts', '**/*.tsx'],
    languageOptions: {{
      parser: tsParser,
      parserOptions: {{
        ecmaVersion: 'latest',
        sourceType: 'module',
      }}
    }},
    plugins: {{
      security: securityPlugin,
      '@typescript-eslint': tsPlugin,
    }},
    rules: {{
      'security/detect-eval-with-expression': 'error',
      'security/detect-non-literal-regexp': 'warn',
      'security/detect-non-literal-require': 'warn',
      'security/detect-object-injection': 'warn',
      'security/detect-child-process': 'warn',
      'security/detect-unsafe-regex': 'warn',
      'security/detect-pseudoRandomBytes': 'warn',
      'security/detect-no-csrf-before-method-override': 'warn',
      '@typescript-eslint/no-explicit-any': 'warn',
      'no-eval': 'error',
      'no-var': 'warn',
      'no-console': 'warn',
      'eqeqeq': 'warn',
    }}
  }},
  {{
    files: ['**/*.js', '**/*.jsx', '**/*.mjs', '**/*.cjs'],
    plugins: {{ security: securityPlugin }},
    rules: {{
      'security/detect-eval-with-expression': 'error',
      'security/detect-non-literal-regexp': 'warn',
      'security/detect-non-literal-require': 'warn',
      'security/detect-object-injection': 'warn',
      'security/detect-child-process': 'warn',
      'security/detect-unsafe-regex': 'warn',
      'security/detect-pseudoRandomBytes': 'warn',
      'security/detect-no-csrf-before-method-override': 'warn',
      'no-eval': 'error',
      'no-implied-eval': 'error',
      'no-new-func': 'error',
      'no-unused-vars': 'warn',
      'no-debugger': 'warn',
      'no-console': 'warn',
      'no-var': 'warn',
      'prefer-const': 'warn',
      'eqeqeq': 'warn',
      'no-with': 'error',
      'no-async-promise-executor': 'error',
      'require-await': 'warn',
    }},
    languageOptions: {{
      ecmaVersion: 2022,
      sourceType: 'commonjs',
      globals: {{
        require: 'readonly', module: 'readonly', exports: 'readonly',
        __dirname: 'readonly', __filename: 'readonly', process: 'readonly',
        console: 'readonly', Buffer: 'readonly', setTimeout: 'readonly',
        setInterval: 'readonly', clearTimeout: 'readonly', clearInterval: 'readonly',
      }},
    }},
  }}
];
"""
        else:
            return f"""import securityPlugin from '{plugin_path}/index.js';

export default [
  {{
    plugins: {{ security: securityPlugin }},
    rules: {{
      'security/detect-eval-with-expression': 'error',
      'security/detect-non-literal-regexp': 'warn',
      'security/detect-non-literal-require': 'warn',
      'security/detect-possible-timing-attacks': 'warn',
      'security/detect-unsafe-regex': 'error',
      'security/detect-buffer-noassert': 'warn',
      'security/detect-child-process': 'warn',
      'security/detect-disable-mustache-escape': 'error',
      'security/detect-new-buffer': 'warn',
      'security/detect-object-injection': 'warn',
      'security/detect-pseudoRandomBytes': 'warn',
      'no-eval': 'error',
      'no-implied-eval': 'error',
      'no-new-func': 'error',
      'no-unused-vars': 'warn',
      'no-debugger': 'warn',
      'no-console': 'warn',
      'no-var': 'warn',
      'prefer-const': 'warn',
      'eqeqeq': 'warn',
      'no-with': 'error',
      'no-async-promise-executor': 'error',
      'require-await': 'warn',
    }},
    languageOptions: {{
      ecmaVersion: 2022,
      sourceType: 'commonjs',
      globals: {{
        require: 'readonly', module: 'readonly', exports: 'readonly',
        __dirname: 'readonly', __filename: 'readonly', process: 'readonly',
        console: 'readonly', Buffer: 'readonly', setTimeout: 'readonly',
        setInterval: 'readonly', clearTimeout: 'readonly', clearInterval: 'readonly',
      }},
    }},
  }}
];
"""

    def _run_semgrep_js(self, output_file: Path, results: dict[str, Any]) -> None:
        """Run Semgrep with JS-specific rules."""
        # Load all js-*.yml rule files from TOOLS/semgrep/ for comprehensive coverage
        # Must resolve to absolute path since we change cwd for the subprocess!
        semgrep_dir = (Path(__file__).resolve().parent.parent.parent / "TOOLS" / "semgrep").resolve()
        js_rule_files = sorted(semgrep_dir.glob("js-*.*yml"))

        # Use only version-controlled custom rules (TOOLS/semgrep/js-*.yml).
        # p/javascript is intentionally excluded — it is a floating reference that
        # updates over time and breaks evaluation reproducibility. All security
        # rules relevant to the thesis evaluation are in our custom rule files.
        rules_args: list[str] = []

        for rule_file in js_rule_files:
            rules_args.extend(["--config", str(rule_file)])

        cmd = [
            "semgrep",
            *rules_args,
            "--json",
            "--quiet",
            "--include",
            "*.js",
            "--include",
            "*.jsx",
            "--include",
            "*.ts",
            "--include",
            "*.tsx",
            "--include",
            "*.mjs",
            "--include",
            "*.ejs",
            "--no-git-ignore",  # Crucial for scanning checked out repos outside the core git tree
            str(self.target_dir),
        ]

        try:
            # We use cwd=str(self.target_dir) for consistency so it runs with the
            # correct root context.
            proc = subprocess.run(cmd, capture_output=True, text=True, timeout=180, cwd=str(self.target_dir))
            raw = proc.stdout.strip() or "{}"
            semgrep_data = json.loads(raw)
            results["semgrep"] = semgrep_data
            output_file.write_text(raw)
            finding_count = len(semgrep_data.get("results", []))
            logger.info("Semgrep JS: %d findings", finding_count)
        except subprocess.TimeoutExpired:
            results["errors"].append("Semgrep JS timed out (180s)")
        except (json.JSONDecodeError, FileNotFoundError) as e:
            results["errors"].append(f"Semgrep JS error: {e}")

    def _run_npm_audit(self, output_file: Path, results: dict[str, Any]) -> None:
        """Run npm audit --json for dependency vulnerabilities."""
        cmd = ["npm", "audit", "--json"]
        try:
            proc = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=60,
                cwd=str(self.target_dir),
            )
            raw = proc.stdout.strip() or "{}"
            audit_data = json.loads(raw)
            results["npm_audit"] = audit_data
            output_file.write_text(raw)
            vuln_count = len(audit_data.get("vulnerabilities", {}))
            logger.info("npm audit: %d vulnerable packages", vuln_count)
        except subprocess.TimeoutExpired:
            results["errors"].append("npm audit timed out")
        except (json.JSONDecodeError, FileNotFoundError) as e:
            results["errors"].append(f"npm audit error: {e}")

    # ──────────────────────────────────────────────────────────────────────────
    # Normalization: ESLint / Semgrep JS / npm audit → CanonicalFinding
    # ──────────────────────────────────────────────────────────────────────────

    def normalize_eslint(self, eslint_data: list[dict]) -> list[CanonicalFinding]:
        """Convert ESLint JSON output to CanonicalFindings."""
        findings: list[CanonicalFinding] = []
        for file_result in eslint_data:
            file_path = file_result.get("filePath", "unknown")
            for msg in file_result.get("messages", []):
                # Suppress purely informational "File ignored" warnings
                if msg.get("ruleId") is None and "File ignored" in msg.get("message", ""):
                    continue

                rule_id = msg.get("ruleId") or "eslint-unknown"
                canonical_rule_id = JS_RULE_MAPPING.get(rule_id, f"CUSTOM-{rule_id}")
                severity_raw = msg.get("severity", 1)
                # ESLint severity: 2=error→high, 1=warn→medium
                severity = "high" if severity_raw == 2 else "medium"
                findings.append(
                    CanonicalFinding(
                        canonical_rule_id=canonical_rule_id,
                        original_rule_id=rule_id,
                        message=msg.get("message", ""),
                        file=file_path,
                        line=msg.get("line", 0),
                        column=msg.get("column", 0),
                        severity=severity,
                        category=self._infer_category(canonical_rule_id),
                        language="javascript",
                        tool_raw={
                            "tool_name": "eslint",
                            "rule_id": rule_id,
                            "column": msg.get("column"),
                            "source": "eslint",
                        },
                    )
                )
        return findings

    def normalize_npm_audit(self, audit_data: dict) -> list[CanonicalFinding]:
        """Convert npm audit JSON output to CanonicalFindings."""
        findings: list[CanonicalFinding] = []
        vulnerabilities = audit_data.get("vulnerabilities", {})
        for pkg_name, vuln in vulnerabilities.items():
            sev_raw = vuln.get("severity", "low")
            canonical_rule_id = "SECURITY-059" if sev_raw in ("critical", "high") else "SECURITY-060"
            via = vuln.get("via", [])
            cve_info = via[0] if via and isinstance(via[0], dict) else {}
            # Normalise severity to high/medium/low (SECURITY-059 = high)
            severity = "high" if sev_raw in ("critical", "high") else "medium" if sev_raw == "moderate" else "low"
            findings.append(
                CanonicalFinding(
                    canonical_rule_id=canonical_rule_id,
                    original_rule_id=f"npm-audit-{sev_raw}",
                    message=(
                        f"Vulnerable dependency: {pkg_name} ({sev_raw}) — " f"{cve_info.get('title', 'CVE advisory')}"
                    ),
                    file="package.json",
                    line=0,
                    column=0,
                    severity=severity,
                    category="security",
                    language="javascript",
                    tool_raw={"tool_name": "npm-audit", "package": pkg_name, "via": via, "severity": sev_raw},
                )
            )
        return findings

    def normalize_semgrep_js(self, semgrep_data: dict) -> list[CanonicalFinding]:
        """Convert Semgrep JS results to CanonicalFindings using JS_RULE_MAPPING.

        Deliberately does NOT delegate to normalizer.normalize_semgrep because that
        function uses the Python RULE_MAPPING which does not contain JS rule IDs like
        'js-global-variable'. All JS Semgrep rule IDs must be resolved via JS_RULE_MAPPING.
        """
        findings: list[CanonicalFinding] = []
        for item in semgrep_data.get("results", []):
            check_id = item.get("check_id", "")
            # Semgrep check_id format: "<namespace>.<rule-id>" — take last segment
            rule_id = check_id.split(".")[-1] if "." in check_id else check_id
            canonical_rule_id = JS_RULE_MAPPING.get(rule_id, f"CUSTOM-{rule_id}")
            sev_raw = item.get("extra", {}).get("severity", "WARNING").lower()
            severity = "high" if sev_raw == "error" else "low" if sev_raw == "info" else "medium"
            category_raw = item.get("extra", {}).get("metadata", {}).get("category", "security")
            findings.append(
                CanonicalFinding(
                    canonical_rule_id=canonical_rule_id,
                    original_rule_id=rule_id,
                    message=item.get("extra", {}).get("message", ""),
                    file=item.get("path", "unknown"),
                    line=item.get("start", {}).get("line", 0),
                    column=item.get("start", {}).get("col", 0),
                    severity=severity,
                    category=self._infer_category(canonical_rule_id) or category_raw,
                    language="javascript",
                    tool_raw={
                        "tool_name": "semgrep",
                        "rule_id": rule_id,
                        "check_id": check_id,
                        "source": "semgrep",
                    },
                )
            )
        return findings

    def get_all_findings(self, results: dict[str, Any]) -> list[CanonicalFinding]:
        """
        Normalize all tool results into a unified CanonicalFinding list.

        Deduplicates findings with the same (file, line, canonical_rule_id) — this
        removes duplicates where ESLint and Semgrep both flag the same pattern on
        the same line (e.g. no-var + js-global-variable on every ``var`` declaration).

        Call after run_tools().
        """
        all_findings: list[CanonicalFinding] = []

        if results.get("eslint"):
            eslint_findings = self.normalize_eslint(results["eslint"])
            all_findings.extend(eslint_findings)
            logger.info("ESLint normalized: %d findings", len(eslint_findings))

        if results.get("semgrep", {}).get("results"):
            semgrep_findings = self.normalize_semgrep_js(results["semgrep"])
            all_findings.extend(semgrep_findings)
            logger.info("Semgrep JS normalized: %d findings", len(semgrep_findings))

        if results.get("npm_audit"):
            npm_findings = self.normalize_npm_audit(results["npm_audit"])
            all_findings.extend(npm_findings)
            logger.info("npm audit normalized: %d findings", len(npm_findings))

        # Deduplicate: same file + line + column + canonical rule from different tools.
        # Column is included to preserve multiple violations on the same line (e.g. two
        # bracket accesses on the same line both flagged by detect-object-injection).
        # Graceful: column defaults to 0 if a tool doesn't emit it.
        seen: set[tuple[str, int, int, str]] = set()
        deduped: list[CanonicalFinding] = []
        for f in all_findings:
            key = (f.file, f.line, f.column, f.canonical_rule_id)
            if key not in seen:
                seen.add(key)
                deduped.append(f)
        removed = len(all_findings) - len(deduped)
        if removed:
            logger.info("Deduplication removed %d duplicate findings", removed)

        return deduped

    def get_rule_mappings(self) -> dict[str, str]:
        """Return JS rule ID → canonical ID mapping."""
        return JS_RULE_MAPPING

    @staticmethod
    def _infer_category(canonical_id: str) -> str:
        """Infer category from canonical ID prefix (must match CanonicalFinding.validate_category values)."""
        prefix_map = {
            "SECURITY": "security",
            "HARDCODE": "security",
            "STYLE": "style",
            "VAR": "dead-code",
            "DEAD": "dead-code",
            "PATTERN": "best-practice",
            "IMPORT": "best-practice",
            "DUP": "duplication",
            "COMPLEXITY": "design",
            "ASYNC": "best-practice",
            "BEST-PRACTICE": "best-practice",
            "NAMING": "style",
            "CUSTOM": "security",
        }
        for prefix, category in prefix_map.items():
            if canonical_id.startswith(prefix):
                return category
        return "best-practice"

    @staticmethod
    def detect_language(target_dir: str) -> str:
        """
        Auto-detect primary language of a project directory.

        Returns 'javascript', 'python', or 'mixed'.
        """
        target = Path(target_dir)
        py_files = list(target.rglob("*.py"))
        js_files = [
            f
            for ext in (".js", ".ts", ".jsx", ".tsx", ".ejs")
            for f in target.rglob(f"*{ext}")
            if "node_modules" not in str(f)
        ]
        has_package_json = (target / "package.json").exists()
        has_setup_py = (target / "setup.py").exists() or (target / "pyproject.toml").exists()

        if has_package_json and len(js_files) > len(py_files):
            return "javascript"
        if has_setup_py and len(py_files) > len(js_files):
            return "python"
        if js_files and py_files:
            return "mixed"
        if js_files:
            return "javascript"
        return "python"
