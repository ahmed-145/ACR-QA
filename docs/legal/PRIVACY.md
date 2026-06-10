# ACR-QA Privacy & Data-Flow Disclosure

ACR-QA offers three operating modes that differ in what data leaves your machine.
Set `ACRQA_MODE` to control the mode.

---

## Mode Summary

| Mode | `ACRQA_MODE` value | LLM calls | CVE lookups | Any external network? |
|------|:------------------:|:---------:|:-----------:|:--------------------:|
| **Cloud** (default) | `cloud` | Groq API (USA) | osv.dev API | ✅ Yes |
| **Hybrid** | `hybrid` | Groq API (USA) | Local OSV snapshot | Partial (LLM only) |
| **Offline** | `offline` | Local Ollama | Local OSV snapshot | ❌ No |

---

## Detailed Data-Flow per Mode

### Cloud mode (`ACRQA_MODE=cloud`)

| Data sent externally | Destination | Purpose |
|----------------------|-------------|---------|
| Code snippet (≤500 chars) per HIGH finding | Groq API | AI explanation + path feasibility |
| Finding message + rule ID | Groq API | AI explanation |
| Package name + version | osv.dev JSON API | CVE lookup |

**What is NOT sent:** full source files, repository history, secrets, database contents.

Code snippets are truncated at 500 characters before transmission. No data is retained
by ACR-QA after the API call completes (Groq retention policies apply).

### Hybrid mode (`ACRQA_MODE=hybrid`)

Same as Cloud except CVE lookups use the local OSV snapshot (`~/.acrqa/osv-snapshot/`)
downloaded by `make sync-osv`. Only LLM calls reach the network.

### Offline mode (`ACRQA_MODE=offline`)

**Zero egress.** All LLM inference runs via Ollama (`localhost:11434`). CVE lookups use
the local OSV snapshot. The egress guard (`CORE/utils/egress_guard.py`) raises
`EgressBlockedError` if any code path attempts an outbound HTTP call.

---

## Environment Variables

| Variable | Default | Purpose |
|----------|---------|---------|
| `ACRQA_MODE` | `cloud` | Master mode knob (`cloud` / `hybrid` / `offline`) |
| `ACRQA_LLM_PROVIDER` | `groq` | Override LLM provider (`groq` / `agentrouter` / `ollama` / `none`) |
| `ACRQA_LLM_MODEL` | `qwen2.5-coder:1.5b` (offline) | Main Ollama model |
| `ACRQA_LLM_MODEL_FAST` | same as MODEL | Fast model for path feasibility |
| `OLLAMA_BASE_URL` | `http://localhost:11434` | Ollama server URL |
| `OSV_SNAPSHOT_DIR` | `~/.acrqa/osv-snapshot` | Local OSV advisory directory |
| `ACRQA_OFFLINE` | `0` | Set to `1` to force offline mode without `ACRQA_MODE` |

---

## Third-Party Services Used in Cloud Mode

| Service | URL | Data sent | Privacy policy |
|---------|-----|-----------|---------------|
| Groq | api.groq.com | Code snippets, finding messages | groq.com/privacy |
| OSV.dev | api.osv.dev | Package names + versions | osv.dev |

Neither service is used in offline mode.

---

## Hosted SaaS (acrqa.dev) — Additional Disclosures

When using the hosted deployment at **acrqa.dev**, the following additional data is collected:

| Data | Purpose | Retention |
|------|---------|-----------|
| Email address | Account authentication | Until account deletion |
| Scan results (findings, severity, file paths) | Historical dashboard | 90 days unless pinned by user |
| Groq token usage per user | Quota enforcement | Rolling 30-day window |
| AI chat messages per finding | Conversation history | Deleted immediately on `DELETE /v1/findings/{id}/chat` |

### Your rights

- **Access:** `GET /v1/users/me/quota` returns your current token usage.
- **Deletion:** `DELETE /v1/auth/users/me` permanently deletes your account and all personal data within 24 hours. Anonymised aggregate analytics are retained.
- **Portability:** scan results are available via `GET /v1/runs` in JSON format.

### Data residency

acrqa.dev runs on Railway (US region). Groq API calls are routed to US data centers. No EU-specific region is available at this time.

### Contact

For privacy inquiries: ahmedabbass871@gmail.com
