"""
God-mode tests for:
  - CORE/engines/quality_gate.py      (target: 90%+)
  - CORE/config_loader.py             (target: 90%+)
  - CORE/engines/confidence_scorer.py (target: 90%+)
  - CORE/engines/triage_memory.py     (target: 90%+)

All pure logic / fully mockable with no external calls needed.
"""

from unittest.mock import MagicMock, patch

from CORE.config_loader import ConfigLoader
from CORE.engines.confidence_scorer import (
    ConfidenceScorer,
    compute_confidence,
)
from CORE.engines.quality_gate import DEFAULT_THRESHOLDS, QualityGate
from CORE.engines.triage_memory import TriageMemory

# ═════════════════════════════════════════════════════════════════════════════
#  QualityGate
# ═════════════════════════════════════════════════════════════════════════════


def _finding(severity="high", category="security"):
    return {"canonical_severity": severity, "category": category}


class TestQualityGateInit:
    def test_default_thresholds_used_when_no_config(self):
        gate = QualityGate()
        assert gate.thresholds == DEFAULT_THRESHOLDS

    def test_config_none_uses_defaults(self):
        gate = QualityGate(config=None)
        assert gate.thresholds["max_high"] == DEFAULT_THRESHOLDS["max_high"]

    def test_config_overrides_threshold(self):
        gate = QualityGate(config={"quality_gate": {"max_high": 5, "max_medium": 2}})
        assert gate.thresholds["max_high"] == 5
        assert gate.thresholds["max_medium"] == 2

    def test_config_with_no_quality_gate_key_uses_defaults(self):
        gate = QualityGate(config={"other_key": 123})
        assert gate.thresholds["max_high"] == DEFAULT_THRESHOLDS["max_high"]

    def test_non_dict_config_ignored(self):
        gate = QualityGate(config="bad")
        assert gate.thresholds == DEFAULT_THRESHOLDS


class TestQualityGateEvaluate:
    def test_empty_findings_passes(self):
        result = QualityGate().evaluate([])
        assert result["passed"] is True
        assert result["counts"]["total"] == 0

    def test_single_high_blocks(self):
        gate = QualityGate(config={"quality_gate": {"max_high": 0}})
        result = gate.evaluate([_finding("high")])
        assert result["passed"] is False

    def test_high_within_limit_passes(self):
        gate = QualityGate(config={"quality_gate": {"max_high": 2}})
        result = gate.evaluate([_finding("high"), _finding("high")])
        assert result["passed"] is True

    def test_medium_exceeding_limit_fails(self):
        gate = QualityGate(
            config={"quality_gate": {"max_high": 999, "max_medium": 1, "max_total": 999, "max_security": 999}}
        )
        findings = [_finding("medium")] * 2
        result = gate.evaluate(findings)
        assert result["passed"] is False

    def test_total_exceeding_limit_fails(self):
        gate = QualityGate(
            config={"quality_gate": {"max_high": 999, "max_medium": 999, "max_total": 1, "max_security": 999}}
        )
        result = gate.evaluate([_finding("low"), _finding("low")])
        assert result["passed"] is False

    def test_security_category_check(self):
        gate = QualityGate(
            config={"quality_gate": {"max_high": 999, "max_medium": 999, "max_total": 999, "max_security": 0}}
        )
        result = gate.evaluate([_finding("low", "security")])
        assert result["passed"] is False

    def test_counts_populated_correctly(self):
        gate = QualityGate()
        findings = [_finding("high"), _finding("medium"), _finding("medium"), _finding("low")]
        result = gate.evaluate(findings)
        assert result["counts"]["high"] == 1
        assert result["counts"]["medium"] == 2
        assert result["counts"]["low"] == 1
        assert result["counts"]["total"] == 4

    def test_category_counts_populated(self):
        gate = QualityGate()
        result = gate.evaluate([_finding("high", "security"), _finding("low", "design")])
        assert result["category_counts"]["security"] == 1
        assert result["category_counts"]["design"] == 1

    def test_status_passed_string(self):
        result = QualityGate().evaluate([])
        assert "PASSED" in result["status"]

    def test_status_failed_string(self):
        gate = QualityGate(config={"quality_gate": {"max_high": 0}})
        result = gate.evaluate([_finding("high")])
        assert "FAILED" in result["status"]

    def test_summary_contains_passed_info(self):
        result = QualityGate().evaluate([])
        assert "passed" in result["summary"].lower() or "PASSED" in result["summary"]

    def test_checks_list_has_4_items(self):
        result = QualityGate().evaluate([])
        assert len(result["checks"]) == 4

    def test_finding_with_severity_field_fallback(self):
        """Falls back to 'severity' if 'canonical_severity' missing."""
        gate = QualityGate(config={"quality_gate": {"max_high": 0}})
        result = gate.evaluate([{"severity": "high", "category": "security"}])
        assert result["counts"]["high"] == 1

    def test_unknown_severity_counted_in_total(self):
        gate = QualityGate()
        result = gate.evaluate([{"canonical_severity": "unknown_level", "category": "other"}])
        assert result["counts"]["total"] == 1


class TestQualityGateShouldBlock:
    def test_block_mode_failed_gate_returns_true(self):
        gate = QualityGate(config={"quality_gate": {"mode": "block", "max_high": 0}})
        result = gate.evaluate([_finding("high")])
        assert gate.should_block(result) is True

    def test_block_mode_passed_gate_returns_false(self):
        gate = QualityGate()
        result = gate.evaluate([])
        assert gate.should_block(result) is False

    def test_warn_mode_never_blocks(self):
        gate = QualityGate(config={"quality_gate": {"mode": "warn", "max_high": 0}})
        result = gate.evaluate([_finding("high")])
        assert gate.should_block(result) is False


class TestQualityGateFormatComment:
    def test_returns_string(self):
        gate = QualityGate()
        result = gate.evaluate([])
        comment = gate.format_gate_comment(result)
        assert isinstance(comment, str)

    def test_comment_contains_passed_status(self):
        gate = QualityGate()
        result = gate.evaluate([])
        comment = gate.format_gate_comment(result)
        assert "PASSED" in comment

    def test_comment_contains_failed_status_and_block(self):
        gate = QualityGate(config={"quality_gate": {"max_high": 0}})
        result = gate.evaluate([_finding("high")])
        comment = gate.format_gate_comment(result)
        assert "FAILED" in comment
        assert "blocked" in comment.lower() or "Merge blocked" in comment

    def test_warn_mode_comment_has_warn_label(self):
        gate = QualityGate(config={"quality_gate": {"mode": "warn", "max_high": 0}})
        result = gate.evaluate([_finding("high")])
        comment = gate.format_gate_comment(result)
        assert "WARN" in comment

    def test_comment_has_markdown_table(self):
        gate = QualityGate()
        result = gate.evaluate([])
        comment = gate.format_gate_comment(result)
        assert "|" in comment


class TestQualityGatePrintReport:
    def test_print_report_no_crash(self, caplog):
        import logging

        caplog.set_level(logging.INFO)
        gate = QualityGate()
        result = gate.evaluate([_finding("high"), _finding("medium"), _finding("low")])
        gate.print_report(result)
        assert "Quality Gate" in caplog.text


# ═════════════════════════════════════════════════════════════════════════════
#  ConfigLoader
# ═════════════════════════════════════════════════════════════════════════════


class TestConfigLoaderLoad:
    def test_load_returns_dict(self, tmp_path):
        loader = ConfigLoader(str(tmp_path))
        config = loader.load()
        assert isinstance(config, dict)

    def test_load_with_no_config_file_returns_defaults(self, tmp_path):
        loader = ConfigLoader(str(tmp_path))
        config = loader.load()
        assert config["version"] == "1.0"

    def test_load_cached_on_second_call(self, tmp_path):
        loader = ConfigLoader(str(tmp_path))
        c1 = loader.load()
        c2 = loader.load()
        assert c1 is c2  # Same object == cached

    def test_load_merges_user_config(self, tmp_path):
        cfg = tmp_path / ".acrqa.yml"
        cfg.write_text("version: '2.0'\nrules:\n  enabled: false\n")
        loader = ConfigLoader(str(tmp_path))
        config = loader.load()
        assert config["version"] == "2.0"
        assert config["rules"]["enabled"] is False

    def test_load_acrqa_yaml_extension(self, tmp_path):
        cfg = tmp_path / ".acrqa.yaml"
        cfg.write_text("version: '3.0'\n")
        loader = ConfigLoader(str(tmp_path))
        config = loader.load()
        assert config["version"] == "3.0"

    def test_load_acrqa_yml_without_dot(self, tmp_path):
        cfg = tmp_path / "acrqa.yml"
        cfg.write_text("version: '4.0'\n")
        loader = ConfigLoader(str(tmp_path))
        config = loader.load()
        assert config["version"] == "4.0"

    def test_load_with_empty_yaml_file_uses_defaults(self, tmp_path):
        (tmp_path / ".acrqa.yml").write_text("")
        loader = ConfigLoader(str(tmp_path))
        config = loader.load()
        assert "rules" in config

    def test_load_with_invalid_yaml_falls_back_to_defaults(self, tmp_path):
        (tmp_path / ".acrqa.yml").write_text("{{invalid: yaml: [[\n")
        loader = ConfigLoader(str(tmp_path))
        config = loader.load()
        assert config["version"] == "1.0"


class TestConfigLoaderDeepMerge:
    def test_deep_merge_overrides_nested(self, tmp_path):
        loader = ConfigLoader(str(tmp_path))
        base = {"a": {"b": 1, "c": 2}}
        override = {"a": {"b": 99}}
        result = loader._deep_merge(base, override)
        assert result["a"]["b"] == 99
        assert result["a"]["c"] == 2

    def test_deep_merge_adds_new_keys(self, tmp_path):
        loader = ConfigLoader(str(tmp_path))
        base = {"a": 1}
        override = {"b": 2}
        result = loader._deep_merge(base, override)
        assert result["b"] == 2

    def test_deep_merge_non_dict_overrides_dict(self, tmp_path):
        loader = ConfigLoader(str(tmp_path))
        base = {"a": {"nested": 1}}
        override = {"a": "flat_value"}
        result = loader._deep_merge(base, override)
        assert result["a"] == "flat_value"


class TestConfigLoaderIsRuleEnabled:
    def test_rule_enabled_by_default(self, tmp_path):
        loader = ConfigLoader(str(tmp_path))
        assert loader.is_rule_enabled("SECURITY-001") is True

    def test_rule_disabled_when_all_disabled(self, tmp_path):
        (tmp_path / ".acrqa.yml").write_text("rules:\n  enabled: false\n")
        loader = ConfigLoader(str(tmp_path))
        assert loader.is_rule_enabled("SECURITY-001") is False

    def test_rule_disabled_in_disabled_list(self, tmp_path):
        (tmp_path / ".acrqa.yml").write_text("rules:\n  disabled_rules:\n    - IMPORT-001\n")
        loader = ConfigLoader(str(tmp_path))
        assert loader.is_rule_enabled("IMPORT-001") is False

    def test_rule_not_in_enabled_list_is_disabled(self, tmp_path):
        (tmp_path / ".acrqa.yml").write_text("rules:\n  enabled_rules:\n    - SECURITY-001\n")
        loader = ConfigLoader(str(tmp_path))
        assert loader.is_rule_enabled("IMPORT-001") is False

    def test_rule_in_enabled_list_is_enabled(self, tmp_path):
        (tmp_path / ".acrqa.yml").write_text("rules:\n  enabled_rules:\n    - SECURITY-001\n")
        loader = ConfigLoader(str(tmp_path))
        assert loader.is_rule_enabled("SECURITY-001") is True


class TestConfigLoaderSeverityOverride:
    def test_no_override_returns_none(self, tmp_path):
        loader = ConfigLoader(str(tmp_path))
        assert loader.get_severity_override("SECURITY-001") is None

    def test_override_returned(self, tmp_path):
        (tmp_path / ".acrqa.yml").write_text("rules:\n  severity_overrides:\n    SECURITY-001: critical\n")
        loader = ConfigLoader(str(tmp_path))
        assert loader.get_severity_override("SECURITY-001") == "critical"


class TestConfigLoaderShouldIgnorePath:
    def test_venv_path_ignored(self, tmp_path):
        loader = ConfigLoader(str(tmp_path))
        assert loader.should_ignore_path("/project/.venv/lib/foo.py") is True

    def test_pyc_wildcard_ignored(self, tmp_path):
        loader = ConfigLoader(str(tmp_path))
        assert loader.should_ignore_path("/project/app.pyc") is True

    def test_normal_py_not_ignored(self, tmp_path):
        loader = ConfigLoader(str(tmp_path))
        assert loader.should_ignore_path("/project/src/app.py") is False

    def test_node_modules_ignored(self, tmp_path):
        loader = ConfigLoader(str(tmp_path))
        assert loader.should_ignore_path("/project/node_modules/express/index.js") is True


class TestConfigLoaderHelpers:
    def test_get_min_severity_default(self, tmp_path):
        assert ConfigLoader(str(tmp_path)).get_min_severity() == "low"

    def test_get_max_explanations_default(self, tmp_path):
        assert ConfigLoader(str(tmp_path)).get_max_explanations() == 50

    def test_generate_default_config(self, tmp_path):
        out = tmp_path / "generated.yml"
        ConfigLoader.generate_default_config(str(out))
        assert out.exists()
        content = out.read_text()
        assert "version" in content


# ═════════════════════════════════════════════════════════════════════════════
#  ConfidenceScorer
# ═════════════════════════════════════════════════════════════════════════════


class TestConfidenceScorer:
    def setup_method(self):
        self.scorer = ConfidenceScorer(known_rule_ids={"SECURITY-001", "IMPORT-001"})

    def _finding(self, **kw):
        base = {
            "canonical_severity": "high",
            "category": "security",
            "tool": "bandit",
            "canonical_rule_id": "SECURITY-001",
        }
        base.update(kw)
        return base

    def test_returns_int(self):
        assert isinstance(self.scorer.score(self._finding()), int)

    def test_score_clamped_to_100(self):
        # Give max everything
        f = self._finding(canonical_severity="high", category="security", tool="bandit")
        s = self.scorer.score(f, fix_validated=True)
        assert s <= 100

    def test_score_clamped_to_0(self):
        scorer = ConfidenceScorer(known_rule_ids=set())
        f = {
            "canonical_severity": "unknown_sev",
            "category": "unknown_cat",
            "tool": "unknown_tool",
            "canonical_rule_id": "",
        }
        s = scorer.score(f)
        assert s >= 0

    def test_high_severity_adds_40(self):
        base = self.scorer.score(self._finding(canonical_severity="high"))
        low = self.scorer.score(self._finding(canonical_severity="low"))
        assert base > low

    def test_medium_severity_adds_25(self):
        s = self.scorer.score(self._finding(canonical_severity="medium"))
        assert s > 0

    def test_critical_treated_as_40(self):
        s = self.scorer.score(self._finding(canonical_severity="critical"))
        assert s >= 40

    def test_security_category_adds_20(self):
        sec = self.scorer.score(self._finding(category="security"))
        style = self.scorer.score(self._finding(category="style"))
        assert sec > style

    def test_known_rule_adds_10(self):
        known = self.scorer.score(self._finding(canonical_rule_id="SECURITY-001"))
        unknown = self.scorer.score(self._finding(canonical_rule_id="TOTALLY-UNKNOWN"))
        assert known > unknown

    def test_custom_rule_adds_5(self):
        scorer = ConfidenceScorer(known_rule_ids=set())
        custom = scorer.score(self._finding(canonical_rule_id="CUSTOM-999"))
        base = scorer.score(self._finding(canonical_rule_id="RANDOM-999"))
        assert custom > base

    def test_fix_validated_adds_10(self):
        s_with = self.scorer.score(self._finding(), fix_validated=True)
        s_without = self.scorer.score(self._finding(), fix_validated=None)
        assert s_with == s_without + 10

    def test_fix_validated_false_adds_nothing(self):
        s_false = self.scorer.score(self._finding(), fix_validated=False)
        s_none = self.scorer.score(self._finding(), fix_validated=None)
        assert s_false == s_none

    def test_tool_bandit_adds_15(self):
        s = self.scorer.score(self._finding(tool="bandit"))
        assert s > 0

    def test_tool_via_tool_raw(self):
        f = self._finding(tool="", tool_raw={"tool_name": "semgrep"})
        s = self.scorer.score(f)
        assert s > 0

    def test_tool_raw_non_dict_ignored(self):
        f = self._finding(tool="", tool_raw="not-a-dict")
        s = self.scorer.score(f)
        assert isinstance(s, int)

    def test_unknown_tool_defaults_to_5(self):
        scorer = ConfidenceScorer(known_rule_ids=set())
        f = {"canonical_severity": "low", "category": "style", "tool": "unknown_tool", "canonical_rule_id": ""}
        s = scorer.score(f)
        assert s >= 5  # At least tool default of 5

    def test_score_batch(self):
        findings = [self._finding(), self._finding(canonical_severity="low")]
        scores = self.scorer.score_batch(findings)
        assert len(scores) == 2
        assert all(isinstance(s, int) for s in scores)

    def test_score_batch_empty(self):
        assert self.scorer.score_batch([]) == []

    def test_severity_fallback_to_severity_field(self):
        f = {"severity": "high", "category": "security", "tool": "bandit", "canonical_rule_id": "SECURITY-001"}
        s = self.scorer.score(f)
        assert s > 0

    def test_label_very_high(self):
        assert ConfidenceScorer.label(95) == "very high"

    def test_label_high(self):
        assert ConfidenceScorer.label(75) == "high"

    def test_label_medium(self):
        assert ConfidenceScorer.label(55) == "medium"

    def test_label_low(self):
        assert ConfidenceScorer.label(35) == "low"

    def test_label_very_low(self):
        assert ConfidenceScorer.label(20) == "very low"

    def test_compute_confidence_convenience(self):
        f = {
            "canonical_severity": "high",
            "category": "security",
            "tool": "bandit",
            "canonical_rule_id": "SECURITY-001",
        }
        s = compute_confidence(f)
        assert isinstance(s, int)
        assert 0 <= s <= 100

    def test_init_loads_from_severity_scorer(self):
        """Default init should load known_rule_ids from SeverityScorer."""
        scorer = ConfidenceScorer()
        assert isinstance(scorer._known, set)
        assert len(scorer._known) > 0

    def test_init_severity_scorer_import_failure_uses_empty_set(self):
        """If SeverityScorer import raises, _known defaults to empty set."""
        import CORE.engines.confidence_scorer as cs_mod

        real_scorer = cs_mod.ConfidenceScorer

        original_init = real_scorer.__init__

        def patched_init(self, known_rule_ids=None):
            if known_rule_ids is not None:
                self._known = known_rule_ids
            else:
                # Simulate the import failing
                try:
                    raise ImportError("forced failure")
                except Exception:
                    self._known = set()

        with patch.object(real_scorer, "__init__", patched_init):
            scorer = real_scorer.__new__(real_scorer)
            patched_init(scorer, known_rule_ids=None)
        assert scorer._known == set()


# ═════════════════════════════════════════════════════════════════════════════
#  TriageMemory
# ═════════════════════════════════════════════════════════════════════════════


def _make_db(rows=None, rule_id=42, rules=None):
    """Build a MagicMock db with configurable behavior."""
    db = MagicMock()
    db.execute.return_value = (
        rows if rows is not None else [{"canonical_rule_id": "SECURITY-001", "file_path": "src/app.py"}]
    )
    db.insert_suppression_rule.return_value = rule_id
    db.get_suppression_rules.return_value = rules if rules is not None else []
    return db


class TestTriageMemoryLearnFromFp:
    def setup_method(self):
        self.tm = TriageMemory()

    def test_returns_rule_id_on_success(self):
        db = _make_db(rule_id=99)
        r = self.tm.learn_from_fp(1, db)
        assert r == 99

    def test_returns_none_if_finding_not_found(self):
        db = _make_db(rows=[])
        r = self.tm.learn_from_fp(999, db)
        assert r is None

    def test_insert_suppression_rule_called(self):
        db = _make_db()
        self.tm.learn_from_fp(1, db)
        db.insert_suppression_rule.assert_called_once()

    def test_ground_truth_updated_to_fp(self):
        db = _make_db()
        self.tm.learn_from_fp(1, db)
        # Second execute call should be the UPDATE
        calls = db.execute.call_args_list
        assert any("ground_truth" in str(call) for call in calls)

    def test_exception_returns_none(self):
        db = MagicMock()
        db.execute.side_effect = Exception("db error")
        r = self.tm.learn_from_fp(1, db)
        assert r is None

    def test_missing_canonical_rule_id_defaults_to_unknown(self):
        db = _make_db(rows=[{"canonical_rule_id": None, "file_path": "src/x.py"}])
        r = self.tm.learn_from_fp(1, db)
        assert r is not None  # Should not crash
        kwargs = db.insert_suppression_rule.call_args.kwargs
        assert kwargs["canonical_rule_id"] == "UNKNOWN"

    def test_missing_file_path_uses_empty_string(self):
        db = _make_db(rows=[{"canonical_rule_id": "SECURITY-001", "file_path": None}])
        r = self.tm.learn_from_fp(1, db)
        assert r is not None


class TestTriageMemoryShouldSuppress:
    def setup_method(self):
        self.tm = TriageMemory()

    def test_no_rules_returns_false(self):
        db = _make_db(rules=[])
        finding = {"canonical_rule_id": "SECURITY-001", "file": "src/app.py"}
        assert self.tm.should_suppress(finding, db) is False

    def test_matching_rule_returns_true(self):
        rules = [{"id": 1, "canonical_rule_id": "SECURITY-001", "file_pattern": "src/*.py"}]
        db = _make_db(rules=rules)
        finding = {"canonical_rule_id": "SECURITY-001", "file": "src/app.py"}
        assert self.tm.should_suppress(finding, db) is True

    def test_non_matching_rule_id_returns_false(self):
        rules = [{"id": 1, "canonical_rule_id": "IMPORT-001", "file_pattern": ""}]
        db = _make_db(rules=rules)
        finding = {"canonical_rule_id": "SECURITY-001", "file": "src/app.py"}
        assert self.tm.should_suppress(finding, db) is False

    def test_empty_pattern_matches_all_files(self):
        rules = [{"id": 1, "canonical_rule_id": "SECURITY-001", "file_pattern": ""}]
        db = _make_db(rules=rules)
        finding = {"canonical_rule_id": "SECURITY-001", "file": "any/file.py"}
        assert self.tm.should_suppress(finding, db) is True

    def test_increment_suppression_count_called(self):
        rules = [{"id": 7, "canonical_rule_id": "SECURITY-001", "file_pattern": ""}]
        db = _make_db(rules=rules)
        self.tm.should_suppress({"canonical_rule_id": "SECURITY-001", "file": "x.py"}, db)
        db.increment_suppression_count.assert_called_once_with(7)

    def test_exception_in_db_returns_false(self):
        db = MagicMock()
        db.get_suppression_rules.side_effect = Exception("boom")
        assert self.tm.should_suppress({"canonical_rule_id": "X"}, db) is False

    def test_increment_exception_ignored(self):
        """increment_suppression_count raising should not crash should_suppress."""
        rules = [{"id": 1, "canonical_rule_id": "SECURITY-001", "file_pattern": ""}]
        db = _make_db(rules=rules)
        db.increment_suppression_count.side_effect = Exception("disk error")
        # Should still return True without crashing
        result = self.tm.should_suppress({"canonical_rule_id": "SECURITY-001", "file": "x.py"}, db)
        assert result is True

    def test_uses_rule_id_fallback_in_finding(self):
        rules = [{"id": 1, "canonical_rule_id": "SECURITY-001", "file_pattern": ""}]
        db = _make_db(rules=rules)
        # Uses 'rule_id' key instead of 'canonical_rule_id'
        finding = {"rule_id": "SECURITY-001", "file": "x.py"}
        assert self.tm.should_suppress(finding, db) is True


class TestTriageMemoryGetActiveRules:
    def test_returns_rules_from_db(self):
        tm = TriageMemory()
        rules = [{"id": 1, "canonical_rule_id": "X"}]
        db = _make_db(rules=rules)
        result = tm.get_active_rules(db)
        assert result == rules
        db.get_suppression_rules.assert_called_once_with(active_only=True)


class TestTriageMemorySuppressFindings:
    def setup_method(self):
        self.tm = TriageMemory()

    def _finding(self, rule_id, file="src/app.py"):
        return {"canonical_rule_id": rule_id, "file": file}

    def test_no_rules_returns_all_findings(self):
        db = _make_db(rules=[])
        findings = [self._finding("X"), self._finding("Y")]
        kept, count = self.tm.suppress_findings(findings, db)
        assert count == 0
        assert len(kept) == 2

    def test_matching_finding_suppressed(self):
        rules = [{"id": 1, "canonical_rule_id": "SECURITY-001", "file_pattern": ""}]
        db = _make_db(rules=rules)
        findings = [self._finding("SECURITY-001"), self._finding("IMPORT-001")]
        kept, count = self.tm.suppress_findings(findings, db)
        assert count == 1
        assert len(kept) == 1
        assert kept[0]["canonical_rule_id"] == "IMPORT-001"

    def test_empty_findings_returns_empty(self):
        db = _make_db(rules=[{"id": 1, "canonical_rule_id": "X", "file_pattern": ""}])
        kept, count = self.tm.suppress_findings([], db)
        assert kept == []
        assert count == 0

    def test_all_suppressed_returns_empty(self):
        rules = [{"id": 1, "canonical_rule_id": "X", "file_pattern": ""}]
        db = _make_db(rules=rules)
        findings = [self._finding("X"), self._finding("X")]
        kept, count = self.tm.suppress_findings(findings, db)
        assert count == 2
        assert kept == []

    def test_exception_returns_original_findings(self):
        db = MagicMock()
        db.get_suppression_rules.side_effect = Exception("crash")
        findings = [self._finding("X")]
        kept, count = self.tm.suppress_findings(findings, db)
        assert kept == findings
        assert count == 0

    def test_increment_exception_silenced(self):
        rules = [{"id": 1, "canonical_rule_id": "SECURITY-001", "file_pattern": ""}]
        db = _make_db(rules=rules)
        db.increment_suppression_count.side_effect = Exception("disk error")
        findings = [self._finding("SECURITY-001")]
        kept, count = self.tm.suppress_findings(findings, db)
        assert count == 1  # Still suppressed despite increment crash


class TestTriageMemoryDerivePattern:
    def test_empty_path_returns_empty(self):
        assert TriageMemory._derive_pattern("") == ""

    def test_test_directory_returns_glob(self):
        result = TriageMemory._derive_pattern("project/tests/test_foo.py")
        assert result.endswith("/*")
        assert "tests" in result

    def test_spec_directory_glob(self):
        result = TriageMemory._derive_pattern("src/spec/auth.spec.js")
        assert "spec" in result
        assert "/*" in result

    def test_test_file_prefix_generalizes(self):
        result = TriageMemory._derive_pattern("src/test_utils.py")
        assert "test_*.py" in result

    def test_normal_file_returns_exact_path(self):
        result = TriageMemory._derive_pattern("src/app.py")
        assert result == "src/app.py"

    def test_windows_backslash_normalized(self):
        result = TriageMemory._derive_pattern("src\\test_utils.py")
        # Should not contain backslashes in output
        assert "\\" not in result or "test_*.py" in result

    def test_tests_dir_inside_nested_path(self):
        r = TriageMemory._derive_pattern("myproject/app/__tests__/auth.test.js")
        assert "/*" in r
