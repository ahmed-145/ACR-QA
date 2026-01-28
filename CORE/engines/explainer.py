"""
Cerebras API Integration for Natural Language Explanations
Evidence-grounded prompt engineering for code quality issues
"""

import os
import time
import json
import hashlib
from cerebras.cloud.sdk import Cerebras
from dotenv import load_dotenv
from tenacity import retry, stop_after_attempt, wait_exponential
import yaml

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
        self.max_tokens = 150

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
        canonical_id = finding.get(
            "canonical_rule_id", finding.get("rule_id", "UNKNOWN")
        )
        rule_def = self.rules_catalog.get(canonical_id, {})

        # Build structured prompt with evidence
        prompt = f"""You are a code quality expert. Explain this code issue using ONLY the provided rule definition.

**Rule: {canonical_id}**
Name: {rule_def.get("name", "Code Issue")}
Category: {rule_def.get("category", "unknown")}
Severity: {rule_def.get("severity", "medium")}

**Why This Matters:**
{rule_def.get("rationale", "This pattern should be avoided.")}

**How to Fix:**
{rule_def.get("remediation", "Review and refactor the code.")}

**Good Example:**
```python
{rule_def.get("example_good", "# No example available")}
```

**Bad Example:**
```python
{rule_def.get("example_bad", "# No example available")}
```

**Detected Issue:**
File: {finding.get("file", "unknown")}:{finding.get("line", 0)}
```python
{code_snippet}
```

Provide a 2-3 sentence explanation:
1. WHAT is the issue
2. WHY it matters (cite the rule rationale)
3. HOW to fix it (cite the remediation)

Start with: "This code violates {canonical_id}..."
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
            canonical_id = finding.get(
                "canonical_rule_id", finding.get("rule_id", "UNKNOWN")
            )
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
            }

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
        canonical_id = finding.get(
            "canonical_rule_id", finding.get("rule_id", "UNKNOWN")
        )
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
