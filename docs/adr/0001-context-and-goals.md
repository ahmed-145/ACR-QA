# ADR 0001 — Context and Goals: What ACR-QA Is and Isn't

**Status:** Accepted
**Date:** 2026-05-05
**Author:** Ahmed Mahmoud Abbas

---

## Context

ACR-QA is built as a graduation thesis deliverable at King Salman International University (KSIU), supervised by Dr. Samy AbdelNabi. The timeline runs October 2025 – June 2026.

The problem it addresses: developers using multiple SAST tools (Ruff, Bandit, Semgrep, etc.) face three concrete pain points:

1. **Alert fatigue** — each tool dumps raw JSON in its own schema; no deduplication, no priority ranking.
2. **LLM hallucination** — general-purpose AI assistants (Copilot, ChatGPT) give confident but wrong security advice because they lack domain-specific rules.
3. **Invisible test coverage** — code coverage % doesn't tell you *which* complex functions have no test.

The thesis research questions are:
- **RQ1:** Can RAG reduce LLM hallucination in security explanations?
- **RQ2:** How to ensure full provenance for AI-generated findings?
- **RQ3:** What confidence scoring approach works for static analysis findings?
- **RQ4:** Does the combined pipeline match industry tools on precision/recall?

---

## Decision

Build a **self-hosted, $0-recurring-cost** code review platform that:

- Runs 10+ static tools in parallel and normalises output into a single canonical schema
- Uses RAG (Retrieval-Augmented Generation) with a curated knowledge base — the LLM can only cite rules it can retrieve, preventing hallucination by design
- Measures LLM output consistency via semantic entropy (3 independent runs) and penalises contradictory AI
- Stores full PostgreSQL provenance for every LLM call
- Is designed for local/self-hosted deployment, not SaaS

---

## Consequences

**What we gain:**
- Thesis research questions have direct implementation answers
- $0 cost lets the project run indefinitely on free-tier APIs
- Self-hosted means no privacy concerns about code leaving the organisation
- Canonical schema enables cross-tool deduplication and consistent UX

**What we explicitly do NOT do:**
- CSRF detection (requires runtime, not AST — false positive rate too high statically)
- IDOR / auth bypass / business logic bugs (inherent static analysis limits)
- SaaS multi-tenancy, billing, or enterprise auth (out of thesis scope)
- TypeScript rewrite (Phase 2, post-graduation)

**Constraint this creates:**
Every new feature must be justified against one of the four research questions or directly improve the thesis evaluation metrics (precision, recall, OWASP coverage, user study results). Features that don't serve the thesis are deferred.

---

## Alternatives Considered

| Option | Rejected Because |
|---|---|
| Build a SaaS wrapper around existing tools | Doesn't produce novel research contribution |
| Just use SonarQube for the thesis | No room for RAG, entropy, or test gap analysis — the differentiators |
| Full TypeScript rewrite from day one | Python is faster to iterate on; JS adapter added later (v3.0.1) |
| Local Ollama LLM (no external API) | Too slow for real-time CI/CD; hardware requirements too high |
