"""
CORE.detection.tool_runner
Thin dispatch layer — routes analysis to the correct language adapter.
Used by integration benchmarks and CI entry points.
"""

from __future__ import annotations

from CORE.adapters.js_adapter import JavaScriptAdapter


def detect_language(target_dir: str) -> str:
    """Return 'javascript', 'python', or 'mixed' for a given directory."""
    return JavaScriptAdapter.detect_language(target_dir)


def run_tools(target_dir: str, language: str | None = None) -> dict:
    """
    Run the appropriate tool suite for target_dir.
    If language is None, auto-detects from directory contents.
    Returns raw tool results dict.
    """
    lang = language or detect_language(target_dir)
    if lang in ("javascript", "typescript", "mixed"):
        adapter = JavaScriptAdapter(target_dir=target_dir)
        return adapter.run_tools()
    # Python path — return empty dict; Python tools run via shell in main.py
    return {"language": "python", "target_dir": target_dir}


__all__ = ["detect_language", "run_tools"]
