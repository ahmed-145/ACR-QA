#!/usr/bin/env python3
"""
Tests for ConfigLoader and QualityGate engines.
"""

import sys
import os
import tempfile
import pytest
import yaml
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from CORE.config_loader import ConfigLoader, DEFAULT_CONFIG
from CORE.engines.quality_gate import QualityGate, DEFAULT_THRESHOLDS


# ─── ConfigLoader Tests ────────────────────────────────────────────────────


class TestConfigLoader:
    """Test per-repo configuration loading and merging."""

    def test_defaults_when_no_config_file(self):
        """Should return default config when no .acrqa.yml exists."""
        loader = ConfigLoader(project_dir=tempfile.mkdtemp())
        config = loader.load()
        assert config["version"] == "1.0"
        assert config["rules"]["enabled"] is True
        assert config["analysis"]["file_extensions"] == [".py"]

    def test_loads_custom_yaml(self):
        """Should merge user YAML with defaults."""
        tmpdir = tempfile.mkdtemp()
        config_path = Path(tmpdir) / ".acrqa.yml"
        config_path.write_text(
            yaml.dump(
                {
                    "rules": {"disabled_rules": ["IMPORT-001", "VAR-001"]},
                    "reporting": {"min_severity": "medium"},
                }
            )
        )

        loader = ConfigLoader(project_dir=tmpdir)
        config = loader.load()

        assert "IMPORT-001" in config["rules"]["disabled_rules"]
        assert "VAR-001" in config["rules"]["disabled_rules"]
        assert config["reporting"]["min_severity"] == "medium"
        # Defaults should still be present
        assert config["ai"]["enabled"] is True

    def test_is_rule_enabled_all_enabled(self):
        """All rules enabled by default."""
        loader = ConfigLoader(project_dir=tempfile.mkdtemp())
        assert loader.is_rule_enabled("IMPORT-001") is True
        assert loader.is_rule_enabled("SECURITY-027") is True

    def test_is_rule_disabled(self):
        """Disabled rules should return False."""
        tmpdir = tempfile.mkdtemp()
        (Path(tmpdir) / ".acrqa.yml").write_text(
            yaml.dump({"rules": {"disabled_rules": ["IMPORT-001"]}})
        )

        loader = ConfigLoader(project_dir=tmpdir)
        assert loader.is_rule_enabled("IMPORT-001") is False
        assert loader.is_rule_enabled("VAR-001") is True

    def test_rules_globally_disabled(self):
        """When rules.enabled is False, all rules are disabled."""
        tmpdir = tempfile.mkdtemp()
        (Path(tmpdir) / ".acrqa.yml").write_text(
            yaml.dump({"rules": {"enabled": False}})
        )

        loader = ConfigLoader(project_dir=tmpdir)
        assert loader.is_rule_enabled("IMPORT-001") is False
        assert loader.is_rule_enabled("SECURITY-001") is False

    def test_severity_override(self):
        """Should return severity override for a rule."""
        tmpdir = tempfile.mkdtemp()
        (Path(tmpdir) / ".acrqa.yml").write_text(
            yaml.dump({"rules": {"severity_overrides": {"IMPORT-001": "high"}}})
        )

        loader = ConfigLoader(project_dir=tmpdir)
        assert loader.get_severity_override("IMPORT-001") == "high"
        assert loader.get_severity_override("VAR-001") is None

    def test_should_ignore_path(self):
        """Should ignore paths matching patterns."""
        loader = ConfigLoader(project_dir=tempfile.mkdtemp())
        assert loader.should_ignore_path("__pycache__/something.pyc") is True
        assert loader.should_ignore_path(".venv/lib/site-packages") is True
        assert loader.should_ignore_path("CORE/main.py") is False

    def test_should_ignore_glob_pattern(self):
        """Should handle glob-style *.pyc patterns."""
        loader = ConfigLoader(project_dir=tempfile.mkdtemp())
        assert loader.should_ignore_path("something.pyc") is True
        assert loader.should_ignore_path("something.py") is False

    def test_get_max_explanations(self):
        """Should return max AI explanations from config."""
        loader = ConfigLoader(project_dir=tempfile.mkdtemp())
        assert loader.get_max_explanations() == 50

    def test_custom_max_explanations(self):
        """Should use custom max_explanations from YAML."""
        tmpdir = tempfile.mkdtemp()
        (Path(tmpdir) / ".acrqa.yml").write_text(
            yaml.dump({"ai": {"max_explanations": 10}})
        )

        loader = ConfigLoader(project_dir=tmpdir)
        assert loader.get_max_explanations() == 10

    def test_generate_default_config(self):
        """Should create a valid .acrqa.yml file."""
        tmpdir = tempfile.mkdtemp()
        output = os.path.join(tmpdir, ".acrqa.yml")
        ConfigLoader.generate_default_config(output)

        assert Path(output).exists()
        with open(output) as f:
            config = yaml.safe_load(f)
        assert config["version"] == "1.0"
        assert config["rules"]["enabled"] is True

    def test_caching(self):
        """Config should be loaded once and cached."""
        loader = ConfigLoader(project_dir=tempfile.mkdtemp())
        config1 = loader.load()
        config2 = loader.load()
        assert config1 is config2  # Same object = cached


# ─── QualityGate Tests ──────────────────────────────────────────────────────


class TestQualityGate:
    """Test quality gate evaluation logic."""

    def _make_findings(self, high=0, medium=0, low=0, security=0):
        """Helper to create test findings."""
        findings = []
        for _ in range(high):
            findings.append({"canonical_severity": "high", "category": "best-practice"})
        for _ in range(medium):
            findings.append({"canonical_severity": "medium", "category": "style"})
        for _ in range(low):
            findings.append({"canonical_severity": "low", "category": "style"})
        for _ in range(security):
            findings.append({"canonical_severity": "high", "category": "security"})
        return findings

    def test_gate_passes_no_findings(self):
        """Empty findings should always pass."""
        gate = QualityGate()
        result = gate.evaluate([])
        assert result["passed"] is True
        assert "PASSED" in result["status"]

    def test_gate_passes_within_thresholds(self):
        """Findings within thresholds should pass."""
        gate = QualityGate()
        findings = self._make_findings(high=0, medium=5, low=20)
        result = gate.evaluate(findings)
        assert result["passed"] is True

    def test_gate_fails_high_severity(self):
        """Should fail when high-severity exceeds threshold."""
        gate = QualityGate()
        findings = self._make_findings(high=1)
        result = gate.evaluate(findings)
        assert result["passed"] is False
        assert "FAILED" in result["status"]

    def test_gate_fails_security_findings(self):
        """Should fail when security findings exceed threshold."""
        gate = QualityGate()
        findings = self._make_findings(security=1)
        result = gate.evaluate(findings)
        assert result["passed"] is False

    def test_gate_fails_too_many_medium(self):
        """Should fail when medium severity exceeds threshold."""
        gate = QualityGate()
        findings = self._make_findings(medium=15)
        result = gate.evaluate(findings)
        assert result["passed"] is False

    def test_gate_fails_total_exceeded(self):
        """Should fail when total findings exceeds threshold."""
        gate = QualityGate()
        findings = self._make_findings(low=150)
        result = gate.evaluate(findings)
        assert result["passed"] is False

    def test_custom_thresholds(self):
        """Should respect custom threshold config."""
        config = {"quality_gate": {"max_high": 5, "max_medium": 50}}
        gate = QualityGate(config=config)
        findings = self._make_findings(high=3, medium=40)
        result = gate.evaluate(findings)
        assert result["passed"] is True

    def test_strict_thresholds(self):
        """Zero tolerance should fail on any finding."""
        config = {"quality_gate": {"max_high": 0, "max_medium": 0, "max_total": 0}}
        gate = QualityGate(config=config)
        findings = self._make_findings(low=1)
        result = gate.evaluate(findings)
        assert result["passed"] is False

    def test_gate_returns_counts(self):
        """Should include accurate severity counts."""
        gate = QualityGate()
        findings = self._make_findings(high=2, medium=3, low=5)
        result = gate.evaluate(findings)
        assert result["counts"]["high"] == 2
        assert result["counts"]["medium"] == 3
        assert result["counts"]["low"] == 5
        assert result["counts"]["total"] == 10

    def test_gate_returns_check_details(self):
        """Should include details for each check."""
        gate = QualityGate()
        result = gate.evaluate([])
        assert len(result["checks"]) == 4  # high, medium, total, security
        for check in result["checks"]:
            assert "name" in check
            assert "passed" in check
            assert "actual" in check
            assert "threshold" in check

    def test_print_report_doesnt_crash(self, capsys):
        """print_report should produce output without errors."""
        gate = QualityGate()
        result = gate.evaluate(self._make_findings(high=1))
        gate.print_report(result)
        captured = capsys.readouterr()
        assert "Quality Gate" in captured.out
        assert "FAILED" in captured.out
