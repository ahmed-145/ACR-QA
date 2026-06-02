# ACR-QA Launch Posts

> **Instructions:** Post HN the day after defense. Post LinkedIn the same day.
> Write the blog post first (it's what HN links to).
> DO NOT post until items #2–#11 are at least partially shipped.

---

## Hacker News — "Show HN"

**Title:**
```
Show HN: ACR-QA – open-source SAST that reaches 96.4% precision on production code (F1=98.2%)
```

**Body:**
```
I built ACR-QA as my CS graduation thesis at KSIU. It orchestrates 19 static analysis engines
(Bandit, Semgrep, Ruff, gosec, ESLint, Trivy...), normalises everything into one schema, and
uses RAG-grounded Groq LLaMA to explain each finding.

The problem: most SAST tools have 8-30% precision in practice — developers learn to ignore them.

My approach: a 4-criterion "Confirmed Tier" filter (HIGH severity + 22-rule confirmed set +
production code path + Bandit internal HIGH confidence) that reaches 96.4% conservative precision
(95% CI [90.9%, 100%]) with 100% CVE recall preserved.

Head-to-head on the same 30-repo adversarial corpus (top-20 PyPI + top-6 npm + top-4 Go):
  Bandit alone:     F1 = 21.8%  (1/8 CVEs caught)
  Semgrep CE alone: F1 = 45.7%  (5/8 CVEs caught)
  ACR-QA P4:        F1 = 98.2%  (8/8 CVEs caught)

One-liner to try it:
  docker run --rm -v $(pwd):/scan -e GROQ_API_KEY_1=your_key \
    ghcr.io/ahmed-145/acrqa:latest \
    python3 CORE/main.py --target-dir /scan --rich

What's in the box:
  - 52-endpoint FastAPI service + React 18 dashboard
  - Differential SAST (new-only findings vs last scan)
  - Counterfactual explanations ("what minimal change removes this?")
  - Groq + Gemini multi-LLM jury
  - K8s operator (ACRQAScan CRD)
  - VS Code extension (find me on the Marketplace)
  - SLSA L3 provenance, Cosign-signed GHCR image
  - 2,757 tests, 85% coverage, $0 recurring cost

GitHub: https://github.com/ahmed-145/ACR-QA
Demo: https://acrqa.pages.dev

Happy to answer questions about the evaluation methodology, the Confirmed Tier design,
or why I chose this over just running Bandit + Semgrep together.
```

---

## LinkedIn Article

**Title:**
```
I built a SAST tool with 96.4% precision as my thesis. Here's what I learned.
```

**Body:**
```
Most static analysis tools have a dirty secret: their false positive rate in practice is
between 35% and 80%. Developers learn to ignore them. The tool that cried wolf.

For my graduation thesis at KSIU, I set out to fix this.

**The result:** ACR-QA — an open-source platform that orchestrates 19 analysis engines,
normalises everything into one schema, and uses RAG-grounded AI explanations.

The headline number: **96.4% precision with 100% CVE recall** on a 30-repo adversarial
corpus of production-grade libraries (the top-20 PyPI packages, top npm packages, top Go
packages). F1 score: **98.2%**. Vs Bandit (F1 21.8%) and Semgrep CE (F1 45.7%) on
identical input.

**How?** The "Confirmed Tier" — a 4-criterion filter that only surfaces findings that are:
1. HIGH severity
2. From a 22-rule confirmed rule set
3. In production code (not test files)
4. Flagged HIGH confidence by Bandit's own internal signal

This reduces 1,942 raw findings to 55 — but the precision jumps from 8.6% to 96.4% while
preserving all 8 detectable CVEs from the recall battery.

**What I shipped:**
- 52 FastAPI endpoints, React 18 dashboard (WCAG 2.1 AA, Arabic RTL)
- Multi-LLM jury (Groq + Gemini free tiers)
- Differential SAST ("show me only new findings vs last scan")
- Counterfactual AI explanations ("what minimal change removes this vulnerability?")
- Kubernetes operator with CRDs
- VS Code extension on the Marketplace
- SLSA L3 provenance, Cosign-signed Docker image on GHCR
- 2,757 tests at 85% coverage

**What I learned:**
1. Precision matters more than recall for developer adoption. A 96% precise tool gets
   used; a 30% precise tool gets disabled.
2. RAG hallucination detection (N-gram entropy across 3 independent LLM runs) is the
   most underrated technique in AI-assisted tooling.
3. Adversarial evaluation (testing on clean production code, not toy vulnerable apps)
   is the only honest precision measurement.

The project is fully open-source ($0 recurring cost to run):
👉 https://github.com/ahmed-145/ACR-QA
🐳 docker run ghcr.io/ahmed-145/acrqa:latest
🌐 https://acrqa.pages.dev

If you're building security tooling or doing research in SAST, I'd love to connect.

#softwareengineering #security #sast #ai #openSource #graduation
```

---

## Blog Post Outline

**Platform options (all free):** dev.to · hashnode.dev · medium.com

**Title:** "How I Got 96.4% SAST Precision: The Precision Funnel Explained"

**Sections:**
1. The problem: false positive fatigue in static analysis
2. Architecture overview (pipeline diagram)
3. The 5-rung precision funnel (with the 1942→55 numbers)
4. What the Confirmed Tier gate actually is (non-tautological design)
5. Head-to-head results: Bandit vs Semgrep vs ACR-QA P4
6. The novel evaluations: X1 live-CVE, X2 exploit verify, X3 AI-code study
7. What I'd do differently (inter-procedural taint, more language coverage)
8. How to run it yourself (Docker one-liner)

**Target length:** 1,200–1,800 words
**Publish:** same day as HN post
