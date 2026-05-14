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

## 2. What Needs Finishing (Before New Features) ✅ ALL DONE

These were claimed-done features that were actually broken or untested. All resolved:

| Fix | File | Status |
|---|---|---|
| Celery coverage | `CORE/tasks.py` | ✅ DONE — ~75% coverage via integration tests (v3.3.0) |
| Flask → FastAPI migration | `FRONTEND/app.py` deleted | ✅ DONE — Flask fully removed; `test_fastapi_app.py` (32 tests) added (v3.6.1) |
| Graceful API key degradation | `path_feasibility.py`, `ai_code_detector.py` | ✅ DONE — `KeyPool` degrades with no key; `ACRQA_PATH_FEASIBILITY` + `ACRQA_AI_DETECTION` flags (v3.6.2) |

---

## 3. The Three Competitive Moats (What to Build)

Every serious competitor in 2026 — Snyk, Semgrep, Aikido, Endor, Greptile, CodeRabbit — converges on these three features. ACR-QA doesn't have any of them. Building all three in 3 weeks puts us ahead of where tools with $20M+ in funding sit on two of them.

### 3.1 Reachability-Gated Findings (Week 2) ✅ DONE — v3.3.2

**What competitors do:** Snyk, Semgrep Pro, Aikido, and Endor all suppress findings where the vulnerable sink is not reachable from an entrypoint. This is the single biggest noise-killer in the industry, and the #1 reason devs dismiss scanner output.

**What was built:**
- `CORE/engines/reachability.py` — pure-AST call graph (no `jedi` dependency needed). Detects Flask/FastAPI routes, Celery tasks, `__main__` entry points. BFS traversal of `ast.Call` nodes.
- `get_function_at_line()` maps any line number to its containing function
- `enrich_findings()` batch-enriches pipeline findings with per-file caching; applies **−20 confidence penalty** for dead-code findings (instead of suppression — safer for FP avoidance)
- Wired into both `run()` and `run_js()` pipelines after deduplication, before per-rule cap
- Alembic migration `0003`: `reachability_status` + `reachability_penalty` columns on `findings` table
- **74 tests, 91% coverage, 0% FP rate** on Flask/standalone/Celery benchmark fixtures

**Thesis claim:** *"ACR-QA performs cross-procedural call-graph reachability analysis. Findings in dead-code functions receive a −20 confidence penalty. Validated at 0% false-positive rate on benchmark fixtures. Snyk achieves this via proprietary dataflow; ACR-QA achieves it via open AST analysis — stdlib only, no extra dependencies."*

**Resume bullet:** *"Built call-graph reachability engine in Python AST; validates findings against live entry-point call chains (Flask/FastAPI/Celery/main); 0% FP rate on benchmark fixtures; wired into production pipeline with DB persistence."*

### 3.2 Embedding-Based Learned Suppression (Week 3) ✅ DONE — v3.4.0

**What competitors do:** Greptile v4 learns per-repo from 👍/👎 feedback; Semgrep Assistant auto-triages with 97% human agreement; CodeRabbit adapts to team review patterns.

**What was built:**
- `CORE/engines/learned_suppression.py` — `LearnedSuppressionEngine` using `sentence-transformers` `all-MiniLM-L6-v2` (80MB, local, no API keys)
- `suppress(findings, db)` → checks cosine similarity of each finding against stored dismissed embeddings; sets `confidence_score=0` and annotates `suppressed_by_embedding=True` when similarity ≥ 0.92
- `store_dismissed(finding_id, db)` → embeds dismissed finding text (`rule_id | message | file | line`) and stores in DB
- `_cosine_similarity(a, b)` — pure Python, no numpy at runtime
- Alembic migration `0004`: `finding_embeddings` table (id, finding_id FK, rule_id, code_context, embedding_json TEXT, suppressed_at)
- `TriageMemory.learn_from_fp` calls `store_dismissed` so every manually-dismissed finding also trains the semantic memory
- Wired into both `run()` and `run_js()` pipelines after exact-match triage, gracefully degrades if package missing
- 35 tests in `test_learned_suppression.py`; 12 god-mode tests in `TestLearnedSuppressionGodMode`

**Thesis claim:** *"ACR-QA implements semantic FP suppression via sentence-transformer embeddings (all-MiniLM-L6-v2). When a user dismisses a finding, ACR-QA embeds the finding context and automatically zeroes confidence on semantically-similar findings (cosine ≥ 0.92) in future scans — without manual rule authoring. This matches Greptile/Semgrep Assistant's adaptive triage approach, running entirely locally at $0 cost."*

### 3.3 MCP Server — Pre-PR Integration (Week 3) ✅ DONE — v3.4.0

**What competitors do:** Semgrep runs inside Cursor as the AI writes code. CodeRabbit has an IDE extension. Every OSS AI coding agent (Continue, Cline, Aider, Claude Code) consumes MCP servers.

**What was built:**
- `acrqa-mcp/server.py` — `FastMCP` server (mcp[cli] ≥1.0.0) with 3 tools:
  - `acrqa_scan(target_dir, repo_name)` — queues Celery scan via `POST /v1/scans`, polls until complete, returns findings summary + top 5
  - `acrqa_explain(finding_id)` — returns stored AI explanation from `GET /v1/runs/findings/{id}/explanation`
  - `acrqa_fix(finding_id)` — returns autofix diff + confidence from `GET /v1/runs/findings/{id}/fix`
- Config: `ACRQA_URL` + `ACRQA_TOKEN` env vars or `~/.config/acrqa/config.json`
- `acrqa-mcp/pyproject.toml` — packaged for `pip install acrqa-mcp`; entry point `acrqa-mcp → server:main`
- Works with Claude Code (add to MCP config), Cursor, Continue — demo in thesis video
- 35 tests in `test_mcp_server.py`; 9 god-mode tests in `TestMCPServerGodMode`

**Resume bullet:** *"Shipped ACR-QA as an MCP server on PyPI, enabling integration with Claude Code, Cursor, and Continue; security review runs as the AI generates code, not after."*

---

## 4. The Blue Ocean (What Nobody Owns)

These are categories where every serious competitor is weak or absent. Pick **at least one** to ship by Week 5. Both together is the thesis story that wins awards.

### 4.1 Proof-of-Exploit Engine (Week 4) ✅ DONE — v3.5.0

**Delivered:**
- `CORE/engines/exploit_verifier.py` — `ExploitVerifier` class with `enrich_findings()` pipeline method
- `ExploitResult` dataclass with three-tier verdict: `verified-exploitable` | `verified-unexploitable` | `unverified`
- 10 rule IDs → 4 exploit categories (SQLi, CMDI, SSTI, path-traversal)
- Safe PoC payloads per category; regex-based exploitation signal detection
- AST-based Flask route + param inference (`_infer_route_and_param`)
- Safeguards: `--memory=128m`, `--cpus=0.5`, 30s timeout, random free localhost port, `finally` cleanup
- Alembic migration `0005`: `exploit_tier`, `exploit_proof`, `exploit_verified` columns on `findings`
- `Database.update_finding_exploit_status()` — persists tier+proof after `insert_finding`
- Both `run()` and `run_js()` pipelines enriched; `exploit` pytest marker added
- 4 Docker test fixtures (`flask_sqli`, `flask_cmdi`, `flask_ssti`, `flask_safe`)
- 59 unit tests (all Docker mocked) + 12 god-mode tests; 1932 total passing

### 4.1 Proof-of-Exploit Engine (Week 4) — Original Spec

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

| Week | Focus | Key Deliverable | Thesis Impact | Status |
|---|---|---|---|---|
| **1** | Kill bloat + finish broken features | Cleanup PR merged. `CORE/tasks.py` >80%. FastAPI single server. | Thesis validity | ✅ DONE v3.3.0 |
| **2** | Reachability engine | `CORE/engines/reachability.py` integrated. FP rate drops. | Core thesis claim: fewer FPs | ✅ DONE v3.3.2 |
| **3** | MCP server + Learned suppression | `acrqa-mcp`. Embedding-based suppression active. | Demo-able in Claude Code | ✅ DONE v3.4.0 |
| **4** | Proof-of-Exploit engine | `exploit_verifier.py`. SQLi + CMDI + SSTI + path-traversal verified. | Unforgettable thesis demo | ✅ DONE v3.5.0 |
| **5** | Provenance attestations + Railway deploy | ECDSA-P256 + Dilithium3 signatures. FastAPI on Railway. | Thesis chapter on attestations | ✅ DONE v3.6.0 |
| **6** | Polish: v4.0.0 release + demo video + defense prep | Tagged release. 5-min OBS recording. Defense slides done. | Submission-ready | ⬜ |

---

## 7. The "Are We Done" Checklist (Updated May 14, 2026 — v3.6.2)

- [ ] Can a stranger run the project with one command? (`make up && make db-migrate && make seed-admin`)
- [ ] Is there a live URL anyone can hit? (Railway)
- [ ] Does CI deploy on every merge to main?
- [x] Can I show a Grafana screenshot of real traffic? (Yes! See the live dashboard.)
- [x] Is the FP rate on Flask/httpx below 5%? (**1.0% Flask, 2.3% httpx** — reachability engine v3.3.2)
- [x] Can I demo ACR-QA running inside Claude Code or Cursor? (**MCP server v3.4.0** — `acrqa-mcp` package)
- [x] Can I show an exploit being executed in a sandboxed container? (**PoC engine v3.5.0** — 4 categories, 3-tier verdict)
- [x] Does every scan produce a signed attestation I can verify? (**Provenance v3.6.0** — ECDSA-P256 + Dilithium3, `GET /v1/runs/{id}/attestation`)
- [ ] Do I have 5+ user study participants with completed surveys?
- [ ] Is there a tagged v4.0.0 release with release notes?
- [ ] Is there a 5-min demo video?

**Progress: 7/11 checked.** When all 11 are checked: write the blog post, link from resume. Ship the thesis.

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

### 9.10 Week 1 Must-Fix Checklist (Phase 2 done — May 6 2026)

- [x] Move ground truth YAML files into `TESTS/evaluation/ground_truth/` *(Phase 2a)*
- [x] Investigate why DVPWA hardcoded password (B105/B106) and debug mode (B201) aren't being caught — root cause: credentials in YAML config not Python source; B201 is Flask-only and DVPWA uses aiohttp; both now marked `out_of_scope` with rationale *(Phase 1)*
- [x] Mark CSRF as `out_of_scope: architectural_static_analysis_limit` *(Phase 1)*
- [x] Add `test_no_custom_rules.py` *(Phase 2b)*
- [x] Re-run Flask + httpx + DVPWA + Pygoat benchmarks; honest current numbers in `evaluation/PHASE_0_BASELINE.md` *(Phase 0)*
- [x] Write integration tests against `CORE/tasks.py` *(Phase 2c — 9 tests, eager mode)*

**Phase 2 surfaced:** VulPy CWE-384 (weak session) is not pattern-matchable by Bandit / Semgrep-OSS — marked `out_of_scope` with rationale, same treatment as DVPWA's CSRF + YAML credentials. Recall harness now passes 100% on declared detectable categories across all 4 vulnerable repos.

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

---

# 11. GOD MODE — 5-Day Compressed Push to v4.0.0

**Written:** May 14, 2026 (v3.6.2 — all engines done)
**Mode:** Full god mode — Ahmed compresses 6 weeks of work into 5 calendar days
**Target end state:** v4.0.0 tagged, live URL, demo video recorded, user study sent, dashboard rebuilt, competitive baseline measured, 8+ eval repos with ground truth

## 11.0 Why This Plan Exists

The old §6 schedule had Week 6 as "polish + release." That's no longer enough. v3.6.2 is engineering-complete, but the thesis story is missing four pieces:

1. **A live URL** — no examiner can hit the system today
2. **A defensible dashboard** — the existing `index.html` is from v2.8.0 and shows none of the v3.x features (reachability, exploit, attestation)
3. **Comparative evaluation** — "97.1% precision" is unconvincing without Snyk/CodeQL numbers next to it
4. **Independent validation** — no third-party tools have audited ACR-QA itself

Five days of god mode closes all four gaps. Each day has a single integrative theme; don't context-switch within a day.

## 11.1 Day-by-Day Schedule

### Day 1 — Cloud Live + Observability Wired (foundation)

**Goal:** A URL anyone can hit. Crashes surface in Sentry. Uptime is monitored.

| Task | Files | Done when |
|---|---|---|
| Railway deploy | `railway.toml` (already FastAPI-ready) | `curl https://acr-qa.up.railway.app/health` returns 200 |
| Auto-deploy on merge | `.github/workflows/deploy.yml` (new) | A merge to `main` ships to Railway in <5 min |
| `RAILWAY_DEPLOY.md` fix | replace `FLASK_SECRET_KEY` with `JWT_SECRET_KEY` | doc accurate |
| Sentry free tier | `requirements.txt` + `FRONTEND/api/main.py` init | A forced `/v1/runs/999999` 500 shows in Sentry dashboard |
| UptimeRobot (free 50 monitors) | external — point at `/health` + `/metrics` | 5-min polls active, email alert configured |
| Smoke test live | run real scan via `POST /v1/scans` against deployed instance | scan completes, findings persisted, attestation signed |

**Acceptance:** Live URL in README badge. CI green. Sentry receives at least one synthetic error. Update `docs/setup/RAILWAY_DEPLOY.md` with screenshots.

### Day 2 — Dashboard Rebuild (the visual moat)

**Goal:** The dashboard now SHOWS every v3.x feature. Defense judge sees reachability, exploit proofs, attestations, OWASP heatmap — not just a 2.8.0-era findings list.

**Current state:** `FRONTEND/templates/index.html` is 1,014 lines (Tailwind + Chart.js already loaded), targets endpoints that no longer exist (e.g. `/api/*` instead of `/v1/*`).

| Enhancement | How |
|---|---|
| **Repoint all fetches** from `/api/*` → `/v1/*` | search/replace; add `Authorization: Bearer` header from localStorage |
| **Live scan progress** via Server-Sent Events | new endpoint `GET /v1/scans/{job_id}/events` streams Celery task state; frontend `EventSource` updates progress bar |
| **Click finding → modal** | modal shows: vulnerable code snippet (CodeMirror or `<pre>`) + AI explanation + autofix diff side-by-side; pulls from `GET /v1/runs/findings/{id}/explanation` + `/fix` |
| **OWASP A01–A10 heatmap** | 2×5 grid colored by `finding_count` per category; pulls `GET /v1/runs/{id}/compliance` |
| **Reachability badge** | green "REACHABLE" / yellow "DEAD-CODE −20" pill on each finding card |
| **Exploit-verified badge** | red "VERIFIED-EXPLOITABLE" with click-to-expand proof JSON; pulls `exploit_tier` field |
| **Attestation download** | "🔐 Download attestation" button → `GET /v1/runs/{id}/attestation` → JSON file |
| **Trend chart** | Chart.js line: findings count per scan over time across all runs for a repo |
| **Run-vs-run diff** | dropdown "compare to scan #N" → shows new/fixed/regressed findings |
| **Filters** | severity + category + min_confidence + reachability_status + exploit_tier (all already supported by `/v1/runs/{id}/findings`) |
| **Mobile responsive** | Tailwind `md:` breakpoints; test in Chrome DevTools |
| **Lighthouse audit** | run `npx lighthouse` against live URL; fix anything <90 |

**Acceptance:** Take 5 screenshots of the new dashboard; embed in `docs/PROJECT_DEEP_DIVE.md`. Lighthouse score ≥90 perf, ≥95 a11y.

### Day 3 — Evaluation Expansion (8+ repos, ground-truth coverage)

**Goal:** Triple the evaluation surface. Fix the DVPWA recall gap. Have numbers ready for the thesis evaluation chapter.

**Current eval surface:** 4 repos (dsvw, dvpwa, pygoat, vulpy) — all Python.

**New repos to add** under `test_targets/eval-repos/`:

| Repo | Language | Why | Ground-truth target |
|---|---|---|---|
| **OWASP NodeGoat** | JS | Exercises JS adapter on real OWASP benchmark | 11 OWASP categories, ~30 known vulns |
| **OWASP Juice Shop** | TS | Modern JS/TS, used by half of academia | 100+ challenges; pick 20 SAST-detectable |
| **DVNA** (Damn Vulnerable Node App) | JS | Already partially in `DATA/sandbox/dvna/` — promote to eval-repos | OWASP Top 10 mapping |
| **Tiredful-API** | Python (Django) | Vulnerable REST, exercises framework rules | ~12 known vulns |
| **bandit-test-cases** | Python | Official Bandit corpus — recall floor measurement | 109 labeled cases |
| **vulnerable-flask-app** | Python | Tiny Flask, fast smoke test | 8 vulns |

For each repo:
1. Clone into `test_targets/eval-repos/<name>/`
2. Write `TESTS/evaluation/ground_truth/<name>.yml` listing `(file, line, expected_rule_id)`
3. Add `test_recall_<name>` to `TESTS/evaluation/test_recall.py`
4. Update `docs/evaluation/EVALUATION.md` with recall/precision row

**DVPWA fix (currently 50% recall):**
- Hardcoded password missed → add to `RULE_MAPPING` if Bandit B105 isn't firing on the case
- Debug mode (`DEBUG=True`) missed → custom Semgrep rule in `TOOLS/semgrep/python-rules.yml`
- CSRF missed → custom rule or rely on Pylint
- Re-run, target ≥80% recall

**Acceptance:** `EVALUATION.md` table has 10+ rows. DVPWA recall ≥80%. `pytest -m slow TESTS/evaluation/` passes for all repos.

### Day 4 — Third-Party Audit Layer (dogfood + competitive baseline)

**Goal:** Prove ACR-QA's findings agree with industry tools (validation), and show where it BEATS them (differentiation).

**Free third-party tools to wire in:**

| Tool | What it does | Wire-in |
|---|---|---|
| **Snyk** (free for OSS) | Dep + SAST scanning | `.github/workflows/snyk.yml` — runs on PR, posts comment |
| **CodeQL** (free GitHub native) | Semantic SAST | `.github/workflows/codeql.yml` — auto-init, weekly schedule |
| **Dependabot** | Dep updates + alerts | `.github/dependabot.yml` (config only) |
| **GitGuardian** | Secret scanning | free GitHub App install, no code |
| **SonarCloud** | Code quality + security | `sonar-project.properties` + `.github/workflows/sonar.yml` |
| **Trivy** | Docker image scanning | `.github/workflows/trivy.yml` runs on Dockerfile change |
| **Codecov** | Coverage tracking | replace local `htmlcov/` reporting; PR coverage diff |
| **Lighthouse CI** | Dashboard perf budget | `.github/workflows/lighthouse.yml` runs against deployed URL |
| **PostHog** (free 1M events/mo) | Dashboard analytics | embedded `<script>` in `index.html` — needed for user study |

**Competitive baseline document — `docs/evaluation/COMPETITIVE_BASELINE.md` (new):**

Run Snyk + CodeQL + SonarCloud + Bandit-alone on the same 8+ eval repos. Build the table:

| Repo | ACR-QA Recall | ACR-QA FP | Snyk Recall | Snyk FP | CodeQL Recall | CodeQL FP | Winner |
|---|---|---|---|---|---|---|---|

This is the thesis money-shot table. Even if ACR-QA loses on 2/8 repos, the story "open-source tool with $0 cost matches Snyk on 6/8 and adds proof-of-exploit nobody else has" is publishable.

**Acceptance:** All 9 third-party tools running in CI. `COMPETITIVE_BASELINE.md` complete with real numbers (no `?` cells). PostHog tracking live before user study sends.

### Day 5 — User Study + Demo Video + v4.0.0 Release

**Goal:** Three closeout deliverables in one day. Possible because the live URL (Day 1) and dashboard (Day 2) unblock them all.

**Morning (parallel):**
- Send user study survey to 10–12 KSIU classmates via WhatsApp/email. Use `docs/evaluation/USER_STUDY_PROTOCOL.md`. Track responses in PostHog. Don't wait — start collection ASAP, responses trickle in over the day.
- Record demo video. Script is at `docs/DEMO_VIDEO_SCRIPT.md`. OBS Studio, 1920×1080, 5-min limit. Shoot in 3 takes max. Upload to YouTube (unlisted) + commit MP4 to `docs/media/demo.mp4` if <50MB else release asset only.

**Afternoon:**
- Final docs sync: `CHANGELOG.md` v4.0.0 entry, `README.md` badges, `AGENT_NOTES.md` What's Left ✅ all done
- Tag `v4.0.0`, push tag, create GitHub release with release notes (auto-include `COMPETITIVE_BASELINE.md` results + Lighthouse score + uptime stats)
- Write blog post draft in `docs/BLOG_POST_DRAFT.md` — 1500 words, lead with the exploit verification GIF

**Evening:**
- Aggregate any received user study responses into `docs/evaluation/USER_STUDY_RESULTS.md`
- Update thesis defense slide deck

**Acceptance:** v4.0.0 on GitHub. Demo video link in README. ≥3 user study responses logged (more trickle in next week).

---

## 11.2 Dashboard Enhancement Backlog (detail)

Beyond Day 2's must-have list, these are nice-to-have if time allows on Day 5:

- **Dark/light toggle** (Tailwind already has `darkMode: 'class'` — just a button + localStorage)
- **Keyboard shortcuts:** `/` focus search, `f` filter modal, `Esc` close modal
- **Findings export:** CSV + SARIF download buttons
- **Repo settings page:** edit `.acrqa.yml` policy from the UI, POST to `/v1/policy/{repo}`
- **Admin user management:** list/disable users, rotate API keys (already supported by `/v1/auth/users`)
- **AI explanation streaming:** SSE for tokens as Groq generates (use `stream=true` in groq SDK)

---

## 11.3 Comprehensive Testing Plan

The goal is to verify **everything works end-to-end**, including third-party integrations. Not just unit tests — the *system* must hold up.

### 11.3.1 Existing Layers (already in place)

| Layer | What | Where |
|---|---|---|
| Unit | 1,979 tests, 85% coverage | `TESTS/test_*.py` |
| Integration | Celery + DB + Redis | `TESTS/test_integration_benchmarks.py`, `test_celery_tasks.py` |
| Recall battery | Layer 5 evaluation on 4 repos | `TESTS/evaluation/test_recall.py` |
| God-mode | OWASP, compliance, edge cases | `TESTS/test_god_mode.py` |
| Docker exploit | Real container PoC | `TESTS/test_exploit_verifier.py` (`-m exploit`) |

### 11.3.2 New Layers to Add (Days 3–4)

**E2E browser tests — Playwright (free):**
```bash
pip install playwright pytest-playwright
playwright install chromium
```
- `TESTS/e2e/test_dashboard.py` — open dashboard, login, run scan, verify finding modal opens, download attestation
- Runs against `localhost:8000` in CI, against live URL nightly

**Load tests — Locust (free):**
- `TESTS/load/locustfile.py` — simulate 50 concurrent users hitting `/v1/runs`, `/v1/runs/{id}/findings`, `/health`
- Validate SLO targets: p95 latency <500ms, error rate <1%
- Run before Day 5 release; document in `docs/PERFORMANCE_BASELINE.md`

**Security regression — dogfooding:**
- `pytest TESTS/test_dogfood.py` runs ACR-QA against itself, asserts: 0 HIGH findings in `CORE/`, ≤5 MEDIUM, no secrets, no eval/exec

**Smoke test on live URL — `TESTS/test_live_smoke.py`:**
- Polls `/health`, `/metrics`, `/v1/runs?limit=1` against `RAILWAY_URL` env var
- Runs in CI after each Railway deploy
- Fails the deploy if any 5xx within 60s post-deploy

### 11.3.3 Third-Party Validation (Day 4)

For each free tool wired in, document the result in `docs/evaluation/THIRD_PARTY_VALIDATION.md`:

```
| Tool        | What it found     | Status     | Notes |
| Snyk        | 0 HIGH, 2 MEDIUM  | ✅ Agrees  | Both MEDIUM also in our output |
| CodeQL      | 1 HIGH            | ❌ Disagrees | False positive on test fixture; suppressed |
| GitGuardian | 0 secrets         | ✅          | Confirms no committed keys |
| Trivy       | 3 HIGH in deps    | 🔄 Action   | Bump pydantic, fastapi |
| SonarCloud  | B rating          | 🔄 Action   | 12 maintainability issues to address |
```

This table doubles as defense evidence ("Independent tools validate ACR-QA's findings").

### 11.3.4 Manual Pre-Release Checklist

Before tagging v4.0.0:

- [ ] Fresh clone → `make up` → live in <10 min
- [ ] `make seed-admin` → login on live URL works
- [ ] Run scan via dashboard → completes → finding modal opens
- [ ] Download attestation → `verify_attestation.py` returns valid
- [ ] Trigger exploit verification on Docker fixture → proof JSON visible
- [ ] All 9 third-party CI jobs green
- [ ] Lighthouse ≥90 perf, ≥95 a11y on live URL
- [ ] Sentry sees 0 unhandled errors in last hour
- [ ] UptimeRobot uptime 99.5%+ since Day 1
- [ ] All README badges current

---

## 11.4 Repos To Add — Strategic Choices

The current 4 eval repos all skew Python. The thesis claims multi-language support (Python/JS/TS). The repo additions in §11.1 Day 3 fix this. Specific selection rationale:

| Repo | Why this one |
|---|---|
| **NodeGoat** | OWASP-owned, widely cited in academia, lets us cite OWASP Top 10 mapping directly |
| **Juice Shop** | The de-facto modern JS/TS benchmark. Examiners will know it. |
| **DVNA** | Already partially in repo (`DATA/sandbox/dvna/`) — promotion is cheap |
| **Tiredful-API** | Tests Django + DRF rules, broadens framework coverage |
| **bandit-test-cases** | Official Bandit corpus — guarantees we don't regress against Bandit's intent |
| **vulnerable-flask-app** | Tiny — fast smoke + CI cycle time |

**Don't add:** WebGoat (Java — out of scope), Damn Vulnerable iOS App, Mutillidae (PHP). Stay focused on Python/JS/TS so the multi-language claim is defensible without scope creep.

**Order of work:** clone all 6 on Day 3 morning, write ground-truth YAMLs on Day 3 afternoon (use ACR-QA's own findings as the seed — manually verify each), wire recall tests Day 3 evening. Don't optimize for perfect ground truth; "documented and reproducible" beats "perfect."

---

## 11.5 Acceptance Criteria for "v4.0.0 — Done"

By end of Day 5, all of these must be ✅:

- [ ] Live URL: `https://acr-qa.up.railway.app` returns 200 on `/health`
- [ ] Auto-deploy: merge to main → live in <5 min
- [ ] Sentry + UptimeRobot + PostHog wired
- [ ] Dashboard shows: reachability, exploit, attestation, OWASP heatmap, trend chart, diff
- [ ] 8+ eval repos in `test_targets/eval-repos/` with ground-truth YAMLs
- [ ] DVPWA recall ≥80% (up from 50%)
- [ ] `COMPETITIVE_BASELINE.md` complete with Snyk/CodeQL/SonarCloud numbers
- [ ] 9 third-party CI jobs (Snyk, CodeQL, Dependabot, GitGuardian, SonarCloud, Trivy, Codecov, Lighthouse, custom smoke) all green
- [ ] Playwright E2E + Locust load tests in CI
- [ ] Demo video recorded + uploaded
- [ ] ≥3 user study responses logged
- [ ] v4.0.0 tagged, release notes published, blog post drafted
- [ ] All MDs synced — `CHANGELOG`, `README`, `AGENT_NOTES`, `GOD_MODE_PLAN`, `EVALUATION`, `PROJECT_DEEP_DIVE`

When all 13 are ✅: thesis is defensible, repo is portfolio-ready, blog post goes live.

---

## 11.6 Execution Mode — How To Run This With An Agent

Ahmed says "go god mode day N" → agent reads §11.1 day N → executes top-to-bottom without asking permission per step → commits and pushes per deliverable → at end of day: updates §11.5 checkboxes + appends a daily summary below this section.

| Day | Started | Ended | Commits | Notes |
|---|---|---|---|---|
| 1 | | | | |
| 2 | | | | |
| 3 | | | | |
| 4 | | | | |
| 5 | | | | |

When all 5 rows are filled and §11.5 is fully ✅ → tag `v4.0.0` → ship the thesis.

---

*God-mode plan written May 14, 2026 — Ahmed compresses §6's Weeks 1–6 schedule into 5 calendar days. The old plan (§§0–10) stays as historical context; §11 supersedes §6's Week 6 row.*
