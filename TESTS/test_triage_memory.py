"""Tests for CORE/engines/triage_memory.py — Feature 6"""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from CORE.engines.triage_memory import TriageMemory


@pytest.fixture
def memory():
    return TriageMemory()


def _mock_db(rows=None, suppression_rules=None):
    db = MagicMock()
    db.execute.return_value = rows or []
    db.get_suppression_rules.return_value = suppression_rules or []
    db.insert_suppression_rule.return_value = 42
    db.increment_suppression_count.return_value = None
    return db


def _finding(rule="SECURITY-001", path="app/main.py", sev="high", cat="security"):
    return {"canonical_rule_id": rule, "file_path": path, "canonical_severity": sev, "category": cat}


def _rule(canonical="SECURITY-001", pattern="app/*.py", rule_id=1):
    return {"id": rule_id, "canonical_rule_id": canonical, "file_pattern": pattern}


class TestLearnFromFP:
    def test_returns_rule_id_on_success(self, memory):
        db = _mock_db(rows=[{"canonical_rule_id": "SECURITY-001", "file_path": "app/main.py"}])
        result = memory.learn_from_fp(1, db)
        assert result == 42

    def test_returns_none_when_finding_not_found(self, memory):
        db = _mock_db(rows=[])
        result = memory.learn_from_fp(999, db)
        assert result is None

    def test_calls_insert_suppression_rule(self, memory):
        db = _mock_db(rows=[{"canonical_rule_id": "SECURITY-001", "file_path": "app/main.py"}])
        memory.learn_from_fp(1, db)
        db.insert_suppression_rule.assert_called_once()

    def test_updates_ground_truth(self, memory):
        db = _mock_db(rows=[{"canonical_rule_id": "SECURITY-001", "file_path": "app/main.py"}])
        memory.learn_from_fp(1, db)
        calls = [str(c) for c in db.execute.call_args_list]
        assert any("FP" in c for c in calls)

    def test_returns_none_on_db_exception(self, memory):
        db = MagicMock()
        db.execute.side_effect = Exception("DB down")
        result = memory.learn_from_fp(1, db)
        assert result is None

    def test_handles_missing_file_path(self, memory):
        db = _mock_db(rows=[{"canonical_rule_id": "SECURITY-001", "file_path": None}])
        result = memory.learn_from_fp(1, db)
        assert result == 42


class TestShouldSuppress:
    def test_suppresses_matching_rule_and_pattern(self, memory):
        db = _mock_db(suppression_rules=[_rule("SECURITY-001", "app/*.py")])
        f = _finding("SECURITY-001", "app/main.py")
        assert memory.should_suppress(f, db) is True

    def test_does_not_suppress_different_rule(self, memory):
        db = _mock_db(suppression_rules=[_rule("SECURITY-002", "app/*.py")])
        f = _finding("SECURITY-001", "app/main.py")
        assert memory.should_suppress(f, db) is False

    def test_does_not_suppress_non_matching_pattern(self, memory):
        db = _mock_db(suppression_rules=[_rule("SECURITY-001", "other/*.py")])
        f = _finding("SECURITY-001", "app/main.py")
        assert memory.should_suppress(f, db) is False

    def test_suppresses_empty_pattern(self, memory):
        db = _mock_db(suppression_rules=[_rule("SECURITY-001", "")])
        f = _finding("SECURITY-001", "anywhere/file.py")
        assert memory.should_suppress(f, db) is True

    def test_increments_suppression_count(self, memory):
        db = _mock_db(suppression_rules=[_rule("SECURITY-001", "app/*.py")])
        f = _finding("SECURITY-001", "app/main.py")
        memory.should_suppress(f, db)
        db.increment_suppression_count.assert_called_once_with(1)

    def test_returns_false_on_exception(self, memory):
        db = MagicMock()
        db.get_suppression_rules.side_effect = Exception("DB error")
        assert memory.should_suppress(_finding(), db) is False

    def test_uses_rule_id_fallback_key(self, memory):
        db = _mock_db(suppression_rules=[_rule("SECURITY-001", "")])
        f = {"rule_id": "SECURITY-001", "file": "app/main.py"}
        assert memory.should_suppress(f, db) is True


class TestSuppressFindings:
    def test_no_rules_returns_all(self, memory):
        db = _mock_db(suppression_rules=[])
        findings = [_finding(), _finding("STYLE-001", "utils.py", "low", "style")]
        kept, count = memory.suppress_findings(findings, db)
        assert len(kept) == 2
        assert count == 0

    def test_suppresses_matching_finding(self, memory):
        db = _mock_db(suppression_rules=[_rule("SECURITY-001", "app/*.py")])
        findings = [_finding("SECURITY-001", "app/main.py"), _finding("STYLE-001", "utils.py", "low", "style")]
        kept, count = memory.suppress_findings(findings, db)
        assert count == 1
        assert len(kept) == 1
        assert kept[0]["canonical_rule_id"] == "STYLE-001"

    def test_returns_all_on_exception(self, memory):
        db = MagicMock()
        db.get_suppression_rules.side_effect = Exception("DB error")
        findings = [_finding()]
        kept, count = memory.suppress_findings(findings, db)
        assert kept == findings
        assert count == 0

    def test_empty_findings_returns_empty(self, memory):
        db = _mock_db(suppression_rules=[_rule()])
        kept, count = memory.suppress_findings([], db)
        assert kept == []
        assert count == 0

    def test_increment_called_per_suppressed(self, memory):
        db = _mock_db(suppression_rules=[_rule("SECURITY-001", "")])
        findings = [_finding("SECURITY-001", "a.py"), _finding("SECURITY-001", "b.py")]
        kept, count = memory.suppress_findings(findings, db)
        assert count == 2
        assert db.increment_suppression_count.call_count == 2


class TestGetActiveRules:
    def test_delegates_to_db(self, memory):
        db = _mock_db(suppression_rules=[_rule()])
        rules = memory.get_active_rules(db)
        db.get_suppression_rules.assert_called_once_with(active_only=True)
        assert len(rules) == 1


class TestDerivePattern:
    @pytest.mark.parametrize(
        "path,expected",
        [
            ("tests/test_auth.py", "tests/*"),
            ("src/test/helper.py", "src/test/*"),
            ("spec/api_spec.py", "spec/*"),
            ("app/test_main.py", "app/test_*.py"),
            ("test_utils.py", "test_*.py"),
            ("app/main.py", "app/main.py"),
            ("", ""),
            ("src\\windows\\file.py", "src/windows/file.py"),
        ],
    )
    def test_derive_pattern(self, expected, path):
        result = TriageMemory._derive_pattern(path)
        assert result == expected
