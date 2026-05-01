# LLM Provider Configuration

**Last Updated:** May 1, 2026

ACR-QA uses LLMs for two tasks:
1. **Explanation Engine** — generates natural-language explanations for findings (`CORE/engines/explainer.py`)
2. **Path Feasibility Validator** — checks if HIGH-severity security paths are reachable (`CORE/engines/path_feasibility.py`)

---

## Current Provider: Groq (Default)

| Setting | Value |
|---------|-------|
| **SDK** | `groq` Python SDK + `httpx` for async |
| **Model (explanations)** | `llama-3.3-70b-versatile` |
| **Model (feasibility)** | `llama-3.1-8b-instant` |
| **Auth** | `GROQ_API_KEY_1` … `GROQ_API_KEY_4` (round-robin via `KeyPool`) |
| **Endpoint** | `https://api.groq.com/openai/v1/chat/completions` |
| **Cost** | Free tier / ~$0.59 per 1M tokens (paid) |
| **Rate limit** | ~30 req/min per key → ~120 req/min with 4 keys |

### Setup

```bash
# .env (project root, gitignored)
GROQ_API_KEY_1=gsk_...
GROQ_API_KEY_2=gsk_...
GROQ_API_KEY_3=gsk_...
GROQ_API_KEY_4=gsk_...
```

See [TOKEN_SETUP.md](TOKEN_SETUP.md) for key generation instructions.

---

## Alternative Provider: AgentRouter ($150 Credits Available)

[AgentRouter](https://agentrouter.org) is an **OpenAI-compatible API gateway** that provides access to multiple LLM providers (OpenAI, Anthropic, DeepSeek, etc.) through a single API key and base URL.

| Setting | Value |
|---------|-------|
| **Base URL** | `https://agentrouter.org/v1` |
| **Auth** | Single API key from agentrouter.org dashboard |
| **Schema** | OpenAI-compatible (drop-in for `httpx` calls) |
| **Pricing** | Pay-as-you-go, mirrors upstream provider pricing |
| **Credits** | $150 available (as of May 2026) |

### Why Use AgentRouter?

1. **Multi-model access** — Test GPT-4o, Claude Sonnet, DeepSeek V3, etc. without separate accounts
2. **Thesis evaluation data** — Compare explanation quality across models for Chapter 5
3. **Fallback provider** — Use when Groq rate-limits you
4. **Stronger feasibility checks** — Route HIGH-severity path validation through a stronger model

### Available Models (via AgentRouter)

| Model | Best For | Approx. Cost/1K tokens |
|-------|----------|----------------------|
| `gpt-4o` | Highest accuracy explanations | ~$0.005 |
| `claude-sonnet-4-20250514` | Strong reasoning, code understanding | ~$0.003 |
| `deepseek-chat` | Cost-efficient alternative | ~$0.001 |
| `llama-3.3-70b` | Same as Groq default | ~$0.0006 |

> [!NOTE]
> Model names may change. Check the [AgentRouter docs](https://agentrouter.org) for the current model catalog.

---

## Integration Plan

### Option A: A/B Model Comparison (Recommended for Thesis)

Run the same findings through multiple models and compare quality metrics. This produces an **evaluation table** for the thesis:

| Metric | Llama 3.3-70b (Groq) | GPT-4o (AgentRouter) | Claude Sonnet (AgentRouter) | DeepSeek V3 (AgentRouter) |
|--------|-----------------------|----------------------|-----------------------------|---------------------------|
| Cites Rule % | 94.8% | ? | ? | ? |
| Avg Latency | ~800ms | ? | ? | ? |
| Self-Eval Score | 4.2/5 | ? | ? | ? |
| Cost / Finding | ~$0.0003 | ? | ? | ? |
| Semantic Entropy | ? | ? | ? | ? |

**Estimated cost:** ~$20–30 for a thorough comparison across 50+ findings × 4 models.

### Option B: Upgrade Path Feasibility

Replace `llama-3.1-8b-instant` with a stronger model (e.g., `gpt-4o`) for HIGH-severity security findings only. Better reachability analysis, minimal cost.

**Estimated cost:** ~$10–20 total.

### Option C: Fallback Provider

When Groq hits rate limits, automatically fall back to AgentRouter. Cheap insurance for demo day.

---

## How to Integrate (Technical)

### Step 1: Environment Variables

```bash
# .env
ACRQA_LLM_PROVIDER=agentrouter   # or "groq" (default)
AGENTROUTER_API_KEY=ar_...
AGENTROUTER_MODEL=gpt-4o         # optional, defaults to llama-3.3-70b
```

### Step 2: Code Changes Required

The integration is minimal since AgentRouter uses the **OpenAI-compatible schema**, and our async path (`_explain_one_async`) already uses raw `httpx` POST calls:

```python
# In CORE/engines/explainer.py — _explain_one_async()
# Current:
base_url = "https://api.groq.com/openai/v1/chat/completions"

# With AgentRouter:
provider = os.getenv("ACRQA_LLM_PROVIDER", "groq")
if provider == "agentrouter":
    base_url = "https://agentrouter.org/v1/chat/completions"
    api_key = os.getenv("AGENTROUTER_API_KEY")
else:
    base_url = "https://api.groq.com/openai/v1/chat/completions"
    api_key = self.key_pool.next_key()
```

### Step 3: Benchmark Script

Create `scripts/benchmark_models.py` to:
1. Load a fixed set of test findings
2. Run each through multiple models via AgentRouter
3. Collect: latency, token usage, cites_rule %, self-eval score, semantic entropy
4. Output a CSV/markdown comparison table

> [!IMPORTANT]
> The `groq` SDK `Groq()` client does **not** support custom base URLs. For AgentRouter, use the `httpx`-based async path or the `openai` SDK with `base_url` override.

---

## Budget Planning ($150 Credits)

| Use Case | Estimated Cost | Findings | Priority |
|----------|---------------|----------|----------|
| A/B comparison (4 models × 50 findings) | ~$25 | 200 API calls | ⭐ High |
| Path feasibility upgrade (GPT-4o) | ~$15 | ~100 calls | Medium |
| Demo day fallback buffer | ~$10 | reserve | Medium |
| **Total planned** | **~$50** | | |
| **Remaining buffer** | **~$100** | for iteration | |

> [!TIP]
> Start with the A/B comparison — it's the highest-value use for the thesis and costs very little. You can always use the remaining $100 for further experiments or demo-day safety net.

---

## Decision Log

| Date | Decision | Rationale |
|------|----------|-----------|
| 2026-05-01 | Documented AgentRouter as alternative provider | $150 credits available; thesis evaluation needs multi-model comparison data |
| 2026-05-01 | Recommended A/B comparison as primary use | Strongest academic value for thesis Chapter 5 evaluation |
| — | Groq remains default provider | Free tier, already integrated, KeyPool working well |
