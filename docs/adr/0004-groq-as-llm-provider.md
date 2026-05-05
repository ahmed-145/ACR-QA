# ADR 0004 — Groq as LLM Provider

**Status:** Accepted
**Date:** 2026-05-05
**Author:** Ahmed Mahmoud Abbas

---

## Context

ACR-QA's AI explanation layer (`CORE/engines/explainer.py`) needs a fast LLM API that can:
- Respond quickly enough for real-time CI/CD pipelines (< 2 s per explanation target)
- Handle semantic entropy (3× calls per finding) without killing latency budgets
- Cost $0 on a student budget

The LLM is called for:
1. **Explanation generation** — RAG-grounded explanation per finding (Llama 3.3-70b)
2. **Path feasibility validation** — "Is this code path actually reachable?" (Llama 3.1-8b)
3. **Self-evaluation** — LLM rates its own explanation 1–5 (Llama 3.3-70b)

All three are async via `httpx` to avoid blocking the pipeline.

---

## Decision

Use **Groq** as the primary LLM provider, with a **4-key rotation pool** to work around per-key rate limits.

| Use case | Model | Why |
|---|---|---|
| Explanation + self-eval | `llama-3.3-70b-versatile` | Best quality on free tier; 70B params give nuanced security explanations |
| Path feasibility | `llama-3.1-8b-instant` | Ultra-low latency needed; feasibility only needs a binary REACHABLE/UNREACHABLE verdict |

**Key pool rotation** (`GROQ_API_KEY_1` through `GROQ_API_KEY_4`):
- Round-robin across 4 accounts
- Effective throughput: ~120 requests/minute (4× the single-key limit of ~30 req/min)
- Implemented in `ExplanationEngine` constructor — transparent to callers

**Model selection rationale (Groq-specific):**
Groq's hardware (LPU — Language Processing Unit, Wafer-Scale Engine) achieves 500+ tokens/second on Llama inference — 5–10× faster than GPU-based providers. This makes semantic entropy (3× calls) feasible in a CI/CD context where total scan time matters.

---

## Consequences

**What we gain:**
- $0 recurring cost — entire thesis runs on free tier
- Sub-second LLM calls (typically 300–900 ms per explanation including network)
- Semantic entropy (3× calls) adds only +600–1800 ms — acceptable for a background CI step
- Easy model upgrades — swap model string in one place

**What we lose:**
- Groq rate limits become the hard ceiling at scale (120 req/min with 4 keys)
- Provider dependency — if Groq changes pricing/availability, API calls fail gracefully (fallback to static rule description)
- `llama-3.3-70b-versatile` is not available offline; `--no-ai` flag exists for offline runs

**Graceful degradation:**
If Groq is unavailable or rate-limited, `ExplanationEngine.get_fallback_explanation()` returns the static `rules.yml` description. Scans still complete; they just lack the AI-generated explanation.

**API key security:**
Keys are stored in `.env` (gitignored). Never committed. The `conftest.py` global `mock_env` fixture injects dummy keys for all tests — no real keys needed to run the test suite.

---

## Alternatives Considered

| Option | Rejected Because |
|---|---|
| OpenAI GPT-4o | ~$0.005/call × 3 entropy calls × 50 findings = ~$0.75/scan — not sustainable for a student project |
| Anthropic Claude API | Similar cost; no free tier for automation |
| Google Gemini (free tier) | Slower, lower quality on coding tasks than Llama 3.3-70b at time of decision |
| Local Ollama (Llama 3.1-8b) | 8B model on CPU: 20–60 s/call — unusable in CI/CD; GPU not available |
| Cerebras API | Originally used (visible in AGENT_NOTES.md); migrated to Groq in v3.2.4 for better rate limits and model availability |
