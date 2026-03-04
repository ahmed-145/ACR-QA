#!/usr/bin/env python3
"""
ACR-QA Python Language Adapter
Orchestrates Python-specific analysis tools: Ruff, Semgrep, Bandit, Vulture, Radon, jscpd.
"""

import subprocess
import shutil
from pathlib import Path
from typing import Dict, List, Any

from CORE.adapters.base import LanguageAdapter


class PythonAdapter(LanguageAdapter):
    """
    Python language adapter for ACR-QA.
    
    Tools:
        - Ruff: Style, imports, PEP8, best practices
        - Semgrep: Security patterns, OWASP, custom rules
        - Bandit: Python security vulnerabilities
        - Vulture: Dead code detection
        - Radon: Cyclomatic complexity
        - jscpd: Code duplication
    """

    @property
    def language_name(self) -> str:
        return "Python"

    @property
    def file_extensions(self) -> List[str]:
        return [".py"]

    def get_tools(self) -> List[Dict[str, Any]]:
        return [
            {"name": "ruff", "purpose": "Style, imports, PEP8, best practices", "check": "ruff"},
            {"name": "semgrep", "purpose": "Security patterns, OWASP", "check": "semgrep"},
            {"name": "bandit", "purpose": "Python security vulnerabilities", "check": "bandit"},
            {"name": "vulture", "purpose": "Dead code detection", "check": "vulture"},
            {"name": "radon", "purpose": "Cyclomatic complexity", "check": "radon"},
            {"name": "jscpd", "purpose": "Code duplication detection", "check": "jscpd"},
        ]

    def check_tools_available(self) -> Dict[str, bool]:
        """Check which tools are installed and available."""
        availability = {}
        for tool in self.get_tools():
            cmd = tool["check"]
            availability[tool["name"]] = shutil.which(cmd) is not None
        return availability

    def run_tools(self, output_dir: str = "DATA/outputs") -> Dict[str, Any]:
        """
        Run all Python analysis tools via the existing run_checks.sh script.
        
        This delegates to the battle-tested shell script for now.
        Future: migrate each tool invocation to pure Python for better control.
        """
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)
        
        results = {"tools_run": [], "errors": []}
        
        try:
            subprocess.run(
                ["bash", "TOOLS/run_checks.sh", str(self.target_dir)],
                check=True,
                capture_output=True,
                text=True,
            )
            results["tools_run"] = [t["name"] for t in self.get_tools()]
        except subprocess.CalledProcessError as e:
            results["errors"].append(f"run_checks.sh failed: {e.stderr}")
        except FileNotFoundError:
            results["errors"].append("TOOLS/run_checks.sh not found")

        return results

    def get_rule_mappings(self) -> Dict[str, str]:
        """
        Return Python-specific rule mappings.
        These are already defined in normalizer.py's RULE_MAPPING dict.
        This method returns the subset relevant to Python tools.
        """
        # Import from normalizer to avoid duplication
        try:
            from CORE.engines.normalizer import RULE_MAPPING
            return RULE_MAPPING
        except ImportError:
            return {}


# Placeholder for Phase 2: JavaScript/TypeScript adapter
class JavaScriptAdapter(LanguageAdapter):
    """
    JavaScript/TypeScript language adapter for ACR-QA.
    
    Phase 2 implementation will add:
        - ESLint: Style, best practices, security
        - Semgrep: JS security patterns
        - jscpd: Duplication (already supports JS)
        - npm audit / Snyk: Dependency vulnerabilities
    
    Folder structure when implemented:
        TOOLS/
        ├── run_checks.sh          # Python tools
        ├── run_js_checks.sh       # [NEW] JS/TS tools
        └── semgrep/
            ├── python-rules.yml   # Existing
            └── js-rules.yml       # [NEW] JS security rules
    """

    @property
    def language_name(self) -> str:
        return "JavaScript"

    @property
    def file_extensions(self) -> List[str]:
        return [".js", ".jsx", ".ts", ".tsx", ".mjs", ".cjs"]

    def get_tools(self) -> List[Dict[str, Any]]:
        return [
            {"name": "eslint", "purpose": "Style, best practices, security", "check": "eslint"},
            {"name": "semgrep", "purpose": "JS security patterns", "check": "semgrep"},
            {"name": "jscpd", "purpose": "Code duplication detection", "check": "jscpd"},
        ]

    def run_tools(self, output_dir: str = "DATA/outputs") -> Dict[str, Any]:
        # Phase 2: Will implement JS tool orchestration
        raise NotImplementedError(
            "JavaScript adapter is a Phase 2 feature. "
            "See CORE/adapters/base.py for the interface to implement."
        )

    def get_rule_mappings(self) -> Dict[str, str]:
        # Phase 2: ESLint rule → canonical mappings
        return {
            # ESLint rules → Universal IDs (to be expanded)
            "no-unused-vars": "VAR-001",
            "no-eval": "SECURITY-027",
            "no-console": "STYLE-002",
            "no-var": "STYLE-003",
            "prefer-const": "STYLE-004",
            "no-debugger": "DEAD-001",
        }
