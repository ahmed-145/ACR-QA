# ACR-QA God Mode Plan v2

**Author:** Rewritten May 5, 2026 after competitive audit + codebase reality check
**Target:** Graduation thesis defense (Jun 2026) + backend/DevOps career launchpad
**Version at rewrite:** v3.3.0 (FastAPI + Celery + Auth complete)
**Old plan:** archived at `docs/archive/GOD_MODE_PLAN_V1.md`

---

## 0. The Honest Read (v2)

v3.3.0 is genuinely solid: 1,690 tests, 85% coverage, FastAPI with 28 async endpoints, Celery background jobs, JWT + API key auth, Alembic migrations, SRE runbooks, Prometheus + Grafana. **The engineering fundamentals are done.**

What v1 of this plan got wrong: it optimized for resume bullets (Helm, Terraform, webhooks, multi-tenancy) — visible but generic. Every bootcamp project has a Helm chart. None of them have what competitors are paying teams of 50 to build, and still doing wrong.

**v2 bets on three things competitors are converging on + one category nobody owns.**

---

## 1. What Was Killed (Cleanup Done May 5)

| Removed | Why |
|---|---|
| `vscode-extension/` (26MB) | Stub that called Flask `/api/analyze`. Replaced by MCP server (§4) |
| `FRONTEND/static/dashboard.{html,css,js}` | Dead — `templates/index.html` is the real dashboard |
| `scripts/benchmark_models.py` | Never used in production or CI |
| `scripts/scale_benchmark.py` | Never used in production or CI |
| `scripts/post_gitlab_comments.py` | Repo is on GitHub, not GitLab |
| **Phase 2 TypeScript rewrite** (from ROADMAP) | Procrastination dressed as ambition — the Python core is correct |
| **Helm chart, Terraform, multi-tenancy, webhooks** (from v1 plan) | Generic resume-padding; 3 weeks of effort that buys zero differentiation |

## 2. What Needs Finishing (Before New Features)

These are claimed-done features that are actually broken or untested:

| Fix | File | Status |
|---|---|---|
| Celery coverage | `CORE/tasks.py` — **0% coverage** | Write integration tests; currently untestable = unshippable |
| Flask → FastAPI migration | `FRONTEND/app.py` still runs at :5000; `FRONTEND/api/main.py` at :8000 | Port `test_flask_app.py` (637 LOC) to FastAPI TestClient; delete Flask |
| Graceful API key degradation | `path_feasibility.py`, `ai_code_detector.py` silently fail without `GROQ_API_KEY` | Feature flags + clean degradation path |

**Do these in Week 1 before adding anything new.**

---

## 3. The Three Competitive Moats (What to Build)

Every serious competitor in 2026 — Snyk, Semgrep, Aikido, Endor, Greptile, CodeRabbit — converges on these three features. ACR-QA doesn't have any of them. Building all three in 3 weeks puts us ahead of where tools with $20M+ in funding sit on two of them.

### 3.1 Reachability-Gated Findings (Week 2)

**What competitors do:** Snyk, Semgrep Pro, Aikido, and Endor all suppress findings where the vulnerable sink is not reachable from an entrypoint. This is the single biggest noise-killer in the industry, and the #1 reason devs dismiss scanner output.

**What to build:**
- `CORE/engines/reachability.py` — builds a lightweight call graph from AST for Python (using `ast` + `jedi`), JS (using `@typescript-eslint/parser` via subprocess), and Go
- For each HIGH/MEDIUM finding: check if the sink function (`eval`, `subprocess.call`, raw SQL concat, etc.) is transitively callable from an entrypoint (`main`, route handler decorated with `@app.route`/`@router.get`, CLI entrypoint)
- If unreachable: downgrade finding to LOW with rationale `"sink not reachable from any entrypoint"`, don't suppress entirely
- Wire into pipeline between `normalizer.py` and `quality_gate.py`

**Thesis claim:** *"ACR-QA performs cross-procedural reachability analysis on its findings, reducing confirmed false positives by X% on benchmark repos. Snyk achieves this via proprietary dataflow; ACR-QA achieves it via open AST analysis."*

**Resume bullet:** *"Built call-graph reachability engine in Python + jedi; reduced FP rate from 10.3% to <5% on Flask/httpx benchmark repos."*

### 3.2 Embedding-Based Learned Suppression (Week 3)

**What competitors do:** Greptile v4 learns per-repo from 👍/👎 feedback; Semgrep Assistant auto-triages with 97% human agreement; CodeRabbit adapts to team review patterns.

**What ACR-QA has:** `triage_memory.py` writes exact-match suppression rules when a user marks a finding as FP. That's pattern-matching, not learning.

**What to build:**
- Extend `triage_memory.py`: when a finding is dismissed, embed its `(rule_id + code_snippet + file_context)` using `sentence-transformers` (local, free, 80MB, no API calls)
- On next scan: for each finding, compute cosine similarity against the dismissed embedding store; if similarity > 0.92, auto-downgrade confidence to 0 and annotate `"suppressed: similar to previously-dismissed finding"`
- Model: `all-MiniLM-L6-v2` — runs in <50ms per embedding, fits in RAM, no API keys
- New Alembic migration: `finding_embeddings` table (id, rule_id, embedding BLOB, suppressed_at, workspace_id)

**Thesis claim:** *"ACR-QA implements semantic deduplication via sentence-transformer embeddings. After 3 reviews of the same repo, FP rate drops to X% without manual rule-authoring."*

### 3.3 MCP Server — Pre-PR Integration (Week 3)

**What competitors do:** Semgrep runs inside Cursor as the AI writes code. CodeRabbit has an IDE extension. Every OSS AI coding agent (Continue, Cline, Aider, Claude Code) consumes MCP servers.

**What to build:** Replace the dead vscode-extension with an MCP server — 10x the reach, 1/10th the effort.

- New `acrqa-mcp/` package at repo root: `server.py` implementing the MCP protocol
- 3 exposed tools:
  - `acrqa.scan(target_dir: str) → ScanResult` — triggers async Celery scan, returns job ID
  - `acrqa.explain(finding_id: str) → Explanation` — returns AI explanation for a finding
  - `acrqa.fix(finding_id: str) → FixSuggestion` — returns autofix diff
- Distribute on PyPI: `pip install acrqa-mcp`
- Config: `~/.config/acrqa/config.json` with `ACRQA_URL` pointing at the running FastAPI server
- Works with Claude Code, Continue, Cursor — demo this in the thesis video

**Resume bullet:** *"Shipped ACR-QA as an MCP server on PyPI, enabling integration with Claude Code, Cursor, and Continue; security review runs as the AI generates code, not after."*

---

## 4. The Blue Ocean (What Nobody Owns)

These are categories where every serious competitor is weak or absent. Pick **at least one** to ship by Week 5. Both together is the thesis story that wins awards.

### 4.1 Proof-of-Exploit Engine (Week 4) — HIGH PRIORITY

**The gap:** Every competitor stops at "this looks vulnerable." Nobody ships a sandbox that *proves* the finding is exploitable.

**What to build:**
- `CORE/engines/exploit_verifier.py`
- Scope: SQLi, command injection, SSTI, path traversal (the 4 categories with reliable, automatable payloads)
- Workflow:
  1. For each HIGH finding in one of the 4 categories
  2. Use Groq LLM to generate a safe PoC payload (e.g., `'; SELECT version(); --`, `$(id)`, `{{7*7}}`, `../../etc/passwd`)
  3. Spin up an ephemeral Docker container with the user's code (`docker run --rm --network=none --memory=128m`)
  4. Execute the payload against the running app (via HTTP if it's a web app, via stdin if CLI)
  5. Capture stdout/stderr/HTTP response; look for exploitation signals (SQL data, command output, template eval result, file content)
  6. Emit `exploit_verified: true/false` + captured evidence on the finding

- **Output changes:** Finding now has three tiers: `unverified` → `verified-exploitable` → `verified-unexploitable`
- `verified-exploitable` findings get a `proof` field: `{ "payload": "...", "evidence": "SELECT version()...", "container_id": "...", "timestamp": "..." }`

**Why this wins:**
- Zero false positives on `verified-exploitable` findings
- Demo is unforgettable — show the cursor hovering over a SQL injection, then show ACR-QA executing the exploit in a sandbox
- No competitor ships this. Snyk has "reachability" to *reduce* FPs; we have *proof* to *eliminate* them
- Thesis chapter: "ACR-QA as the first DAST-augmented SAST via LLM-guided exploit generation"

**Safeguards (important):**
- `--network=none` on Docker container (no outbound)
- `--memory=128m`, `--cpus=0.5` resource caps
- Timeout: 30 seconds max
- Blocklist: never run against production URLs; only local `target_dir` code

### 4.2 Signed Provenance Attestations (Week 5) — MEDIUM PRIORITY

**The gap:** A CISO can't prove which version of which scanner reviewed which commit. Supply-chain security for the review pipeline itself is unaddressed by every competitor.

**What to build:**
- `CORE/engines/attestation.py`
- After every scan: generate a signed attestation in [in-toto](https://in-toto.io/) / SLSA format:
  ```json
  {
    "predicateType": "https://acrqa.io/scan/v1",
    "subject": { "sha1": "<commit_sha>" },
    "predicate": {
      "ruleset_version": "v3.4.0",
      "ai_model": "llama-3.3-70b-versatile",
      "findings_count": 12,
      "high_count": 2,
      "scan_timestamp": "2026-05-05T...",
      "reachability_enabled": true,
      "verified_exploitable": 1
    }
  }
  ```
- Sign with [Sigstore](https://www.sigstore.dev/) (`sigstore` Python package — free, no infra)
- **Bonus moat:** Add post-quantum signature using `pqcrypto` (Dilithium3 — NIST-standardized). 10 lines of code now → procurement checkbox in 18 months when NIST PQC mandates land.
- Store attestation in DB + expose at `GET /v1/runs/{id}/attestation`
- Verification: `acrqa verify --commit <sha>` prints the attestation + signature validity

**Thesis angle:** "ACR-QA emits SLSA-grade provenance attestations of the scan itself, signed with both classical (ECDSA-P256 via Sigstore) and post-quantum (Dilithium3) signatures. This closes the audit-log gap in existing SAST tooling."

---

## 5. The Don't-Do List (Updated)

These appeared in v1. They're still wrong.

| Do NOT build | Why |
|---|---|
| TypeScript rewrite | Procrastination. Python core is correct and tested. |
| Helm chart | You don't need K8s for the thesis. Docker Compose + Railway is sufficient. |
| Terraform | Same — Railway handles infra for thesis scope. |
| Kafka / NATS | Redis pub/sub and Celery handle everything you need. |
| Webhooks + outbox | Nice pattern, wrong priority when PoC engine isn't built yet. |
| Multi-tenancy | `workspace_id` FK is fine as a stub; don't build the enforcement layer yet. |
| GraphQL | REST + OpenAPI is more impressive than mediocre GraphQL. |
| Fine-tune your own model | AI explanation via Groq is the right amount of AI. |
| Microservices split | One service. Stay monolithic with clean module boundaries. |
| React/Vite frontend | The Tailwind SPA in `templates/index.html` is sufficient for thesis demo. |

---

## 6. The 6-Week Schedule (May 5 → Jun 16)

| Week | Focus | Key Deliverable | Thesis Impact |
|---|---|---|---|
| **1 (this week)** | Kill bloat + finish broken features | Cleanup PR merged. `CORE/tasks.py` at >80% coverage. Flask killed, FastAPI is the single server. ACR-QA runs clean on 3 fresh repos with updated metrics. | Thesis validity — project actually works end-to-end |
| **2** | Reachability engine | `CORE/engines/reachability.py` integrated. Re-run benchmarks. FP rate drops. | Core thesis claim: measurably fewer FPs than competitors |
| **3** | MCP server + Learned suppression | `acrqa-mcp` on PyPI. Embedding-based suppression active. | Demo-able in Claude Code for thesis video |
| **4** | Proof-of-Exploit engine | `CORE/engines/exploit_verifier.py`. At least SQLi + CMDI verified. | Unforgettable thesis demo — "here is the actual exploit" |
| **5** | Provenance attestations + Railway deploy + User study | Sigstore + Dilithium signatures. Live URL. 5+ user study participants complete. | Thesis chapter on attestations; live URL for committee |
| **6** | Polish: v4.0.0 release + demo video + defense prep | Tagged release. 5-min OBS recording. Defense slides done. | Submission-ready |

---

## 7. The "Are We Done" Checklist (Updated)

- [ ] Can a stranger run the project with one command? (`make up && make db-migrate && make seed-admin`)
- [ ] Is there a live URL anyone can hit? (Railway)
- [ ] Does CI deploy on every merge to main?
- [ ] Can I show a Grafana screenshot of real traffic?
- [ ] Is the FP rate on Flask/httpx below 5% (down from 10.3%)? (Reachability engine)
- [ ] Can I demo ACR-QA running inside Claude Code or Cursor? (MCP server)
- [ ] Can I show an exploit being executed in a sandboxed container? (PoC engine)
- [ ] Does every scan produce a signed attestation I can verify? (Provenance)
- [ ] Do I have 5+ user study participants with completed surveys?
- [ ] Is there a tagged v4.0.0 release with release notes?
- [ ] Is there a 5-min demo video?

When all 11 are checked: write the blog post, link from resume. Ship the thesis.

---

## 8. What Each New Feature Maps to in Interviews

| Feature | What they ask | What you say |
|---|---|---|
| Reachability engine | "How did you reduce false positives?" | "Cross-procedural call graph analysis via AST + jedi — same approach Snyk uses, built open-source." |
| MCP server | "How do you integrate with developer workflows?" | "Shipped as an MCP server on PyPI — works with Claude Code, Cursor, Continue. Security review runs pre-PR, inside the AI's context." |
| Proof-of-Exploit | "How is this different from Bandit?" | "Bandit finds patterns. ACR-QA proves the finding by executing a sandboxed exploit and capturing evidence." |
| Provenance attestations | "How do you handle compliance?" | "Every scan emits a SLSA-L3 attestation signed with Sigstore and Dilithium3 post-quantum signatures. CISO can prove which commit was reviewed by which ruleset." |
| Learned suppression | "How do you handle FP feedback?" | "Sentence-transformer embeddings on dismissed findings — future similar findings are auto-suppressed without writing suppression rules." |

---

## 9. Testing Strategy — Read This Before Writing Any Code

### 9.1 The Lesson — Why Coverage % Is The Wrong Target

We have **85% line coverage** and **1,690 passing tests**. Both numbers are misleading for a security analysis tool.

**Coverage measures whether lines RUN, not whether they FIND BUGS.** A test that calls `normalize_ruff(fake_input)` and asserts the result is a dict will run 200 lines without testing whether ACR-QA actually catches a SQL injection. You can build 100% coverage with tests that catch zero bugs. Coverage is a *tripwire* (sudden drops mean dead code or removed tests), not a *target*.

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
| `CORE/tasks.py` | Celery code | — | — | **0% coverage — claimed feature unverified** |

**Status:** strong on the easy benchmarks, **weak on DVPWA**, **stale on FP rate**. Without addressing DVPWA recall, the thesis claim "97.1% precision" is structurally fragile under defense questioning ("What about the 50% you missed?").

### 9.2 The Real Testing Pyramid for a Security Tool

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

### 9.3 Layer-By-Layer Plan

#### 9.3.1 Layer 1 — Static Guards (passive, already in CI)

ruff format, ruff check, mypy, pre-commit hooks. Catches typos, type bugs, dead imports.

**Add:** A test that fails CI if any pipeline output contains `CUSTOM-*` (means a rule isn't in `RULE_MAPPING`). This was a recurring bug — let's make it impossible to ship.

```python
# TESTS/test_no_custom_rules.py
def test_no_custom_rules_on_benchmark():
    findings = run_acrqa_on("test_targets/eval-repos/dsvw")
    custom = [f for f in findings if f.canonical_id.startswith("CUSTOM-")]
    assert custom == [], f"Unmapped rules leaked into output: {custom}"
```

#### 9.3.2 Layer 2 — Unit Tests (the regression net)

**Have:** 1,690 tests, 85% coverage. **Status: keep, do not grow without reason.** We don't need 2,000 unit tests.

**Fix:**
- `CORE/tasks.py` — **0% coverage**, currently a paper feature. Add 5-10 integration tests that actually invoke a Celery worker and verify task lifecycle.
- Property-based tests for `normalizer.py` using `hypothesis`: any valid Bandit/Ruff/Semgrep JSON should not crash. Catches edge cases we'll never hand-write.

**Don't:** Write more unit tests just to pump coverage to 90%. Time is better spent on Layer 5.

#### 9.3.3 Layer 3 — Integration Tests (real subprocess, no mocks)

**Have:** ~15 tests in `test_integration_benchmarks.py`. Most actually invoke Ruff/Bandit/Semgrep.

**Missing:**
- An end-to-end FastAPI test: `POST /v1/scans → 202 → poll /v1/scans/{id} → assert findings shape`
- A Celery worker test: spin up a real worker, dispatch `run_analysis_task`, assert result
- A DB test: insert a finding, query it back, assert schema match

```python
# TESTS/integration/test_fastapi_e2e.py
@pytest.mark.integration
def test_async_scan_lifecycle(api_client, celery_worker):
    token = login_admin(api_client)
    r = api_client.post("/v1/scans", json={"target_dir": "TESTS/samples/comprehensive-issues"},
                        headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 202
    job_id = r.json()["job_id"]
    for _ in range(30):
        r = api_client.get(f"/v1/scans/{job_id}", headers={"Authorization": f"Bearer {token}"})
        if r.json()["status"] in ("completed", "failed"):
            break
        time.sleep(1)
    assert r.json()["status"] == "completed"
    assert r.json()["findings_count"] > 0
```

**CI:** every PR. Test must complete in <60s.

#### 9.3.4 Layer 4 — Snapshot Tests (catch silent drift)

Run ACR-QA on a fixed corpus, save the output JSON, commit it. On future runs, diff. If the output changes, fail the test and force the developer to either accept the change (`--update-snapshots`) or fix the regression.

**Have:** nothing. Every refactor risks silently changing finding output until a thesis demo goes wrong.

**Add:**
```python
# TESTS/snapshot/test_snapshot_dsvw.py
def test_dsvw_snapshot():
    findings = run_acrqa_on("test_targets/eval-repos/dsvw", deterministic=True)
    expected = json.load(open("TESTS/snapshot/dsvw_expected.json"))
    assert findings == expected, "DSVW output drifted — review and update snapshot"
```

Plus a `--update-snapshots` pytest flag to regenerate when changes are intentional.

#### 9.3.5 Layer 5 — Evaluation Benchmarks (THE THESIS)

This is the work that proves ACR-QA actually works. **Everything else is plumbing for this layer.**

##### 9.3.5.1 Vulnerable Repos (Recall Battery)

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
   recall_target: 0.95
   precision_target: 0.85
   ```
3. New test harness: `TESTS/evaluation/test_recall.py` runs ACR-QA against each, asserts recall ≥ target.
4. **Address DVPWA's 50% recall before the thesis defense** — the 3 misses are hardcoded password (B105/B106), debug mode (B201), CSRF. The first two are detectable. CSRF needs runtime context — accept the gap, mark it `out_of_scope: static_analysis_limit` in YAML.

##### 9.3.5.2 Clean Repos (FP Battery)

**Goal:** "On real, well-maintained code, do we stay quiet?"

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

```python
def test_flask_fp_rate(repo_clone_flask):
    findings = run_acrqa_on(repo_clone_flask)
    high = [f for f in findings if f.severity == "high"]
    assert len(high) <= 5, f"FP regression on Flask: {len(high)} HIGH findings"
```

**Run nightly in CI**, not on every PR (too slow). Failure opens a GitHub issue automatically.

##### 9.3.5.3 Differential vs Raw Tools

**Goal:** "Do we lose any signal compared to running Bandit/Ruff/Semgrep raw?"

ACR-QA normalizes + dedups. Dedup is supposed to remove noise without losing real findings. We need to prove that.

For each benchmark repo: run raw Bandit, Ruff, Semgrep separately. Run ACR-QA. Assert: every HIGH finding in the union of raw outputs appears in ACR-QA output (after canonical-ID translation). If a tool found `B608` (SQLi) but ACR-QA didn't surface `SECURITY-027`, that's a regression.

##### 9.3.5.4 Reachability Validation Harness (NEW — Week 2)

**Goal:** Prove the reachability engine actually works once it ships.

Test fixture `TESTS/fixtures/reachability/`:
```
reachable_sqli.py            # SQLi inside a route handler — should be flagged HIGH
unreachable_sqli.py          # SQLi in a function never called — should be downgraded LOW
conditionally_reachable.py   # SQLi behind an if-False branch — should be flagged with caveat
```

```python
def test_reachable_sqli_is_high():
    findings = run_acrqa_on("TESTS/fixtures/reachability/reachable_sqli.py")
    assert any(f.severity == "high" and f.canonical_id == "SECURITY-027" for f in findings)

def test_unreachable_sqli_is_downgraded():
    findings = run_acrqa_on("TESTS/fixtures/reachability/unreachable_sqli.py")
    sqli = next((f for f in findings if f.canonical_id == "SECURITY-027"), None)
    assert sqli is not None
    assert sqli.severity == "low"
    assert "not reachable from any entrypoint" in sqli.rationale
```

**This is the test that defends the §3.1 thesis claim.** Without it, "we built reachability" is unsubstantiated.

##### 9.3.5.5 Proof-of-Exploit Validation Harness (NEW — Week 4)

**Goal:** Prove the exploit verifier actually generates working exploits.

Test fixture `TESTS/fixtures/exploits/`:
```
flask_sqli/    # tiny Flask app with real SQLi — Dockerfile included
flask_cmdi/    # command injection
flask_ssti/    # server-side template injection
flask_safe/    # control: no vuln, must NOT verify-exploit
```

```python
@pytest.mark.exploit
def test_sqli_exploit_succeeds():
    result = run_exploit_verifier("TESTS/fixtures/exploits/flask_sqli")
    assert result.verified is True
    assert "version()" in result.evidence
    assert result.payload is not None

def test_safe_code_no_exploit():
    result = run_exploit_verifier("TESTS/fixtures/exploits/flask_safe")
    assert result.verified is False
    assert result.attempts > 0
```

##### 9.3.5.6 MCP Server Smoke Tests (NEW — Week 3)

```python
async def test_mcp_scan_tool():
    async with mcp_client(acrqa_mcp_server) as client:
        result = await client.call_tool("acrqa.scan", {"target_dir": "TESTS/samples/issues"})
        assert "job_id" in result
        for _ in range(30):
            status = await client.call_tool("acrqa.status", {"job_id": result["job_id"]})
            if status["status"] == "completed":
                break
            await asyncio.sleep(1)
        assert status["findings_count"] > 0
```

#### 9.3.6 Layer 6 — User Study (human validity)

5-8 participants. Documented in `docs/evaluation/USER_STUDY_PROTOCOL.md` + `USER_STUDY_SURVEY.md`. **Not engineering tests** — but the only layer that proves the *output* is useful, not just correct.

**Metrics to capture:**
- Time-to-fix per finding (with vs. without AI explanation)
- Self-reported confidence (1-5) in fix correctness
- "Would you use this in your team?" — Likert
- Open-ended: most/least useful feature?

**Schedule:** Recruit Week 2 (DM 8 people, expect 5 yes). Run sessions Week 4-5. Compile Week 5.

### 9.4 The Metrics We Ship (Thesis Numbers)

These are the numbers that go into the thesis chapter and the defense slides. **Every one is generated by the evaluation harness above; none is fabricated.**

| Metric | Source | Target (v4.0.0) |
|---|---|---|
| Overall precision | §9.3.5.1 + §9.3.5.2 | ≥ 97% |
| Overall recall | §9.3.5.1 | ≥ 90% (up from 87% — DVPWA gap fix) |
| HIGH-severity FP rate on Flask | §9.3.5.2 | < 5% (down from 10.3%) |
| HIGH-severity FP rate on httpx | §9.3.5.2 | < 5% (down from ~9%) |
| OWASP Top 10 coverage | §9.3.5.1 | 9/10 categories |
| Reachability lift | §9.3.5.4 | -X% FPs vs no reachability (measure!) |
| Verified-exploitable findings | §9.3.5.5 | ≥ 2 categories (SQLi + CMDI) |
| Reachability validation tests | §9.3.5.4 | 100% pass |
| Exploit verifier tests | §9.3.5.5 | 100% pass |
| Snapshot tests | §9.3.4 | 100% pass on every PR |
| User study completions | §9.3.6 | ≥ 5 |

The thesis chapter on evaluation cites these numbers in a single sentence each, with the YAML/test that generated each as the appendix citation. **No hand-typed numbers anywhere.**

### 9.5 CI Integration

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

### 9.6 Six-Week Testing Schedule (Mapped to §6 Feature Schedule)

| Week | Feature work | Testing work |
|---|---|---|
| **1** | Cleanup ✅ + Flask kill + tasks.py coverage | Move ground truth to YAML. Fix DVPWA recall (3 missing CWEs). Add Layer 1 no-CUSTOM-* test. Re-measure FP rate on Flask post-cleanup. |
| **2** | Reachability engine | Build §9.3.5.4 reachability harness FIRST (TDD). Then build engine to make it pass. Measure FP lift. |
| **3** | MCP server + Learned suppression | §9.3.5.6 MCP smoke tests. Snapshot tests on suppression behavior. |
| **4** | Proof-of-Exploit | Build §9.3.5.5 exploit harness FIRST. Then engine. PoC against fixtures = the demo. |
| **5** | Provenance + Railway + User study | Add attestation verification test. Compile evaluation results across all benchmarks. Generate the metrics table. |
| **6** | v4.0.0 release + demo video + defense | Final eval run, snapshot lock, screenshot all charts. |

### 9.7 Three Things That Change in How We Work

1. **Stop counting tests, start asking "what would fail if this broke?"** A test that doesn't catch a real failure is a liability — it adds runtime to CI without paying back.

2. **Ground truth lives in YAML, not Python.** Anyone (committee, future student) can `cat TESTS/evaluation/ground_truth/pygoat.yml` and audit the claim.

3. **Every thesis number has a test that generated it.** "97.1% precision" without a green test is a hand-typed number. With a green test, it's reproducible evidence. The committee distinguishes these.

### 9.8 What This Strategy Refuses to Do

- **No mutation testing** (mutmut/cosmic-ray). Interesting in theory, slow in practice, doesn't move the thesis needle.
- **No fuzzing the analyzer.** ACR-QA is not the attack surface; the *target* code is.
- **No load tests in this scope** (Locust deferred per §5).
- **No 90% coverage chase.** 85% is fine. Time invested in Layer 5 returns 100x more thesis value than Layer 2 expansion.
- **No K8s integration tests.** We don't deploy to K8s.

### 9.9 Open Questions (Document, Don't Hide)

1. **CSRF on DVPWA** — static analysis can't detect CSRF without runtime context. We accept this gap and document it. *Action:* mark `out_of_scope: static_analysis_limit` in DVPWA YAML; §9.1's "50% recall" becomes "100% recall on detectable categories."
2. **Hardcoded password regex on DVPWA** — Bandit B105/B106 should catch this. Why aren't we? *Action:* debug Week 1.
3. **Debug mode detection** — Bandit B201 is the rule. Is it in our `RULE_MAPPING`? *Action:* check Week 1.
4. **Exploit sandboxing safety** — running LLM-generated payloads in a container is non-trivial. *Action:* require `--network=none`, `--memory=128m`, `--cpus=0.5`, 30s timeout. Test the container itself never escapes.

### 9.10 Week 1 Must-Fix Checklist (Before Any New Feature)

- [ ] Move ground truth YAML files into `TESTS/evaluation/ground_truth/`
- [ ] Investigate why DVPWA hardcoded password (B105/B106) and debug mode (B201) aren't being caught
- [ ] Mark CSRF as `out_of_scope: static_analysis_limit`
- [ ] Add `test_no_custom_rules.py`
- [ ] Re-run Flask + httpx + requests benchmarks post-cleanup; capture honest current FP numbers
- [ ] Write 5-10 integration tests against `CORE/tasks.py` (Celery worker lifecycle)

---

## 10. Key Numbers to Beat (Evaluation Targets)

| Metric | Current (v3.3.0) | Target (v4.0.0) |
|---|---|---|
| FP rate on Flask | 10.3% | < 5% (reachability engine) |
| FP rate on httpx | ~9% | < 5% |
| Precision overall | 97.1% | 98%+ |
| Verified-exploitable findings | 0 (not built) | ≥2 categories (SQLi + CMDI) |
| Test coverage | 85% | 88%+ |
| Signed attestations | 0 | 100% of scans |
| MCP server tools | 0 | 3 (scan, explain, fix) |

---

*Plan written May 5, 2026. Revisit every 2 weeks. If a section is untouched for 2 weeks, delete it — momentum beats planning.*
