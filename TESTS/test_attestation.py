"""
Tests for CORE/engines/attestation.py — Feature 13: Provenance Attestation Engine.

All DB interactions are mocked in unit tests.
"""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

# ---------------------------------------------------------------------------
# Import
# ---------------------------------------------------------------------------


class TestImport:
    def test_module_importable(self):
        from CORE.engines import attestation  # noqa: F401

    def test_engine_importable(self):
        from CORE.engines.attestation import AttestationEngine

        assert AttestationEngine

    def test_helpers_importable(self):
        from CORE.engines.attestation import (
            build_attestation,
            build_predicate,
            load_bundle_from_db,
        )

        assert build_attestation
        assert build_predicate
        assert load_bundle_from_db

    def test_constants_present(self):
        from CORE.engines.attestation import ATTESTATION_VERSION, PREDICATE_TYPE

        assert PREDICATE_TYPE == "https://acrqa.io/scan/v1"
        assert ATTESTATION_VERSION == "1"


# ---------------------------------------------------------------------------
# build_predicate
# ---------------------------------------------------------------------------


class TestBuildPredicate:
    def _scan_result(self, **kw):
        return {
            "repo_name": "test-repo",
            "commit_sha": "abc123",
            "total_findings": 5,
            "high_count": 2,
            "medium_count": 2,
            "low_count": 1,
            "reachability_enabled": True,
            "verified_exploitable": 1,
            **kw,
        }

    def test_returns_dict(self):
        from CORE.engines.attestation import build_predicate

        p = build_predicate(42, self._scan_result())
        assert isinstance(p, dict)

    def test_has_required_keys(self):
        from CORE.engines.attestation import build_predicate

        p = build_predicate(42, self._scan_result())
        for key in ("run_id", "repo_name", "findings_count", "high_count", "scan_timestamp", "acrqa_version"):
            assert key in p, f"Missing key: {key}"

    def test_run_id_is_string(self):
        from CORE.engines.attestation import build_predicate

        p = build_predicate(42, self._scan_result())
        assert p["run_id"] == "42"

    def test_counts_match_scan_result(self):
        from CORE.engines.attestation import build_predicate

        p = build_predicate(1, self._scan_result(total_findings=10, high_count=3))
        assert p["findings_count"] == 10
        assert p["high_count"] == 3

    def test_missing_fields_default_safely(self):
        from CORE.engines.attestation import build_predicate

        p = build_predicate(1, {})
        assert p["findings_count"] == 0
        assert p["repo_name"] == ""


# ---------------------------------------------------------------------------
# build_attestation
# ---------------------------------------------------------------------------


class TestBuildAttestation:
    def test_envelope_structure(self):
        from CORE.engines.attestation import build_attestation

        a = build_attestation(1, {"repo_name": "myrepo", "commit_sha": "deadbeef"})
        assert a["predicateType"] == "https://acrqa.io/scan/v1"
        assert "subject" in a
        assert "predicate" in a

    def test_subject_has_digest(self):
        from CORE.engines.attestation import build_attestation

        a = build_attestation(1, {"commit_sha": "abc123"})
        assert a["subject"]["digest"]["sha1"] == "abc123"

    def test_predicate_is_dict(self):
        from CORE.engines.attestation import build_attestation

        a = build_attestation(1, {})
        assert isinstance(a["predicate"], dict)


# ---------------------------------------------------------------------------
# AttestationEngine — key management
# ---------------------------------------------------------------------------


class TestKeyManagement:
    def test_engine_creates_without_env_key(self):
        from CORE.engines.attestation import AttestationEngine

        with patch.dict("os.environ", {}, clear=False):
            eng = AttestationEngine()
        assert eng is not None

    def test_engine_loads_env_key(self):
        from cryptography.hazmat.primitives import serialization
        from cryptography.hazmat.primitives.asymmetric import ec

        from CORE.engines.attestation import AttestationEngine

        key = ec.generate_private_key(ec.SECP256R1())
        pem = key.private_bytes(
            serialization.Encoding.PEM,
            serialization.PrivateFormat.PKCS8,
            serialization.NoEncryption(),
        ).decode()

        with patch.dict("os.environ", {"ACRQA_SIGNING_KEY": pem}):
            eng = AttestationEngine()
        assert eng is not None

    def test_public_key_pem_is_valid_pem(self):
        from CORE.engines.attestation import AttestationEngine

        eng = AttestationEngine()
        pem = eng.public_key_pem()
        assert pem.startswith("-----BEGIN PUBLIC KEY-----")

    def test_key_id_is_16_hex_chars(self):
        from CORE.engines.attestation import AttestationEngine

        eng = AttestationEngine()
        kid = eng._kid
        assert len(kid) == 16
        assert all(c in "0123456789abcdef" for c in kid)


# ---------------------------------------------------------------------------
# AttestationEngine.sign
# ---------------------------------------------------------------------------


class TestSign:
    def _engine(self):
        from CORE.engines.attestation import AttestationEngine

        return AttestationEngine()

    def _attestation(self):
        from CORE.engines.attestation import build_attestation

        return build_attestation(1, {"repo_name": "test", "total_findings": 3})

    def test_sign_returns_bundle(self):
        eng = self._engine()
        bundle = eng.sign(self._attestation())
        assert "attestation" in bundle
        assert "signatures" in bundle

    def test_bundle_has_ecdsa_signature(self):
        eng = self._engine()
        bundle = eng.sign(self._attestation())
        algorithms = [s["algorithm"] for s in bundle["signatures"]]
        assert "ECDSA-P256" in algorithms

    def test_ecdsa_signature_is_hex(self):
        eng = self._engine()
        bundle = eng.sign(self._attestation())
        sig = next(s for s in bundle["signatures"] if s["algorithm"] == "ECDSA-P256")
        assert all(c in "0123456789abcdef" for c in sig["signature"])

    def test_ecdsa_key_id_present(self):
        eng = self._engine()
        bundle = eng.sign(self._attestation())
        sig = next(s for s in bundle["signatures"] if s["algorithm"] == "ECDSA-P256")
        assert sig["key_id"] == eng._kid

    def test_dilithium3_included_when_available(self):
        eng = self._engine()
        bundle = eng.sign(self._attestation())
        algorithms = [s["algorithm"] for s in bundle["signatures"]]
        # dilithium-py is installed in this environment
        assert "Dilithium3" in algorithms

    def test_dilithium3_graceful_degradation(self):
        eng = self._engine()
        with patch("CORE.engines.attestation.AttestationEngine._sign_dilithium3", return_value=None):
            bundle = eng.sign(self._attestation())
        assert len(bundle["signatures"]) == 1
        assert bundle["signatures"][0]["algorithm"] == "ECDSA-P256"

    def test_attestation_preserved_in_bundle(self):
        eng = self._engine()
        attest = self._attestation()
        bundle = eng.sign(attest)
        assert bundle["attestation"] == attest


# ---------------------------------------------------------------------------
# AttestationEngine.verify
# ---------------------------------------------------------------------------


class TestVerify:
    def _signed_bundle(self):
        from CORE.engines.attestation import AttestationEngine, build_attestation

        eng = AttestationEngine()
        attest = build_attestation(1, {"repo_name": "test"})
        return eng, eng.sign(attest)

    def test_valid_signature_returns_true(self):
        eng, bundle = self._signed_bundle()
        assert eng.verify(bundle) is True

    def test_tampered_payload_returns_false(self):
        eng, bundle = self._signed_bundle()
        bundle["attestation"]["predicate"]["findings_count"] = 9999
        assert eng.verify(bundle) is False

    def test_wrong_signature_returns_false(self):
        eng, bundle = self._signed_bundle()
        bundle["signatures"][0]["signature"] = "deadbeef" * 8
        assert eng.verify(bundle) is False

    def test_no_ecdsa_sig_returns_false(self):
        eng, bundle = self._signed_bundle()
        bundle["signatures"] = [s for s in bundle["signatures"] if s["algorithm"] != "ECDSA-P256"]
        assert eng.verify(bundle) is False

    def test_empty_bundle_returns_false(self):
        from CORE.engines.attestation import AttestationEngine

        eng = AttestationEngine()
        assert eng.verify({}) is False


# ---------------------------------------------------------------------------
# AttestationEngine.attest_scan
# ---------------------------------------------------------------------------


class TestAttestScan:
    def _make_db(self):
        db = MagicMock()
        db.store_attestation.return_value = 1
        return db

    def test_returns_bundle_dict(self):
        from CORE.engines.attestation import AttestationEngine

        eng = AttestationEngine()
        db = self._make_db()
        result = eng.attest_scan(42, {"repo_name": "test", "total_findings": 5}, db)
        assert isinstance(result, dict)
        assert "attestation" in result

    def test_calls_store_attestation(self):
        from CORE.engines.attestation import AttestationEngine

        eng = AttestationEngine()
        db = self._make_db()
        eng.attest_scan(42, {"repo_name": "test"}, db)
        db.store_attestation.assert_called_once()

    def test_returns_none_on_db_failure(self):
        from CORE.engines.attestation import AttestationEngine

        eng = AttestationEngine()
        db = MagicMock()
        db.store_attestation.side_effect = RuntimeError("DB down")
        result = eng.attest_scan(42, {}, db)
        assert result is None

    def test_ecdsa_stored_as_hex_in_db(self):
        from CORE.engines.attestation import AttestationEngine

        eng = AttestationEngine()
        db = self._make_db()
        eng.attest_scan(42, {}, db)
        call_kwargs = db.store_attestation.call_args
        sig = call_kwargs[1]["signature"] if call_kwargs[1] else call_kwargs[0][2]
        assert all(c in "0123456789abcdef" for c in sig)


# ---------------------------------------------------------------------------
# load_bundle_from_db
# ---------------------------------------------------------------------------


class TestLoadBundleFromDb:
    def test_returns_dict_when_found(self):
        from CORE.engines.attestation import AttestationEngine, build_attestation, load_bundle_from_db

        eng = AttestationEngine()
        attest = build_attestation(1, {})
        bundle = eng.sign(attest)
        bundle_json = json.dumps(bundle)

        db = MagicMock()
        db.get_attestation.return_value = {"attestation_json": bundle_json}

        result = load_bundle_from_db(1, db)
        assert result is not None
        assert "signatures" in result

    def test_returns_none_when_not_found(self):
        from CORE.engines.attestation import load_bundle_from_db

        db = MagicMock()
        db.get_attestation.return_value = None
        assert load_bundle_from_db(1, db) is None

    def test_returns_none_on_corrupt_json(self):
        from CORE.engines.attestation import load_bundle_from_db

        db = MagicMock()
        db.get_attestation.return_value = {"attestation_json": "not-json{{"}
        assert load_bundle_from_db(1, db) is None


# ---------------------------------------------------------------------------
# DB methods
# ---------------------------------------------------------------------------


class TestDBMethods:
    def test_store_attestation_method_exists(self):
        from DATABASE.database import Database

        assert callable(getattr(Database, "store_attestation", None))

    def test_get_attestation_method_exists(self):
        from DATABASE.database import Database

        assert callable(getattr(Database, "get_attestation", None))

    def test_store_attestation_calls_execute(self):
        from DATABASE.database import Database

        db = object.__new__(Database)
        db.execute = MagicMock(return_value=[{"id": 1}])
        result = db.store_attestation(1, '{"ok":true}', "sigdata", "kid123")
        db.execute.assert_called_once()
        assert result == 1

    def test_get_attestation_returns_none_when_empty(self):
        from DATABASE.database import Database

        db = object.__new__(Database)
        db.execute = MagicMock(return_value=[])
        assert db.get_attestation(999) is None


# ---------------------------------------------------------------------------
# Alembic migration 0006
# ---------------------------------------------------------------------------


class TestMigration0006:
    def _migration_path(self):
        return Path(__file__).parent.parent / "alembic" / "versions" / "20260514_0006_attestations.py"

    def _migration_text(self):
        return self._migration_path().read_text()

    def test_migration_file_exists(self):
        assert self._migration_path().exists()

    def test_revision_is_0006(self):
        content = self._migration_text()
        assert 'revision: str = "0006"' in content
        assert 'down_revision: str | None = "0005"' in content

    def test_upgrade_creates_table(self):
        content = self._migration_text()
        assert "scan_attestations" in content
        assert "op.create_table" in content

    def test_downgrade_drops_table(self):
        content = self._migration_text()
        assert "op.drop_table" in content


# ---------------------------------------------------------------------------
# Pipeline integration
# ---------------------------------------------------------------------------


class TestPipelineIntegration:
    def test_attest_scan_wired_into_python_pipeline(self):
        src = (Path(__file__).parent.parent / "CORE" / "main.py").read_text()
        assert "AttestationEngine" in src
        assert src.count("AttestationEngine") >= 2

    def test_fastapi_attestation_endpoint_exists(self):
        src = (Path(__file__).parent.parent / "FRONTEND" / "api" / "routers" / "runs.py").read_text()
        assert "attestation" in src
        assert "get_attestation" in src

    def test_verify_script_exists(self):
        script = Path(__file__).parent.parent / "scripts" / "verify_attestation.py"
        assert script.exists()

    def test_dilithium_in_requirements(self):
        req = (Path(__file__).parent.parent / "requirements.txt").read_text()
        assert "dilithium" in req

    def test_engine_not_crash_without_db(self):
        from CORE.engines.attestation import AttestationEngine, build_attestation

        eng = AttestationEngine()
        attest = build_attestation(1, {"repo_name": "test"})
        bundle = eng.sign(attest)
        assert eng.verify(bundle) is True
