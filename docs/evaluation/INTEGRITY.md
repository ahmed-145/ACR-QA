# Evaluation Integrity Charter

**Status:** Active — Tier 0 infrastructure deployed (2026-05-17)
**Companion to:** `EVAL_EXPANSION_PLAN.md` Tier 0, `MASTER_SCHEDULE.md`
**Enforcement scripts:** `scripts/audit_eval_numbers.py` · `make eval-audit` · `make eval-reproduce`

---

## Purpose

This document is the contract between the author and the evaluation. It exists to prevent the
four ways researchers fool themselves: cherry-picking, moving goalposts, stale numbers, and
silent skips. Every commitment below is enforced by automation (`scripts/audit_eval_numbers.py`,
`make eval-reproduce`) so violations are mechanically caught, not policed by honesty alone.

## Commitments

### 1. Pre-Registration

Every CVE in the recall test (`docs/evaluation/CVE_RECALL.md`) MUST be committed to git as a YAML
file in `TESTS/evaluation/cve_recall/` **before** ACR-QA is run against the pre-fix commit.

**Enforcement:** YAML files have a `pre_registered_sha` field with the commit SHA of when the
CVE was added to the repo. The recall test script verifies that the CVE YAML was committed
before the scan run.

**Why:** Without pre-registration, the temptation to silently drop CVEs ACR-QA missed is
overwhelming. With pre-registration, every miss is publicly logged.

### 2. Strict Scoring Rule

A CVE is "detected" if and only if ACR-QA produces a HIGH-severity finding within **±3 lines**
of the vulnerable line declared in the CVE YAML's `affected_lines` field.

**Edge cases (decided in advance, not on the fly):**
- Multi-line vulnerabilities: ANY line in the declared range, ±3, counts
- Adjacent helper function: does NOT count (we need to flag the actual sink)
- Wrong rule_id but right line: counts (correct detection, wrong category)
- Right rule_id but >3 lines away: does NOT count (rule misfired, accidentally adjacent)

**Why:** Without a strict rule written in advance, "did we catch it?" becomes a judgment call
at 2am on the 14th CVE.

### 3. Skipped-CVE Log

Every CVE we *considered but excluded* MUST be logged here with a reason. No silent skips.

**Format:**

| CVE ID | Project | Why skipped | Decided when |
|--------|---------|-------------|--------------|
| CVE-2022-24302 | Paramiko | `mktemp()` absent from 2.10.0 clone — vuln_version_tag wrong; needs fix before Tier 1 inclusion | 2026-05-17 |

**Acceptable skip reasons:**
- "Requires runtime context (CSRF, IDOR, business logic)"
- "Patch fixes a config file, not source code"
- "Affected library not in our adapter scope (e.g., C extension)"
- "CVE description too vague to map to specific lines"

**Unacceptable skip reasons:**
- "ACR-QA didn't catch it" ← this is a result, not a reason
- "Made the numbers look worse" ← obviously

### 4. Automated Number Verification

Every percentage, count, and ratio in `docs/evaluation/EVALUATION.md` MUST be re-derivable from
source data by `scripts/audit_eval_numbers.py`. The CI gate runs this script on every PR.

**What counts as a "number":**
- Precision / recall / F1 percentages
- Repo counts, finding counts, CVE counts
- κ values from peer validation
- FP rate values
- LOC counts, scan time values

**What doesn't:**
- Counts in code comments
- Numbers in narrative prose that aren't formal claims (e.g., "About 50 contributors")
- Numbers in historical CHANGELOG entries

### 5. One-Command Reproducibility

The full evaluation must be reproducible by anyone with:

```bash
make eval-reproduce
```

This:
- Clones all eval repos at pinned commit SHAs (from `TESTS/evaluation/repo_pins.yml`)
- Runs ACR-QA against each
- Generates fresh numbers into `coverage/eval/`
- Compares to checked-in `EVALUATION.md` values
- Exits non-zero if drift exceeds rounding tolerance (0.5%)

### 6. Adversarial Review Checklist

Before EVERY claim is published, the author asks:

- [ ] **Sample size:** is this claim based on enough data points to be meaningful? (n ≥ 10 for any percentage)
- [ ] **Version:** was the scan run on the version we're claiming about? (Check commit SHA)
- [ ] **Double-counting:** could a different rule have caught this and we're counting it twice?
- [ ] **Strongest counter-argument:** what would a hostile examiner say? Is the claim still defendable?
- [ ] **Cherry-pick risk:** did we look at all candidates, or stop at favorable ones?
- [ ] **Selection bias:** were the eval repos chosen because they'd score well? (Yes for Layer A by design; no for Layer B.)

### 7. Things I Tried to Disprove and Couldn't

This section grows during the eval. Every time the author tries to break a claim and fails,
log it here. Builds confidence that the claim isn't fragile.

**Format:**

| Claim | What I tried | Result | Date |
|-------|--------------|--------|------|
| *(none yet — populated during execution)* | | | |

Example entries (illustrative):

| Claim | What I tried | Result | Date |
|-------|--------------|--------|------|
| "FP rate 1.0% on Flask" | Re-ran scan with --no-ai disabled (different code path) | FP rate 1.1%, well within tolerance | 2026-05-20 |
| "CVE recall 65%" | Tried to find a CVE in the corpus that should be excluded as out-of-scope | All 13 missed CVEs already had documented out-of-scope reasons | 2026-05-22 |

### 8. Limitations Section (Honest, Not Defensive)

The published `EVALUATION.md` MUST contain a Limitations section that lists what the eval
**does not** prove. This is not a confession; it's scope-setting that prevents the examiner
from constructing limits we didn't acknowledge.

Required limitations to document:
- Sample size of eval corpus (16 repos is small vs Snyk's >10k)
- Author bias on Layer B labels (mitigated by peer validation Tier 2)
- Language scope (Python primary; JS, TS, Go secondary)
- Vulnerability category scope (no CSRF, IDOR, business logic — by design)
- Time-bounded snapshot (commit SHAs pinned; results don't generalize forward)

---

## Compliance Audit Log

Every quarterly review (or before any tag release), run this checklist:

- [ ] `scripts/audit_eval_numbers.py` passes
- [ ] `make eval-reproduce` succeeds with no drift
- [ ] Skipped-CVE log has not grown silently (compare line count to last release)
- [ ] All claims in EVALUATION.md have been adversarial-reviewed in the last 90 days
- [ ] Limitations section is current with most recent methodology decisions

| Audit date | Auditor | Result | Notes |
|------------|---------|--------|-------|
| 2026-05-17 | Author (ahmeed-145) | ✅ Pass — 17/17 internal-consistency claims verified | Initial Tier 0 deploy; Layer A + Layer B arithmetic verified; YAML count = 10 ✓ |
| 2026-05-17 | Author (ahmeed-145) | ⚠ Pilot — CVE recall 1/5 (20%) | Tier 1 W1 pilot; 2 methodology errors (wrong version/file), 2 genuine tool gaps; see CVE_RECALL.md |

---

## Why This Matters Beyond the Thesis

This charter is **the** thing that converts a thesis project into a research deliverable.
Anyone — supervisor, examiner, future maintainer, contributor — can:

1. Read the claims in EVALUATION.md
2. Re-derive every number via `make eval-reproduce`
3. Check this charter for the methodology
4. See exactly what we excluded and why

That's the difference between *"trust me"* and *"verify yourself."* This document makes ACR-QA
verifiable, which is the bar for research-grade software.
