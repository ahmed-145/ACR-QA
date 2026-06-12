# ACR-QA — 5-Minute Live Demo Script

Word-for-word, timed. Rehearse 3× out loud. The goal: **real repos → real findings → real
exploit-proof → signed.** Calm, slow, let the screen do the work.

---

## T-minus (before you present — do this in the hallway)

```bash
source .venv/bin/activate
make seed-demo            # pre-loads payments-api, web-backend, internal-tools (real scans)
make api                 # serve dashboard on :8000   (or: uvicorn FRONTEND.api.main:app --port 8000)
```
Open `http://localhost:8000`, log in, confirm the Overview shows numbers. Leave it on the Overview.
**If the venue Wi-Fi/projector misbehaves, everything is already seeded — you never depend on a live scan.**

---

## [0:00–0:45] Overview — "this is the trust layer"

> "This is the ACR-QA dashboard. It's already scanned a fleet of projects — including real
> open-source libraries you'll recognise: **requests, FastAPI, Flask, React**. Up top is the
> number that matters most: the **Confirmed Tier** — these are findings we're confident enough
> in to **automatically block a merge**, at 96.4% precision. The green banner shows the live
> trust KPIs: precision, CVE recall, F1, self-scan."

*(Point at the Confirmed Tier tile and the Trust Layer banner. Don't click yet.)*

## [0:45–1:15] Famous repo — credibility

> "Let me open a real one — **FastAPI**, the actual production source. ACR-QA scanned it like any
> repo: it ran six tools in parallel, normalised everything to one schema, and prioritised by
> severity. This isn't a toy — it's how it behaves on code the whole industry uses."

*(Open `tiangolo/fastapi` from the fleet; show the findings list briefly.)*

## [1:15–1:45] Zero-false-positives — answer the FP question before they ask

> "And here's the other side. These mature packages — **numpy, pandas, pydantic** — ACR-QA
> reports **zero high-severity findings**. That's deliberate: on clean code it stays quiet.
> **0.0% high false-positive rate.** A scanner that cries wolf gets ignored; this one doesn't."

*(Point at a 0-finding package in the fleet. This is your X6 evidence.)*

## [1:45–3:15] Live scan — show it work end to end

> "Now let's run one live. I'll scan **payments-api** — a sample backend with planted
> vulnerabilities."

*(Trigger the scan. While it runs ~60–90s, narrate:)*

> "Right now it's running Ruff, Semgrep, Bandit and the others in parallel, normalising their
> output, then applying the trust gates — confidence scoring, reachability, taint, and the
> Confirmed Tier. Watch the live progress."

*(When it completes:)*

> "Done — 64 findings, 13 high-severity, and **4 made it into the Confirmed Tier**."

## [3:15–4:30] One confirmed finding — the heart of the project

> "Let me open one — a **SQL injection**. Three things on this page. First, the **code and the
> rule** it violated. Second, the **AI explanation** — and notice it **cites the rule**; it's
> grounded in our knowledge base, not guessing, so it doesn't hallucinate. Third — and this is
> the part nothing else does — the **exploit verification**."

> "ACR-QA didn't just flag this. It spun up a throwaway Docker sandbox and **fired a real
> payload** — `' OR 1=1` — and confirmed the database leaked. So this isn't 'maybe a bug.' It's
> **proven exploitable.** And when there's a fix, it re-fires the exploit to confirm the fix
> actually closed it."

*(Open a confirmed SQLi finding; point to code → RAG explanation → exploit-verified verdict.)*

## [4:30–5:00] Attestation — close strong

> "Finally — every scan is **cryptographically signed**, ECDSA plus a post-quantum signature,
> and logged to a public transparency log. An auditor can verify this exact scan happened, with
> this exact result, in one command. **Detection you can trust, exploit-proof you can verify,
> and a signed record of all of it — self-hosted, at zero cost.** That's ACR-QA."

*(Show the attestation / signature on the run. Switch back to slides for Q&A.)*

---

## If something breaks (stay calm)

- **Live scan hangs / Wi-Fi dies:** "I'll show you a scan I ran earlier" → open the pre-seeded
  `payments-api` run. Identical story, zero dependence on the network.
- **Dashboard won't load:** you have the slide screenshots in the deck as backup — narrate from those.
- **Asked "is this a real repo?":** "payments-api is a deliberately-vulnerable sample app — like the
  ones used in security courses. The famous ones — FastAPI, requests — are the genuine sources. The
  detection, the exploit, and the signature are all real."

## Three lines to land no matter what

1. "We separated **detection** from **trust** — the Confirmed Tier is precise enough to auto-block."
2. "We don't **claim** a vulnerability — we **detonate** it in a sandbox."
3. "Every result is **signed** — verifiable provenance, self-hosted, zero cost."
