# ACR-QA Unit Economics — One-Pager

> **Version:** v5.0.0rc2 · **Date:** 2026-06-10 · **Status:** pre-revenue

---

## Cost Structure (current burn: $0)

| Cost category | Current | At scale |
|---|---|---|
| Infrastructure (self-hosted) | $0 | $0 (customer hosts) |
| LLM API (Groq LLaMA-3.3-70B) | $0 (free tier) | ~$0.0008/scan at scale |
| CI/CD | $0 (GitHub Actions free) | ~$0.004/scan |
| Maintainer salary | $0 (thesis project) | TBD (Phase 5) |
| **Total COGS (hosted tier)** | **$0** | **<$0.01/scan** |

Self-hosted Free tier has **zero marginal cost** by design — ACR-QA runs entirely on the
customer's infrastructure.

---

## Revenue Model (open-core, 3-tier)

| Tier | Price | Target customer | Conversion path |
|---|---|---|---|
| **Free (OSS-forever)** | $0 | Individual devs, OSS projects, academic | `pip install acrqa` → inbound |
| **Team** | ~$29/dev/mo | 5–50 dev teams wanting CI dashboard + PR gates | Free → dashboard trial → Team |
| **Compliance** | ~$59/dev/mo | Regulated industries (EU, US Gov, fintech, healthcare) | CRA/SOC2 deadline → Compliance |

### Per-seat economics at Team tier

| Input | Value |
|---|---|
| ASP (average selling price) | $29/dev/mo = $348/dev/yr |
| Assumed team size (SMB) | 10 devs |
| ARR per SMB account | **$3,480** |
| Gross margin (COGS ~$0) | **~100%** |
| Payback at $0 CAC (inbound) | **immediate** |

### Compliance tier uplift

A 10-dev team upgrading from Team → Compliance:
`10 × ($59 − $29) × 12 = $3,600/yr incremental ARR` per account.

EU CRA deadline (2026-09-11) is the forcing function: companies selling software in the EU
face market exclusion if they lack machine-readable SBOM and 24h vuln reporting. ACR-QA's
Compliance tier delivers both, pre-built. **One EU-facing customer converting to Compliance
recovers the full infra cost of hosting for months.**

---

## Capital Efficiency

| Metric | Value |
|---|---|
| Current spend to v5.0.0rc2 | **$0** (thesis project) |
| Lines of production code | ~12,000 |
| Test suite | 3,017 tests, 87.5% CORE coverage |
| Distribution channels | PyPI + GHCR + GitHub Actions Marketplace |
| Regulatory compliance | EU CRA / SLSA L3 / FIPS 204 — all pre-built |
| Engineering headcount | 1 (solo grad student) |

This is the primary VC story: the moat (exploit-verify + PQC attestation + compliance evidence)
was built as a side-effect of a thesis, not as funded R&D. The "startup" phase starts with a
feature-complete, compliance-ready product at $0 burn.

---

## Free-Tier Ceilings (prevent abuse, preserve margin)

| Limit | Free tier cap | Rationale |
|---|---|---|
| Repos per org | Unlimited OSS / 3 private | OSS goodwill; private repos need Team |
| AI enrichment calls | 50/day | Groq free-tier headroom |
| Exploit-verify sandbox | 10 detonations/day | Docker compute cap |
| Scan history retention | 7 days | Storage cost boundary |
| SSO / RBAC | ❌ | Team/Compliance gate |
| Evidence pack generation | ❌ | Compliance gate (the wedge) |

---

## Non-VC Funding Path (pre-revenue)

| Source | Amount | Deadline | Fit |
|---|---|---|---|
| GitHub SOSS Fund | $10k | rolling | ✅ best fit — solo, GitHub-hosted, OSS security |
| NLnet NGI0 Commons/Entrust | €5k–50k | **2026-08-01** | ✅ PQC + Sigstore alignment |
| Sovereign Tech Fund | min €50k | rolling (~6mo lead) | ✅ public-interest infra framing |
| EU SECURE cascade (as vendor to EU mSMEs) | €30k/mSME | open calls | ✅ indirect — sell compliance packs |

**Recommended first move:** GitHub SOSS grant application (rolling, highest probability, fastest).
No equity dilution. Positions ACR-QA as funded security infrastructure, not a hobby project.
