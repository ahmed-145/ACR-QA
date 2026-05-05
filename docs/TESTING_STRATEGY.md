# ACR-QA Testing Strategy

**Author:** Written May 5, 2026 — companion to `GOD_MODE_PLAN.md` v2
**Status:** Plan, not yet executed. Tracks the path from "1690 unit tests pass" to "thesis-defendable evidence."

---

## 1. The Lesson — Why Coverage % Is The Wrong Target

We have **85% line coverage** and **1,690 passing tests**. Both numbers are misleading for a security analysis tool. Here's why:

**Coverage measures whether lines RUN, not whether they FIND BUGS.** A test that calls `normalize_ruff(fake_input)` and asserts the result is a dict will run 200 lines and add 200 lines to coverage — without testing whether ACR-QA actually catches a SQL injection. You can build 100% coverage with tests that catch zero bugs. Coverage is a *tripwire* (sudden drops mean dead code or removed tests), not a *target*.

**The real question for ACR-QA is one sentence:**

> *Does it find the bugs that exist, and stay quiet on the bugs that don't?*

Translated to numbers: **recall** (% of known vulns we catch) and **precision** (% of our findings that are real). Coverage doesn't measure either.

**The honest evidence we have today:**

| Repo | Type | Recall | Precision | Status |
|---|---|---|---|---|
| DVPWA | Vulnerable Python | **50% (3/6)** | 81.8% | 🔴 Thesis risk — missing hardcoded password, debug mode, CSRF |
| Pygoat | Vulnerable Django | 100% | 96.4% | 🟢 Strong |
| VulPy | Vulnerable Python | 100% | 100% | 🟢 Strong |
| DSVW | Vulnerable tiny | 100% | 100% | 🟢 Strong |
| Flask 68k★ | Real clean | — | — | FP rate 10.3% (need re-measure post-cleanup) |
| httpx | Real clean | — | — | FP rate ~9% (need re-measure) |

**Status:** strong on the easy benchmarks, **weak on DVPWA**, **stale on FP rate**. Without addressing DVPWA recall, the thesis claim "97.1% precision" is structurally fragile under defense questioning ("What about the 50% you missed?").

---

## 2. The Real Testing Pyramid for a Security Tool

Standard SaaS apps use the classic pyramid: many unit tests, fewer integration, fewer E2E. **Security analysis tools need a different pyramid** because the value is in the analysis, not in the plumbing.

```
                        ┌─────────────────────────┐
                        │   USER STUDY (Layer 6)  │   Human validity (5-8 participants)
                        ├─────────────────────────┤
                        │ EVAL BENCHMARKS (Layer 5)│   THE THESIS EVIDENCE — recall, precision, FP rate
                        ├─────────────────────────┤
                        │  SNAPSHOT TESTS (Layer 4)│   Detect any output drift on fixed inputs
                        ├─────────────────────────┤
                        │ INTEGRATION TESTS (L3)   │   Real subprocess, real DB, real Celery
                        ├─────────────────────────┤
                        │   UNIT TESTS (Layer 2)   │   Regression net for individual functions
                        ├─────────────────────────┤
                        │ STATIC GUARDS (Layer 1)  │   Type checking, lint, no-CUSTOM-* in output
                        └─────────────────────────┘
```

**Layer 1-2 prevent regressions. Layer 3-4 prove the pipeline works. Layer 5 IS the thesis. Layer 6 is the human story.**

Most of our 1,690 tests are Layer 2. They're necessary but not sufficient. We need to grow Layer 3, 4, and 5 dramatically.

---

## 3. Layer-By-Layer Plan

### Layer 1 — Static Guards (passive, already in CI)

**What it is:** ruff format, ruff check, mypy, pre-commit hooks. Catches typos, type bugs, dead imports.

**What's missing:** A lint that fails CI if any pipeline output contains `CUSTOM-*` (means a rule isn't in `RULE_MAPPING`). This was a recurring bug — let's make it impossible to ship.

**To add:**
```python
# TESTS/test_no_custom_rules.py
def test_no_custom_rules_on_benchmark():
    findings = run_acrqa_on("test_targets/eval-repos/dsvw")
    custom = [f for f in findings if f.canonical_id.startswith("CUSTOM-")]
    assert custom == [], f"Unmapped rules leaked into output: {custom}"
```

### Layer 2 — Unit Tests (the regression net)

**What we have:** 1,690 tests, 85% coverage. **Status: keep, do not grow without reason.** We don't need 2,000 unit tests. We need the existing 1,690 to keep passing on every PR.

**What to fix:**
- `CORE/tasks.py` — **0% coverage**, currently a paper feature. Add 5-10 integration tests that actually invoke a Celery worker and verify task lifecycle. Without this, the "background jobs" claim is unverifiable.
- Property-based tests for `normalizer.py` using `hypothesis`: any valid Bandit/Ruff/Semgrep JSON should not crash. Catches edge cases we'll never hand-write.

**Don't:** Write more unit tests just to pump coverage to 90%. Time is better spent on Layer 5.

### Layer 3 — Integration Tests (real subprocess, no mocks)

**What we have:** ~15 tests in `test_integration_benchmarks.py`. Most actually invoke Ruff/Bandit/Semgrep.

**What's missing:**
- An end-to-end FastAPI test: `POST /v1/scans → 202 → poll /v1/scans/{id} → assert findings shape`. This test fails today because nobody wrote it.
- A Celery worker test: spin up a real worker, dispatch `run_analysis_task`, assert result.
- A DB test: insert a finding, query it back, assert schema match.

**Sketch:**
```python
# TESTS/integration/test_fastapi_e2e.py
@pytest.mark.integration
def test_async_scan_lifecycle(api_client, celery_worker):
    # 1. Login
    token = login_admin(api_client)
    # 2. Submit scan
    r = api_client.post("/v1/scans", json={"target_dir": "TESTS/samples/comprehensive-issues"},
                        headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 202
    job_id = r.json()["job_id"]
    # 3. Poll until done (max 30s)
    for _ in range(30):
        r = api_client.get(f"/v1/scans/{job_id}", headers={"Authorization": f"Bearer {token}"})
        if r.json()["status"] in ("completed", "failed"):
            break
        time.sleep(1)
    # 4. Assert
    assert r.json()["status"] == "completed"
    assert r.json()["findings_count"] > 0
```

**CI:** Run on every PR. Test must complete in <60s.

### Layer 4 — Snapshot Tests (catch silent drift)

**What it is:** Run ACR-QA on a fixed corpus, save the output JSON, commit it. On future runs, diff. If the output changes, fail the test and force the developer to either accept the change (`--update-snapshots`) or fix the regression.

**What's missing:** We have no snapshot tests today. Every refactor risks silently changing finding output without anyone noticing until a thesis demo goes wrong.

**To add:**
```python
# TESTS/snapshot/test_snapshot_dsvw.py
def test_dsvw_snapshot():
    findings = run_acrqa_on("test_targets/eval-repos/dsvw", deterministic=True)
    expected = json.load(open("TESTS/snapshot/dsvw_expected.json"))
    assert findings == expected, "DSVW output drifted — review and update snapshot"
```

**Plus a `--update-snapshots` pytest flag** to regenerate when changes are intentional.

**CI:** Run on every PR. Failures gate merging.

### Layer 5 — Evaluation Benchmarks (THE THESIS)

This is the work that proves ACR-QA actually works. **Everything else is plumbing for this layer.**

#### 5.1 Vulnerable Repos (Recall Battery)

**Goal:** "Given a repo with KNOWN bugs, did we find them?"

**Existing assets:** `scripts/run_evaluation.py` already has hardcoded ground truth dicts for DVPWA, Pygoat, VulPy, DSVW. **But the ground truth is incomplete and the test isn't gating CI.**

**To do:**
1. Move ground truth out of Python and into versioned YAML files: `TESTS/evaluation/ground_truth/dvpwa.yml`, `pygoat.yml`, `dsvw.yml`, `vulpy.yml`, `dvna.yml` (Node), `govwa.yml` (Go).
2. Format:
   ```yaml
   # TESTS/evaluation/ground_truth/pygoat.yml
   repo: pygoat
   url: https://github.com/adeyosemanputra/pygoat
   commit: <sha>  # pin for reproducibility
   language: python
   expected_findings:
     - id: pygoat-sqli-1
       cwe: CWE-89
       file: introduction/views.py
       line: 42
       canonical_id: SECURITY-027
       severity: high
       reachable_from: [introduction.views.sql_lab]  # for reachability validation
   recall_target: 0.95          # we expect to find 95%+ of these
   precision_target: 0.85
   ```
3. New test harness: `TESTS/evaluation/test_recall.py` runs ACR-QA against each, asserts recall ≥ target.
4. **Address DVPWA's 50% recall before the thesis defense** — the 3 misses are: hardcoded password, debug mode, CSRF. Two are detectable (hardcoded creds, debug mode). CSRF needs runtime context — accept the gap, document it, update DVPWA ground truth to mark CSRF as `out_of_scope: static_analysis_limit`.

#### 5.2 Clean Repos (FP Battery)

**Goal:** "On real, well-maintained code, do we stay quiet?"

**To do:**
1. Add ground truth files for Flask, httpx, requests, FastAPI, click — all real Python repos with known low real-vuln density.
2. Format:
   ```yaml
   # TESTS/evaluation/ground_truth/flask.yml
   repo: flask
   url: https://github.com/pallets/flask
   commit: <sha>
   language: python
   fp_threshold:
     high: 5      # >5 HIGH findings = test fails (likely FPs)
     medium: 30
     total: 100
   ```
3. The test:
   ```python
   def test_flask_fp_rate(repo_clone_flask):
       findings = run_acrqa_on(repo_clone_flask)
       high = [f for f in findings if f.severity == "high"]
       assert len(high) <= 5, f"FP regression on Flask: {len(high)} HIGH findings"
   ```
4. **Run nightly in CI**, not on every PR (too slow). Failure opens a GitHub issue automatically.

#### 5.3 Differential vs Raw Tools

**Goal:** "Do we lose any signal compared to running Bandit/Ruff/Semgrep raw?"

ACR-QA normalizes + dedups. Dedup is supposed to remove noise without losing real findings. We need to prove that.

**To do:**
- For each benchmark repo, run raw Bandit, Ruff, Semgrep separately. Save findings.
- Run ACR-QA. Save findings.
- Assert: every HIGH finding in the union of raw outputs appears in ACR-QA output (after canonical-ID translation). If a tool found `B608` (SQLi) but ACR-QA didn't surface `SECURITY-027`, that's a regression.

#### 5.4 Reachability Validation Harness (NEW — Week 2)

**Goal:** Prove the reachability engine actually works once it ships.

**Test fixture:** `TESTS/fixtures/reachability/`
```
TESTS/fixtures/reachability/
  reachable_sqli.py      # SQL injection inside a route handler — should be flagged
  unreachable_sqli.py    # SQL injection in a function never called — should be downgraded
  conditionally_reachable.py  # SQLi behind an if-False branch — should be flagged with caveat
```

**Tests:**
```python
def test_reachable_sqli_is_high():
    findings = run_acrqa_on("TESTS/fixtures/reachability/reachable_sqli.py")
    assert any(f.severity == "high" and f.canonical_id == "SECURITY-027" for f in findings)

def test_unreachable_sqli_is_downgraded():
    findings = run_acrqa_on("TESTS/fixtures/reachability/unreachable_sqli.py")
    sqli = next((f for f in findings if f.canonical_id == "SECURITY-027"), None)
    assert sqli is not None
    assert sqli.severity == "low"  # downgraded
    assert "not reachable from any entrypoint" in sqli.rationale
```

**This is the test that defends the §3.1 thesis claim.** Without it, "we built reachability" is unsubstantiated.

#### 5.5 Proof-of-Exploit Validation Harness (NEW — Week 4)

**Goal:** Prove the exploit verifier actually generates working exploits.

**Test fixture:** `TESTS/fixtures/exploits/`
```
TESTS/fixtures/exploits/
  flask_sqli/         # tiny Flask app with real SQLi — Dockerfile included
  flask_cmdi/         # tiny Flask app with command injection
  flask_ssti/         # tiny Flask app with SSTI
```

**Tests:**
```python
@pytest.mark.exploit  # only run on machines with Docker
def test_sqli_exploit_succeeds():
    result = run_exploit_verifier("TESTS/fixtures/exploits/flask_sqli")
    assert result.verified is True
    assert "version()" in result.evidence  # we got a SQL response back
    assert result.payload is not None

def test_safe_code_no_exploit():
    result = run_exploit_verifier("TESTS/fixtures/exploits/flask_safe")
    assert result.verified is False
    assert result.attempts > 0  # we tried, but no exploitation signal
```

#### 5.6 MCP Server Smoke Tests (NEW — Week 3)

**Goal:** Prove the MCP server speaks the protocol correctly.

```python
async def test_mcp_scan_tool():
    async with mcp_client(acrqa_mcp_server) as client:
        result = await client.call_tool("acrqa.scan", {"target_dir": "TESTS/samples/issues"})
        assert "job_id" in result
        # Poll
        for _ in range(30):
            status = await client.call_tool("acrqa.status", {"job_id": result["job_id"]})
            if status["status"] == "completed":
                break
            await asyncio.sleep(1)
        assert status["findings_count"] > 0
```

### Layer 6 — User Study (human validity)

5-8 participants. Documented in `docs/evaluation/USER_STUDY_PROTOCOL.md` + `USER_STUDY_SURVEY.md`. **Not engineering tests** — but the only layer that proves the *output* is useful, not just correct.

**Metrics to capture:**
- Time-to-fix per finding (with vs. without AI explanation)
- Self-reported confidence (1-5) in fix correctness
- "Would you use this in your team?" — Likert
- Open-ended: what was the most/least useful feature?

**Schedule:** Recruit Week 2 (DM 8 people, expect 5 yes). Run sessions Week 4-5. Compile Week 5.

---

## 4. The Metrics We Ship (Thesis Numbers)

These are the numbers that go into the thesis chapter and the defense slides. **Every one is generated by the evaluation harness above; none is fabricated.**

| Metric | Source | Target (v4.0.0) |
|---|---|---|
| Overall precision | Layer 5.1 + 5.2 | ≥ 97% |
| Overall recall | Layer 5.1 | ≥ 90% (up from 87% — DVPWA gap fix) |
| HIGH-severity FP rate on Flask | Layer 5.2 | < 5% (down from 10.3%) |
| HIGH-severity FP rate on httpx | Layer 5.2 | < 5% (down from ~9%) |
| OWASP Top 10 coverage | Layer 5.1 | 9/10 categories |
| Reachability lift | Layer 5.4 | -X% FPs vs no reachability (measure this!) |
| Verified-exploitable findings | Layer 5.5 | ≥ 2 categories (SQLi + CMDI) |
| Reachability validation tests | Layer 5.4 | 100% pass |
| Exploit verifier tests | Layer 5.5 | 100% pass |
| Snapshot tests | Layer 4 | 100% pass on every PR |
| User study completions | Layer 6 | ≥ 5 |

The thesis chapter on evaluation cites these numbers in a single sentence each, with the YAML/test that generated each as the appendix citation. **No hand-typed numbers anywhere.**

---

## 5. CI Integration

| Job | Frequency | What it runs | Time budget |
|---|---|---|---|
| `lint` | every PR | ruff + mypy + actionlint | < 30s |
| `unit` | every PR | Layer 2 (1,690 tests) | < 60s |
| `integration` | every PR | Layer 3 (FastAPI + Celery + DB) | < 90s |
| `snapshot` | every PR | Layer 4 (drift detection) | < 30s |
| `recall_smoke` | every PR | Layer 5.1, only on DSVW (smallest) | < 30s |
| `evaluation_full` | nightly | Layer 5.1 + 5.2 + 5.3 across all benchmarks | ≤ 30 min |
| `exploit_verify` | nightly | Layer 5.5 | ≤ 15 min |
| `coverage_drop_alert` | every PR | Fail if coverage drops > 2 percentage points | — |

**Coverage role:** Tripwire only. CI fails if coverage drops > 2 points; never targeted for "let's pump it to 90%."

---

## 6. The 6-Week Testing Schedule (Mapped to GOD_MODE_PLAN v2)

| Week | Feature work | Testing work | Why these happen together |
|---|---|---|---|
| **1** | Cleanup ✅ + Flask kill + tasks.py coverage | Move ground truth to YAML. Fix DVPWA recall (3 missing CWEs). Add Layer 1 no-CUSTOM-* test. Re-measure FP rate on Flask post-cleanup. | Without Week 1 testing fixes, we ship a thesis with a known 50% recall hole. |
| **2** | Reachability engine | Build Layer 5.4 reachability harness FIRST (TDD). Then build engine to make it pass. Measure FP lift. | Reachability without measurement = unproven claim. |
| **3** | MCP server + Learned suppression | Layer 5.6 MCP smoke tests. Snapshot tests on suppression behavior. | Suppression without snapshot = silent drift risk. |
| **4** | Proof-of-Exploit | Build Layer 5.5 exploit harness FIRST. Then engine. PoC against fixtures = the demo. | "We have exploit verification" needs a green test, not a vibe. |
| **5** | Provenance attestations + Railway deploy + User study runs | Add attestation verification test. Compile evaluation results across all benchmarks. Generate the metrics table. | All numbers must be reproducible by anyone who clones the repo. |
| **6** | v4.0.0 release + demo video + defense | Final eval run, snapshot lock, screenshot all charts. | The committee will scroll the README; everything must be evidence-backed. |

---

## 7. The Three Things That Change in How We Work

1. **Stop counting tests, start asking "what would fail if this broke?"** A test that doesn't catch a real failure is a liability — it adds runtime to CI without paying back.

2. **Ground truth lives in YAML, not Python.** Anyone (committee, future student) can `cat TESTS/evaluation/ground_truth/pygoat.yml` and audit the claim.

3. **Every thesis number has a test that generated it.** "97.1% precision" without a green test is a hand-typed number. With a green test, it's reproducible evidence. The committee distinguishes these.

---

## 8. What This Strategy Refuses to Do

- **No mutation testing** (mutmut/cosmic-ray). Interesting in theory, slow in practice, doesn't move the thesis needle.
- **No fuzzing the analyzer.** ACR-QA is not the attack surface; the *target* code is.
- **No load tests in this scope** (deferred — Locust is out-of-scope per `GOD_MODE_PLAN.md` v2).
- **No 90% coverage chase.** 85% is fine. Time invested in Layer 5 returns 100x more thesis value than Layer 2 expansion.
- **No K8s integration tests.** We don't deploy to K8s.

---

## 9. Open Questions (Document, Don't Hide)

1. **CSRF on DVPWA** — static analysis can't detect CSRF without runtime context. We accept this gap and document it. *Action:* mark `out_of_scope: static_analysis_limit` in DVPWA YAML; Section 1's "50% recall" becomes "100% recall on detectable categories."
2. **Hardcoded password regex on DVPWA** — Bandit B105/B106 should catch this. Why aren't we? *Action:* debug in Week 1.
3. **Debug mode detection** — Bandit B201 is the rule. Is it in our `RULE_MAPPING`? *Action:* check in Week 1.
4. **Exploit sandboxing safety** — running LLM-generated payloads in a container is non-trivial. *Action:* require `--network=none`, `--memory=128m`, `--cpus=0.5`, 30s timeout. Test the container itself never escapes.

---

*Strategy written May 5, 2026. Owner: Ahmed. Revisit at the end of every week — if a layer hasn't moved in 2 weeks, downgrade or drop.*
