"""Stable vulnerability fingerprint computation.

A fingerprint identifies a vulnerability across scans. Two findings that represent
the same offence in the same code produce the same fingerprint. Refactors that move
unrelated code do NOT change the fingerprint as long as the rule, file, and offending
content stay the same.

Algorithm (v1 — content-normalized hash):
    fingerprint = SHA256( canonical_rule_id "::" file_path "::" normalized_snippet )

    normalized_snippet = evidence["snippet"] with:
      - leading/trailing whitespace stripped
      - runs of internal whitespace collapsed to single space
      - empty string if no snippet available

This is resistant to indentation changes and trailing-space edits. It is NOT resistant
to identifier renames or function reordering — that requires full AST hashing (v2,
tracked in the Open Questions section of GOD_MODE_PLAN.md).
"""

from __future__ import annotations

import hashlib
import re


def _normalize(text: str) -> str:
    """Collapse whitespace so minor formatting changes don't shift the fingerprint."""
    stripped = text.strip()
    return re.sub(r"\s+", " ", stripped)


def compute_fingerprint(
    canonical_rule_id: str,
    file_path: str,
    evidence: dict | None = None,
    message: str = "",
) -> str:
    """Return a hex SHA-256 fingerprint for a finding.

    Args:
        canonical_rule_id: e.g. "SECURITY-001"
        file_path:          e.g. "src/auth/login.py"
        evidence:           finding evidence dict; uses evidence["snippet"] when present
        message:            fallback content when evidence has no snippet

    Returns:
        64-char lowercase hex digest.
    """
    snippet = ""
    if evidence and isinstance(evidence, dict):
        snippet = evidence.get("snippet") or evidence.get("code") or ""
    if not snippet:
        snippet = message

    normalized = _normalize(snippet)
    payload = f"{canonical_rule_id}::{file_path}::{normalized}"
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def short_fingerprint(fingerprint: str, length: int = 12) -> str:
    """Return a human-readable prefix of a full fingerprint, e.g. for URLs."""
    return fingerprint[:length]
