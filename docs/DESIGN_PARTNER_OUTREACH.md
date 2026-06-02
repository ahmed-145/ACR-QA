# ACR-QA Design-Partner Outreach

> **Goal:** 5 design partners in 60 days. White-glove onboarding in exchange for:
> logos, a written case study, and verification-loop data (the moat).
>
> **Target ICP:** maintainers of OSS repos 1k–50k stars (Python/JS/Go) who use GitHub Actions.
> No procurement, instant install, public logos.

---

## Email / DM Template — OSS Maintainer

**Subject:** Free security review for [project-name] — want to try a different approach?

```
Hi [name],

I built ACR-QA (https://github.com/ahmed-145/ACR-QA) as my CS graduation project
and I'm looking for 5 OSS maintainers to try it on their repos before I open the
design-partner program publicly.

The short version: it's a trust layer for code review.
Instead of dumping 200 findings at you, it surfaces only what it can prove —
specifically, findings that pass a 4-criterion precision gate and (for security bugs)
a live exploit-verification step in a Docker sandbox. The result is ~25 findings at
96.4% precision instead of 1,942 at 8.6%.

What you get:
  - Free white-glove scan of [project-name] — I'll run it, triage the output, send
    you a clean report with only the Confirmed Tier findings
  - If anything is real, help fixing it (I'll send a PR or at minimum a pinpointed
    code snippet)
  - Your name/logo on the project page once you're comfortable

What I'd ask in return:
  - 30 minutes of your time to review the report and tell me if the findings are
    accurate (a simple "yes this is real" / "false positive" is enough)
  - A one-sentence quote I can use on the landing page

No strings. No email drip. If it's not useful, just ignore the report.

Interested? I can have the scan report to you within 48 hours.

Ahmed
(GitHub: ahmed-145 | email: ahmedabbass871@gmail.com)
```

---

## LinkedIn / GitHub Discussion Template (shorter)

```
Hey [name] — I built a SAST tool for my CS thesis that does exploit-verification
(fires real payloads in a Docker sandbox) so it only reports what it can prove.

Looking for 5 OSS maintainers to test it on their repos for free. Takes 2 minutes
to set up as a GitHub Action and produces ~25 findings at 96.4% precision instead
of the usual 200+ false-alarm flood.

Interested? Happy to send a free scan report for [project-name] with no strings.
```

---

## Target Repo List (prioritised)

| Repo | Stars | Language | Why |
|------|------:|----------|-----|
| httpx | ~14k | Python | Active HTTP library, known security surface |
| Flask | ~68k | Python | Classic Python web, known benchmark repo for ACR-QA |
| fastapi | ~80k | Python | Fast-growing, ASGI security surface |
| black | ~40k | Python | Low security risk — good for precision/FP study |
| express | ~65k | JS | High-value JS security surface |
| gin | ~80k | Go | Go web — exercises gosec + staticcheck |

**For each:** scan privately first → review findings manually → only reach out if ≥1 Confirmed finding is real (avoids wasting their time).

---

## What to Track (copy into a spreadsheet)

| Repo | Contacted | Responded | Scan Done | Report Sent | Verdict | Case Study |
|------|:---------:|:---------:|:---------:|:-----------:|---------|:----------:|
| | | | | | | |

---

## Conversion Goal

- **5 case studies** with: repo name · before (raw findings) · after (Confirmed count) · % that were TP · quote
- **1 filed CVE** from a real scan (biggest credibility unlock)
- **Start the verification data loop** — every confirmed/refuted finding logged to `verification_log`
