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

## 9. Key Numbers to Beat (Evaluation Targets)

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
