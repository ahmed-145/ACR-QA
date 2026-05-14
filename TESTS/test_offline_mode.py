"""Tests for Phase 2 — Offline Mode (Ollama provider, OSV offline, egress guard, ACRQA_MODE)."""

from __future__ import annotations

import json
import os
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

# ---------------------------------------------------------------------------
# OllamaClient unit tests
# ---------------------------------------------------------------------------


class TestOllamaClient:
    def test_default_model_from_env(self, monkeypatch):
        monkeypatch.setenv("ACRQA_LLM_MODEL", "llama3.2:3b")
        from CORE.engines.ollama_provider import ollama_model

        assert ollama_model() == "llama3.2:3b"

    def test_default_model_fallback(self, monkeypatch):
        monkeypatch.delenv("ACRQA_LLM_MODEL", raising=False)
        from CORE.engines.ollama_provider import ollama_model

        assert ollama_model() == "qwen2.5-coder:1.5b"

    def test_model_fast_env(self, monkeypatch):
        monkeypatch.setenv("ACRQA_LLM_MODEL_FAST", "llama3.2:1b")
        from CORE.engines.ollama_provider import ollama_model_fast

        assert ollama_model_fast() == "llama3.2:1b"

    def test_model_fast_falls_back_to_model(self, monkeypatch):
        monkeypatch.delenv("ACRQA_LLM_MODEL_FAST", raising=False)
        monkeypatch.setenv("ACRQA_LLM_MODEL", "qwen2.5-coder:7b")
        from CORE.engines.ollama_provider import ollama_model_fast

        assert ollama_model_fast() == "qwen2.5-coder:7b"

    def test_ollama_base_url_env(self, monkeypatch):
        monkeypatch.setenv("OLLAMA_BASE_URL", "http://gpu-server:11434")
        from CORE.engines.ollama_provider import _ollama_base

        assert _ollama_base() == "http://gpu-server:11434"

    def test_ollama_chat_url(self, monkeypatch):
        monkeypatch.setenv("OLLAMA_BASE_URL", "http://localhost:11434")
        from CORE.engines.ollama_provider import ollama_chat_url

        assert ollama_chat_url() == "http://localhost:11434/v1/chat/completions"

    def test_ollama_client_create_returns_completion(self):
        import importlib

        from CORE.engines import ollama_provider

        importlib.reload(ollama_provider)
        mock_resp = MagicMock()
        mock_resp.json.return_value = {
            "choices": [{"message": {"content": "  This is eval abuse.  "}}],
            "usage": {"total_tokens": 42},
        }
        mock_resp.raise_for_status = MagicMock()

        with patch("httpx.Client") as mock_client_cls:
            mock_client = MagicMock()
            mock_client.__enter__ = MagicMock(return_value=mock_client)
            mock_client.__exit__ = MagicMock(return_value=False)
            mock_client.post.return_value = mock_resp
            mock_client_cls.return_value = mock_client

            client = ollama_provider.OllamaClient()
            result = client.chat.completions.create(
                messages=[{"role": "user", "content": "explain this"}],
                model="qwen2.5-coder:1.5b",
            )

        assert result.choices[0].message.content == "This is eval abuse."
        assert result.usage.total_tokens == 42

    def test_ollama_completion_choices(self):
        from CORE.engines.ollama_provider import _OllamaCompletion

        c = _OllamaCompletion("hello", 10)
        assert c.choices[0].message.content == "hello"
        assert c.usage.total_tokens == 10

    def test_ollama_client_is_available_false_when_no_server(self, monkeypatch):
        monkeypatch.setenv("OLLAMA_BASE_URL", "http://127.0.0.1:19999")
        import importlib

        from CORE.engines import ollama_provider

        importlib.reload(ollama_provider)
        client = ollama_provider.OllamaClient()
        assert client.is_available() is False


# ---------------------------------------------------------------------------
# KeyPool ollama + none dispatch
# ---------------------------------------------------------------------------


class TestKeyPoolOllamaDispatch:
    def test_keypool_ollama_provider(self, monkeypatch):
        monkeypatch.setenv("ACRQA_LLM_PROVIDER", "ollama")
        monkeypatch.setenv("ACRQA_LLM_MODEL", "qwen2.5-coder:1.5b")

        from CORE.engines.explainer import KeyPool

        pool = KeyPool()
        assert pool.provider == "ollama"
        assert pool.has_keys

    def test_keypool_none_provider(self, monkeypatch):
        monkeypatch.setenv("ACRQA_LLM_PROVIDER", "none")

        from CORE.engines.explainer import KeyPool

        pool = KeyPool()
        assert not pool.has_keys
        assert pool.pool_size == 0

    def test_keypool_none_raises_on_next_client(self, monkeypatch):
        monkeypatch.setenv("ACRQA_LLM_PROVIDER", "none")

        from CORE.engines.explainer import KeyPool

        pool = KeyPool()
        with pytest.raises(RuntimeError, match="No LLM provider"):
            pool.next_client()

    def test_keypool_provider_property(self, monkeypatch):
        monkeypatch.setenv("ACRQA_LLM_PROVIDER", "groq")
        monkeypatch.setenv("GROQ_API_KEY", "test-key")

        from CORE.engines.explainer import KeyPool

        pool = KeyPool()
        assert pool.provider == "groq"


# ---------------------------------------------------------------------------
# OSV Offline Reader
# ---------------------------------------------------------------------------


class TestOsvOfflineReader:
    def _make_advisory(self, tmp_path: Path, osv_id: str, pkg: str) -> None:
        adv = {
            "id": osv_id,
            "affected": [
                {
                    "package": {"name": pkg, "ecosystem": "PyPI"},
                    "versions": ["1.0.0", "1.1.0"],
                    "ranges": [{"type": "ECOSYSTEM", "events": [{"introduced": "0"}, {"fixed": "1.2.0"}]}],
                }
            ],
        }
        (tmp_path / f"{osv_id}.json").write_text(json.dumps(adv))

    def test_empty_dir_returns_empty(self, tmp_path):
        from CORE.engines.osv_offline import OsvOfflineReader

        reader = OsvOfflineReader(snapshot_dir=tmp_path)
        assert reader.query("requests") == []

    def test_missing_dir_returns_empty(self, tmp_path):
        from CORE.engines.osv_offline import OsvOfflineReader

        missing = tmp_path / "no-such-dir"
        reader = OsvOfflineReader(snapshot_dir=missing)
        assert reader.query("flask") == []

    def test_query_known_package(self, tmp_path):
        self._make_advisory(tmp_path, "GHSA-0001-test-xxxx", "requests")
        from CORE.engines.osv_offline import OsvOfflineReader

        reader = OsvOfflineReader(snapshot_dir=tmp_path)
        results = reader.query("requests")
        assert len(results) == 1
        assert results[0]["id"] == "GHSA-0001-test-xxxx"

    def test_query_unknown_package(self, tmp_path):
        self._make_advisory(tmp_path, "GHSA-0002-test-xxxx", "requests")
        from CORE.engines.osv_offline import OsvOfflineReader

        reader = OsvOfflineReader(snapshot_dir=tmp_path)
        assert reader.query("flask") == []

    def test_query_case_insensitive(self, tmp_path):
        self._make_advisory(tmp_path, "GHSA-0003-test-xxxx", "Flask")
        from CORE.engines.osv_offline import OsvOfflineReader

        reader = OsvOfflineReader(snapshot_dir=tmp_path)
        assert len(reader.query("flask")) == 1

    def test_is_available_true(self, tmp_path):
        self._make_advisory(tmp_path, "GHSA-0004-test-xxxx", "django")
        from CORE.engines.osv_offline import OsvOfflineReader

        reader = OsvOfflineReader(snapshot_dir=tmp_path)
        assert reader.is_available is True

    def test_is_available_false_empty_dir(self, tmp_path):
        from CORE.engines.osv_offline import OsvOfflineReader

        reader = OsvOfflineReader(snapshot_dir=tmp_path)
        assert reader.is_available is False

    def test_advisory_count(self, tmp_path):
        self._make_advisory(tmp_path, "GHSA-0005-test-xxxx", "requests")
        self._make_advisory(tmp_path, "GHSA-0006-test-xxxx", "flask")
        from CORE.engines.osv_offline import OsvOfflineReader

        reader = OsvOfflineReader(snapshot_dir=tmp_path)
        assert reader.advisory_count >= 2

    def test_index_cached_after_first_build(self, tmp_path):
        self._make_advisory(tmp_path, "GHSA-0007-test-xxxx", "requests")
        from CORE.engines.osv_offline import OsvOfflineReader

        reader = OsvOfflineReader(snapshot_dir=tmp_path)
        reader.query("requests")  # builds index
        idx1 = id(reader._index)
        reader.query("requests")  # re-uses index
        assert id(reader._index) == idx1

    def test_version_filter(self, tmp_path):
        self._make_advisory(tmp_path, "GHSA-0008-test-xxxx", "requests")
        from CORE.engines.osv_offline import OsvOfflineReader

        reader = OsvOfflineReader(snapshot_dir=tmp_path)
        assert len(reader.query("requests", version="1.0.0")) == 1
        # version not in explicit list but range says "0" introduced, no fixed
        # our conservative impl returns True for (introduced="0", fixed=None) — but advisory has fixed="1.2.0"
        # version "2.0.0" is NOT in the versions list so filtered out
        assert len(reader.query("requests", version="2.0.0")) == 0

    def test_broken_json_skipped(self, tmp_path):
        (tmp_path / "bad.json").write_text("{not valid json")
        from CORE.engines.osv_offline import OsvOfflineReader

        reader = OsvOfflineReader(snapshot_dir=tmp_path)
        result = reader.query("anything")
        assert result == []


# ---------------------------------------------------------------------------
# Egress Guard
# ---------------------------------------------------------------------------


class TestEgressGuard:
    def test_install_and_is_installed(self):
        from CORE.utils.egress_guard import install, is_installed, uninstall

        uninstall()
        assert not is_installed()
        install()
        assert is_installed()
        uninstall()
        assert not is_installed()

    def test_uninstall_idempotent(self):
        from CORE.utils.egress_guard import uninstall

        uninstall()
        uninstall()  # should not raise

    def test_install_idempotent(self):
        from CORE.utils.egress_guard import install, uninstall

        uninstall()
        install()
        install()  # second call is no-op
        uninstall()

    def test_maybe_install_offline_mode(self, monkeypatch):
        monkeypatch.setenv("ACRQA_MODE", "offline")
        from CORE.utils import egress_guard

        egress_guard._INSTALLED = False
        egress_guard.maybe_install()
        assert egress_guard.is_installed()
        egress_guard.uninstall()

    def test_maybe_install_cloud_mode_does_not_block(self, monkeypatch):
        monkeypatch.setenv("ACRQA_MODE", "cloud")
        from CORE.utils import egress_guard

        egress_guard._INSTALLED = False
        egress_guard.maybe_install()
        assert not egress_guard.is_installed()

    def test_maybe_install_acrqa_offline_flag(self, monkeypatch):
        monkeypatch.delenv("ACRQA_MODE", raising=False)
        monkeypatch.setenv("ACRQA_OFFLINE", "1")
        from CORE.utils import egress_guard

        egress_guard._INSTALLED = False
        egress_guard.maybe_install()
        assert egress_guard.is_installed()
        egress_guard.uninstall()


# ---------------------------------------------------------------------------
# ACRQA_MODE knob
# ---------------------------------------------------------------------------


class TestAcrqaMode:
    def test_offline_mode_sets_provider(self, monkeypatch):
        monkeypatch.setenv("ACRQA_MODE", "offline")
        monkeypatch.delenv("ACRQA_LLM_PROVIDER", raising=False)

        from CORE.main import _apply_acrqa_mode
        from CORE.utils import egress_guard

        egress_guard._INSTALLED = False
        _apply_acrqa_mode()
        assert os.environ.get("ACRQA_LLM_PROVIDER") == "ollama"
        egress_guard.uninstall()

    def test_hybrid_mode_sets_groq(self, monkeypatch):
        monkeypatch.setenv("ACRQA_MODE", "hybrid")
        monkeypatch.delenv("ACRQA_LLM_PROVIDER", raising=False)

        from CORE.main import _apply_acrqa_mode

        _apply_acrqa_mode()
        assert os.environ.get("ACRQA_LLM_PROVIDER") == "groq"

    def test_cloud_mode_does_not_override_provider(self, monkeypatch):
        monkeypatch.setenv("ACRQA_MODE", "cloud")
        monkeypatch.setenv("ACRQA_LLM_PROVIDER", "agentrouter")

        from CORE.main import _apply_acrqa_mode

        _apply_acrqa_mode()
        assert os.environ.get("ACRQA_LLM_PROVIDER") == "agentrouter"

    def test_offline_does_not_override_explicit_provider(self, monkeypatch):
        monkeypatch.setenv("ACRQA_MODE", "offline")
        monkeypatch.setenv("ACRQA_LLM_PROVIDER", "none")

        from CORE.main import _apply_acrqa_mode
        from CORE.utils import egress_guard

        egress_guard._INSTALLED = False
        _apply_acrqa_mode()
        # setdefault should not override the explicitly-set value
        assert os.environ.get("ACRQA_LLM_PROVIDER") == "none"
        egress_guard.uninstall()
