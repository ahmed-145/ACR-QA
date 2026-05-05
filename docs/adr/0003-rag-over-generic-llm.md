# ADR 0003 — RAG + Semantic Entropy over Generic LLM Prompting

**Status:** Accepted
**Date:** 2026-05-05
**Author:** Ahmed Mahmoud Abbas

---

## Context

ACR-QA needs to explain security findings to developers in plain language, with actionable remediation steps. Two naive approaches were considered and rejected:

**Naive approach A — Raw LLM prompt:**
```
"Explain this finding: eval() used at app.py:42"
```
Problem: LLMs hallucinate. They give confident, plausible-sounding but incorrect security advice, especially for language-specific or framework-specific rules. There is no way to know *which* part of the response is grounded in fact.

**Naive approach B — No AI, just rule descriptions:**
Static rule descriptions from `config/rules.yml` are accurate but generic. They don't reference the specific code, don't explain *why* this particular instance is dangerous, and don't generate localised fix examples.

The thesis research question RQ1 is: *"Can RAG reduce LLM hallucination in security explanations?"* The implementation must be able to answer this quantitatively.

---

## Decision

Implement **Retrieval-Augmented Generation (RAG)** with a curated knowledge base, combined with **semantic entropy scoring** to detect residual hallucination:

### RAG implementation

1. Every canonical rule ID has a corresponding entry in `config/rules.yml` with: name, category, severity, description, rationale, remediation steps, and code examples. 100% rule coverage (66 rules as of v3.2.4).

2. Before calling the LLM, `ExplanationEngine` retrieves the matching `rules.yml` entry and injects it into the prompt:
   ```
   "Based ONLY on the following rule documentation:
    [rule text from rules.yml]
   Explain why this code is dangerous and how to fix it:
    [code snippet]"
   ```
   The LLM cannot invent a rule it wasn't given. If no rule is found, it falls back to the raw rule description — it cannot fabricate security advice.

3. The explanation is evidence-grounded: every response cites the rule ID it was given, making it auditable.

### Semantic entropy scoring

To quantify residual hallucination (RQ1 measurement):
1. The same prompt is sent to the LLM **3 times** with different temperature values.
2. N-gram similarity across the 3 responses is computed: `consistency_score ∈ [0, 1]`.
3. A `consistency_score < 0.5` means the LLM contradicted itself — the finding gets a lower confidence badge on the dashboard.

### Self-evaluation

After generating the explanation, the LLM is asked to rate its own output on relevance / accuracy / clarity (1–5 scale). This `self_eval_score` is stored in PostgreSQL alongside the explanation, enabling longitudinal analysis.

---

## Consequences

**What we gain:**
- Hallucination is detectable and quantifiable (answers RQ1)
- Every explanation is auditable via the `llm_explanations` PostgreSQL table (answers RQ2)
- `consistency_score` and `self_eval_score` form the basis of per-finding confidence (answers RQ3)
- 100% of findings have a rules.yml entry — there is no "unknown rule" that falls back to pure LLM guessing

**What we lose:**
- Every explanation requires 3 LLM calls instead of 1 — 3× API cost and latency
- The 66-rule knowledge base must be maintained manually; new rules need KB entries before they get grounded explanations
- Groq rate limits become the bottleneck at scale (mitigated by 4-key rotation pool)

**Mitigations:**
- Entropy scoring only runs for HIGH severity findings by default (configurable)
- LLM responses are Redis-cached with a 7-day TTL — repeated scans of unchanged code don't re-call the API
- 4 Groq API keys in rotation give ~120 requests/minute effective throughput

---

## Alternatives Considered

| Option | Rejected Because |
|---|---|
| Generic LLM prompt with no KB | Hallucination rate too high for academic submission — can't be cited as trustworthy |
| Vector database (FAISS/Pinecone) for RAG | 66 rules fit in RAM as a simple dict — vector DB adds dependency without benefit at this scale |
| Fine-tuned model | Requires training data and GPU — far outside thesis scope and budget |
| No AI, rule descriptions only | Misses the core research contribution; RQ1 can't be answered |
| OpenAI GPT-4 | $$$; rate limits without significant cost; Groq free tier is sufficient |
