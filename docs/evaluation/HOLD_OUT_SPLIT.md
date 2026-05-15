# Evaluation Hold-Out Split — ACR-QA

**Purpose:** Prevent overfitting in reported evaluation numbers.
The "training" set contains repos that were used to tune rules,
thresholds, and RULE_MAPPING during development. The "hold-out"
set was never touched during development — numbers on these repos
are unbiased estimates of real-world performance.

---

## Training Set (used during development — tuned on these)

These 4 repos were used throughout Phases 1–9 to validate detection
rules and calibrate thresholds. Evaluation numbers on these repos
are **optimistic** and should not be reported as generalization evidence.

| Repository | Language | Used for |
|------------|----------|----------|
| **DVPWA** | Python | Primary taint analysis tuning target |
| **Pygoat** | Python | SQL injection + XSS rule calibration |
| **VulPy** | Python | Multi-vulnerability rule coverage check |
| **DSVW** | Python | Edge case detection (SSRF, XXE) |

---

## Hold-Out Test Set (never used during development)

These 6 repos were added in Phase 8 **after** all rule tuning was
complete. No rule or threshold was adjusted based on their results.
Numbers reported on these repos represent genuine generalization ability.

| Repository | Language | Ground Truth | Recall (actual) | Notes |
|------------|----------|:------------:|:---------------:|-------|
| **vulnerable-flask-app** | Python | 5 findings | ✅ ≥80% | Phase 8 baseline |
| **bandit-test-cases** | Python | 4 findings | ✅ 100% | Official Bandit test suite |
| **NodeGoat** | JavaScript | 2 findings | ✅ ≥50% | JS taint flows |
| **DVNA** | JavaScript | 2 findings | ✅ 100% | Node.js vulns |
| **DVWS-Node** | JavaScript | 2 findings | ✅ ≥50% | WebSocket vulns |
| **Juice Shop** | TypeScript | 3 findings | ✅ ≥67% | OWASP flagship app |

---

## Reporting Convention

When stating precision/recall in the thesis or a paper:

- **"On the training set"** = DVPWA + Pygoat + VulPy + DSVW
- **"On the hold-out test set"** = the 6 repos above
- **"Overall"** = all 10 repos combined

The thesis abstract should cite hold-out numbers, not training numbers.

---

## How to Re-run Hold-Out Evaluation

```bash
# Run the full recall test suite (marks repos as slow)
pytest TESTS/evaluation/test_recall.py -m slow -v

# Or run just the hold-out repos:
pytest TESTS/evaluation/test_recall.py -k "flask or bandit or nodegoat or dvna or dvws or juice" -v
```

Results are written to `TESTS/evaluation/evaluation_results.json`.

---

## Phase 12 Update

After Task 12.7 (inter-procedural taint), rerun the hold-out evaluation
to measure recall improvement from cross-function taint flows.
Track in this table:

| Task | Change | Hold-out Recall Δ |
|------|--------|-------------------|
| 12.7 inter-procedural taint | Taint crosses function boundaries | TBD — run after scale test |
| 12.8 sanitizer recognition | FP reduction from known sanitizers | TBD |
| 12.12 Trivy | Container/dep CVEs (new category) | N/A — different finding type |
| 12.13 TruffleHog | Verified secrets (new category) | N/A — different finding type |
