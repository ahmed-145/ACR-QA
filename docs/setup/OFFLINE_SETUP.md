# ACR-QA Offline Mode Setup

Run ACR-QA entirely on-device — no Groq key, no internet, no data leaves your machine.

---

## Prerequisites

- Python 3.10+
- [Ollama](https://ollama.ai) installed and running
- ~4 GB free disk space (model + OSV snapshots)

---

## Step 1 — Install Ollama

**macOS / Linux:**
```bash
curl -fsSL https://ollama.ai/install.sh | sh
```

**Windows:** download the installer from https://ollama.ai/download

Verify it's running:
```bash
ollama list   # should show empty table
```

---

## Step 2 — Pull the default model

```bash
ollama pull qwen2.5-coder:1.5b
```

This is the default model used by ACR-QA in offline mode. For better explanation
quality at the cost of speed, try `qwen2.5-coder:7b`:

```bash
ollama pull qwen2.5-coder:7b
ACRQA_LLM_MODEL=qwen2.5-coder:7b ACRQA_MODE=offline python -m CORE.main <target>
```

---

## Step 3 — Download OSV vulnerability snapshots

```bash
make sync-osv
```

This downloads OSV advisory archives (~1.5 GB compressed) for PyPI, npm, Go, crates.io,
Maven, and RubyGems into `~/.acrqa/osv-snapshot/`. Run it weekly to stay current.

You can also do it manually:
```bash
python scripts/sync_osv_db.py
python scripts/sync_osv_db.py --ecosystems PyPI npm   # subset only
OSV_SNAPSHOT_DIR=/data/osv python scripts/sync_osv_db.py  # custom dir
```

---

## Step 4 — Run in offline mode

```bash
ACRQA_MODE=offline python -m CORE.main /path/to/repo
```

Or set it in your `.env`:
```
ACRQA_MODE=offline
OLLAMA_BASE_URL=http://localhost:11434
```

ACR-QA will:
1. Use Ollama for all AI explanations and path feasibility checks
2. Use the local OSV snapshot for dependency CVE lookups
3. Block all outbound HTTP calls (egress guard raises `EgressBlockedError` if anything tries to reach the network)

---

## Build a portable offline bundle

```bash
make offline-pack
```

This creates `./offline-bundle/` containing:
- Pre-downloaded Python wheels (installable without PyPI)
- An `.env.offline` template
- Instructions to copy to an air-gapped machine

---

## Troubleshooting

| Problem | Fix |
|---------|-----|
| `EgressBlockedError` on startup | A plugin or dep is trying to phone home — check logs for the blocked URL |
| Ollama not found | Make sure `ollama serve` is running: `ollama serve &` |
| OSV snapshot missing | Run `make sync-osv` |
| Slow AI explanations | Use a smaller model: `ACRQA_LLM_MODEL=qwen2.5-coder:1.5b` |
| `model not found` from Ollama | Run `ollama pull <model-name>` |

---

## Environment Variable Reference

| Variable | Default | Description |
|----------|---------|-------------|
| `ACRQA_MODE` | `cloud` | `offline` enables full offline mode |
| `ACRQA_LLM_MODEL` | `qwen2.5-coder:1.5b` | Main Ollama model for explanations |
| `ACRQA_LLM_MODEL_FAST` | same as MODEL | Smaller model for path feasibility |
| `OLLAMA_BASE_URL` | `http://localhost:11434` | Ollama server URL |
| `OSV_SNAPSHOT_DIR` | `~/.acrqa/osv-snapshot` | Local OSV advisory directory |
