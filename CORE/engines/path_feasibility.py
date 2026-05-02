"""
ACR-QA Feature 7 — AI Path Feasibility Validator
Inspired by: LLM4PFA (arXiv) — LLM-based path feasibility analysis for FP elimination.

For HIGH severity findings, a second AI call validates whether the execution path
leading to the flagged vulnerability is actually reachable in practice.

Verdict meanings:
    REACHABLE   — path is reachable, finding is likely a true positive
    UNREACHABLE — path cannot be reached, finding is likely a false positive
    UNKNOWN     — insufficient context to determine reachability
"""

from __future__ import annotations

import asyncio
import time
from typing import Any

import httpx

FEASIBILITY_PROMPT = """You are a static analysis expert reviewing a potential security finding.
Your job is to determine if the flagged code path is actually reachable at runtime.

**Finding:**
Rule: {rule_id}
Severity: {severity}
File: {file_path}:{line_number}
Message: {message}

**Code context:**
{code_snippet}

**Question:** Is the execution path that leads to this vulnerability actually reachable?

Consider:
- Is the flagged code inside a function that is ever called?
- Are there guards, conditions, or checks that prevent the vulnerable path?
- Is this test code, dead code, or production code?
- Does user input actually reach this point?

Respond in exactly this format (3 lines, no extra text):
VERDICT: REACHABLE|UNREACHABLE|UNKNOWN
CONFIDENCE: HIGH|MEDIUM|LOW
REASONING: <one sentence explanation>"""


class PathFeasibilityResult:
    """Result of a path feasibility check."""

    def __init__(
        self,
        verdict: str,
        confidence: str,
        reasoning: str,
        latency_ms: int,
        rule_id: str,
        file_path: str,
        line_number: int,
    ):
        self.verdict = verdict  # REACHABLE | UNREACHABLE | UNKNOWN
        self.confidence = confidence  # HIGH | MEDIUM | LOW
        self.reasoning = reasoning
        self.latency_ms = latency_ms
        self.rule_id = rule_id
        self.file_path = file_path
        self.line_number = line_number

    @property
    def is_unreachable(self) -> bool:
        return self.verdict == "UNREACHABLE"

    @property
    def confidence_penalty(self) -> int:
        """
        Score penalty to apply to finding's confidence_score.
        UNREACHABLE + HIGH confidence -> large penalty
        UNREACHABLE + MEDIUM -> moderate penalty
        UNKNOWN -> small penalty
        REACHABLE -> no penalty
        """
        if self.verdict == "UNREACHABLE":
            return {"HIGH": 30, "MEDIUM": 20, "LOW": 10}.get(self.confidence, 15)
        if self.verdict == "UNKNOWN":
            return 5
        return 0

    def to_dict(self) -> dict[str, Any]:
        return {
            "feasibility_verdict": self.verdict,
            "feasibility_confidence": self.confidence,
            "feasibility_reasoning": self.reasoning,
            "feasibility_latency_ms": self.latency_ms,
            "feasibility_penalty": self.confidence_penalty,
            "is_unreachable": self.is_unreachable,
        }


def _parse_feasibility_response(text: str) -> tuple[str, str, str]:
    """
    Parse the 3-line feasibility response.
    Returns (verdict, confidence, reasoning) with safe fallbacks.
    """
    verdict = "UNKNOWN"
    confidence = "LOW"
    reasoning = "Could not parse feasibility response."

    for line in text.strip().splitlines():
        line = line.strip()
        if line.startswith("VERDICT:"):
            raw = line.split(":", 1)[1].strip().upper()
            if raw in ("REACHABLE", "UNREACHABLE", "UNKNOWN"):
                verdict = raw
        elif line.startswith("CONFIDENCE:"):
            raw = line.split(":", 1)[1].strip().upper()
            if raw in ("HIGH", "MEDIUM", "LOW"):
                confidence = raw
        elif line.startswith("REASONING:"):
            reasoning = line.split(":", 1)[1].strip()

    return verdict, confidence, reasoning


class PathFeasibilityValidator:
    """
    Runs a second AI call to validate execution path reachability.
    Designed to run in the same async context as ExplanationEngine
    to avoid adding latency through sequential calls.
    """

    # Only validate HIGH severity findings — too expensive for medium/low
    ELIGIBLE_SEVERITIES = {"high", "critical"}

    def __init__(self, model: str = "llama-3.1-8b-instant", max_tokens: int = 150, temperature: float = 0.1):
        self.model = model
        self.max_tokens = max_tokens
        self.temperature = temperature  # Low temp for deterministic verdict

    def is_eligible(self, finding: dict[str, Any]) -> bool:
        """Only HIGH/CRITICAL security findings get feasibility validation."""
        sev = finding.get("canonical_severity", finding.get("severity", "low")).lower()
        cat = finding.get("category", "").lower()
        return sev in self.ELIGIBLE_SEVERITIES and cat == "security"

    async def validate_async(
        self,
        client: httpx.AsyncClient,
        finding: dict[str, Any],
        code_snippet: str,
        api_key: str,
    ) -> PathFeasibilityResult:
        """Run feasibility check for a single finding asynchronously."""
        start = time.time()

        prompt = FEASIBILITY_PROMPT.format(
            rule_id=finding.get("canonical_rule_id", finding.get("rule_id", "UNKNOWN")),
            severity=finding.get("canonical_severity", finding.get("severity", "unknown")),
            file_path=finding.get("file_path", finding.get("file", "unknown")),
            line_number=finding.get("line_number", finding.get("line", 0)),
            message=finding.get("message", ""),
            code_snippet=code_snippet[:500] if code_snippet else "# No code context available",
        )

        payload = {
            "model": self.model,
            "max_tokens": self.max_tokens,
            "temperature": self.temperature,
            "messages": [{"role": "user", "content": prompt}],
        }

        rule_id = finding.get("canonical_rule_id", "UNKNOWN")
        file_path = finding.get("file_path", finding.get("file", "unknown"))
        line_number = finding.get("line_number", finding.get("line", 0))

        import os

        provider = os.getenv("ACRQA_LLM_PROVIDER", "groq")
        if provider == "agentrouter":
            base_url = "https://agentrouter.org/v1/chat/completions"
            actual_api_key = os.getenv("AGENTROUTER_API_KEY", api_key)
        else:
            base_url = "https://api.groq.com/openai/v1/chat/completions"
            actual_api_key = api_key

        try:
            response = await client.post(
                base_url,
                json=payload,
                headers={"Authorization": f"Bearer {actual_api_key}"},
                timeout=15.0,
            )
            response.raise_for_status()
            data = response.json()
            text = data["choices"][0]["message"]["content"].strip()
            verdict, confidence, reasoning = _parse_feasibility_response(text)
        except Exception as e:
            verdict, confidence, reasoning = "UNKNOWN", "LOW", f"Validation error: {e}"

        latency_ms = int((time.time() - start) * 1000)
        return PathFeasibilityResult(
            verdict=verdict,
            confidence=confidence,
            reasoning=reasoning,
            latency_ms=latency_ms,
            rule_id=rule_id,
            file_path=file_path,
            line_number=line_number,
        )

    async def validate_batch_async(
        self,
        findings_with_snippets: list[dict[str, Any]],
        api_key: str,
    ) -> list[PathFeasibilityResult | None]:
        """
        Validate feasibility for a batch of findings.
        Returns list of PathFeasibilityResult (or None if finding not eligible).
        Eligible findings are checked concurrently within one shared AsyncClient.
        """
        eligible_results: list[PathFeasibilityResult | None] = []
        async with httpx.AsyncClient(timeout=20.0) as client:
            for item in findings_with_snippets:
                finding = item["finding"]
                snippet = item.get("snippet", "")
                if self.is_eligible(finding):
                    eligible_results.append(await self.validate_async(client, finding, snippet, api_key))
                else:
                    eligible_results.append(None)
        return eligible_results

    def validate_batch(
        self,
        findings_with_snippets: list[dict[str, Any]],
        api_key: str,
    ) -> list[PathFeasibilityResult | None]:
        """Synchronous wrapper for validate_batch_async."""
        return asyncio.run(self.validate_batch_async(findings_with_snippets, api_key))
