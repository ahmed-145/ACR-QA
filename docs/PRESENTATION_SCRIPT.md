# ACR-QA Thesis Defense & Demo Script (v4.6.0)

*7 minutes total: 2 min slides → 5 min live demo. Show, don't tell.*

---

## Before the Meeting (Do This 10 Minutes Early)

### Terminal Setup
```bash
cd ~/Documents/KSIU/GRAD/SOLO
source .venv/bin/activate
docker compose up -d        # Start Postgres + Redis + FastAPI + Celery + Grafana
```

### Browser Tabs (Open These)
- **Tab 1:** `http://localhost:8001/ui/` — Static HTML dashboard (login: admin@acrqa.local)
- **Tab 2:** `https://github.com/ahmed-145/ACR-QA/releases/tag/v4.6.0` — Release page
- **Tab 3:** `https://github.com/ahmed-145/ACR-QA/actions` — CI/CD green checkmarks
- **Tab 4:** `https://acrqa-api-production.up.railway.app/health` — Live production deploy

### Terminal Tabs
- **Terminal 1:** `make api` — FastAPI started by docker compose
- **Terminal 2:** This is your demo terminal (run commands here)

---

## Part 1: Slides (2 Minutes)

### Slides 1-2: Context
> "Hello Dr. Samy. Today I want to show you the completed enterprise release: ACR-QA v4.6.0. It's a fully automated, AI-powered Code Review platform that runs 10 analysis tools across Python, JavaScript, and Go — normalises them into a single standard, and uses RAG-enhanced AI to explain every finding."

### Slides 3-7: What Makes It Different
> "There are three things no commercial competitor — not SonarQube, not CodeRabbit — offers. First, I built a Policy-as-Code engine where teams define quality rules in a YAML file and the system enforces them in CI. Second, I wrote a Test Gap Analyzer from scratch using Python's Abstract Syntax Tree to find untested business logic by complexity. Third, I implemented semantic entropy scoring — the AI runs 3 times and the system mathematically detects when it contradicts itself, preventing hallucination."

### Slide 8: Evaluation
> "Most importantly, I built a rigorous, multi-layer evaluation stack. We have 2,279 automated tests, 37 API endpoints, 13 repos across 4 languages, a CVE recall study against NIST-published vulnerabilities, and inter-rater agreement of kappa=0.74 on a blind peer validation study. But rather than talking about it, let me show you."

---

## Part 2: Live Demo (5 Minutes)

### Demo 1: The Dashboard (Browser - 1.5 min)
> "First, this is the 13-page product dashboard — built entirely from scratch."

- Switch to Browser **Tab 1** (`localhost:8001/ui/`)
- **Landing page:** "Marketing-grade landing with a live demo mode — click Try Live Demo and you get findings in under 30 seconds without creating an account."
- **Log in** with `admin@acrqa.local` — "JWT authentication, works offline or on Railway."
- **Overview page:** "Quality gate status, severity counters, pipeline health — all live."
- **Click Findings then click a finding:** "Confidence gauge, reachability verdict, exploit status, taint flow diagram, and 4-step AI reasoning trace. Hit Cmd+K for the command palette."
- **Compare page:** "Run-vs-run diff — shows what was fixed and what regressed between two scans."

### Demo 2: The 2,279 Tests (Terminal - 1 min)
> "Now let me prove the reliability. I'm going to run all 2,279 Python tests right now."

```bash
make test-all
```

> "2,279 Python tests plus 66 TypeScript tests — covering databases, API endpoints, AI logic, chaos engineering, supply chain, and WCAG accessibility — all passing."

### Demo 3: AST Test Gap Analyzer (Terminal - 1 min)
> "Now, this is one of our most competitive features. No existing tool does this."

```bash
python3 scripts/test_gap_analyzer.py --target CORE/ --format text
```

> "It scanned 103 functions, found 40 that are untested, and ranked them by cyclomatic complexity. The red ones are the most dangerous — complex logic with zero test coverage."

### Demo 4: AI Security Engine (Terminal - 1 min)
> "Finally, let me run the core AI engine on sample code with known vulnerabilities."

```bash
python3 CORE/main.py --target-dir TESTS/samples --rich --limit 5
```

> "It caught security vulnerabilities, mapped them to OWASP standards, and the Quality Gate correctly failed — meaning in a real CI/CD pipeline, this code would be blocked from merging."

### Demo 5: Distribution (Browser - 30 sec)
- Switch to Browser **Tab 2** (Releases): "I created an official v4.6.0 release, distributed on PyPI (`pip install acrqa`) and the GitHub Actions Marketplace (`uses: ahmed-145/acrqa-action@v1`)."
- Switch to Browser **Tab 3** (Actions): "Every push triggers 2,279 tests automatically."
- Switch to Browser **Tab 4** (Live): "And this is the live production deployment on Railway. It's running right now."

### Closing Line
> "This is no longer a prototype, Dr. Samy. It is a fully automated, enterprise-ready product — distributed on PyPI and the GitHub Actions Marketplace. Do you have any questions?"

---

## Q&A Cheat Sheet

### Q: "Your benchmarks are toy apps. How do I know this works on real production code?" [MOST IMPORTANT]

> "That's the most important question about the evaluation, and I want to answer it directly. You're right that DVPWA, Pygoat, VulPy and DSVW are intentionally vulnerable. They are not my proof that the tool works on real code — they are my proof that it can find known bugs against ground truth. That's a controlled experiment, the same way a drug trial uses controlled groups.
>
> For real-world validation I ran ACR-QA on Flask — 68 thousand stars on GitHub, used by millions of production apps. I manually triaged every HIGH-severity finding. Result: 1.0% false-positive rate. Same exercise on httpx: 2.3%. Industry baseline for SonarQube on Python is 30 to 40 percent.
>
> And methodologically, this mirrors the SAST research standard — every published SAST evaluation since 2008 uses synthetic ground-truth corpora because there's no other way to measure recall at scale. What's novel is the layered approach: synthetic ground truth plus real-world FP measurement plus independent CVE recall plus blind peer validation."

**Backup numbers:**
- Flask: 100 HIGH findings, 1 FP = 1.0%
- httpx: 43 HIGH findings, 1 FP = 2.3%
- SonarQube baseline: 30-40% Python FP rate
- Corpus: 13 repos, 4 languages, 9/10 OWASP Top 10 covered

**Follow-up ("Why not more real repos?"):**
> "I expanded to 13 repos across 4 languages. I chose depth over breadth: well-labelled repos give defendable numbers; unlabelled repos are noise."

---

### Q: "You ran CVEs — how many did you actually detect?"

> "I ran 10 disclosed CVEs from NIST-published Python vulnerabilities. Result: 2 out of 10 (20%). I'm not hiding that number — I'm leading with it. Each miss is explained by a documented failure mode: alias/indirection patterns the tools can't follow, ORM-internal SQL construction, and TOCTOU races. These are genuine open research problems — the same patterns Snyk and Semgrep miss. The CVE data is pre-registered before scanning, so I cannot cherry-pick results retroactively."

---

### Q: "Did anyone independently verify your findings?"

> "Yes. I ran a blind inter-rater agreement study: 20 findings from the Flask scan were given to an independent reviewer with no context about my labels. Cohen's kappa = 0.74 — that's substantial agreement on the Landis & Koch 1977 scale, the same scale used in medical research and NLP annotation. Full study in docs/evaluation/PEER_VALIDATION.md."

---

### Q: "What are these 2,279 tests? Where did they come from?"
> "In Phase 1, we only had about 30 tests checking the happy path. These 2,279 tests simulate real-world disasters: database crashes mid-review, corrupted file uploads, 1,000 findings at once. We even have chaos engineering tests that inject Postgres and Redis failures. I wrote them to prove the system won't break under pressure."

### Q: "What is CI/CD? Why now? Doesn't deployment cost money?"
> "CI/CD is Continuous Integration / Continuous Deployment, using GitHub Actions — 100% free for open-source projects. Every time I push code, GitHub's servers automatically run our 2,279 tests and block the code if anything fails."

### Q: "How is this different from SonarQube or CodeRabbit?"
> "Three things no competitor offers. First, our Test Gap Analyzer uses AST to find untested complex code — SonarQube and CodeRabbit don't do this. Second, our hallucination detection runs the LLM 3 times and measures consistency using Semantic Entropy. Third, we publish ECDSA-signed provenance attestations for every scan. And we do all of this at zero recurring cost using free-tier APIs."

### Q: "What's next?"
> "The tool is already shipped — v4.6.0 is on PyPI and the GitHub Actions Marketplace. Watching the download counter. The remaining thesis task is filming the 5-minute demo video. Longer-term: expanding CVE recall to MEDIUM-severity CVEs would bring recall from 20% to approximately 40% based on our near-hit analysis."

---

## Quick Command Reference

### Before the Meeting (10 min early)
```bash
cd ~/Documents/KSIU/GRAD/SOLO
source .venv/bin/activate
docker compose up -d
make seed-admin
```

### Demo Commands

```bash
# 1 — Run all 2,279 Python tests
make test-all

# 2 — AST Test Gap Analyzer
python3 scripts/test_gap_analyzer.py --target CORE/ --format text

# 3 — AI Security Engine
python3 CORE/main.py --target-dir TESTS/samples --rich --limit 5

# 4 — Real repo scan (DVPWA)
python3 CORE/main.py --target-dir /tmp/dvpwa --limit 0
```

### Browser Tabs
1. `http://localhost:8001/ui/` — Dashboard (login: admin@acrqa.local)
2. `https://github.com/ahmed-145/ACR-QA/releases/tag/v4.6.0` — Release Page
3. `https://github.com/ahmed-145/ACR-QA/actions` — CI/CD
4. `https://acrqa-api-production.up.railway.app/health` — Live Railway

### Key Numbers
| Metric | Value |
|--------|------:|
| Version | v4.6.0 |
| Python tests | 2,279 |
| TypeScript tests | 66 |
| FastAPI endpoints | 37 |
| Alembic migrations | 11 |
| Eval corpus | 13 repos, 4 languages |
| Precision (ground truth) | 97.1% |
| FP rate (Flask) | 1.0% |
| FP rate (httpx) | 2.3% |
| CVE recall | 2/10 (20%) |
| Inter-rater kappa | 0.74 (substantial) |
| OWASP coverage | 9/10 Top 10 |
| Distribution | PyPI + GitHub Actions Marketplace |
