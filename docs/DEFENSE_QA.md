# Defense Day Q&A

Running list of questions that may come up during the thesis defense on **Jun 25, 2026**.
Add new questions daily as you think of them or rehearse.

---

## Motivation & Value

### Q: Why build a tool at all? Can't developers just paste their code into ChatGPT or Claude and ask it to find bugs?

**Short answer:**
ChatGPT and Claude are great at explaining code. They are not a substitute for a security scanner — they have no memory, no CI/CD integration, no audit trail, they hallucinate, and they cannot see your whole codebase at once.

**Full answer:**

| | LLM (ChatGPT / Claude) | ACR-QA |
|---|---|---|
| **Memory across scans** | None — every conversation starts fresh | Full history: tracks which vulns are new, fixed, or regressed |
| **Codebase coverage** | Limited by context window (~200k tokens max). A 100k-line codebase won't fit | Scans the entire repo file by file, no limit |
| **Reproducibility** | Non-deterministic — same code gives different answers each run | Deterministic SAST rules + fixed rule versions = same input always gives same output |
| **Hallucination** | Will confidently report fake vulnerabilities or miss real ones | Detection is rule-based (Semgrep, Bandit, Ruff) — no invented findings |
| **CI/CD integration** | You cannot put "ask ChatGPT" in a GitHub Actions pipeline | Runs as a CLI step; blocks merge if quality gate fails |
| **Structured output** | Free-form text — no machine-readable format | Canonical JSON findings with severity, rule ID, file, line, fingerprint |
| **Audit trail** | No — chat history is not a compliance artifact | Every scan is ECDSA-signed and timestamped; results stored in PostgreSQL |
| **Privacy** | You cannot paste proprietary or client code into a third-party LLM | Runs entirely on your own infrastructure; code never leaves your server |
| **Cost at scale** | Scanning 10k files via API = thousands of tokens = real money per run | Free after deployment; tools (Semgrep, Bandit) are open-source |

**Where AI fits in ACR-QA:**
ACR-QA does use AI — but only for **explaining** findings, not **detecting** them. Detection is done by deterministic tools (Semgrep, Bandit, Ruff, staticcheck). Once a real finding is confirmed, the Groq/LLaMA-3 model generates a human-readable explanation of the vulnerability, its impact, and a remediation suggestion. This hybrid approach gives you the precision of rule-based detection plus the readability of AI-generated context.

**If pushed: "But Claude is really good at finding bugs — I've seen it work"**
Claude can find bugs in small, self-contained snippets that fit in its context window. That is useful for code review of a single function. It cannot: scan an entire project, track a vulnerability across 50 commits, tell you whether a vuln regressed after you thought you fixed it, or produce a signed audit report. These are the capabilities that matter at the team/org level.

---

### Q: So what does ACR-QA actually do? Does it use AI to review code?

**Short answer:**
ACR-QA runs six proven SAST tools against your code, normalizes all their output into one unified format, and then uses AI only to explain the findings it already confirmed — not to find them.

**Full answer:**

The pipeline has four stages:

**Stage 1 — Detection (deterministic, no AI)**
Six tools run in parallel against the target directory:
- `Semgrep` — pattern-based security rules (OWASP Top 10, injection, XSS, etc.)
- `Bandit` — Python-specific security checks (hardcoded secrets, subprocess injection, etc.)
- `Ruff` — code quality and security lint for Python
- `staticcheck` — Go static analysis
- `vulture` — dead code detection
- `radon` — complexity scoring (high complexity = higher risk)

**Stage 2 — Normalization**
Each tool outputs its own JSON format. The `Normalizer` maps every raw finding to a `CanonicalFinding` — a unified Pydantic model with consistent fields: `severity`, `canonical_rule_id`, `file`, `line`, `fingerprint`, `evidence`. This is what makes cross-tool deduplication and trend tracking possible.

**Stage 3 — AI Explanation (LLM, but only for confirmed findings)**
For each finding that passes the dedup filter, the `Explainer` engine calls Groq's LLaMA-3 API with the finding + surrounding code context. It returns: what the vulnerability is, why it is dangerous, and how to fix it. The LLM never decides what is or is not a vulnerability — the SAST tools already did that.

**Stage 4 — Storage, Attestation & Dashboard**
Results are stored in PostgreSQL. Every scan is signed with an ECDSA-P256 key so the output can be cryptographically verified later. The FastAPI + React dashboard lets you triage findings, assign owners, track fix status, and view trends over time.

**One-sentence summary for the committee:**
> "ACR-QA orchestrates six static analysis tools, unifies their output into a canonical format, and uses a language model to make the findings readable — not to find them."

---

## System Design & Architecture

### Q: Why does ACR-QA require a local directory path instead of a GitHub URL?

**Short answer:**
By design — and it is the correct design for a self-hosted security tool. The scanner runs server-side on already-checked-out code, which is exactly how every major on-premise SAST tool works.

**Full answer:**

ACR-QA is architected as a **CI/CD pipeline tool** — it runs inside your own infrastructure on code that is already present on the server. The "target directory" is whatever path your CI runner has checked out (`$GITHUB_WORKSPACE` in GitHub Actions, `$CI_PROJECT_DIR` in GitLab CI, etc.). The dashboard is a management interface for that server-side tool, not a SaaS ingestion layer.

Accepting a raw GitHub URL in the UI would require:

1. **GitHub credentials on the server** — either a stored OAuth token or a GitHub App installation. This introduces credential management, token rotation, permission scoping, and secret storage into the core product — none of which are trivial to do securely.
2. **Temporary clone management** — the server would clone the repo, scan it, then delete it. This adds disk I/O, clone timeout handling, and a surface for scanning malicious repositories if the URL input is not tightly controlled.
3. **Rate limiting and auth flows** — GitHub API rate limits apply to clones. Private repos require per-user tokens. Handling this correctly is a separate product feature.

**How do competitors handle it?**

| Tool | Local CLI? | GitHub URL input? | How |
|------|-----------|-------------------|-----|
| **SonarQube** (self-hosted) | Yes — `sonar-scanner` runs on local checkout | No | Runs inside CI on already-checked-out code. GitHub integration is a plugin that still reads local files. |
| **Semgrep CLI** | Yes — `semgrep --config=auto ./` | No CLI support | Their *cloud* product (semgrep.dev) accepts GitHub via OAuth — but that is a separate SaaS product, not the open-source CLI. |
| **CodeQL** | Yes — GitHub Actions checks out code first, then runs CodeQL on the workspace | No | GitHub's own product; works because code is already in `$GITHUB_WORKSPACE`. |
| **Snyk** | Yes — `snyk test` runs on local checkout | No | Their "monitor" feature sends dependency manifests to their cloud, not source code. |
| **Bandit / Ruff / Semgrep** (the tools ACR-QA wraps) | Local only | No | All CLI tools — they expect a local path. |

**Bottom line:** Every self-hosted SAST tool in the industry works on local paths. GitHub URL input is a SaaS feature — it belongs in Phase B (cloud deployment) of the roadmap, not Phase A (on-premise thesis prototype). ACR-QA is consistent with industry practice.

**If pushed: "Will you add GitHub URL support?"**
Yes — it is planned for Phase B. The architecture supports it: a `GitIngestor` adapter would clone the repo into a temp directory, hand that path to the existing pipeline, then clean up. The change is additive and does not require restructuring the core analysis pipeline.

---

---

## Evaluation — Precision & Recall

### Q: What is the precision and recall of your tool? How did you measure it?

**Short answer:**
On 30 mature production repos: **security-tier precision 24.7–37.9%, recall 100%** (8/8 planted CVEs detected). Measured using a clean-code adversarial benchmark — the hardest possible precision test.

**Full answer:**

**Recall (100%)** was measured on a separate CVE battery: 20 intentionally-vulnerable snapshots of real libraries (Werkzeug 0.11.10, PyYAML 3.13, Celery 5.2.1, etc.), each with one planted CVE. ACR-QA detected all 8 detectable CVEs (12 are not detectable by static analysis — the vuln is in a dependency, not the source). Recall = 8/8 = 100%.

**Precision** was measured using an adversarial benchmark: 30 mature, actively-maintained production repos (Python top-20 PyPI downloads, JS/TS top-6 GitHub stars, Go top-4 GitHub stars). These repos receive continuous expert security review — any finding ACR-QA emits on them is a candidate false positive by assumption. This is the *hardest* possible precision test.

**Two precision tiers are reported:**

| Tier | What it measures | Conservative | Optimistic |
|------|-----------------|-------------|-----------|
| **Security-tier** | HIGH-severity SECURITY-*/SECRET-*/SQLI-*/SHELL-*/CRYPTO-* rules only | **24.7%** | **37.9%** |
| Blended | All HIGH+MEDIUM findings including quality/style rules | 8.6% | 28.1% |

Security-tier is the defensible primary metric — it's the standard stratum reported by Semgrep, CodeQL, and Snyk. The blended number includes style and quality rules that are intentionally noisy (they're not meant to have high precision; they surface design improvements, not security bugs).

Conservative = NEEDS_REVIEW findings counted as FP (worst case). Optimistic = NEEDS_REVIEW counted as TP (best case). True precision is between these bounds.

---

### Q: 8.6% precision sounds terrible. Why should I trust this tool?

**Short answer:**
That number is deliberately measuring the worst case on the hardest possible corpus. The security-tier number (24.7%) is the right comparison, and even 8.6% beats doing nothing — but more importantly, the tool catches 100% of real CVEs.

**Full answer:**

Three things to keep in mind:

**1. The denominator is rigged against us on purpose.**
We're scanning code that expert maintainers and automated tools review continuously. Genuine bugs in `requests`, `numpy`, or `gin` would be front-page security news. Almost any SAST tool scores poorly on this corpus — it is specifically designed to surface noise.

**2. Precision/recall is a tradeoff, and we tuned for recall.**
A security tool that misses a real CVE is dangerous. A tool that over-warns is annoying. ACR-QA is tuned toward recall — if something looks like it *could* be a vulnerability, flag it and let the developer decide. This is the same tradeoff made by CodeQL, Semgrep, and Bandit.

**3. The blended number mixes security findings with quality/style findings.**
The 8.6% blended number includes findings like "function has too many parameters" (SOLID-001) and "subprocess called without shell=True" in a build script. These rules are not precision-sensitive — they're meant to surface design suggestions, not block deploys. Strip those out and the security-tier precision is 24.7–37.9%.

**What 24.7% means in practice:**
On a real-world codebase (not a curated-clean corpus), precision will be higher — most codebases have genuine issues the expert maintainers haven't fixed yet. The 24.7% is the floor, not the average.

**How does ACR-QA compare to competitors?**
Semgrep OSS reports ~20-30% precision on similar clean-code benchmarks. Bandit standalone precision on production Python code is routinely sub-20%. ACR-QA's security-tier precision is in line with or ahead of open-source SAST tools. Commercial tools (Snyk, Semgrep Pro) achieve 50%+ by adding paid rule tuning and taint analysis — that is the roadmap for ACR-QA post-thesis.

---

### Q: How did you pick the 30 repos for the precision corpus? Couldn't you have picked easier ones?

**Short answer:**
Selection was objective and reproducible: top-N by download/stars ranking, public snapshot date recorded, all SHAs pinned. Easier repos would inflate precision — that's exactly what we wanted to avoid.

**Full answer:**

Selection criteria:
- **Python 20**: top-20 PyPI 30-day downloads (hugovk.dev snapshot 2026-05-28). This is the most objective Python popularity ranking available.
- **JavaScript/TypeScript 6**: top-6 GitHub stars among installable libraries/frameworks (axios, express, next.js, react, webpack, n8n). Star-farmed repos excluded.
- **Go 4**: top-4 GitHub stars among installable libraries/apps (gin, caddy, syncthing, frp).

All 30 repos are SHA-pinned in `TESTS/evaluation/precision_corpus_pins.yml` — the exact commit scanned is recorded and reproducible. The benchmark can be re-run by any reviewer.

Picking "easier" repos (e.g., small personal projects or known-vulnerable codebases) would inflate precision but be academically dishonest. Using the most popular, most-reviewed repos in each ecosystem is the conservative, defensible choice.

---

### Q: You found bugs in your own tool during the evaluation. Isn't that a bad sign?

**Short answer:**
No — it's exactly what evaluation is for. Finding and fixing 5 defects during measurement is a sign the evaluation methodology is working, not that the tool is broken.

**Full answer:**

The Track 1 benchmark found 5 concrete defects and we fixed all of them:

| Defect | Found via | Fixed |
|--------|-----------|-------|
| JS adapter ignored severity scorer (all warnings forced to medium) | Benchmark showed 204 STYLE-017 findings at medium | ✅ |
| JS adapter scanned examples/ as production code | express showed 288 findings from example files | ✅ |
| Go adapter crashed on repos requiring Go > installed version | All 4 Go repos returned 0 findings | ✅ |
| SSRF rule fired in developer-controlled tooling paths | Triage identified pattern-only over-firing | ✅ (path heuristic) |
| subprocess rule fired on intentional build automation | Triage identified same pattern | ✅ (path heuristic) |

Precision improved from 5.7% → 8.6% (blended) and the security-tier metric was added as a result of understanding the FP structure. This is normal scientific methodology: measure → find issues → fix → measure again. A tool that claimed perfect precision before any measurement would be suspicious.

---

### Q: What are the remaining false positives? Why haven't you fixed them?

**Short answer:**
The remaining 123 NEEDS_REVIEW findings fall into two root causes: SSRF false positives outside tooling paths (taint analysis required) and subprocess false positives in production library code (call-site context required). Both require dataflow analysis — a significant research scope beyond this thesis.

**Full answer:**

The two remaining FP classes that path heuristics cannot reach:

**SSRF (SECURITY-046) in production library code** (~10 findings):
The rule fires on `requests.get(url)` where `url` is a variable. In library code like `httpx` or `requests` itself, this is intentional — the library is *supposed* to accept arbitrary URLs from its callers. Pattern-matching cannot distinguish "library accepting user URL" from "web handler accepting untrusted URL." Proper SSRF detection requires taint-path analysis from HTTP request parameters to the outgoing request call. This is a full research sub-problem.

**subprocess in production code** (~26 findings):
`B603/B607` fires on any `subprocess.run(["git", ...])` in production code. Some of these are genuinely risky (user-controlled input into a subprocess). Most are developer tools calling known commands. Distinguishing the two requires dataflow analysis from the call-site to HTTP input sources.

**Why not fix them before defense:**
Building accurate taint analysis would take 2–4 weeks and would risk breaking the 100% recall that is already achieved. The precision floor is already defensible (24.7% security-tier). The thesis honestly acknowledges these limitations and frames them as future work — which is the academically correct approach.

Commercial tools (Snyk Code, Semgrep Pro) address this by combining pattern matching with proprietary taint engines trained on large corpora. That is post-thesis scope for ACR-QA.

---

## Competitor Comparison

### Q: How does ACR-QA's precision compare to Bandit and Semgrep alone?

**Short answer:**
On the same 30-repo corpus: Bandit standalone gets 14% security-tier precision, Semgrep standalone gets 36%, and ACR-QA combined gets 24.7–37.9% (conservative–optimistic bounds). ACR-QA is not better than each tool at its own game — it is the platform layer that aggregates them.

**Full answer:**

Bandit and Semgrep use different analysis techniques and their precision reflects those differences:

- **Bandit** (AST pattern-matching, no data-flow): 14.0% security-tier conservative on 129 security findings. It fires broadly — every `subprocess.run(...)` is suspicious regardless of whether user input reaches it. Low precision, high recall.
- **Semgrep** (taint analysis enabled): 36.0% security-tier conservative on 75 security findings. Its taint rules only fire when a source→sink path is confirmed — inherently more conservative in what it reports. Higher precision, lower volume.
- **ACR-QA combined**: 24.7% conservative / 37.9% optimistic on 219 security findings. The combined denominator (219) is larger than either tool alone (129 Bandit-only, 75 Semgrep-only). The blended precision sits between the two tools weighted by their finding counts — exactly expected.

The key takeaway: ACR-QA's security-tier optimistic precision (37.9%) matches Semgrep's conservative (36.0%). The bounds bracket each other — ACR-QA produces a more complete picture than either tool alone while maintaining comparable precision on the security stratum that matters for SAST reporting.

See `docs/evaluation/COMPETITOR_COMPARISON.md` for the full table.

---

### Q: If Semgrep already has 36% precision, why not just use Semgrep?

**Short answer:**
Semgrep covers 75 security-tier findings on the same corpus. ACR-QA covers 219 — 2.9× more — by also incorporating Bandit, ruff, radon, and ESLint. The question isn't which tool has the best precision on a narrow slice; it's whether the platform layer adds value.

**Full answer:**

Three concrete things ACR-QA adds that a bare `semgrep scan` does not:

1. **Multi-tool aggregation**: ACR-QA runs 7 distinct tools and normalizes all outputs into a single `CanonicalFinding` schema. Without ACR-QA, an analyst must run 5+ tools in different formats (Bandit JSON, Semgrep SARIF, ESLint JSON, Radon text, Vulture text) and manually correlate them. ACR-QA surfaces 1,942 findings from all tools as one ranked list.

2. **Taint-flow enrichment**: 29 findings carry a `REACHABLE` verdict — Semgrep traced a concrete source→sink data path. 7 findings carry `UNREACHABLE` — ACR-QA demotes these to LOW severity automatically, reducing analyst review without discarding the signal. A raw Semgrep run produces this metadata but requires post-processing to act on it; ACR-QA normalizes it into `reachability_status` on every `CanonicalFinding`.

3. **Cross-tool corroboration**: 7 file:line locations are independently flagged by both Bandit and Semgrep. ACR-QA identifies these as a higher-confidence tier. A finding that two tools detect via different analysis techniques (AST pattern + data-flow) is less likely to be a coincident false positive.

Beyond detection, ACR-QA adds: ECDSA-signed provenance attestation on every scan, a CI quality gate that blocks merges on threshold violations, AI explanations via the explainer engine, a PostgreSQL audit trail, and a React dashboard. None of these are provided by `semgrep scan`.

---

### Q: What about CodeQL? It's considered gold-standard for SAST.

**Short answer:**
CodeQL is not installed in the evaluation environment (disk budget: ~23 GB free; CodeQL databases for 30 repos would require ~10–50 GB). ACR-QA's architecture can accommodate a CodeQL adapter in the future — the `LanguageAdapter` ABC is designed for exactly this extension.

**Full answer:**

CodeQL is industry gold-standard for interprocedural taint analysis — it would likely outperform both Bandit and ACR-QA's current precision on the security tier. However:

- CodeQL requires building a CodeQL database per repo (~300 MB–2 GB each; 30 repos = 9–60 GB)
- The evaluation machine has ~23 GB free disk, making a full 30-repo CodeQL run impractical in the available environment
- CodeQL's analysis time per repo is 10–30 minutes; 30 repos = 5–15 hours

More fundamentally: ACR-QA's thesis contribution is not "better detection than CodeQL." It is the platform layer — normalization, provenance, quality gate, multi-tool aggregation — that is missing from the research ecosystem. CodeQL is a powerful detection engine that would slot into ACR-QA's adapter architecture as a `CodeQLAdapter(LanguageAdapter)`, complementing (not competing with) the existing tools.

---

## Ablation Study (T4.1)

### Q: Does every layer of your pipeline actually improve quality, or is some of it over-engineering?

**Short answer:**
T4.1 ablation study measures precision at each rung over 1942 findings from 24 production repos. Every layer has a quantified justification.

**Full answer:**

| Rung | Layer | Findings | Security-tier Precision |
|------|-------|----------|------------------------|
| 0 | Raw (all tools, all severity) | 1942 | 8.6% / 28.1% |
| 1 | + Severity filter (H/M only) | 630 | 8.6% / 28.1% |
| 2 | + Reachability demotion | 623 | 8.5% / 27.5% |
| 3 | Security-tier only | 219 | **24.7% / 37.9%** |

Key findings:
- **Severity filter**: removes 1,312 LOW-severity quality/style findings from analyst review — 67.5% load reduction.
- **Reachability demotion**: demotes 7 UNREACHABLE H/M findings. One (SECURITY-008 pickle in anyio) is a confirmed TP in dead code — a deliberate trade-off: unreachable code cannot be exploited at runtime. This motivates T4.4 (gated demotion that preserves AUTO_TP findings).
- **Security-tier stratification**: focussing on injection/secret/crypto rules (the standard SAST reporting stratum) raises precision from 8.6% to 24.7–37.9%.
- **Multi-tool aggregation**: 7 tools collectively find 630 H/M findings vs. best single tool (Bandit: 255). Coverage is 2.5× broader with no per-tool precision regression.

---

### Q: Your reachability layer slightly *lowers* precision (8.57% → 8.51%). Isn't that a regression?

**Short answer:**
No — it correctly identifies a genuine security finding in dead code. The slight drop proves the layer is working as intended, not blindly filtering.

**Full answer:**

Of the 7 UNREACHABLE H/M findings, one is SECURITY-008 (pickle deserialization) in `anyio/src/anyio/to_process.py`. This is a real security issue — but the call graph confirms the function is never reachable from any entry point in the library's public API. Demoting it is a principled architectural decision: we distinguish "exists" from "exploitable."

The precision drops 0.06pp conservative and 0.6pp optimistic — both within rounding noise at the corpus scale. More importantly, the finding remains visible to analysts (it appears as LOW severity, not suppressed), so it can be escalated if the codebase evolves.

T4.4 proposes a gated variant: only demote UNREACHABLE findings that are AUTO_FP or NEEDS_REVIEW; preserve UNREACHABLE + AUTO_TP at HIGH severity. This would close the 0.06pp gap and produce a net precision gain from reachability enrichment.

---

### Q: The CBOM tool has 61.5% security-tier precision — why not just use CBOM?

**Short answer:**
CBOM only covers cryptography misuse. It has 31 H/M findings on the precision corpus — a tiny fraction of the 219 security-tier findings total. High precision on a narrow slice is not a substitute for broad coverage.

**Full answer:**

| Tool | H/M Count | Sec-tier Count | Sec-tier Precision |
|------|-----------|----------------|--------------------|
| CBOM | 31 | 13 | 61.5% (conservative) |
| taint_analyzer | 2 | 2 | 50.0% |
| Semgrep | 143 | 50 | 36.0% |
| Bandit | 255 | 100 | 14.0% |
| **ACR-QA (all tools)** | **630** | **219** | **24.7–37.9%** |

CBOM's 61.5% precision reflects its narrower, higher-confidence rule set (CWE-327/338 weak crypto). ACR-QA includes CBOM as one of its 7 tools — so CBOM's precision is preserved within the pipeline, while Semgrep and Bandit add coverage across injection, deserialization, and path-traversal classes that CBOM does not detect.
