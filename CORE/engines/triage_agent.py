"""AI Triage Agent — multi-step reasoning engine for security finding triage.

Uses a 3-step tool-calling loop backed by the existing KeyPool (works with
Groq, Ollama, or any OpenAI-compatible endpoint).

Loop:
  1. Present finding + available tools → LLM requests a tool call (JSON)
  2. Execute tool locally → append result to conversation
  3. Repeat up to MAX_TOOL_CALLS; after final call, force a verdict

Output per finding:
  triage_verdict         TRUE_POSITIVE | FALSE_POSITIVE | NEEDS_REVIEW
  triage_reasoning       chain-of-thought from LLM (last step)
  triage_confidence_delta float in [-0.3, +0.2] applied to confidence_score
"""

from __future__ import annotations

import ast
import logging
import os
import re
import subprocess
import time
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

# ── Constants ─────────────────────────────────────────────────────────────────

MAX_TOOL_CALLS = 4
MAX_TOKENS_PER_STEP = 1500
SKIP_REASON_NO_KEY = "no_llm_key"
SKIP_REASON_DISABLED = "triage_disabled"

_TOOL_CALL_PATTERN = re.compile(
    r"TOOL:\s*(\w+)\s*\(([^)]*)\)",
    re.IGNORECASE,
)
_VERDICT_PATTERN = re.compile(
    r"VERDICT:\s*(TRUE_POSITIVE|FALSE_POSITIVE|NEEDS_REVIEW)",
    re.IGNORECASE,
)

_SYSTEM_PROMPT = """You are a senior security engineer triaging a static analysis finding.
Your goal: determine if the finding is a TRUE_POSITIVE, FALSE_POSITIVE, or NEEDS_REVIEW.

You have access to these tools (call at most {max_tools} times total):
  TOOL: get_imports(filepath)          — list imports in a Python file
  TOOL: get_function_body(filepath, function_name)  — get source of a function
  TOOL: get_callers(function_name, target_dir)      — find call sites
  TOOL: grep(pattern, target_dir)      — search codebase for a pattern

To call a tool, respond with exactly:
  TOOL: <tool_name>(<arg1>, <arg2>)

When you have enough context (or no more tools needed), respond with:
  VERDICT: TRUE_POSITIVE|FALSE_POSITIVE|NEEDS_REVIEW
  REASONING: <one or two sentences>

Rules:
- Only one tool call per response.
- After the tool result, decide whether to call another tool or give a verdict.
- If you cannot determine, use NEEDS_REVIEW.
- Be decisive: most findings are TRUE_POSITIVE unless there is a clear guard."""

_FINDING_TEMPLATE = """Security finding to triage:
  Rule:     {rule_id}
  Severity: {severity}
  File:     {file_path}:{line_number}
  Message:  {message}
  Tool:     {tool}

Code context:
{code_snippet}

Begin triage. Call a tool or give your VERDICT."""


# ── Local tool implementations ─────────────────────────────────────────────────


def _resolve_target(target_dir: str | None) -> str:
    return target_dir or os.getcwd()


def get_imports(filepath: str, **_: Any) -> str:
    """Return the import statements from a Python file."""
    try:
        source = Path(filepath).read_text(encoding="utf-8", errors="replace")
        tree = ast.parse(source)
    except (OSError, SyntaxError) as e:
        return f"Error reading {filepath}: {e}"
    imports: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imports.append(ast.unparse(node))
        elif isinstance(node, ast.ImportFrom):
            imports.append(ast.unparse(node))
    return "\n".join(imports) if imports else "(no imports found)"


def get_function_body(filepath: str, function_name: str, **_: Any) -> str:
    """Return the source of a named function from a file."""
    try:
        source = Path(filepath).read_text(encoding="utf-8", errors="replace")
        tree = ast.parse(source)
    except (OSError, SyntaxError) as e:
        return f"Error reading {filepath}: {e}"
    lines = source.splitlines()
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef) and node.name == function_name:
            start = node.lineno - 1
            end = node.end_lineno or (start + 30)
            snippet = "\n".join(lines[start:end])
            return snippet[:2000]
    return f"Function '{function_name}' not found in {filepath}"


def get_callers(function_name: str, target_dir: str | None = None, **_: Any) -> str:
    """Find call sites of a function in the target directory."""
    target = _resolve_target(target_dir)
    pattern = rf"\b{re.escape(function_name)}\s*\("
    try:
        result = subprocess.run(
            ["grep", "-rn", "--include=*.py", pattern, target],
            capture_output=True,
            text=True,
            timeout=10,
        )
        out = result.stdout.strip()
        if not out:
            return f"No callers of '{function_name}' found in {target}"
        # Limit output
        lines = out.splitlines()[:20]
        return "\n".join(lines)
    except Exception as e:
        return f"grep error: {e}"


def grep(pattern: str, target_dir: str | None = None, **_: Any) -> str:
    """Grep for a pattern across Python files in the target directory."""
    target = _resolve_target(target_dir)
    try:
        result = subprocess.run(
            ["grep", "-rn", "--include=*.py", pattern, target],
            capture_output=True,
            text=True,
            timeout=10,
        )
        out = result.stdout.strip()
        if not out:
            return f"No matches for '{pattern}' in {target}"
        lines = out.splitlines()[:20]
        return "\n".join(lines)
    except Exception as e:
        return f"grep error: {e}"


_TOOLS: dict[str, Any] = {
    "get_imports": get_imports,
    "get_function_body": get_function_body,
    "get_callers": get_callers,
    "grep": grep,
}


def _parse_args(raw: str) -> list[str]:
    """Parse comma-separated tool args from a TOOL: call(...) match."""
    parts = [p.strip().strip("'\"") for p in raw.split(",") if p.strip()]
    return parts


def _call_tool(name: str, raw_args: str, target_dir: str | None) -> str:
    func = _TOOLS.get(name)
    if func is None:
        return f"Unknown tool: {name}"
    args = _parse_args(raw_args)
    try:
        if name == "get_imports":
            return func(args[0] if args else "") if args else "Missing filepath"
        if name == "get_function_body":
            fp = args[0] if len(args) > 0 else ""
            fn = args[1] if len(args) > 1 else ""
            return func(fp, fn)
        if name == "get_callers":
            fn = args[0] if args else ""
            return func(fn, target_dir)
        if name == "grep":
            pat = args[0] if args else ""
            return func(pat, target_dir)
    except Exception as e:
        return f"Tool error: {e}"
    return "Tool call error"


# ── Triage result ─────────────────────────────────────────────────────────────


class TriageResult:
    def __init__(
        self,
        verdict: str,
        reasoning: str,
        confidence_delta: float,
        tool_calls_used: int,
        latency_ms: int,
        skip_reason: str | None = None,
    ) -> None:
        self.verdict = verdict
        self.reasoning = reasoning
        self.confidence_delta = confidence_delta
        self.tool_calls_used = tool_calls_used
        self.latency_ms = latency_ms
        self.skip_reason = skip_reason

    def to_dict(self) -> dict[str, Any]:
        return {
            "triage_verdict": self.verdict,
            "triage_reasoning": self.reasoning,
            "triage_confidence_delta": self.confidence_delta,
            "triage_tool_calls": self.tool_calls_used,
            "triage_latency_ms": self.latency_ms,
            "triage_skip_reason": self.skip_reason,
        }

    @classmethod
    def skipped(cls, reason: str) -> TriageResult:
        return cls(
            verdict="NEEDS_REVIEW",
            reasoning="Triage skipped.",
            confidence_delta=0.0,
            tool_calls_used=0,
            latency_ms=0,
            skip_reason=reason,
        )


def _verdict_to_delta(verdict: str) -> float:
    """Map verdict to a confidence score adjustment."""
    return {"TRUE_POSITIVE": 0.15, "FALSE_POSITIVE": -0.30, "NEEDS_REVIEW": 0.0}.get(verdict, 0.0)


# ── TriageAgent ───────────────────────────────────────────────────────────────


class TriageAgent:
    """Multi-step LLM reasoning agent for security finding triage."""

    def __init__(self, _key_pool: Any = None) -> None:
        if _key_pool is not None:
            self._key_pool = _key_pool
        else:
            from CORE.engines.explainer import KeyPool

            self._key_pool = KeyPool()
        self._model = self._key_pool._model_override or "llama-3.1-8b-instant"

    @property
    def is_available(self) -> bool:
        return self._key_pool.has_keys

    def triage(self, finding: dict[str, Any], target_dir: str | None = None, code_snippet: str = "") -> TriageResult:
        """Run triage loop for a single finding. Returns a TriageResult."""
        if not self.is_available:
            return TriageResult.skipped(SKIP_REASON_NO_KEY)
        if os.getenv("ACRQA_TRIAGE_AGENT", "1") == "0":
            return TriageResult.skipped(SKIP_REASON_DISABLED)

        start = time.time()
        messages: list[dict[str, str]] = [
            {
                "role": "system",
                "content": _SYSTEM_PROMPT.format(max_tools=MAX_TOOL_CALLS),
            },
            {
                "role": "user",
                "content": _FINDING_TEMPLATE.format(
                    rule_id=finding.get("canonical_rule_id", finding.get("rule_id", "UNKNOWN")),
                    severity=finding.get("severity", "unknown"),
                    file_path=finding.get("file", finding.get("file_path", "unknown")),
                    line_number=finding.get("line", finding.get("line_number", 0)),
                    message=finding.get("message", ""),
                    tool=finding.get("tool", "unknown"),
                    code_snippet=code_snippet[:800] if code_snippet else "(no code context)",
                ),
            },
        ]

        verdict = "NEEDS_REVIEW"
        reasoning = "No verdict reached."
        tool_calls_used = 0

        for _ in range(MAX_TOOL_CALLS + 1):
            try:
                client = self._key_pool.next_client()
                completion = client.chat.completions.create(
                    messages=messages,
                    model=self._model,
                    max_tokens=MAX_TOKENS_PER_STEP,
                    temperature=0.1,
                )
                reply = completion.choices[0].message.content.strip()
            except Exception as e:
                logger.debug(f"Triage LLM error: {e}")
                break

            messages.append({"role": "assistant", "content": reply})

            # Check for verdict
            v_match = _VERDICT_PATTERN.search(reply)
            if v_match:
                verdict = v_match.group(1).upper()
                r_match = re.search(r"REASONING:\s*(.+)", reply, re.IGNORECASE)
                reasoning = r_match.group(1).strip() if r_match else reply[:300]
                break

            # Check for tool call
            t_match = _TOOL_CALL_PATTERN.search(reply)
            if t_match and tool_calls_used < MAX_TOOL_CALLS:
                tool_name = t_match.group(1).lower()
                tool_args = t_match.group(2)
                tool_result = _call_tool(tool_name, tool_args, target_dir)
                tool_calls_used += 1
                messages.append(
                    {
                        "role": "user",
                        "content": f"Tool result for {tool_name}:\n{tool_result[:1000]}\n\nContinue triage.",
                    }
                )
            else:
                # LLM gave a free-form response without tool call or verdict
                reasoning = reply[:300]
                break

        latency_ms = int((time.time() - start) * 1000)
        return TriageResult(
            verdict=verdict,
            reasoning=reasoning,
            confidence_delta=_verdict_to_delta(verdict),
            tool_calls_used=tool_calls_used,
            latency_ms=latency_ms,
        )

    def enrich_findings(
        self,
        findings: list[dict[str, Any]],
        target_dir: str | None = None,
        snippets: dict[str, str] | None = None,
    ) -> list[dict[str, Any]]:
        """Run triage on HIGH/CRITICAL security findings and annotate them."""
        if not self.is_available:
            logger.debug("Triage agent skipped: no LLM key")
            return findings

        snippets = snippets or {}
        eligible = [
            f
            for f in findings
            if f.get("severity", "").lower() in ("high", "critical") and f.get("category", "").lower() == "security"
        ]

        if not eligible:
            return findings

        triaged = 0
        for f in eligible:
            fp = f.get("file", f.get("file_path", ""))
            snippet = snippets.get(fp, "")
            try:
                result = self.triage(f, target_dir=target_dir, code_snippet=snippet)
                f.update(result.to_dict())
                triaged += 1
            except Exception as e:
                logger.debug(f"Triage failed for {fp}: {e}")

        if triaged:
            logger.info(f"      - Triage Agent: {triaged} finding(s) triaged")
        return findings
