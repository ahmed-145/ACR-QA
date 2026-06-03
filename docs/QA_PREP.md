# ACR-QA Defense Q&A Preparation — 40 Questions

*Memorise the answer structure, not the exact words. Keep each answer under 60 seconds.*

---

## Category 1 — Evaluation Validity (Most Dangerous)

### Q1. "Your benchmarks are toy apps. How do I know this works on real code?" ⚠️ MOST IMPORTANT

Toy apps are the *controlled group* — the same methodology every SAST paper since 2008 uses because there's no other way to measure recall at scale (you need ground truth). They are not my proof of real-world accuracy; they are my proof the tool finds known bugs. For real-world validation: I ran ACR-QA on Flask (68k stars) — 1.0% FP rate. On httpx — 2.3%. SonarQube's published Python baseline is 30–40%. My layered approach is: synthetic ground truth + real-world FP measurement + pre-registered CVE recall + blind peer validation. No single layer is sufficient; all four together are a credible case.

**Backup numbers:** Flask: 100 HIGH → 1 FP. httpx: 43 HIGH → 1 FP.

---

### Q2. "13 repositories — is that enough to generalise?"

I chose depth over breadth. Each repository has a labelled ground-truth YAML with exact expected findings, severity, and canonical rule IDs. A hundred unlabelled repos would be noise — I can't measure recall without ground truth. The 13 repos span Python (7), JavaScript/TypeScript (4), and Go (1), covering 9/10 OWASP Top 10. This mirrors the evaluation discipline of published SAST papers (e.g., Croft et al. 2023), not industry marketing claims.

---

### Q3. "Why not test on Java or C++?"

Honest limitation — documented in the paper. The scope decision was deliberate: build one language stack deeply and correctly rather than four stacks shallowly. Java support is Phase B (SpotBugs + FindSecBugs adapter). The canonical schema means adding a language is an adapter only — no changes to normalisation, reachability, or AI engines.

---

### Q4. "You say 100% recall — that sounds too good. Where are the misses?"

The 100% is on the 13-repo non-CVE benchmark where every finding is labelled. On the broader 20-CVE battery the overall recall is 40% (8/20) — I lead with that in every paper and talk. The 12 misses are documented with root-cause categories: protocol-level (HTTP smuggling), C-extension, algorithmic, semantic taint. Neither ACR-QA nor Semgrep CE detects them. Claiming 100% coverage would be false. The 100% benchmark result and the 40% CVE result are both true simultaneously.

---

### Q5. "Did you cherry-pick the 20 CVEs after you saw which ones you detected?"

No. Pre-registration means the CVE list was committed to version control (ground-truth YAML files with `recall_target: 0` or `1`) before any scan was run. The git log timestamp proves the target was set before the result. That's the definition of pre-registration — same discipline used in clinical trials and empirical SE papers.

---

### Q6. "Your CVE recall is only 40% — isn't that low?"

40% is the honest overall number. On the *detectable* subset it is 100%. The 12 misses represent structural limits of all static analysis — no SAST tool in the world detects HTTP smuggling statically because it requires dynamic protocol analysis. I document each miss with a category label and root cause. Semgrep's marketing claims do not disclose their CVE miss rate at all. I do. That's the more rigorous position, not the weaker one.

---

### Q7. "How do you know Semgrep CE got 71.2% and not something higher?"

Both tools ran on the same 13 ground-truth repositories with the same expected-finding YAMLs. Semgrep CE used the `p/default` + `p/python` + `p/javascript` + `p/go` community rulesets — the same rulesets any user would apply. The methodology is described in `docs/evaluation/HEAD_TO_HEAD_BENCHMARK.md` and the eval code is in `scripts/run_eval.py`. It's reproducible.

---

### Q8. "How did you measure precision — did you manually label 836 findings?"

Yes. For the four core benchmark repos (DVPWA, Pygoat, VulPy, DSVW), every HIGH-severity finding was manually triaged. 812 TP, 24 FP. The 24 FP are all Vulture dead-code findings in Flask URL dispatch functions — documented category, not random noise. This gives 97.1% overall, 100% security class.

---

## Category 2 — AI + Hallucination

### Q9. "How exactly does Semantic Entropy prevent hallucination?"

The explainer runs three independent calls to the LLM at temperatures 0.3, 0.7, and 1.0. For each pair of outputs we compute N-gram overlap (bigram F1). If the variance across the three outputs is high — meaning the model is uncertain — the N-gram entropy score falls below threshold (τ = 3.2 bits) and the explanation is suppressed rather than shown. The user sees "explanation unavailable" instead of a confident wrong answer. RAG grounds the content; entropy validates the specificity.

---

### Q10. "What is RAG and why does it prevent hallucination?"

RAG = Retrieval-Augmented Generation. Instead of asking the LLM "explain this vulnerability," I first retrieve the rule definition from a curated 66-rule knowledge base verbatim, inject it into the prompt, and ask the LLM to specialise it to the specific code context. The LLM cannot fabricate a rule citation because the rule text is already in the prompt. It can only rephrase what I gave it. This bounds the hallucination surface to the rule knowledge base quality, not the model's training data.

---

### Q11. "What's the difference between your Second Opinion and just running the same model twice?"

Second Opinion uses two *different* models: Groq Llama-3.3-70B (primary, hosted) and Ollama qwen2.5-coder:1.5b (local, free). Different architectures have different failure modes. If both agree: +15 confidence. If they disagree: -10 confidence. If Ollama is unavailable (no GPU, no internet): neutral (0 delta, graceful degradation). Same-model-twice would have correlated errors — the insight from the LinkedIn post that motivated this feature.

---

### Q12. "The LLM used is free-tier Groq — doesn't that limit quality?"

Groq Llama-3.3-70B is a 70-billion parameter model — larger than most commercial deployments. The free tier has rate limits, which is why we have a 4-key rotation pool and the per-user daily quota (100K tokens). For a thesis evaluation on deterministic test cases this is sufficient. The explanation quality is not under evaluation — only the filtering mechanism (entropy threshold) is. Production deployments can swap in any OpenAI-compatible endpoint.

---

## Category 3 — Architecture + Design

### Q13. "Why did you use Bandit + Semgrep + Ruff + … instead of just one tool?"

Each tool has a structural advantage the others don't. Bandit is import-aware — it knows that `yaml.load()` is B506 because it tracks the import origin. Semgrep is great at cross-file dataflow patterns. Ruff catches Python anti-patterns Bandit misses. staticcheck catches Go-specific SQL injection that no Semgrep CE rule covers. A single tool would leave structured blind spots. The canonical schema means adding a tool is a one-file adapter change.

---

### Q14. "What is CanonicalFinding and why does it matter?"

It's a Pydantic model in `CORE/engines/normalizer.py` that every tool output is converted to before any downstream engine sees it. 327+ mappings from tool-specific rule IDs to canonical IDs (e.g., B601 → `SECURITY-001`). This is the architectural bet: no engine ever sees raw tool dictionaries. The consequence is that I can add a new language adapter without touching reachability, taint, or AI — they all consume the same type.

---

### Q15. "Why PostgreSQL and not SQLite? The system feels over-engineered."

PostgreSQL was chosen for the concurrent multi-user demo (Railway hosted endpoint), connection pooling (ThreadedConnectionPool 1→10), and JSONB storage for findings. SQLite would have been fine for single-user local use but breaks under the load tests (1,000-findings chaos test). The architecture is documented in `CLAUDE.md` and the trade-off is explicit.

---

### Q16. "Why FastAPI and not Flask?"

Async-native SSE (Server-Sent Events) for live scan progress. Flask would require a thread-per-connection model which doesn't scale for the streaming case. FastAPI also provides automatic OpenAPI spec generation which drives `npm run generate-api` to keep the React client types in sync.

---

### Q17. "Your Quality Gate is just a threshold check — that's not sophisticated."

The threshold IS the feature. Policy-as-Code means the policy lives in a YAML file that non-security engineers can read and modify without touching tool configuration. The sophistication is in what feeds the threshold: reachability-filtered, taint-checked, entropy-filtered findings. The gate itself is deliberately simple — it's the signal quality that matters.

---

### Q18. "Why did you not use ML for the risk predictor?"

Two reasons. First, I don't have labelled vulnerability data at the scale required for ML generalisation (Croft et al. 2023 estimate ≥10k samples). My corpus is 13 repos. Training on 13 repos would overfit catastrophically. Second, a committee can ask "what is the model doing?" about a linear model in one sentence per weight. It cannot ask that about a neural network. Interpretability dominates accuracy at thesis scale. The model achieves r=0.71 correlation — sufficient for attention-direction, which is the stated purpose.

---

## Category 4 — Comparison to Commercial Tools

### Q19. "How is this different from SonarQube?"

Three things SonarQube CE doesn't offer: (1) AST Test Gap Analyzer — SonarQube measures coverage percentage, not which untested functions are complex and dangerous. (2) Hallucination detection — SonarQube has no LLM explainer at all. (3) Per-scan ECDSA provenance attestation. Also: SonarQube CE's Python false-positive rate is 30–40%; ACR-QA is 1.0% on Flask. And SonarQube's code is closed.

---

### Q20. "How is this different from CodeRabbit?"

CodeRabbit is LLM-first with no multi-tool normalisation layer. It has no published recall measurement, no semantic entropy filter, no reachability gate. It produces per-PR comments but cannot block a merge with a policy gate. It has no time-travel analyzer, no IaC scanner beyond basic checks, and no ECDSA provenance. And CodeRabbit charges $15/user/month for teams.

---

### Q21. "How is this different from Snyk?"

Snyk's reachability and dataflow are proprietary — you cannot audit what they do. ACR-QA's `reachability.py` is 190 lines of pure-AST code that anyone can read. Snyk charges per seat and doesn't publish precision/recall numbers. We publish ours — including the unflattering 40% CVE overall.

---

### Q22. "GitHub Copilot review already does this — why build another tool?"

Copilot review had a 22% hallucination rate in the 2024 audit. It has no recall measurement, no deterministic rule engine, no quality gate, no IaC scanner, no time-travel analyzer. It generates suggestions; it doesn't enforce policy. ACR-QA's architecture starts with deterministic SAST and uses LLM only for explanation enrichment — the opposite design.

---

## Category 5 — Test Suite

### Q23. "2,759 tests — where did they come from? Did you write them all?"

Yes. Starting from Phase 1's ~30 happy-path tests, I wrote them iteratively alongside each feature. Categories: unit tests per engine, database integration tests, FastAPI endpoint tests (including auth, rate limiting, SSE), chaos engineering (Postgres/Redis failure injection), supply chain (pip-audit/npm-audit mocked), WCAG accessibility (axe-core), and property-based tests using Hypothesis. The test count is not padding — each test class is in a separate file with a specific failure scenario.

---

### Q24. "How do the chaos engineering tests work?"

They use `unittest.mock.patch` to inject exceptions at the psycopg2 and redis-py level. For example, `test_database_resilience.py` patches `psycopg2.connect` to raise `OperationalError` and verifies the API returns 503 with a retry hint — not a 500 or a hang. The Celery worker tests simulate mid-scan database loss. This validates the system behaves gracefully under infrastructure failure.

---

### Q25. "Your mutation score is 61% — is that good enough?"

61% exceeds the Phase A target of 60% and is above the industry median for security tooling (typically 40–55% for complex analysis code). It could be improved — that's documented. The gap is in the AI engines where mock-heavy tests don't kill mutations in the prompt construction logic. Higher mutation scores for LLM-heavy code require deterministic output fixtures which are expensive to maintain.

---

## Category 6 — Technical Implementation

### Q26. "How does the Time-Travel engine avoid being too slow on large repos?"

Bounded commit walk: default N=50 (configurable, `--full-history` removes cap). Hunk-level extraction: only lines within changed hunks are fed to the normaliser, not entire files. Complexity is O(N × mean_hunk_scan_time). Measured: N=50 adds <90s at p95 on the 13-repo corpus. That's acceptable for a PR-level gate, not a real-time IDE check.

---

### Q27. "How does the taint analyzer work?"

Source→sink→sanitizer model, config-driven via YAML files in `config/`. Sources are HTTP inputs, env vars, file reads. Sinks are dangerous calls: SQL execute, subprocess, eval, pickle.loads. Sanitizers are html.escape, parameterize, etc. The engine does intra-procedural taint propagation via AST traversal — it does not do inter-procedural (across function boundaries). That's a documented limitation. Findings that touch a sink without passing through a sanitizer get a taint_confirmed flag.

---

### Q28. "Explain your ECDSA provenance attestation."

Each scan result is signed using an ECDSA P-256 key. The signature covers a hash of: scan timestamp, tool versions used, git SHA of the target, finding count, and a Merkle-style hash of the canonical finding IDs. The signature and public key are returned at `GET /v1/runs/{id}/attestation`. Anyone can verify: load the public key, recompute the message hash, verify the signature. Tampered results (e.g., findings deleted post-hoc) produce an invalid signature. This is why the evaluation data can be trusted.

---

### Q29. "How does the PR Risk Score work in GitHub Actions?"

`scripts/post_pr_risk_comment.py` calls `GET /v1/runs/{run_id}/pr-risk?changed_lines=N` where N is extracted from `git diff --numstat`. The result (0–100, band, breakdown text) is posted as a PR comment via `GITHUB_TOKEN`. The workflow file is two lines: `uses: ahmed-145/acrqa-action@v1` with `fail-on: high`. Green (0–30) = auto-approve signal. Amber (31–60) = request review. Red (61–100) = block merge.

---

### Q30. "Why subprocess argv-only invocation? Why not shell=True?"

Shell injection. If a filename contains a semicolon or backtick and you use `shell=True`, the shell interprets it. Three real `shell=True` bugs were found and fixed during the A4 security hardening pass (`test_subprocess_safety.py` caught them). Every tool invocation in `tool_runner.py` is now `subprocess.run([...], shell=False)`. The test file verifies this at the AST level — it greps for `shell=True` in the source and fails if found.

---

## Category 7 — Distribution + Production

### Q31. "How did you get it on PyPI?"

GitHub Actions workflow (`pypi-publish.yml`) triggered on version tag (`v*.*.* `). Uses PyPI OIDC Trusted Publisher — no API key stored in secrets. The workflow builds a wheel via `python -m build`, uploads via `twine`. Package is at `pip install acrqa==5.0.0rc2`.

---

### Q32. "Does the Railway deployment cost money?"

Railway's Starter plan is free for open-source and hobby projects up to $5/month in usage. At zero production traffic this is effectively free. The deployed stack is FastAPI + PostgreSQL + Redis. Cloudflare proxy in front for caching and DDoS mitigation (free tier). Domain registration is ~$12/year.

---

### Q33. "Is the system secure? What's your attack surface?"

JWT authentication on all data endpoints. bcrypt password hashing. Rate limiting (redis-backed token bucket). Subprocess argv-only (no shell injection). No `eval()` or `exec()` in production paths — our own scanner would catch it. Input validation via Pydantic. SQL via parameterized queries only. ECDSA signatures on outputs. The remaining attack surface: the LLM prompt injection surface (an attacker could craft code that manipulates the explanation) — documented limitation, not yet mitigated.

---

## Category 8 — Research Method

### Q34. "What is Cohen's κ and why does κ=0.74 matter?"

Cohen's κ measures inter-rater agreement corrected for chance. Formula: (P_o - P_e) / (1 - P_e) where P_o is observed agreement and P_e is expected agreement by chance. κ=0.74 is "substantial" on the Landis & Koch 1977 scale (the same scale used in medical research, NLP annotation, and legal dispute resolution). It means the independent reviewer agreed with my labels on 74% of findings, well above what chance predicts. Full study in `docs/evaluation/PEER_VALIDATION.md`.

---

### Q35. "Why only 2 raters? Shouldn't you have more?"

Yes — that's documented as a limitation. The 5-rater study is in progress, targeting κ ≥ 0.78 (Fleiss' κ). Recruiting 5 faculty/practitioner raters takes time. The 2-rater result (κ=0.74) is a lower bound — more raters generally increase κ stability. The methodology (blinding procedure, finding set, labelling form) is published in the PEER_VALIDATION.md so the 5-rater extension can be conducted by others.

---

### Q36. "What does pre-registration actually mean in your CVE battery?"

Before running any scan, I committed the ground-truth YAML files to version control with `recall_target: 0` or `1` for each CVE. The git timestamp proves the expected outcome was set before the scan. This eliminates the ability to choose CVEs after seeing which ones I detected. It's the same discipline as clinical trial pre-registration with ClinicalTrials.gov — the design is locked before data collection.

---

## Category 9 — Scope + Contributions

### Q37. "Is this really a research contribution or just integration work?"

Integration at scale is a contribution. But ACR-QA has five things no integration would produce: (1) Entropy-based hallucination detection — novel mechanism for LLM explanation validation. (2) Time-Travel regression-chain tracking — novel application of bounded git history to SAST. (3) Interpretable file risk predictor with empirical calibration — novel framing (anti-ML argument at thesis scale). (4) Pre-registered CVE recall battery — novel evaluation methodology for SAST tools. (5) PR Risk Score collapsing multi-dimensional security signals — novel interface abstraction. These are research contributions, not just glue code.

---

### Q38. "What would you do differently?"

Two things. First, I'd add Java support earlier — Go coverage gave +28.8pp against Semgrep CE but the Java gap is larger in industry. Second, I'd instrument a production deployment earlier (even a small one) to get real-world failure data. The chaos engineering tests simulate failures but they can't capture every production failure mode. Everything else I'd repeat.

---

## Category 10 — Quick Factual

### Q39. "What is CI/CD?"

Continuous Integration / Continuous Deployment. Every git push triggers GitHub Actions (free for open source): linting, type checking, and all 2,759 tests run automatically. If any test fails, the push is blocked from `main`. This means every commit to `main` has passed 2,759 tests — no manual testing required. The green checkmarks in the Actions tab are the proof.

---

### Q40. "What's the next step after defense?"

Three things: (1) Tag v5.0.0 final (removing the beta label) after defense. (2) Film the 5-minute demo video and publish to YouTube. (3) Begin Phase B — public launch at acrqa.dev, VSCode plugin, GitHub App, targeting 100+ users. The PyPI package and GitHub Actions integration are already live — users can start today with `pip install acrqa==5.0.0rc2`.

---

### Q45. "Your synthetic-snippet benchmark shows 91%. What about real production code?" ⚠️ HIGH RISK

We ran it. RealVuln (kolega-ai/Real-Vuln-Benchmark) — 26 real multi-file Python apps (Flask, Django, APIs), 697 hand-labelled TP + 120 FP traps, strict CWE+file+line(±10) matching, third-party ground truth. ACR-QA: **23.5% recall**, Bandit: 18.3%. ACR-QA leads Bandit by +5.2pp on neutral ground. The drop from 91% is explained by three documented causes: (1) ~40% of RealVuln entries are auth/IDOR/logic flaws that NO static tool detects; (2) strict line matching (±10) vs file-level matching; (3) multi-file framework abstractions. The honest statement: ACR-QA detects ~35–40% of statically-detectable real vulns, consistently ahead of Bandit, with 97 FP traps correctly avoided. Both numbers are published: `docs/evaluation/REALVULN_BENCHMARK.md`.

---

### Q46. "Can your exploit verifier actually handle 10 different vulnerability types?"

Yes — fully wired and unit-tested. All 10 categories (SQLi, CMDi, SSTI, path-traversal, SSRF, XXE, insecure-deserialization, open-redirect, ReDoS, LDAP-injection) have PAYLOADS, EXPLOITATION_SIGNALS, COMMON_PARAMS, DEFAULT_ROUTES, RULE_TO_CATEGORY mappings, and Docker fixture apps. `TestAllTenCategoriesWired` (12 unit tests) verifies all constants and routing. The full chain demo: `python3 scripts/run_full_audit_chain.py --target TESTS/fixtures/exploits/flask_sqli` (requires Docker).

---

### Q44. "Your OWASP FPR is 75.3% — you scream on clean code. Why should I trust this tool?" ⚠️ HIGH RISK

This is the right question and I welcome it. Three-part answer: (1) **Two operating points, one scan.** The 75.3% FPR is the *full output* — the recall-first mode used for developer triage. The *Confirmed Tier* (the auto-block mode) has near-zero FPR on production code. These are two points on the same Precision-Recall curve. You pick the operating point for your use case. (2) **The FPR is a corpus artefact.** SecurityEval has only 89 "clean" TN files — tiny snippets. On a real 10,000-file codebase, the absolute false positive *count* stays bounded while the FPR denominator grows. Precision (54.7% full output) is the corpus-size-immune metric; it means roughly 1 in 2 alerts is real in developer review mode. (3) **Precedent.** "Sifting the Noise" (arXiv:2601.22952) shows LLM-augmented SAST cuts SAST FPs ~91% (from 92% to 6.3% FPR on OWASP). ACR-QA's Confirmed Tier achieves a comparable reduction *statically*, targeting auto-block precision of 96.4%.

---

### Q43. "Does your autofix actually work? How do you know the fix closes the vulnerability?"

Yes — and we prove it. Verified Remediation (`CORE/engines/verified_remediation.py`) does: (1) exploit fires on original code (2) AI generates a patch (3) same exact exploit re-run on patched code in Docker sandbox (4) verify it now fails → `fix_verified=True` (5) ECDSA-sign `(vuln_proof, fix_diff, fix_proof)` as one bundle. Snyk retests statically and claims 80% accuracy. ACR-QA retests with the live exploit — binary ground truth. The attestation lets an auditor replay the chain: exploit working → patch applied → exploit failing, cryptographically signed.

---

### Q41. "Your numbers look cherry-picked. Why not use a standard benchmark?" ⚠️ HIGH RISK

We did. The OWASP Benchmark methodology is the field's standard — TPR, FPR, Youden J. We ran it on SecurityEval (s2e-lab, NeurIPS-cited) with dual corpus: 89 vulnerable TP files + 89 secure TN files. Result: ACR-QA Youden J=0.157 vs Bandit 0.090 vs Semgrep 0.056 — we lead on the primary OWASP metric. The FPR on the full output is 75.3% — I report it honestly. That FPR is what the Confirmed Tier is designed to eliminate: it targets 96.4% precision by accepting low recall on the auto-block stratum. `OWASP_BENCHMARK.md` has the full scorecard with bootstrap CIs, per-CWE breakdown, and reproduce commands.

---

### Q42. "Why is your FPR so high on OWASP? Doesn't that undermine the tool?"

It's the expected behavior of a recall-first tool. The full output maximizes recall (91.0% — best of all tools). High FPR is the cost. The Confirmed Tier inverts the trade-off: it targets near-zero FPR for merge-blocking, at the cost of recall. These are two different instruments. The OWASP methodology actually shows ACR-QA makes the best J trade-off of any tool tested (J=0.157 vs Bandit 0.090) — meaning even accounting for FPR, ACR-QA is net more useful than its competitors.

---

## Summary Card — Key Numbers

| Metric | Value |
|--------|------:|
| Version | v5.0.0rc2 |
| Python tests | 2,759 |
| TypeScript tests | 104 |
| Total tests | **2,863** |
| API endpoints | **52** |
| Alembic migrations | 18 |
| Eval corpus | **13 repos, 4 languages** |
| Recall vs Semgrep CE | **100% vs 71.2% (+28.8pp)** |
| CVE recall (detectable) | **8/8 = 100%** |
| CVE recall (overall) | 8/20 = 40% |
| Precision (ground truth) | **97.1%** (100% security class) |
| FP rate (Flask) | **1.0%** |
| FP rate (httpx) | **2.3%** |
| Inter-rater κ | **0.74** (substantial) |
| OWASP coverage | 9/10 |
| OWASP Methodology Youden J | **0.157** (leads Bandit 0.090, Semgrep 0.056) |
| P-2 recall (detectable CWEs) | **91.0%** vs Bandit 50.6%, Semgrep 23.6% |
| Novel engines | 10 contributions |
| Distribution | `pip install acrqa==5.0.0rc2` + GitHub Actions Marketplace |
