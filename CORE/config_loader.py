#!/usr/bin/env python3
"""
ACR-QA Per-Repository Configuration Loader
Reads .acrqa.yml from a project to customize analysis behavior.
"""

import yaml
from pathlib import Path
from typing import Dict, List, Any, Optional


DEFAULT_CONFIG = {
    "version": "1.0",
    "rules": {
        "enabled": True,
        "severity_overrides": {},
        "disabled_rules": [],
        "enabled_rules": [],  # Empty = all enabled
    },
    "analysis": {
        "max_file_size_kb": 500,
        "ignore_paths": [
            "__pycache__",
            ".venv",
            "node_modules",
            ".git",
            "htmlcov",
            "*.pyc",
        ],
        "file_extensions": [".py"],
    },
    "autofix": {
        "enabled": True,
        "auto_apply_confidence": 80,  # Only auto-apply fixes with >= 80% confidence
    },
    "reporting": {
        "min_severity": "low",  # Minimum severity to report: low, medium, high
        "include_explanations": True,
        "max_findings": 500,
    },
    "ai": {
        "enabled": True,
        "max_explanations": 50,  # Limit AI calls per run
        "model": "llama-3.1-8b-instant",
    },
}


class ConfigLoader:
    """Load and merge per-repo .acrqa.yml with defaults."""

    CONFIG_FILENAMES = [".acrqa.yml", ".acrqa.yaml", "acrqa.yml", "acrqa.yaml"]

    def __init__(self, project_dir: str = "."):
        self.project_dir = Path(project_dir)
        self._config = None

    def load(self) -> Dict[str, Any]:
        """Load config from project directory, falling back to defaults."""
        if self._config is not None:
            return self._config

        # Try to find config file
        config_file = self._find_config_file()

        if config_file:
            try:
                with open(config_file) as f:
                    user_config = yaml.safe_load(f) or {}
                self._config = self._deep_merge(DEFAULT_CONFIG.copy(), user_config)
                print(f"📋 Loaded config from {config_file}")
            except Exception as e:
                print(f"⚠️ Error reading {config_file}: {e}. Using defaults.")
                self._config = DEFAULT_CONFIG.copy()
        else:
            self._config = DEFAULT_CONFIG.copy()

        return self._config

    def _find_config_file(self) -> Optional[Path]:
        """Search for config file in project directory."""
        for name in self.CONFIG_FILENAMES:
            path = self.project_dir / name
            if path.exists():
                return path
        return None

    def _deep_merge(self, base: dict, override: dict) -> dict:
        """Deep merge override into base dict."""
        result = base.copy()
        for key, value in override.items():
            if key in result and isinstance(result[key], dict) and isinstance(value, dict):
                result[key] = self._deep_merge(result[key], value)
            else:
                result[key] = value
        return result

    def is_rule_enabled(self, rule_id: str) -> bool:
        """Check if a specific rule is enabled."""
        config = self.load()
        rules = config.get("rules", {})

        if not rules.get("enabled", True):
            return False

        disabled = rules.get("disabled_rules", [])
        if rule_id in disabled:
            return False

        enabled = rules.get("enabled_rules", [])
        if enabled and rule_id not in enabled:
            return False

        return True

    def get_severity_override(self, rule_id: str) -> Optional[str]:
        """Get severity override for a rule, if any."""
        config = self.load()
        overrides = config.get("rules", {}).get("severity_overrides", {})
        return overrides.get(rule_id)

    def should_ignore_path(self, file_path: str) -> bool:
        """Check if a file path should be ignored."""
        config = self.load()
        ignore_patterns = config.get("analysis", {}).get("ignore_paths", [])

        for pattern in ignore_patterns:
            if pattern in file_path:
                return True
            # Glob-style wildcard matching
            if pattern.startswith("*") and file_path.endswith(pattern[1:]):
                return True

        return False

    def get_min_severity(self) -> str:
        """Get minimum severity level to report."""
        config = self.load()
        return config.get("reporting", {}).get("min_severity", "low")

    def get_max_explanations(self) -> int:
        """Get max AI explanations per run."""
        config = self.load()
        return config.get("ai", {}).get("max_explanations", 50)

    @staticmethod
    def generate_default_config(output_path: str = ".acrqa.yml"):
        """Generate a default .acrqa.yml config file."""
        content = """# ACR-QA Configuration
# Place this file in your project root to customize analysis.

version: "1.0"

rules:
  enabled: true
  # Disable specific rules:
  disabled_rules: []
  #   - IMPORT-001
  #   - VAR-001
  
  # Override severity for specific rules:
  severity_overrides: {}
  #   SECURITY-001: high
  #   STYLE-001: low

analysis:
  max_file_size_kb: 500
  ignore_paths:
    - __pycache__
    - .venv
    - node_modules
    - .git
    - htmlcov
    - "*.pyc"
  file_extensions:
    - .py

autofix:
  enabled: true
  auto_apply_confidence: 80  # Only auto-apply fixes >= 80% confidence

reporting:
  min_severity: low  # low, medium, or high
  include_explanations: true
  max_findings: 500

ai:
  enabled: true
  max_explanations: 50
  model: llama-3.1-8b-instant
"""
        with open(output_path, "w") as f:
            f.write(content)
        print(f"✅ Generated default config: {output_path}")
        return output_path


if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1 and sys.argv[1] == "--generate":
        output = sys.argv[2] if len(sys.argv) > 2 else ".acrqa.yml"
        ConfigLoader.generate_default_config(output)
    else:
        loader = ConfigLoader()
        config = loader.load()
        print(yaml.dump(config, default_flow_style=False))
