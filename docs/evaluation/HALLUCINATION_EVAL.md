# T4.9 Hallucination-Detection Evaluation

_Generated: 2026-05-30T10:53:14Z_

## Method

Semantic entropy (3× llama-3.3-70b runs, trigram Jaccard consistency) + CVE fabrication check. Flagged when consistency < 0.5 OR LLM introduces CVE IDs absent from the finding.

## Summary

| Metric | Value |
|--------|------:|
| True-positive rate (hallucination detected) | **80.0%** |
| True-negative rate (grounded not flagged) | **0.0%** |
| Balanced accuracy | **40.0%** |
| TP / FP / TN / FN | 4 / 5 / 0 / 1 |
| Avg consistency — grounded | 0.259 |
| Avg consistency — hallucination | 0.343 |

## Probe Results

| ID | Label | Rule | Consistency | Flagged | CVE Fabricated | Correct |
|----|-------|------|:-----------:|:-------:|:--------------:|:-------:|
| G1 | GROUNDED | SECURITY-008 | 0.23 | ✓ | — | ✗ |
| G2 | GROUNDED | SECURITY-021 | 0.356 | ✓ | — | ✗ |
| G3 | GROUNDED | SECURITY-001 | 0.235 | ✓ | — | ✗ |
| G4 | GROUNDED | SECURITY-018 | 0.201 | ✓ | — | ✗ |
| G5 | GROUNDED | SQLI-001 | 0.272 | ✓ | — | ✗ |
| H1 | HALLUCINATION | SECURITY-001 | 0.233 | ✓ | — | ✓ |
| H2 | HALLUCINATION | SECURITY-005 | 0.456 | ✓ | — | ✓ |
| H3 | HALLUCINATION | SHELL-001 | 0.523 | — | — | ✗ |
| H4 | HALLUCINATION | SECURITY-003 | 0.242 | ✓ | — | ✓ |
| H5 | HALLUCINATION | CRYPTO-001 | 0.262 | ✓ | — | ✓ |

## Interpretation

The semantic-entropy mechanism flags explanations where three independent LLM calls disagree substantially on content (trigram Jaccard < 0.5). Grounded findings — where the code snippet provides concrete evidence — should produce consistent explanations. Hallucination-prone findings — where the LLM must invent details (fabricated CVEs, empty snippets, contradictory messages) — produce inconsistent explanations that are flagged.

The CVE fabrication check is a secondary signal: if any LLM call introduces a CVE ID not present in the original finding or snippet, it is flagged regardless of the consistency score.

**Threshold:** consistency < 0.5 → flagged. Chosen to match the implementation in `CORE/engines/explainer.py` `compute_semantic_entropy()`.
