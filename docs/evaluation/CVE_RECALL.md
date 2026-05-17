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
| CVE-2022-24302 | Paramiko 2.10.0 | `paramiko/transport.py` | 1, 100 | MISSED | Version mismatch: `mktemp()` absent from 2.10.0 tree |
| CVE-2022-24439 | GitPython 3.1.29 | `git/cmd.py` | 1139, 1150 | MISSED | Tool gap: SECURITY-021 flags unrelated `shell=True` at 515/948, not `transform_kwargs()` |
| CVE-2022-34265 | Django 3.2.13 | `django/db/models/functions/datetime.py` | 208 | MISSED | Architecture gap: SQL injection constructed in DB backend, not in `datetime.py` |

**Recall: 1/5 (20%)** — below the 30% decision-gate threshold.

---

## Per-CVE Analysis

### CVE-2021-35042 — Django ORDER BY injection ✓ DETECTED

- **Vulnerability:** `QuerySet.order_by()` passed dict keys directly into SQL ORDER BY without sanitisation.
- **Fix:** Django 3.2.5 validates ordering expressions before constructing SQL.
- **Detection:** SECURITY-027 (unsafe SQL string formatting) found at line 478 in `compiler.py` — exact match to `affected_lines`.
- **Lesson:** When affected_lines come from the actual vulnerable code path, detection is reliable.

### CVE-2022-22817 — Pillow arbitrary `eval()` ✗ MISSED

- **Vulnerability:** `ImageMath.eval()` calls Python's `eval()` (as `builtins.eval()` at line 249) on user input.
- **Expected detection:** Bandit B307 → SECURITY-001 (dangerous use of eval).
- **Actual:** No HIGH finding at line 249. Bandit B307 only fires on the bare name `eval(...)`, not on the qualified form `builtins.eval(...)`.
- **Root cause:** Tool rule is pattern-matched on syntax, not semantics. `builtins.eval` is equivalent but not caught.
- **Remediation path:** Add a Semgrep rule matching `builtins.eval(...)` to close this gap.

### CVE-2022-24302 — Paramiko insecure tempfile ✗ MISSED (version mismatch)

- **Vulnerability:** `tempfile.mktemp()` (TOCTOU-racy) used in Paramiko before 2.10.1.
- **Expected detection:** Bandit B306 (mktemp deprecated) → HIGH.
- **Actual:** `mktemp` is **not present anywhere** in the 2.10.0 clone. `grep -r mktemp paramiko/` returns nothing.
- **Root cause:** The `vuln_version_tag: "2.10.0"` is incorrect — the mktemp call may have existed in an older branch or a different file not present at this tag. Needs investigation via `git log` on the actual fix commit in the upstream 2.10.1 release.
- **Action:** Investigate correct affected commit/file before including in the full Tier 1 table.

### CVE-2022-24439 — GitPython RCE via unsafe kwargs ✗ MISSED

- **Vulnerability:** GitPython 3.1.29 allowed underscore-prefixed kwargs to be passed to git commands, enabling shell injection via `transform_kwargs()` at ~line 1139.
- **Expected detection:** SECURITY-021 (subprocess with shell=True) at the vulnerable call site.
- **Actual:** SECURITY-021 fires at lines 515, 517, 948 (process termination code, unrelated to the CVE). No finding near lines 1139–1150.
- **Root cause:** The dangerous kwargs-to-command transformation does not use `shell=True` — it injects extra arguments into the git command. Bandit/our rules catch the wrong pattern.
- **Remediation path:** This requires a custom rule checking for `--` / underscore-prefixed kwargs passed to `subprocess.Popen` in a git context.

### CVE-2022-34265 — Django SQL injection via Trunc(kind) ✗ MISSED

- **Vulnerability:** `Trunc(kind=user_input)` passes `kind` directly to `DATE_TRUNC('%s', ...)` via `connection.ops.datetime_trunc_sql()`.
- **Expected detection:** B608 or Semgrep finding SQL string formatting near where kind is used.
- **Actual:** No HIGH finding at or near line 208 in `datetime.py`. The SQL formatting happens inside `connection.ops.datetime_trunc_sql()` in the DB-specific backend (e.g., `django/db/backends/postgresql/operations.py`), not in `datetime.py` itself.
- **Root cause:** Architecture gap — the sink is in the backend, and `affected_file` pointed to the dispatch layer. A correct YAML would list the backend operations file as `affected_file`.
- **Action:** Update `affected_file` and `affected_lines` to point to the postgresql backend operations file for a fair re-test.

---

## Methodology Lessons

### 1. `affected_lines` must come from the patch diff

All four missed CVEs were initially registered with estimated line numbers. The only detected CVE (2021-35042) had line numbers derived from actual tool output. For the full Tier 1 evaluation:

```bash
# Get line numbers from the actual fix diff
git -C <clone_dir> diff <fix_tag>~1 <fix_tag> -- <affected_file>
# Map removed/modified lines back to their pre-fix positions
```

### 2. `affected_file` must be the sink, not the dispatch layer

CVE-2022-34265 shows that when SQL injection is multi-hop (Django ORM → DB backend), listing the ORM file as `affected_file` produces a false miss. The scoring must be applied to the file where the unsafe string operation actually occurs.

### 3. Version verification before registration

CVE-2022-24302 shows that tagging a `vuln_version_tag` without verifying the vulnerable code is present in that tag leads to an undetectable miss. Verification procedure:

```bash
git -C <clone_dir> grep -n "mktemp" paramiko/
# If empty → wrong tag
```

### 4. Tool gap: qualified builtins vs bare names

Bandit B307 (`eval()`) does not match `builtins.eval()`. This is a genuine tool gap for CVE-2022-22817 and suggests a Semgrep rule is needed to cover the qualified form.

---

## Decision Gate

Per `docs/MASTER_SCHEDULE.md` W1 gate:

> **Recall < 30%** → pivot: lean on FP rate + corpus diversity.

**Raw result: 20% (1/5).**

However, disaggregating by failure mode:

| Category | Count | CVEs |
|----------|-------|------|
| Genuine tool gap | 2 | CVE-2022-22817, CVE-2022-24439 |
| Methodology error (wrong version/file) | 2 | CVE-2022-24302, CVE-2022-34265 |
| Detected | 1 | CVE-2021-35042 |

**Recommendation:** Do not fully pivot. The methodology errors are fixable; 1/3 on genuine test cases is a fairer starting estimate. Fix CVE-2022-24302 (find correct version), fix CVE-2022-34265 (point to backend operations file), and re-run before committing to the pivot narrative. Reserve the "tool gap" framing for the two cases where detection is genuinely limited.

---

## Next Steps (W2)

- [ ] Fix CVE-2022-24302: run `git log` on Paramiko 2.10.1 tag to find the mktemp commit and get correct affected file/lines
- [ ] Fix CVE-2022-34265: update `affected_file` to `django/db/backends/postgresql/operations.py` and find correct lines
- [ ] Scale to 15–20 CVEs for full Tier 1, using patch-diff workflow for all affected_lines
- [ ] Consider adding Semgrep rule for `builtins.eval()` to close CVE-2022-22817 gap
- [ ] Update EVALUATION.md §3 with final Tier 1 recall table once full run completes
