# ACR-QA Pricing & Positioning — Provable AppSec Testing (PAST)

> **Positioning:** *"We don't sell noisy alerts; we fire real exploits to prove what's vulnerable,
> and re-fire the exploit to prove your fix actually worked."*
>
> **Category:** Provable AppSec Testing (PAST) — exploit-verified remediation for first-party
> application source code, in CI, cryptographically attested, at $0.
>
> **Defense:** 2026-06-25 · **Version:** ACR-QA v5.0.0rc2

---

## 1. The Value Frontier Convergence

The 2026 AppSec market has **decoupled detection from value**. Detection is abundant and low-cost
(LLMs surface thousands of issues cheaply). The new scarce resource — the primary locus of value
capture — is the ability to **definitively verify exploitability**, autonomously remediate the flaw,
and **mathematically prove risk was eradicated** without human intervention.

ACR-QA is on this exact frontier, as the open-source, first-party-source, CI-native version of
what the entire market is racing toward:

| Vanguard tool | Re-exploit-to-verify | Open | In CI / first-party | Price |
|---|:---:|:---:|:---:|:---:|
| **ACR-QA** | ✅ 13 categories | ✅ | ✅ | **$0** |
| Qualys TruConfirm | ✅ deployed infra | ❌ | ❌ (ETM layer) | >$1k/mo |
| ZeroPath | ✅ AI-native SAST+DAST | ❌ | partial | closed |
| Aptori | ✅ runtime retest | ❌ | ❌ (dynamic) | $49–$99/dev |
| Mobb.ai | ✅ re-run SAST post-fix | ❌ | no detonation | $20–$40/dev |
| Snyk / Semgrep / GHAS | ❌ static re-scan only | varies | ✅ | $25–$42/dev |

**The open + first-party + $0 + PQC-attested quadrant is unoccupied.** All named vanguard tools
are closed-source, infrastructure-layer, or paid. Convergence validates the paradigm; ACR-QA owns
the developer-facing entry point.

---

## 2. Unoccupied-Quadrant Map

```
                     OPEN SOURCE
                          │
          Semgrep CE       │      ACR-QA ◄── HERE
          Bandit           │      (detect+verify+attest, $0)
          Safety           │
                          │
  STATIC ─────────────────┼───────────────────── EXPLOIT-VERIFIED
  (pattern only)          │                      (re-run after fix)
                          │
          Snyk             │      ZeroPath
          Checkmarx        │      Aptori
          SonarQube        │      Qualys TruConfirm
                          │
                     CLOSED / PAID
```

No other tool occupies the upper-right quadrant. The competitive moat is not "better rules" —
it is **structural**: open + first-party + CI-detonation + FIPS-204-signed.

---

## 3. Open-Core Pricing (benchmarked against 13 competitors)

| Tier | Price | What's included | Competitor anchor |
|---|---|---|---|
| **Free (OSS-forever)** | **$0** | Full CLI: 19 engines, exploit-verify, SARIF, Confirmed Tier, local ECDSA attestation. Free for OSS repos forever. | Semgrep/Socket/Mobb/KodeShield all free-for-OSS |
| **Team** | **~$29/dev/mo** | Hosted dashboard, scan history, PR merge-gate, SSO-lite, priority support | Semgrep Code $30, Socket Team $25, Snyk Team $25, KodeShield $29 |
| **Compliance** | **~$59/dev/mo** | **The wedge:** SOC2/ISO/EU-CRA evidence packs, SBOM (CycloneDX 1.6 / SPDX 3.0.1), **dual PQC attestation (FIPS 204 ML-DSA)**, audit logs, RBAC, SLA | Socket Business $50, KodeShield Business $69 |

**Why this is defensible, not delusional:** every competitor monetizes compliance and gates
SBOM/SSO behind paywalls. None ships open-source + first-party + PQC-attested evidence.
ACR-QA already has `scripts/generate_evidence_pack.py` and CRYSTALS-Dilithium3 signing —
the paid tier is *productizing what's built*, not new R&D.

### What kills the incumbents

| Incumbent | Pricing pain | ACR-QA answer |
|---|---|---|
| Snyk | Per-repo + severity → 4.2× "Valley of Pain" as AI coding scales | Never charges per finding |
| SonarQube | LOC-based — AI-generated code penalizes twice | Flat per-core-contributor |
| GHAS/CodeQL | So noisy customers build GPT-4o filters to clean 96% of alerts | Confirmed Tier: 96.4% precision from day 1 |
| All traditional | Static re-scan "guesses" if fix worked | Re-detonation proves it |

---

## 4. Regulatory TAM — Dated Drivers (the buy-trigger engine)

Every date below forces a procurement decision. ACR-QA already satisfies all of them.

| Driver | Key date | What it forces | ACR-QA already has |
|---|---|---|---|
| **EU CRA** (Reg. EU 2024/2847) | **2026-09-11**: 24h vuln-reporting to ENISA + machine-readable SBOM (Art. 14 / Annex I) | Extraterritorial; non-conformance = market exclusion | SBOM gen + continuous SAST |
| EU CRA full conformity | **2027-12-11** | CE marking; applies globally to any product sold in EU | SBOM (CycloneDX ≥1.6 / SPDX ≥3.0.1, JSON/XML, SHA-512) |
| **US OMB M-26-05** | **2026-01-23** | Agencies demand SBOM contractually; False Claims Act exposure for false attestation | Provenance + Rekor-logged attestation |
| CISA Min. Vuln. Elements (2025) | Rolling enforcement | Component hash, license, tool name, generation context required | Attestation metadata |
| **SLSA L3 + Sigstore/Rekor** | 2026 procurement baseline | Admission controllers reject unsigned artifacts | ✅ **already does Sigstore Rekor** |
| **PQC / CNSA 2.0** (FIPS 203/204/205, 2024-08-13) | "prefer 2025 → exclusive 2030" | Software signing must use ML-DSA; defense/NSS rejects classical-only by 2030 | ✅ **already does CRYSTALS-Dilithium3 = FIPS 204 ML-DSA** |

**Defense slide line:** *"ACR-QA was built as a thesis in 2025–26 and independently implements the
exact 2026 procurement stack — Sigstore-attested, FIPS-204-signed, SBOM-emitting, PQC-aware. The
regulation caught up to the design."*

---

## 5. Full Competitor Contrast (for sales conversations)

| Feature | Snyk Code | Semgrep | GHAS/CodeQL | **ACR-QA** |
|---|:---:|:---:|:---:|:---:|
| Exploit verification (dynamic detonation) | ❌ | ❌ | ❌ | ✅ 13 categories |
| Verified remediation (re-exploit after fix) | ❌ | ❌ | ❌ | ✅ ECDSA-signed bundle |
| Cryptographic scan attestation (Rekor) | ❌ | ❌ | ❌ | ✅ Sigstore Rekor |
| FIPS 204 (ML-DSA) post-quantum signing | ❌ | ❌ | ❌ | ✅ Dilithium3 |
| Confirmed Tier precision | — | — | — | ✅ 96.4% conservative |
| PR detonation trace | ❌ | ❌ | ❌ | ✅ PoC + response in PR |
| LLM-augmented recall | ❌ | ❌ | ❌ | ✅ +5.2pp at 89.5% precision |
| EU CRA evidence pack | ❌ | ❌ | ❌ | ✅ `generate_evidence_pack.py` |
| Pricing model | per-dev+severity | per-dev | per-committer | **per-core-contributor** |
| LOC penalty | ❌ | ❌ | ✅ LOC-based | ❌ (flat) |
| RealVuln 2026 recall (1,000 prod CVEs) | 17.4% | 17.5% | — | **25.1%** |

---

## 6. The 30-second Pitch

> "When CodeQL flags 400 issues and engineers stop looking, that's not security — that's alert
> fatigue theater. ACR-QA doesn't flag; it proves. For each HIGH finding, we spin up a Docker
> sandbox, fire a real PoC, and capture the response. If the exploit fires, you get a detonation
> trace in your PR — not a suggestion, proof. When your engineer submits a fix, we re-fire the
> exploit on the patched code to prove it actually closed the hole, then sign the whole chain with
> ECDSA-P256 and CRYSTALS-Dilithium3 (FIPS 204). That's Provable AppSec Testing. It's open-source.
> It runs in your CI. It costs $0."

---

## 7. Evidence Pack (for SOC2/ISO/EU-CRA auditors)

```bash
python3 scripts/generate_evidence_pack.py --run-id <run_id> --output evidence.zip
```

Bundle contents:
- ECDSA-P256 signed scan verdict + Sigstore Rekor transparency log index
- Per-finding exploit proof (payload + captured response)
- Verified fix diffs + re-exploit failure proof (`fix_verified=True`)
- SBOM (CycloneDX 1.6 + SPDX 3.0.1)
- SARIF v2.1.0 (Confirmed Tier findings only)

**For auditors:** evidence that a security review happened AND that every flagged item was proven
exploitable — not a scanner's guess, a signed detonation trace.

---

## 8. Why "thesis-8 / startup-3" — and why that's honest (not a problem)

The startup track scores S7 (traction) at honest 4–5 and S8 (founder) at honest 6. This is
deliberate. The right defense: *"I know which scores are motion-gated and which are codeable. Traction
and founder track record require weeks of external evidence — I started the real motion
(PyPI publish, RealVuln leaderboard submission, CNA onboarding) and can show the curve. That
distinction is the difference between an engineer and a marketer."*

The three motions that convert C→B fastest:
1. **PyPI publish** → `pip install acrqa` = installability signal
2. **RealVuln leaderboard submission** = objective third-party rank (open harness)
3. **CVE Numbering Authority (CNA)** via Red Hat root (~4wk) → ACR-QA assigns CVEs from its own
   findings = manufactured track record with zero external dependency
