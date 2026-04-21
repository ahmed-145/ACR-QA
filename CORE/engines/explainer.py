"""
Cerebras API Integration for Natural Language Explanations
Evidence-grounded prompt engineering for code quality issues
"""

import asyncio
import hashlib
import json
import os
import time

import httpx
import yaml
from cerebras.cloud.sdk import Cerebras
from dotenv import load_dotenv
from tenacity import retry, stop_after_attempt, wait_exponential

load_dotenv()


class ExplanationEngine:
    def __init__(self, redis_client=None):
        # Initialize Cerebras client
        api_key = os.getenv("CEREBRAS_API_KEY")
        if not api_key:
            raise ValueError("CEREBRAS_API_KEY not found in environment")

        self.client = Cerebras(api_key=api_key)
        self.model = "llama3.1-8b"
        self.temperature = 0.3
        self.max_tokens = 300

        # Redis caching (Phase 2 feature)
        self.redis = redis_client
        self.cache_ttl = 604800  # 7 days in seconds
        self.cache_hits = 0
        self.cache_misses = 0

        # Load rules catalog for RAG
        try:
            with open("config/rules.yml") as f:
                self.rules_catalog = yaml.safe_load(f)
        except FileNotFoundError:
            print("⚠️  Warning: rules.yml not found, using empty catalog")
            self.rules_catalog = {}

    def _get_cache_key(self, finding, code_snippet):
        """Generate cache key from finding characteristics"""
        key_data = (
            f"{finding.get('canonical_rule_id', '')}:"
            f"{finding.get('file', '')}:"
            f"{finding.get('line', 0)}:"
            f"{code_snippet[:100]}"  # First 100 chars of snippet
        )
        hash_key = hashlib.md5(key_data.encode()).hexdigest()
        return f"explanation:{hash_key}"

    def _build_evidence_grounded_prompt(self, finding, code_snippet):
        """
        Construct evidence-grounded prompt using rule definition
        This is the RAG approach that reduces hallucinations
        """
        # Get canonical rule definition
        canonical_id = finding.get("canonical_rule_id", finding.get("rule_id", "UNKNOWN"))
        rule_def = self.rules_catalog.get(canonical_id, {})

        # For unmapped CUSTOM-* rules: use the tool's raw message as the rationale
        # This prevents generic filler like "because it matters" in AI explanations
        tool_message = finding.get("message", "")
        rationale = rule_def.get("rationale") or (
            tool_message if tool_message else "This pattern should be avoided in production code."
        )
        remediation = rule_def.get("remediation") or (
            "Review the flagged code and apply the fix shown in the issue message."
        )
        rule_name = rule_def.get("name") or (canonical_id.replace("CUSTOM-", "").replace("-", " ").title())

        # Build structured prompt with evidence
        prompt = f"""You are a code quality expert. Explain this code issue using ONLY the provided rule definition.

**Rule: {canonical_id}**
Name: {rule_name}
Category: {rule_def.get("category", finding.get("category", "unknown"))}
Severity: {rule_def.get("severity", finding.get("canonical_severity", "medium"))}

**Why This Matters:**
{rationale}

**How to Fix:**
{remediation}

**Good Example:**
```python
{rule_def.get("example_good", "# See fix below")}
```

**Bad Example:**
```python
{rule_def.get("example_bad", "# See detected issue below")}
```

**Detected Issue:**
File: {finding.get("file", "unknown")}:{finding.get("line", 0)}
```python
{code_snippet}
```

Provide a concise explanation in this format:
1. WHAT: One sentence on what the issue is (cite the rule ID)
2. WHY: One sentence on why it matters (cite the rule rationale)
3. FIX: Show a corrected code snippet that fixes the issue

Start with: "This code violates {canonical_id}..." and end with a ```python code block showing the fix.
"""
        return prompt

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
    def generate_explanation(self, finding, code_snippet=""):
        """
        Generate RAG-enhanced explanation for a finding

        Args:
            finding: Dict with canonical_rule_id, severity, file, line, message
            code_snippet: String of code context

        Returns:
            Dict with explanation metadata (prompt, response, latency, cost, etc.)
        """
        start_time = time.time()

        # Phase 2: Check cache first
        cache_key = self._get_cache_key(finding, code_snippet)
        if self.redis:
            try:
                cached = self.redis.get(cache_key)
                if cached:
                    self.cache_hits += 1
                    cached_data = json.loads(cached)
                    cached_data["cache_hit"] = True
                    cached_data["latency_ms"] = int((time.time() - start_time) * 1000)
                    return cached_data
            except Exception as e:
                print(f"Cache read error: {e}")

        self.cache_misses += 1

        # Build evidence-grounded prompt
        prompt_filled = self._build_evidence_grounded_prompt(finding, code_snippet)

        try:
            # Call Cerebras API
            completion = self.client.chat.completions.create(
                messages=[{"role": "user", "content": prompt_filled}],
                model=self.model,
                max_tokens=self.max_tokens,
                temperature=self.temperature,
            )

            latency_ms = int((time.time() - start_time) * 1000)
            response_text = completion.choices[0].message.content.strip()

            # Extract token usage
            tokens_used = None
            if hasattr(completion, "usage") and completion.usage:
                tokens_used = completion.usage.total_tokens

            # Validate: Check if response cites the rule_id
            canonical_id = finding.get("canonical_rule_id", finding.get("rule_id", "UNKNOWN"))
            cites_rule = canonical_id in response_text

            result = {
                "model_name": self.model,
                "prompt_filled": prompt_filled,
                "response_text": response_text,
                "temperature": self.temperature,
                "max_tokens": self.max_tokens,
                "tokens_used": tokens_used,
                "latency_ms": latency_ms,
                "cost_usd": self._calculate_cost(tokens_used),
                "status": "success",
                "cites_rule": cites_rule,
                "confidence": 0.9 if cites_rule else 0.6,
                "cache_hit": False,
                "consistency_score": None,
                "self_eval_score": None,
            }

            # Phase 2: Store in cache
            if self.redis:
                try:
                    self.redis.setex(cache_key, self.cache_ttl, json.dumps(result))
                except Exception as e:
                    print(f"Cache write error: {e}")

            return result

        except Exception as e:
            latency_ms = int((time.time() - start_time) * 1000)

            # Fallback to template-based explanation
            fallback_text = self.get_fallback_explanation(finding)

            return {
                "model_name": self.model,
                "prompt_filled": prompt_filled,
                "response_text": fallback_text,
                "temperature": self.temperature,
                "max_tokens": self.max_tokens,
                "tokens_used": None,
                "latency_ms": latency_ms,
                "cost_usd": 0,
                "status": "fallback",
                "error": str(e),
                "cites_rule": False,
                "confidence": 0.5,
                "consistency_score": None,
                "self_eval_score": None,
            }

    async def _explain_one_async(
        self, client: httpx.AsyncClient, finding: dict, code_snippet: str, api_key: str
    ) -> dict:
        start_time = time.time()

        # Check cache
        cache_key = self._get_cache_key(finding, code_snippet)
        if self.redis:
            try:
                cached = self.redis.get(cache_key)
                if cached:
                    self.cache_hits += 1
                    cached_data = json.loads(cached)
                    cached_data["cache_hit"] = True
                    cached_data["latency_ms"] = int((time.time() - start_time) * 1000)
                    return cached_data
            except Exception:
                pass

        self.cache_misses += 1
        prompt_filled = self._build_evidence_grounded_prompt(finding, code_snippet)

        payload = {
            "model": self.model,
            "max_tokens": self.max_tokens,
            "temperature": self.temperature,
            "messages": [{"role": "user", "content": prompt_filled}],
        }

        try:
            response = await client.post(
                "https://api.cerebras.ai/v1/chat/completions",
                json=payload,
                headers={"Authorization": f"Bearer {api_key}"},
            )
            response.raise_for_status()
            data = response.json()

            latency_ms = int((time.time() - start_time) * 1000)
            response_text = data["choices"][0]["message"]["content"].strip()

            tokens_used = data.get("usage", {}).get("total_tokens")

            canonical_id = finding.get("canonical_rule_id", finding.get("rule_id", "UNKNOWN"))
            cites_rule = canonical_id in response_text

            result = {
                "model_name": self.model,
                "prompt_filled": prompt_filled,
                "response_text": response_text,
                "temperature": self.temperature,
                "max_tokens": self.max_tokens,
                "tokens_used": tokens_used,
                "latency_ms": latency_ms,
                "cost_usd": self._calculate_cost(tokens_used),
                "status": "success",
                "cites_rule": cites_rule,
                "confidence": 0.9 if cites_rule else 0.6,
                "cache_hit": False,
                "consistency_score": None,
                "self_eval_score": None,
            }

            # --- Feature 1: Validated Autofix Loop ---
            # Extract the first ```...``` code block from the AI response and
            # validate it with the appropriate linter before surfacing the fix.
            try:
                import re as _re

                from CORE.engines.autofix import validate_fix

                code_match = _re.search(
                    r"```(?:python|javascript|js|ts|typescript)?\s*\n(.*?)```",
                    response_text,
                    _re.DOTALL,
                )
                fix_code = code_match.group(1).strip() if code_match else None

                if fix_code:
                    lang = finding.get("language", "python")
                    rule_id = finding.get("canonical_rule_id", finding.get("rule_id", ""))
                    validation = validate_fix(
                        original_code=code_snippet,
                        fixed_code=fix_code,
                        language=lang,
                        rule_id=rule_id,
                    )
                    result["fix_validated"] = validation["valid"]
                    result["fix_confidence"] = validation["confidence"]
                    result["fix_validation_note"] = validation["validation_note"]
                    result["validated_fix"] = validation.get("validated_fix")
                    if not validation["valid"]:
                        result["fix_warning"] = f"⚠️ AI fix requires review: {validation['validation_note']}"
                else:
                    result["fix_validated"] = None
                    result["fix_confidence"] = None
                    result["fix_validation_note"] = "No code block in AI response"
            except Exception:
                # Never let validation crash the explanation pipeline
                result["fix_validated"] = None
                result["fix_confidence"] = None
                result["fix_validation_note"] = "Validation unavailable"
            # -----------------------------------------

            # --- Feature 7: Path Feasibility Validation ---
            # Run a second AI call for HIGH security findings to check
            # if the execution path is actually reachable (LLM4PFA approach).
            try:
                from CORE.engines.path_feasibility import PathFeasibilityValidator

                _pf_validator = PathFeasibilityValidator(
                    model=self.model,
                    max_tokens=150,
                    temperature=0.1,
                )
                if _pf_validator.is_eligible(finding):
                    _pf_result = await _pf_validator.validate_async(client, finding, code_snippet, api_key)
                    result["feasibility_verdict"] = _pf_result.verdict
                    result["feasibility_confidence"] = _pf_result.confidence
                    result["feasibility_reasoning"] = _pf_result.reasoning
                    result["feasibility_latency_ms"] = _pf_result.latency_ms
                    result["feasibility_penalty"] = _pf_result.confidence_penalty
                    result["feasibility_checked"] = True
                else:
                    result["feasibility_verdict"] = None
                    result["feasibility_checked"] = False
            except Exception:
                # Never let feasibility check crash the explanation pipeline
                result["feasibility_verdict"] = None
                result["feasibility_checked"] = False
            # ------------------------------------------------

            if self.redis:
                try:
                    self.redis.setex(cache_key, self.cache_ttl, json.dumps(result))
                except Exception:
                    pass

            return result

        except Exception as e:
            latency_ms = int((time.time() - start_time) * 1000)
            fallback_text = self.get_fallback_explanation(finding)
            return {
                "model_name": self.model,
                "prompt_filled": prompt_filled,
                "response_text": fallback_text,
                "temperature": self.temperature,
                "max_tokens": self.max_tokens,
                "tokens_used": None,
                "latency_ms": latency_ms,
                "cost_usd": 0,
                "status": "fallback",
                "error": str(e),
                "cites_rule": False,
                "confidence": 0.5,
                "consistency_score": None,
                "self_eval_score": None,
            }

    async def _explain_batch_async(self, findings_with_snippets: list, api_key: str) -> list:
        async with httpx.AsyncClient(timeout=30.0) as client:
            tasks = [
                self._explain_one_async(client, f["finding"], f["snippet"], api_key) for f in findings_with_snippets
            ]
            return await asyncio.gather(*tasks, return_exceptions=True)

    def generate_explanation_batch(self, findings_with_snippets: list) -> list:
        api_key = os.getenv("CEREBRAS_API_KEY", "")
        return asyncio.run(self._explain_batch_async(findings_with_snippets, api_key))

    def compute_semantic_entropy(self, finding, code_snippet="", num_samples=3):
        """
        N1: Semantic Entropy for Hallucination Detection

        Runs the prompt multiple times with temperature=0.5 and computes
        the consistency score across responses using n-gram similarity.
        Low consistency → likely hallucination.

        Returns:
            Dict with consistency_score (0.0-1.0), individual responses, variance info
        """
        prompt = self._build_evidence_grounded_prompt(finding, code_snippet)
        responses = []

        for _ in range(num_samples):
            try:
                completion = self.client.chat.completions.create(
                    messages=[{"role": "user", "content": prompt}],
                    model=self.model,
                    max_tokens=self.max_tokens,
                    temperature=0.5,  # Slightly higher temp for variance detection
                )
                responses.append(completion.choices[0].message.content.strip())
            except Exception as e:
                responses.append(f"[Error: {e}]")

        if len(responses) < 2:
            return {
                "consistency_score": None,
                "responses": responses,
                "status": "insufficient_samples",
            }

        # Compute pairwise n-gram similarity
        scores = []
        for i in range(len(responses)):
            for j in range(i + 1, len(responses)):
                score = self._ngram_similarity(responses[i], responses[j])
                scores.append(score)

        consistency = sum(scores) / len(scores) if scores else 0.0

        return {
            "consistency_score": round(consistency, 3),
            "num_samples": len(responses),
            "pairwise_scores": [round(s, 3) for s in scores],
            "responses": responses,
            "is_likely_hallucination": consistency < 0.5,
            "status": "success",
        }

    def _ngram_similarity(self, text_a, text_b, n=3):
        """Compute n-gram (trigram) Jaccard similarity between two texts."""

        def get_ngrams(text, n):
            words = text.lower().split()
            return set(tuple(words[i : i + n]) for i in range(len(words) - n + 1))

        ngrams_a = get_ngrams(text_a, n)
        ngrams_b = get_ngrams(text_b, n)

        if not ngrams_a and not ngrams_b:
            return 1.0
        if not ngrams_a or not ngrams_b:
            return 0.0

        intersection = ngrams_a & ngrams_b
        union = ngrams_a | ngrams_b
        return len(intersection) / len(union)

    def self_evaluate_explanation(self, explanation_text, finding):
        """
        N2: Explanation Quality Self-Evaluation

        Asks the LLM to rate its own explanation on three criteria:
        - Relevance (1-5): Does it address the actual code issue?
        - Accuracy (1-5): Is the information technically correct?
        - Clarity (1-5): Is it easy to understand?

        Returns:
            Dict with scores and overall average
        """
        canonical_id = finding.get("canonical_rule_id", finding.get("rule_id", "UNKNOWN"))

        eval_prompt = f"""Rate this code review explanation on a scale of 1-5 for each criterion.

**Explanation to evaluate:**
{explanation_text}

**Original issue:** {canonical_id} - {finding.get("message", "")}

Rate each criterion (1=poor, 5=excellent):
1. Relevance: Does this explanation directly address the code issue?
2. Accuracy: Is the technical information correct?
3. Clarity: Is the explanation clear and easy to understand?

Respond ONLY in this exact format:
Relevance: X
Accuracy: X
Clarity: X"""

        try:
            completion = self.client.chat.completions.create(
                messages=[{"role": "user", "content": eval_prompt}],
                model=self.model,
                max_tokens=50,
                temperature=0.1,
            )
            response = completion.choices[0].message.content.strip()

            # Parse scores
            scores = {}
            for line in response.split("\n"):
                for key in ["Relevance", "Accuracy", "Clarity"]:
                    if key.lower() in line.lower():
                        try:
                            val = int("".join(c for c in line.split(":")[-1] if c.isdigit())[:1])
                            scores[key.lower()] = min(max(val, 1), 5)
                        except (ValueError, IndexError):
                            scores[key.lower()] = 3  # Default

            avg_score = round(sum(scores.values()) / len(scores), 1) if scores else 3.0
            return {
                "scores": scores,
                "overall": avg_score,
                "raw_response": response,
                "status": "success",
            }

        except Exception as e:
            return {"scores": {}, "overall": None, "status": "error", "error": str(e)}

    def _calculate_cost(self, tokens):
        """
        Calculate cost based on Cerebras pricing
        Current rate: $0.60 per 1M tokens
        """
        if not tokens:
            return 0

        cost_per_million = 0.60
        return (tokens / 1_000_000) * cost_per_million

    def get_fallback_explanation(self, finding):
        """
        Template-based fallback when LLM fails
        Uses rule catalog if available
        """
        canonical_id = finding.get("canonical_rule_id", finding.get("rule_id", "UNKNOWN"))
        rule_def = self.rules_catalog.get(canonical_id, {})

        if rule_def:
            # Use rule-based template
            return (
                f"This code violates {canonical_id} ({rule_def.get('name', 'Code Issue')}). "
                f"{rule_def.get('rationale', 'This pattern should be avoided.')} "
                f"Fix: {rule_def.get('remediation', 'Review and refactor.')}"
            )

        # Generic fallback by category
        category = finding.get("category", "unknown")
        templates = {
            "security": (
                f"Security issue detected: {finding.get('message', 'Unknown issue')}. "
                "This could lead to vulnerabilities. Review and fix using secure coding practices."
            ),
            "best-practice": (
                f"Code quality issue: {finding.get('message', 'Unknown issue')}. "
                "Following best practices improves maintainability and reduces bugs."
            ),
            "style": (
                f"Style violation: {finding.get('message', 'Unknown issue')}. "
                "Following style guidelines makes code more consistent and readable."
            ),
            "dead-code": (
                f"Unused code detected: {finding.get('message', 'Unknown issue')}. "
                "Remove unused code to reduce maintenance burden."
            ),
            "duplication": (
                f"Code duplication found: {finding.get('message', 'Unknown issue')}. "
                "Extract common logic into a shared function to follow DRY principle."
            ),
        }

        return templates.get(
            category,
            f"Issue detected: {finding.get('message', 'Unknown issue')}. Review and address.",
        )


# Test function
if __name__ == "__main__":
    engine = ExplanationEngine()

    # Test finding
    test_finding = {
        "canonical_rule_id": "SOLID-001",
        "rule_id": "PLR0913",
        "severity": "medium",
        "category": "design",
        "file": "test.py",
        "line": 42,
        "message": "Too many arguments",
    }

    test_snippet = "def authenticate(user, password, token, session, db, cache):"

    print("Testing explanation generation...")
    result = engine.generate_explanation(test_finding, test_snippet)

    print(f"\nStatus: {result['status']}")
    print(f"Latency: {result['latency_ms']}ms")
    print(f"Cost: ${result['cost_usd']:.6f}")
    print(f"\nExplanation:\n{result['response_text']}")
