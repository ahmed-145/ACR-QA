# ADR 0013 — CanonicalFinding: the Data-Flow Contract Between All 36 Engines

**Status:** Accepted
**Date:** 2026-06-09
**Author:** Ahmed Mahmoud Abbas

---

## Context

ACR-QA runs 36 engines across 7 layers. Early prototypes passed raw tool output (JSON dicts) from
one engine to the next. This caused three recurring failures:

1. **Field-name drift** — Bandit uses `"test_id"`, Semgrep uses `"check_id"`, gosec uses `"RuleID"`.
   Downstream engines had to know each tool's schema individually.
2. **Silent data loss** — if a tool changed its output schema between versions, the pipeline continued
   silently with `None` fields instead of failing fast.
3. **Untestable intermediate state** — you couldn't write a unit test for `taint_analyzer` without
   first running `normalizer` (which required running a real tool).

The fix: a single Pydantic model as the exclusive currency between all engines.

---

## Decision

**All inter-engine communication MUST go through `CanonicalFinding`.** No engine may read a raw
tool dict after `normalizer.py` has run. No engine may produce a list of anything other than
`list[CanonicalFinding]` as its primary output.

The contract is defined in `CORE/engines/normalizer.py`:

```python
class CanonicalFinding(BaseModel):
    finding_id:        str    # UUID4 — stable across re-scans
    fingerprint:       str    # SHA-256(canonical_rule_id + file + line + snippet[:120])
    canonical_rule_id: str    # e.g. "SECURITY-027" — from RULE_MAPPING in normalizer
    original_rule_id:  str    # tool-native ID e.g. "B608", "semgrep:path-traversal"
    severity:          str    # "high" | "medium" | "low"
    category:          str    # "security" | "quality" | "complexity" | "secrets"
    file:              str    # repo-relative path — NOT absolute
    line:              int    # 1-indexed line number
    language:          str    # "python" | "javascript" | "go" | "unknown"
    message:           str    # human-readable description
    evidence:          dict   # {"snippet": str, "context_before": list, "context_after": list}
    tool_raw:          dict   # unmodified tool output — preserved for auditability
```

**Immutability rule:** downstream engines (taint, quality_gate, confirmed_tier, exploit_verifier)
may read any field but MUST NOT mutate `CanonicalFinding`. If enrichment is needed (e.g. adding
a taint path), engines return a *new* `CanonicalFinding` or a separate enrichment dict.

**RULE_MAPPING ownership:** the dict `RULE_MAPPING` in `normalizer.py` is the single source of
truth for tool-rule → canonical-rule translation. Every engine depends on `canonical_rule_id`
being stable. Any new tool rule MUST get a `SECURITY-NNN` entry in RULE_MAPPING before it
flows into the pipeline; orphan IDs are caught by `test_normalizer.py::test_no_orphan_rule_ids`.

---

## Consequences

### Positive

- Any engine can be unit-tested with a `CanonicalFinding(...)` fixture — no real tool needed.
- Adding a new tool (e.g. a Rust adapter) requires only a new RULE_MAPPING block + a normalizer
  branch; all downstream engines are unchanged.
- `fingerprint` guarantees deduplication across re-scans without a DB lookup.
- `tool_raw` preserves full provenance for auditability without coupling downstream logic to it.

### Negative / Trade-offs

- The schema is intentionally conservative — tool-specific data that doesn't fit a canonical field
  must go into `evidence` or `tool_raw`. This occasionally requires encoding judgments ("is this
  a `high` or `medium`?") at normalizer time rather than deferring them.
- Adding a new required field to `CanonicalFinding` is a breaking change across all 36 engines
  and their tests. New fields MUST be `Optional` with a sensible default.

---

## Enforcement

- `TESTS/test_normalizer.py::test_canonical_finding_fields` asserts the exact field set.
- `TESTS/test_normalizer.py::test_no_orphan_rule_ids` asserts every tool rule in RULE_MAPPING
  has a unique canonical ID.
- mypy is enforced on `CORE/` — any engine that reads an undeclared field fails the type check.
- The pre-commit hook runs `mypy CORE/` on every commit.

---

## Related ADRs

- [ADR 0001](0001-context-and-goals.md) — why these tools were chosen
- [ADR 0009](0009-taint-analysis-design.md) — how taint uses CanonicalFinding without mutating it
- [ADR 0011](0011-verified-remediation-pipeline.md) — how exploit_verifier consumes CanonicalFinding
- [ADR 0012](0012-language-adapter-pattern.md) — how adapters produce raw output that normalizer converts
