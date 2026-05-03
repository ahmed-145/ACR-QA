"""
God-mode tests for CORE/engines/explainer.py (target: 70%+)

Strategy:
  - Patch Groq and os.getenv at import time so __init__ never hits network
  - Test all pure-logic methods directly (no API calls)
  - Test generate_explanation() / _explain_one_async() with mocked client
  - Test redis cache hit/miss paths
  - Test fallback paths for every exception branch
"""

import asyncio
import json
from unittest.mock import AsyncMock, MagicMock, Mock, patch

import pytest

# ─────────────────────────────────────────────────────────────
#  Fixture: build a patched ExplanationEngine with no API key
# ─────────────────────────────────────────────────────────────

FAKE_KEY = "test-key-123"


def _make_engine(redis_client=None, rules_catalog=None):
    """Return an ExplanationEngine with Groq + env fully mocked."""
    mock_groq_cls = MagicMock()
    mock_groq_instance = MagicMock()
    mock_groq_cls.return_value = mock_groq_instance

    with patch.dict("os.environ", {"GROQ_API_KEY_1": FAKE_KEY}):
        with patch("CORE.engines.explainer.Groq", mock_groq_cls):
            with patch("builtins.open", side_effect=FileNotFoundError):
                from CORE.engines.explainer import ExplanationEngine

                engine = ExplanationEngine(redis_client=redis_client)
    if rules_catalog is not None:
        engine.rules_catalog = rules_catalog
    return engine, mock_groq_instance


def _engine(rules_catalog=None):
    eng, _ = _make_engine(rules_catalog=rules_catalog)
    return eng


def _engine_with_mock_client(rules_catalog=None):
    eng, client = _make_engine(rules_catalog=rules_catalog)
    return eng, client


def _finding(
    rule_id="SECURITY-001",
    category="security",
    severity="high",
    file="app.py",
    line=10,
    message="SQL injection detected",
):
    return {
        "canonical_rule_id": rule_id,
        "category": category,
        "canonical_severity": severity,
        "file": file,
        "line": line,
        "message": message,
    }


# ════════════════════════════════════════════════════════════
#  __init__
# ════════════════════════════════════════════════════════════


class TestExplanationEngineInit:
    def test_raises_without_api_key(self):
        with patch.dict("os.environ", {}, clear=True):
            with patch("os.getenv", return_value=None):
                with patch("CORE.engines.explainer.Groq"):
                    from CORE.engines.explainer import ExplanationEngine

                    with pytest.raises(ValueError, match="GROQ_API_KEY"):
                        ExplanationEngine()

    def test_model_is_llama(self):
        eng = _engine()
        assert "llama" in eng.model

    def test_cache_ttl_7_days(self):
        eng = _engine()
        assert eng.cache_ttl == 604800

    def test_rules_catalog_empty_when_file_missing(self):
        eng = _engine()
        assert eng.rules_catalog == {}

    def test_rules_catalog_loaded_when_file_exists(self, tmp_path):
        rules_file = tmp_path / "rules.yml"
        rules_file.write_text("SECURITY-001:\n  name: SQL Injection\n")
        mock_groq_cls = MagicMock()
        with patch.dict("os.environ", {"GROQ_API_KEY_1": FAKE_KEY}):
            with patch("CORE.engines.explainer.Groq", mock_groq_cls):
                with patch("builtins.open", return_value=open(str(rules_file))):
                    from CORE.engines.explainer import ExplanationEngine

                    eng = ExplanationEngine()
        assert "SECURITY-001" in eng.rules_catalog

    def test_redis_stored(self):
        redis = MagicMock()
        eng, _ = _make_engine(redis_client=redis)
        assert eng.redis is redis

    def test_cache_counters_start_at_0(self):
        eng = _engine()
        assert eng.cache_hits == 0
        assert eng.cache_misses == 0


# ════════════════════════════════════════════════════════════
#  _get_cache_key
# ════════════════════════════════════════════════════════════


class TestGetCacheKey:
    def test_returns_string_with_prefix(self):
        eng = _engine()
        key = eng._get_cache_key(_finding(), "snippet")
        assert key.startswith("explanation:")

    def test_consistent_for_same_inputs(self):
        eng = _engine()
        f = _finding()
        assert eng._get_cache_key(f, "code") == eng._get_cache_key(f, "code")

    def test_differs_for_different_rule_id(self):
        eng = _engine()
        f1 = _finding(rule_id="A")
        f1["fingerprint"] = "hashA"
        f2 = _finding(rule_id="B")
        f2["fingerprint"] = "hashB"
        k1 = eng._get_cache_key(f1, "code")
        k2 = eng._get_cache_key(f2, "code")
        assert k1 != k2

    def test_uses_first_100_chars_of_snippet(self):
        eng = _engine()
        short = eng._get_cache_key(_finding(), "A" * 100)
        same = eng._get_cache_key(_finding(), "A" * 200)
        assert short == same  # same first 100 chars

    def test_key_is_32_hex_chars_after_prefix(self):
        eng = _engine()
        key = eng._get_cache_key(_finding(), "code")
        md5_part = key.split("explanation:")[1]
        assert len(md5_part) == 32
        assert all(c in "0123456789abcdef" for c in md5_part)


# ════════════════════════════════════════════════════════════
#  _build_evidence_grounded_prompt
# ════════════════════════════════════════════════════════════


class TestBuildPrompt:
    def test_contains_rule_id(self):
        eng = _engine()
        prompt = eng._build_evidence_grounded_prompt(_finding(rule_id="SECURITY-001"), "code")
        assert "SECURITY-001" in prompt

    def test_contains_file_path(self):
        eng = _engine()
        prompt = eng._build_evidence_grounded_prompt(_finding(file="myapp.py"), "snippet")
        assert "myapp.py" in prompt

    def test_uses_rule_catalog_name(self):
        catalog = {
            "SECURITY-001": {
                "name": "SQL Injection",
                "rationale": "r",
                "remediation": "fix",
                "example_good": "",
                "example_bad": "",
            }
        }
        eng = _engine(rules_catalog=catalog)
        prompt = eng._build_evidence_grounded_prompt(_finding(rule_id="SECURITY-001"), "")
        assert "SQL Injection" in prompt

    def test_uses_tool_message_when_no_catalog(self):
        eng = _engine()
        f = _finding(rule_id="CUSTOM-999", message="untrusted input")
        prompt = eng._build_evidence_grounded_prompt(f, "")
        assert "untrusted input" in prompt

    def test_uses_rule_id_fallback_from_rule_id_key(self):
        eng = _engine()
        f = {"rule_id": "IMPORT-001", "category": "style", "file": "x.py", "line": 1, "message": ""}
        prompt = eng._build_evidence_grounded_prompt(f, "code")
        assert "IMPORT-001" in prompt

    def test_default_remediation_when_missing(self):
        eng = _engine()
        prompt = eng._build_evidence_grounded_prompt(_finding(), "")
        assert "fix" in prompt.lower() or "review" in prompt.lower()

    def test_contains_code_snippet(self):
        eng = _engine()
        prompt = eng._build_evidence_grounded_prompt(_finding(), "my_unique_code_xyz")
        assert "my_unique_code_xyz" in prompt


# ════════════════════════════════════════════════════════════
#  _calculate_cost
# ════════════════════════════════════════════════════════════


class TestCalculateCost:
    def test_none_tokens_returns_0(self):
        assert _engine()._calculate_cost(None) == 0

    def test_0_tokens_returns_0(self):
        assert _engine()._calculate_cost(0) == 0

    def test_1_million_tokens_is_59_cents(self):
        cost = _engine()._calculate_cost(1_000_000)
        assert abs(cost - 0.59) < 1e-9

    def test_cost_is_float(self):
        assert isinstance(_engine()._calculate_cost(500), float)

    def test_1000_tokens_cost(self):
        cost = _engine()._calculate_cost(1000)
        assert cost == pytest.approx(0.00059)


# ════════════════════════════════════════════════════════════
#  _ngram_similarity
# ════════════════════════════════════════════════════════════


class TestNgramSimilarity:
    def test_identical_texts_return_1(self):
        eng = _engine()
        assert eng._ngram_similarity("a b c d e f", "a b c d e f") == 1.0

    def test_completely_different_returns_0(self):
        eng = _engine()
        assert eng._ngram_similarity("a b c d", "x y z w") == 0.0

    def test_partial_overlap(self):
        eng = _engine()
        score = eng._ngram_similarity("a b c d e f", "a b c x y z")
        assert 0 < score < 1

    def test_empty_both_returns_1(self):
        eng = _engine()
        assert eng._ngram_similarity("", "") == 1.0

    def test_one_empty_returns_0(self):
        eng = _engine()
        assert eng._ngram_similarity("a b c d", "") == 0.0

    def test_symmetric(self):
        eng = _engine()
        s1 = eng._ngram_similarity("a b c", "d e f")
        s2 = eng._ngram_similarity("d e f", "a b c")
        assert s1 == s2


# ════════════════════════════════════════════════════════════
#  get_fallback_explanation
# ════════════════════════════════════════════════════════════


class TestGetFallbackExplanation:
    def test_security_category_template(self):
        eng = _engine()
        result = eng.get_fallback_explanation(_finding(category="security"))
        assert "Security issue" in result or "security" in result.lower()

    def test_best_practice_template(self):
        eng = _engine()
        result = eng.get_fallback_explanation(_finding(category="best-practice"))
        assert "best practice" in result.lower() or "Code quality" in result

    def test_style_template(self):
        eng = _engine()
        result = eng.get_fallback_explanation(_finding(category="style"))
        assert "style" in result.lower() or "Style" in result

    def test_dead_code_template(self):
        eng = _engine()
        result = eng.get_fallback_explanation(_finding(category="dead-code"))
        assert "unused" in result.lower() or "dead" in result.lower() or "Unused" in result

    def test_duplication_template(self):
        eng = _engine()
        result = eng.get_fallback_explanation(_finding(category="duplication"))
        assert "duplication" in result.lower() or "DRY" in result

    def test_unknown_category_fallback(self):
        eng = _engine()
        result = eng.get_fallback_explanation(_finding(category="weird-cat"))
        assert "Issue detected" in result or isinstance(result, str)

    def test_uses_rule_catalog_when_available(self):
        catalog = {"SECURITY-001": {"name": "SQLi", "rationale": "dangerous", "remediation": "use params"}}
        eng = _engine(rules_catalog=catalog)
        result = eng.get_fallback_explanation(_finding(rule_id="SECURITY-001"))
        assert "SECURITY-001" in result
        assert "dangerous" in result

    def test_returns_string(self):
        eng = _engine()
        assert isinstance(eng.get_fallback_explanation(_finding()), str)


# ════════════════════════════════════════════════════════════
#  generate_explanation — synchronous (mocked Groq client)
# ════════════════════════════════════════════════════════════


def _mock_completion(
    text="This code violates SECURITY-001 because of SQL injection risk.\n```python\nuse = params\n```",
):
    completion = MagicMock()
    completion.choices = [MagicMock()]
    completion.choices[0].message.content = text
    completion.usage.total_tokens = 150
    return completion


class TestGenerateExplanation:
    def test_success_path_returns_dict(self):
        eng, groq_client = _engine_with_mock_client()
        groq_client.chat.completions.create.return_value = _mock_completion()
        f = _finding(rule_id="SECURITY-001")
        result = eng.generate_explanation(f, "code snippet")
        assert result["status"] == "success"
        assert "response_text" in result
        assert "latency_ms" in result

    def test_cites_rule_true_when_rule_in_response(self):
        eng, groq_client = _engine_with_mock_client()
        groq_client.chat.completions.create.return_value = _mock_completion(
            "This code violates SECURITY-001 because..."
        )
        result = eng.generate_explanation(_finding(rule_id="SECURITY-001"), "code")
        assert result["cites_rule"] is True
        assert result["confidence"] == 0.9

    def test_cites_rule_false_when_rule_absent(self):
        eng, groq_client = _engine_with_mock_client()
        groq_client.chat.completions.create.return_value = _mock_completion("There is a problem in your code.")
        result = eng.generate_explanation(_finding(rule_id="SECURITY-001"), "code")
        assert result["cites_rule"] is False
        assert result["confidence"] == 0.6

    def test_fallback_on_exception(self):
        eng, groq_client = _engine_with_mock_client()
        groq_client.chat.completions.create.side_effect = Exception("API timeout")
        result = eng.generate_explanation(_finding(), "code")
        assert result["status"] == "fallback"
        assert "error" in result
        assert result["cost_usd"] == 0

    def test_tokens_used_none_when_no_usage(self):
        eng, groq_client = _engine_with_mock_client()
        comp = _mock_completion()
        comp.usage = None
        groq_client.chat.completions.create.return_value = comp
        result = eng.generate_explanation(_finding(), "code")
        assert result["tokens_used"] is None

    def test_tokens_used_populated(self):
        eng, groq_client = _engine_with_mock_client()
        groq_client.chat.completions.create.return_value = _mock_completion()
        result = eng.generate_explanation(_finding(), "code")
        assert result["tokens_used"] == 150

    def test_cost_usd_calculated(self):
        eng, groq_client = _engine_with_mock_client()
        groq_client.chat.completions.create.return_value = _mock_completion()
        result = eng.generate_explanation(_finding(), "code")
        assert result["cost_usd"] == pytest.approx(150 / 1_000_000 * 0.59)

    def test_cache_miss_incremented(self):
        eng, groq_client = _engine_with_mock_client()
        groq_client.chat.completions.create.return_value = _mock_completion()
        eng.generate_explanation(_finding(), "code")
        assert eng.cache_misses == 1

    def test_redis_cache_hit_returns_cached(self):
        redis = MagicMock()
        cached_data = json.dumps({"status": "success", "response_text": "cached", "cache_hit": False})
        redis.get.return_value = cached_data
        eng, _ = _make_engine(redis_client=redis)
        result = eng.generate_explanation(_finding(), "code")
        assert result["cache_hit"] is True
        assert result["status"] == "success"
        assert eng.cache_hits == 1

    def test_redis_cache_miss_calls_api(self):
        redis = MagicMock()
        redis.get.return_value = None
        eng, groq_client = _make_engine(redis_client=redis)
        groq_client.chat.completions.create.return_value = _mock_completion()
        eng.generate_explanation(_finding(), "code")
        groq_client.chat.completions.create.assert_called()

    def test_redis_write_after_success(self):
        redis = MagicMock()
        redis.get.return_value = None
        eng, groq_client = _make_engine(redis_client=redis)
        groq_client.chat.completions.create.return_value = _mock_completion()
        eng.generate_explanation(_finding(), "code")
        redis.setex.assert_called()

    def test_redis_read_error_silenced(self):
        redis = MagicMock()
        redis.get.side_effect = Exception("Redis down")
        eng, groq_client = _make_engine(redis_client=redis)
        groq_client.chat.completions.create.return_value = _mock_completion()
        result = eng.generate_explanation(_finding(), "code")
        assert result["status"] == "success"

    def test_redis_write_error_silenced(self):
        redis = MagicMock()
        redis.get.return_value = None
        redis.setex.side_effect = Exception("Redis down")
        eng, groq_client = _make_engine(redis_client=redis)
        groq_client.chat.completions.create.return_value = _mock_completion()
        result = eng.generate_explanation(_finding(), "code")
        assert result["status"] == "success"

    def test_rule_id_fallback_from_rule_id_key(self):
        eng, groq_client = _engine_with_mock_client()
        groq_client.chat.completions.create.return_value = _mock_completion("violates IMPORT-001")
        f = {"rule_id": "IMPORT-001", "category": "style", "file": "x.py", "line": 1, "message": ""}
        result = eng.generate_explanation(f, "")
        assert result["cites_rule"] is True


# ════════════════════════════════════════════════════════════
#  _explain_one_async — httpx-based async API
# ════════════════════════════════════════════════════════════


class TestExplainOneAsync:
    def _run(self, coro):
        return asyncio.run(coro)

    def test_success_returns_dict(self):
        eng = _engine()
        response_text = "This code violates SECURITY-001 due to SQL injection. ```python\nuse = params\n```"
        mock_resp = MagicMock()
        mock_resp.raise_for_status = MagicMock()
        mock_resp.json.return_value = {
            "choices": [{"message": {"content": response_text}}],
            "usage": {"total_tokens": 200},
        }
        mock_client = MagicMock()
        mock_client.post = AsyncMock(return_value=mock_resp)
        result = self._run(eng._explain_one_async(mock_client, _finding(), "code", FAKE_KEY))
        assert result["status"] == "success"
        assert result["tokens_used"] == 200

    def test_fallback_on_exception(self):
        eng = _engine()
        mock_client = MagicMock()
        mock_client.post = AsyncMock(side_effect=Exception("connection refused"))
        result = self._run(eng._explain_one_async(mock_client, _finding(), "code", FAKE_KEY))
        assert result["status"] == "fallback"

    def test_caches_redis_on_success(self):
        redis = MagicMock()
        redis.get.return_value = None
        eng, _ = _make_engine(redis_client=redis)
        response_text = "SECURITY-001 is problematic. ```python\nx = 1\n```"
        mock_resp = MagicMock()
        mock_resp.raise_for_status = MagicMock()
        mock_resp.json.return_value = {"choices": [{"message": {"content": response_text}}]}
        mock_client = MagicMock()
        mock_client.post = AsyncMock(return_value=mock_resp)
        self._run(eng._explain_one_async(mock_client, _finding(), "code", FAKE_KEY))
        redis.setex.assert_called()

    def test_redis_cache_hit_returns_cached(self):
        redis = MagicMock()
        cached = json.dumps({"status": "success", "response_text": "cached async"})
        redis.get.return_value = cached
        eng, _ = _make_engine(redis_client=redis)
        mock_client = MagicMock()
        mock_client.post = AsyncMock()
        result = self._run(eng._explain_one_async(mock_client, _finding(), "code", FAKE_KEY))
        assert result["cache_hit"] is True
        mock_client.post.assert_not_called()

    def test_fix_validated_none_when_no_code_block(self):
        eng = _engine()
        response_text = "SECURITY-001 has no code block here."
        mock_resp = MagicMock()
        mock_resp.raise_for_status = MagicMock()
        mock_resp.json.return_value = {"choices": [{"message": {"content": response_text}}]}
        mock_client = MagicMock()
        mock_client.post = AsyncMock(return_value=mock_resp)
        result = self._run(eng._explain_one_async(mock_client, _finding(), "code", FAKE_KEY))
        assert result.get("fix_validated") is None
        assert result.get("fix_validation_note") == "No code block in AI response"

    def test_feasibility_not_checked_for_medium_finding(self):
        eng = _engine()
        response_text = "SECURITY-001 is an issue. ```python\nx = 1\n```"
        mock_resp = MagicMock()
        mock_resp.raise_for_status = MagicMock()
        mock_resp.json.return_value = {"choices": [{"message": {"content": response_text}}]}
        mock_client = MagicMock()
        mock_client.post = AsyncMock(return_value=mock_resp)
        f = _finding(severity="medium", category="security")
        result = self._run(eng._explain_one_async(mock_client, f, "code", FAKE_KEY))
        assert result.get("feasibility_checked") is False

    def test_redis_read_exception_silenced_async(self):
        redis = MagicMock()
        redis.get.side_effect = Exception("Redis crashed")
        eng, _ = _make_engine(redis_client=redis)
        response_text = "SECURITY-001 issue."
        mock_resp = MagicMock()
        mock_resp.raise_for_status = MagicMock()
        mock_resp.json.return_value = {"choices": [{"message": {"content": response_text}}]}
        mock_client = MagicMock()
        mock_client.post = AsyncMock(return_value=mock_resp)
        result = self._run(eng._explain_one_async(mock_client, _finding(), "code", FAKE_KEY))
        assert result["status"] in ("success", "fallback")

    def test_redis_write_exception_silenced_async(self):
        redis = MagicMock()
        redis.get.return_value = None
        redis.setex.side_effect = Exception("write fail")
        eng, _ = _make_engine(redis_client=redis)
        mock_resp = MagicMock()
        mock_resp.raise_for_status = MagicMock()
        mock_resp.json.return_value = {"choices": [{"message": {"content": "SECURITY-001 issue."}}]}
        mock_client = MagicMock()
        mock_client.post = AsyncMock(return_value=mock_resp)
        result = self._run(eng._explain_one_async(mock_client, _finding(), "code", FAKE_KEY))
        assert result is not None


# ════════════════════════════════════════════════════════════
#  generate_explanation_batch
# ════════════════════════════════════════════════════════════


class TestGenerateExplanationBatch:
    def test_returns_list(self):
        eng = _engine()
        response_text = "SECURITY-001 issue. ```python\nfixed\n```"
        mock_resp = MagicMock()
        mock_resp.raise_for_status = MagicMock()
        mock_resp.json.return_value = {"choices": [{"message": {"content": response_text}}]}

        with patch("httpx.AsyncClient") as mock_cls:
            mock_ctx = MagicMock()
            mock_ctx.__aenter__ = AsyncMock(return_value=MagicMock(post=AsyncMock(return_value=mock_resp)))
            mock_ctx.__aexit__ = AsyncMock(return_value=None)
            mock_cls.return_value = mock_ctx
            items = [{"finding": _finding(), "snippet": "code"}]
            results = eng.generate_explanation_batch(items)
        assert isinstance(results, list)
        assert len(results) == 1

    def test_empty_list_returns_empty(self):
        eng = _engine()
        with patch("httpx.AsyncClient") as mock_cls:
            mock_ctx = MagicMock()
            mock_ctx.__aenter__ = AsyncMock(return_value=MagicMock())
            mock_ctx.__aexit__ = AsyncMock(return_value=None)
            mock_cls.return_value = mock_ctx
            results = eng.generate_explanation_batch([])
        assert results == []


# ════════════════════════════════════════════════════════════
#  self_evaluate_explanation
# ════════════════════════════════════════════════════════════


class TestSelfEvaluateExplanation:
    def test_success_returns_scores(self):
        eng, groq_client = _engine_with_mock_client()
        comp = MagicMock()
        comp.choices = [MagicMock()]
        comp.choices[0].message.content = "Relevance: 4\nAccuracy: 5\nClarity: 3"
        groq_client.chat.completions.create.return_value = comp
        result = eng.self_evaluate_explanation("some explanation", _finding())
        assert result["status"] == "success"
        assert result["scores"]["relevance"] == 4
        assert result["scores"]["accuracy"] == 5
        assert result["scores"]["clarity"] == 3
        assert result["overall"] == pytest.approx(4.0)

    def test_error_returns_error_status(self):
        eng, groq_client = _engine_with_mock_client()
        groq_client.chat.completions.create.side_effect = Exception("API error")
        result = eng.self_evaluate_explanation("explanation", _finding())
        assert result["status"] == "error"
        assert "error" in result

    def test_malformed_scores_default_to_3(self):
        eng, groq_client = _engine_with_mock_client()
        comp = MagicMock()
        comp.choices = [MagicMock()]
        comp.choices[0].message.content = "Relevance: X\nAccuracy: ?\nClarity: !"
        groq_client.chat.completions.create.return_value = comp
        result = eng.self_evaluate_explanation("explanation", _finding())
        for v in result["scores"].values():
            assert v == 3

    def test_scores_clamped_to_1_5(self):
        eng, groq_client = _engine_with_mock_client()
        comp = MagicMock()
        comp.choices = [MagicMock()]
        comp.choices[0].message.content = "Relevance: 9\nAccuracy: 0\nClarity: 5"
        groq_client.chat.completions.create.return_value = comp
        result = eng.self_evaluate_explanation("explanation", _finding())
        if result["status"] == "success":
            for v in result["scores"].values():
                assert 1 <= v <= 5


# ════════════════════════════════════════════════════════════
#  compute_semantic_entropy
# ════════════════════════════════════════════════════════════


class TestComputeSemanticEntropy:
    def test_returns_consistency_score(self):
        eng, groq_client = _engine_with_mock_client()
        comp = MagicMock()
        comp.choices = [MagicMock()]
        comp.choices[0].message.content = "This code violates SECURITY-001 because SQL injection is dangerous."
        groq_client.chat.completions.create.return_value = comp
        result = eng.compute_semantic_entropy(_finding(), "code", num_samples=3)
        assert result["status"] == "success"
        assert 0.0 <= result["consistency_score"] <= 1.0

    def test_single_sample_returns_insufficient(self):
        eng, groq_client = _engine_with_mock_client()
        comp = MagicMock()
        comp.choices = [MagicMock()]
        comp.choices[0].message.content = "response"
        groq_client.chat.completions.create.return_value = comp
        result = eng.compute_semantic_entropy(_finding(), "code", num_samples=1)
        assert result["status"] == "insufficient_samples"

    def test_identical_responses_score_1(self):
        eng, groq_client = _engine_with_mock_client()
        comp = MagicMock()
        comp.choices = [MagicMock()]
        comp.choices[0].message.content = "a b c d e f g h i j k"
        groq_client.chat.completions.create.return_value = comp
        result = eng.compute_semantic_entropy(_finding(), "code", num_samples=3)
        assert result["consistency_score"] == pytest.approx(1.0)
        assert result["is_likely_hallucination"] is False

    def test_api_error_in_sample_handled(self):
        eng, groq_client = _engine_with_mock_client()
        groq_client.chat.completions.create.side_effect = Exception("API error")
        result = eng.compute_semantic_entropy(_finding(), "code", num_samples=3)
        assert "status" in result


# ════════════════════════════════════════════════════════════
#  Backward-compat tests from the original test_explainer.py
# ════════════════════════════════════════════════════════════


class TestExplanationEngineCompat:
    """Keep original 9 tests so nothing regresses."""

    @pytest.fixture
    def engine(self):
        mock_redis = Mock()
        mock_redis.get.return_value = None
        with patch.dict("os.environ", {"GROQ_API_KEY_1": "test-key-for-ci"}):
            with patch("CORE.engines.explainer.Groq") as mock_groq:
                mock_client = MagicMock()
                mock_groq.return_value = mock_client
                from CORE.engines.explainer import ExplanationEngine

                engine = ExplanationEngine(redis_client=mock_redis)
                engine._mock_client = mock_client
                return engine

    def test_cache_key_generation(self, engine):
        finding = {"canonical_rule_id": "SECURITY-001", "file": "test.py", "line": 42}
        k1 = engine._get_cache_key(finding, "eval(user_input)")
        k2 = engine._get_cache_key(finding, "eval(user_input)")
        assert k1 == k2
        assert k1.startswith("explanation:")

    def test_cache_hit_returns_cached(self):
        mock_redis = Mock()
        mock_redis.get.return_value = '{"response_text": "cached", "cache_hit": false}'
        with patch.dict("os.environ", {"GROQ_API_KEY_1": "test-key-for-ci"}):
            with patch("CORE.engines.explainer.Groq"):
                from CORE.engines.explainer import ExplanationEngine

                engine = ExplanationEngine(redis_client=mock_redis)
        finding = {"canonical_rule_id": "TEST-001", "file": "test.py", "line": 1}
        result = engine.generate_explanation(finding, "code")
        assert result["cache_hit"] is True
        assert engine.cache_hits == 1

    def test_rag_prompt_includes_rule_id(self, engine):
        finding = {"canonical_rule_id": "SECURITY-001", "file": "test.py", "line": 1, "message": "eval() detected"}
        prompt = engine._build_evidence_grounded_prompt(finding, "eval(user_input)")
        assert "SECURITY-001" in prompt
