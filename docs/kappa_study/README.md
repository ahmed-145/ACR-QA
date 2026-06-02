# ACR-QA 5-Rater Inter-Rater Reliability Study

## Purpose

This study measures **Fleiss' κ** (kappa) agreement among five independent raters
classifying a random sample of ACR-QA findings as TP / FP / NEEDS_REVIEW.

A κ ≥ 0.78 ("substantial agreement") justifies the claim that the ground truth used
in the thesis evaluation is reproducible and not author-specific.

## Timeline

| Step | When | Who |
|------|------|-----|
| Recruit 5 raters (KSIU peers / faculty) | Week 1 | Ahmed |
| Share `RATING_FORM.md` + 30 findings sample | Week 1 | Ahmed |
| Raters complete their sheet | Weeks 1–2 | Raters |
| Run `analyze_kappa.py` on submitted sheets | Week 10 | Ahmed |
| Report result in thesis §5.10 | Week 10 | Ahmed |

## Files

| File | Purpose |
|------|---------|
| `RATING_INSTRUCTIONS.md` | Rater instructions + definitions |
| `RATING_FORM_template.csv` | Template raters fill in |
| `sample_30_findings.json` | The 30 findings to classify |
| `analyze_kappa.py` | Compute Fleiss' κ from submitted CSVs |
| `submitted/` | One CSV per rater goes here |

## Recruitment Script (for WhatsApp/Email)

> Hi [Name], I'm running a quick inter-rater reliability study for my thesis.
> It takes ~20 minutes: classify 30 code security findings as TP, FP, or
> NEEDS_REVIEW using the guide I'll share. No coding knowledge needed — just
> read the snippet and the vulnerability description and make a judgement call.
> Would you be willing to help?

## Expected Outcome

| κ | Interpretation |
|---|---------------|
| ≥ 0.90 | Almost perfect — strong thesis claim |
| ≥ 0.78 | **Target** — substantial agreement |
| ≥ 0.61 | Moderate — acceptable but note limitations |
| < 0.61 | Fair — investigate disagreements, report honestly |
