# CVE Recall — Pilot Results (Tier 1, W1)

**Date:** 2026-05-17
**Harness:** `scripts/run_cve_recall.py --no-clone --update`
**Scoring rule:** HIGH-severity finding within ±3 lines of `affected_lines` (INTEGRITY.md §3)
**Pre-registration:** All YAMLs committed at `d572bb8` before scanning

---

## Summary

| CVE | Project | Affected file | affected_lines | Result | Root cause of miss |
|-----|---------|--------------|----------------|--------|-------------------|
| CVE-2021-35042 | Django 3.2.4 | `django/db/models/sql/compiler.py` | 478, 652, 1456, 1483, 1635 | **DETECTED** (SECURITY-027) | — |
| CVE-2022-22817 | Pillow 8.4.0 | `src/PIL/ImageMath.py` | 249 | MISSED | Tool gap: B307 flags `eval()` but not `builtins.eval()` |
| CVE-2022-24302 | Paramiko 2.10.0 | `paramiko/pkey.py` | 561, 562 | MISSED | Tool gap: no rule for `open()+chmod()` TOCTOU race |
| CVE-2022-24439 | GitPython 3.1.29 | `git/cmd.py` | 1139, 1150 | MISSED | Tool gap: SECURITY-021 at L515/948 (unrelated shell=True), not at transform_kwargs |
| CVE-2022-34265 | Django 3.2.13 | `django/db/backends/postgresql/operations.py` | 56, 85 | MISSED (near-hit) | Severity gap: STYLE-004 fires at L59 but scored LOW, not HIGH |

**Recall: 1/5 (20%)** — below the 30% decision-gate threshold.

**Near-hit note:** CVE-2022-34265 — STYLE-004 (`%`-format in SQL context) fires at L59, within ±3 of affected_line 56, but is classified LOW severity. The tool finds the pattern; the severity mapping prevents detection under the strict HIGH-only rule.

---

## Per-CVE Analysis

### CVE-2021-35042 — Django ORDER BY injection ✓ DETECTED

- **Vulnerability:** `QuerySet.order_by()` passed dict keys directly into SQL ORDER BY without sanitisation.
- **Fix:** Django 3.2.5 validates ordering expressions before constructing SQL.
- **Detection:** SECURITY-027 (unsafe SQL string formatting) found at line 478 in `compiler.py` — exact match to `affected_lines`.
- **Lesson:** When `affected_lines` come from the actual vulnerable code path, detection is reliable.

### CVE-2022-22817 — Pillow arbitrary `eval()` ✗ MISSED

- **Vulnerability:** `ImageMath.eval()` calls Python's `eval()` (as `builtins.eval()` at line 249) on user input.
- **Expected detection:** Bandit B307 → SECURITY-001 (dangerous use of eval).
- **Actual:** No HIGH finding at line 249. Bandit B307 only fires on the bare name `eval(...)`, not on the qualified form `builtins.eval(...)`.
- **Root cause:** Tool rule is syntax-matched, not semantics-matched. `builtins.eval` is equivalent but bypasses the rule.
- **Remediation path:** Add a Semgrep rule matching `builtins.eval(...)` to close this gap.

### CVE-2022-24302 — Paramiko TOCTOU race in key file creation ✗ MISSED

- **Vulnerability:** `pkey.py:_write_private_key_file()` at L561-562: creates file with `open(filename, "w")` (world-readable at default umask) then calls `os.chmod(filename, 0o600)`. Race window between creation and chmod exposes private key.
- **Expected detection:** No existing Bandit or Semgrep rule targets the `open()+chmod()` TOCTOU pattern.
- **Actual:** 0 HIGH findings in `pkey.py`. 1354 total findings in Paramiko scan, none relevant.
- **Root cause:** Genuine tool gap — the vulnerable pattern requires dataflow analysis across two sequential calls on the same path variable.
- **Pilot correction:** Original YAML had wrong `affected_file` (transport.py) and wrong mechanism (mktemp). Correct file is `paramiko/pkey.py` L561-562. Still MISSED with corrected metadata.

### CVE-2022-24439 — GitPython RCE via unsafe kwargs ✗ MISSED

- **Vulnerability:** GitPython 3.1.29 allowed underscore-prefixed kwargs to be passed to git commands, enabling shell injection via `transform_kwargs()` at ~line 1139.
- **Expected detection:** SECURITY-021 (subprocess with shell=True) at the vulnerable call site.
- **Actual:** SECURITY-021 fires at lines 515, 517, 948 (process termination code, unrelated). No finding near lines 1139–1150.
- **Root cause:** The dangerous kwargs transformation does not use `shell=True` — it builds extra args injected into the git command array. Bandit catches the wrong pattern.
- **Remediation path:** Requires a custom rule for underscore-kwargs → subprocess arg injection in git contexts.

### CVE-2022-34265 — Django SQL injection via Trunc(kind) ✗ MISSED (near-hit)

- **Vulnerability:** `Trunc(kind=user_input)` passes `kind` as `lookup_type` to `datetime_trunc_sql()` → `"DATE_TRUNC('%s', %s)" % (lookup_type, field_name)` in the PostgreSQL backend.
- **Sink:** `django/db/backends/postgresql/operations.py` L56 (date_trunc_sql) and L85 (datetime_trunc_sql).
- **Actual:** STYLE-004 (`UP031` — use format specifiers instead of `%`-format) fires at **L59**, within ±3 of affected_line 56. But severity is **LOW**, not HIGH → does not pass the strict scoring rule.
- **Root cause:** Severity gap — the tool correctly identifies the `%s`-in-SQL-string pattern at the right location but maps it to a style rule rather than a security rule.
- **Pilot correction:** Original `affected_file` was `datetime.py` (dispatch layer). Correct sink is `postgresql/operations.py`. Still MISSED even with corrected metadata, but now a near-hit.

---

## Methodology Lessons

### 1. `affected_lines` must come from the patch diff

The only detected CVE (2021-35042) had lines confirmed from tool output. For full Tier 1:

```bash
git -C <clone_dir> diff <fix_tag>~1 <fix_tag> -- <affected_file>
# Map removed/modified lines to pre-fix positions
```

### 2. `affected_file` must be the sink, not the dispatch layer

CVE-2022-34265: the ORM dispatch layer (`datetime.py`) calls into the DB backend (`postgresql/operations.py`) where the unsafe `%s` interpolation actually occurs. Scoring must target the file containing the sink.

### 3. Verify vulnerable code is present before registering

CVE-2022-24302: original YAML had wrong file and mechanism. Inspect the cloned repo before finalising the YAML:

```bash
grep -n "mktemp\|chmod\|write_private" <clone>/paramiko/*.py
```

### 4. Tool gap: qualified builtins vs bare names

Bandit B307 misses `builtins.eval()`. Needs Semgrep rule for the qualified form.

### 5. Severity gaps create near-hits

CVE-2022-34265 shows a new failure mode: tool finds the right line but maps it LOW instead of HIGH. This is worth examining — does the severity mapping need tuning, or should the scoring rule accept MEDIUM+?

---

## Decision Gate

Per `docs/MASTER_SCHEDULE.md` W1 gate:

> **Recall < 30%** → pivot: lean on FP rate + corpus diversity.

**Raw result: 20% (1/5).** Confirmed after correcting all metadata errors — all 4 misses are genuine tool gaps.

Disaggregation after corrections:

| Category | Count | CVEs |
|----------|-------|------|
| Genuine tool gap (no rule exists) | 3 | CVE-2022-22817, CVE-2022-24302, CVE-2022-24439 |
| Severity gap (right line, wrong severity) | 1 | CVE-2022-34265 |
| Detected | 1 | CVE-2021-35042 |

**Recommendation:** Proceed with W2 full Tier 1 (15–20 CVEs) but **lead the defense with FP rate + corpus diversity**. Use the CVE recall result to demonstrate honest self-evaluation rather than as the primary evidence of detection quality. The near-hit on CVE-2022-34265 and the documented tool gaps are honest, defensible findings.

---

## Next Steps (W2)

- [ ] Scale to 15–20 CVEs for full Tier 1 using patch-diff workflow for all `affected_lines`
- [ ] Investigate Semgrep rule for `builtins.eval()` to close CVE-2022-22817 gap
- [ ] Evaluate whether MEDIUM+ severity should count in a revised scoring threshold
- [ ] Update EVALUATION.md §3 with final Tier 1 recall table once full run completes
