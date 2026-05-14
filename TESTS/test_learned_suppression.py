"""
Tests for CORE/engines/learned_suppression.py — Feature 10.

Covers:
  - Engine importable and instantiable
  - Text representation of findings
  - Cosine similarity calculation
  - embed_text returns float list
  - suppress() degrades gracefully with empty DB
  - suppress() zeroes confidence for high-similarity findings
  - suppress() keeps findings when similarity below threshold
  - suppress() only compares same-rule embeddings
  - store_dismissed() gracefully handles missing finding
  - is_available() returns bool
  - DB method: insert/get embeddings
  - Pipeline integration: suppress is wired into main after triage memory
"""

from __future__ import annotations

import json
from unittest.mock import MagicMock, patch

import pytest


class TestLearnedSuppressionImport:
    def test_module_importable(self):
        from CORE.engines.learned_suppression import LearnedSuppressionEngine

        assert LearnedSuppressionEngine is not None

    def test_instantiable_with_defaults(self):
        from CORE.engines.learned_suppression import SIMILARITY_THRESHOLD, LearnedSuppressionEngine

        eng = LearnedSuppressionEngine()
        assert eng.threshold == SIMILARITY_THRESHOLD

    def test_instantiable_with_custom_threshold(self):
        from CORE.engines.learned_suppression import LearnedSuppressionEngine

        eng = LearnedSuppressionEngine(threshold=0.85)
        assert eng.threshold == 0.85

    def test_constants_defined(self):
        from CORE.engines.learned_suppression import MODEL_NAME, SIMILARITY_THRESHOLD

        assert 0.8 < SIMILARITY_THRESHOLD < 1.0
        assert "MiniLM" in MODEL_NAME or "minilm" in MODEL_NAME.lower()


class TestFindingToText:
    def test_full_finding(self):
        from CORE.engines.learned_suppression import _finding_to_text

        finding = {
            "canonical_rule_id": "SECURITY-027",
            "message": "SQL injection via string formatting",
            "file": "app/views.py",
            "line": 42,
        }
        text = _finding_to_text(finding)
        assert "SECURITY-027" in text
        assert "SQL injection" in text
        assert "app/views.py" in text
        assert "42" in text

    def test_partial_finding_no_crash(self):
        from CORE.engines.learned_suppression import _finding_to_text

        text = _finding_to_text({})
        assert isinstance(text, str)

    def test_file_path_variant(self):
        from CORE.engines.learned_suppression import _finding_to_text

        finding = {"canonical_rule_id": "SECURITY-001", "file_path": "CORE/main.py", "line_number": 10}
        text = _finding_to_text(finding)
        assert "CORE/main.py" in text

    def test_rule_id_fallback(self):
        from CORE.engines.learned_suppression import _finding_to_text

        finding = {"rule_id": "B608", "message": "raw sql"}
        text = _finding_to_text(finding)
        assert "B608" in text


class TestCosineSimilarity:
    def test_identical_vectors_give_one(self):
        from CORE.engines.learned_suppression import _cosine_similarity

        v = [1.0, 0.5, -0.3, 0.8]
        assert abs(_cosine_similarity(v, v) - 1.0) < 1e-6

    def test_orthogonal_vectors_give_zero(self):
        from CORE.engines.learned_suppression import _cosine_similarity

        a = [1.0, 0.0]
        b = [0.0, 1.0]
        assert abs(_cosine_similarity(a, b)) < 1e-6

    def test_opposite_vectors_give_minus_one(self):
        from CORE.engines.learned_suppression import _cosine_similarity

        a = [1.0, 0.0]
        b = [-1.0, 0.0]
        assert abs(_cosine_similarity(a, b) + 1.0) < 1e-6

    def test_zero_vector_gives_zero(self):
        from CORE.engines.learned_suppression import _cosine_similarity

        assert _cosine_similarity([0.0, 0.0], [1.0, 0.5]) == 0.0

    def test_partial_similarity(self):
        from CORE.engines.learned_suppression import _cosine_similarity

        a = [1.0, 1.0]
        b = [1.0, 0.0]
        sim = _cosine_similarity(a, b)
        assert 0.0 < sim < 1.0


class TestEmbedText:
    @pytest.fixture(autouse=True)
    def mock_model(self):
        """Mock sentence-transformers so tests don't need the 80MB model."""
        import numpy as np

        mock_st = MagicMock()
        mock_st.encode.return_value = np.array([0.1, 0.2, 0.3, 0.4])
        with patch("CORE.engines.learned_suppression._get_model", return_value=mock_st):
            yield mock_st

    def test_embed_returns_list_of_floats(self):
        from CORE.engines.learned_suppression import LearnedSuppressionEngine

        eng = LearnedSuppressionEngine()
        vec = eng.embed_text("some finding text")
        assert isinstance(vec, list)
        assert all(isinstance(x, float) for x in vec)

    def test_embed_json_serialisable(self):
        from CORE.engines.learned_suppression import LearnedSuppressionEngine

        eng = LearnedSuppressionEngine()
        vec = eng.embed_text("test")
        assert json.dumps(vec)  # must not raise


class TestSuppressGracefulDegradation:
    def test_empty_db_returns_all_findings(self):
        from CORE.engines.learned_suppression import LearnedSuppressionEngine

        db = MagicMock()
        db.get_all_finding_embeddings.return_value = []
        findings = [{"canonical_rule_id": "SECURITY-027", "message": "sqli", "file": "a.py", "line": 1}]
        kept, suppressed = LearnedSuppressionEngine().suppress(findings, db)
        assert kept == findings
        assert suppressed == 0

    def test_db_exception_returns_all_findings(self):
        from CORE.engines.learned_suppression import LearnedSuppressionEngine

        db = MagicMock()
        db.get_all_finding_embeddings.side_effect = Exception("DB offline")
        findings = [{"canonical_rule_id": "SECURITY-001", "message": "eval", "file": "b.py", "line": 5}]
        kept, suppressed = LearnedSuppressionEngine().suppress(findings, db)
        assert len(kept) == 1
        assert suppressed == 0

    def test_corrupt_embedding_json_skipped(self):
        from CORE.engines.learned_suppression import LearnedSuppressionEngine

        db = MagicMock()
        db.get_all_finding_embeddings.return_value = [
            {"rule_id": "SECURITY-027", "embedding_json": "not-json"},
        ]
        findings = [{"canonical_rule_id": "SECURITY-027", "message": "sqli", "file": "c.py", "line": 3}]
        # Should not raise, just return findings unchanged
        kept, suppressed = LearnedSuppressionEngine().suppress(findings, db)
        assert len(kept) == 1


class TestSuppressSemanticMatching:
    def _make_vec(self, val: float) -> list[float]:
        return [val, 0.0, 0.0]

    def _vec_json(self, val: float) -> str:
        return json.dumps(self._make_vec(val))

    def test_high_similarity_zeroes_confidence(self):
        from CORE.engines.learned_suppression import LearnedSuppressionEngine

        eng = LearnedSuppressionEngine(threshold=0.90)
        db = MagicMock()
        db.get_all_finding_embeddings.return_value = [
            {"rule_id": "SECURITY-027", "embedding_json": self._vec_json(1.0)},
        ]
        finding = {
            "canonical_rule_id": "SECURITY-027",
            "message": "sqli",
            "file": "a.py",
            "line": 1,
            "confidence_score": 80,
        }
        with patch.object(eng, "embed_text", return_value=self._make_vec(1.0)):
            kept, suppressed = eng.suppress([finding], db)
        assert suppressed == 1
        assert kept[0]["confidence_score"] == 0
        assert kept[0]["suppressed_by_embedding"] is True
        assert "cosine" in kept[0]["suppression_reason"].lower()

    def test_low_similarity_does_not_suppress(self):
        from CORE.engines.learned_suppression import LearnedSuppressionEngine

        eng = LearnedSuppressionEngine(threshold=0.90)
        db = MagicMock()
        # orthogonal vector → similarity = 0
        db.get_all_finding_embeddings.return_value = [
            {"rule_id": "SECURITY-027", "embedding_json": json.dumps([0.0, 1.0, 0.0])},
        ]
        finding = {
            "canonical_rule_id": "SECURITY-027",
            "message": "different",
            "file": "b.py",
            "line": 2,
            "confidence_score": 75,
        }
        with patch.object(eng, "embed_text", return_value=[1.0, 0.0, 0.0]):
            kept, suppressed = eng.suppress([finding], db)
        assert suppressed == 0
        assert kept[0]["confidence_score"] == 75

    def test_different_rule_not_compared(self):
        from CORE.engines.learned_suppression import LearnedSuppressionEngine

        eng = LearnedSuppressionEngine(threshold=0.90)
        db = MagicMock()
        # embedding for SECURITY-001 (identical vector)
        db.get_all_finding_embeddings.return_value = [
            {"rule_id": "SECURITY-001", "embedding_json": self._vec_json(1.0)},
        ]
        # finding is SECURITY-027 — different rule, must NOT be suppressed
        finding = {"canonical_rule_id": "SECURITY-027", "message": "sqli", "file": "a.py", "line": 1}
        with patch.object(eng, "embed_text", return_value=self._make_vec(1.0)):
            kept, suppressed = eng.suppress([finding], db)
        assert suppressed == 0

    def test_multiple_findings_mixed_result(self):
        from CORE.engines.learned_suppression import LearnedSuppressionEngine

        eng = LearnedSuppressionEngine(threshold=0.90)
        db = MagicMock()
        db.get_all_finding_embeddings.return_value = [
            {"rule_id": "SECURITY-027", "embedding_json": self._vec_json(1.0)},
        ]
        findings = [
            {"canonical_rule_id": "SECURITY-027", "message": "sqli", "file": "a.py", "line": 1},  # similar
            {"canonical_rule_id": "SECURITY-001", "message": "eval", "file": "b.py", "line": 5},  # different rule
        ]

        def fake_embed(text):
            return self._make_vec(1.0)

        with patch.object(eng, "embed_text", side_effect=fake_embed):
            kept, suppressed = eng.suppress(findings, db)
        assert suppressed == 1
        assert len(kept) == 2  # findings are kept but confidence zeroed


class TestStoreDismissed:
    def test_missing_finding_returns_false(self):
        from CORE.engines.learned_suppression import LearnedSuppressionEngine

        db = MagicMock()
        db.execute.return_value = []  # no finding found
        result = LearnedSuppressionEngine().store_dismissed(9999, db)
        assert result is False

    def test_success_stores_embedding(self):
        import numpy as np

        from CORE.engines.learned_suppression import LearnedSuppressionEngine

        db = MagicMock()
        db.execute.return_value = [{"canonical_rule_id": "SECURITY-027", "file_path": "views.py", "message": "sqli"}]
        mock_model = MagicMock()
        mock_model.encode.return_value = np.array([0.1, 0.2, 0.3])
        with patch("CORE.engines.learned_suppression._get_model", return_value=mock_model):
            result = LearnedSuppressionEngine().store_dismissed(1, db)
        assert result is True
        db.insert_finding_embedding.assert_called_once()

    def test_db_exception_returns_false(self):
        from CORE.engines.learned_suppression import LearnedSuppressionEngine

        db = MagicMock()
        db.execute.side_effect = Exception("DB error")
        result = LearnedSuppressionEngine().store_dismissed(1, db)
        assert result is False


class TestIsAvailable:
    def test_returns_bool(self):
        from CORE.engines.learned_suppression import LearnedSuppressionEngine

        result = LearnedSuppressionEngine().is_available()
        assert isinstance(result, bool)


class TestDatabaseMethods:
    def test_insert_and_get_embedding(self):
        """Unit-tests the DB method signatures — does not connect to a real DB."""
        from DATABASE.database import Database

        assert hasattr(Database, "insert_finding_embedding")
        assert hasattr(Database, "get_all_finding_embeddings")
        assert hasattr(Database, "get_finding_embeddings_by_rule")
        assert hasattr(Database, "delete_finding_embedding")

    def test_insert_signature(self):
        import inspect

        from DATABASE.database import Database

        sig = inspect.signature(Database.insert_finding_embedding)
        params = list(sig.parameters.keys())
        assert "rule_id" in params
        assert "embedding_json" in params
        assert "code_context" in params
        assert "finding_id" in params


class TestAlembicMigration:
    def test_migration_file_exists(self):
        from pathlib import Path

        root = Path(__file__).parent.parent
        migrations = list((root / "alembic" / "versions").glob("*_finding_embeddings*"))
        assert migrations, "Migration 0004 for finding_embeddings not found"

    def test_migration_has_correct_revision(self):
        from pathlib import Path

        root = Path(__file__).parent.parent
        migration = next((root / "alembic" / "versions").glob("*_finding_embeddings*"))
        content = migration.read_text()
        assert 'revision: str = "0004"' in content
        assert "down_revision" in content and '"0003"' in content
        assert "finding_embeddings" in content


class TestPipelineIntegration:
    def test_learned_suppression_wired_into_main_pipeline(self):
        """Verify main.py imports LearnedSuppressionEngine in both Python and JS pipelines."""
        from pathlib import Path

        main_src = (Path(__file__).parent.parent / "CORE" / "main.py").read_text()
        occurrences = main_src.count("LearnedSuppressionEngine")
        assert occurrences >= 2, f"Expected ≥2 LearnedSuppressionEngine calls in main.py, got {occurrences}"

    def test_triage_memory_calls_embedding_on_fp(self):
        """triage_memory.py must call LearnedSuppressionEngine().store_dismissed after learning an FP rule."""
        from pathlib import Path

        src = (Path(__file__).parent.parent / "CORE" / "engines" / "triage_memory.py").read_text()
        assert "LearnedSuppressionEngine" in src
        assert "store_dismissed" in src

    def test_suppress_returns_tuple(self):
        from CORE.engines.learned_suppression import LearnedSuppressionEngine

        db = MagicMock()
        db.get_all_finding_embeddings.return_value = []
        result = LearnedSuppressionEngine().suppress([], db)
        assert isinstance(result, tuple)
        assert len(result) == 2
