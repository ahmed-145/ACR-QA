# Heuristic Risk Predictor

**Module:** `CORE/engines/risk_predictor.py`
**Introduced:** v5.0.0 Phase A.3 (May 19, 2026)
**Status:** GA — pure-Python, deterministic, no ML.

## Why no ML?

A learned model trained on a 13-repo corpus would not generalize — the corpus is too small,
too unbalanced, and not representative of arbitrary user repos. A *transparent linear model*
with hand-calibrated weights gives:

- **Auditability** — reviewers can subtract any feature's contribution from any score.
- **Determinism** — same inputs → same score, forever. No retraining infra.
- **Honesty** — we don't claim statistical accuracy beyond what each feature already implies.

## Features (per-file, normalized to [0, 1] before weighting)

| Feature | Cap | Source | Why it's a risk signal |
|---|---:|---|---|
| `complexity` | 40 | radon `cc_visit` for Python, LOC/20 fallback for other languages | High-complexity functions hide bugs |
| `churn_90d` | 50 | `git log --since=90.days --oneline -- file` | Recently-churned files are the most likely to regress |
| `age_days` | 1,095 (3 years) | `git log --reverse --format=%ct --max-count=1` | Older code is harder to safely refactor |
| `author_count` | 10 | `git log --format=%an` (deduplicated, capped at 500 commits) | Diffuse ownership → harder to assign risk review |
| `coverage_gap` | binary | filesystem scan for `test_<name>.py` / `<name>_test.py` / `<name>.test.{ts,js}` | Untested code has the highest engineer-discovery cost |
| `high_density` | 5 HIGH per 100 LOC | current run's findings | The *current* security signal |

## Weights (sum = 1.0)

| Feature | Weight | Rationale |
|---|---:|---|
| `high_density` | 0.30 | Strongest — this is observed current state |
| `complexity` | 0.20 | Strong structural risk proxy |
| `churn` | 0.20 | Strong recent-change signal |
| `coverage_gap` | 0.15 | Strong "untested" proxy |
| `authors` | 0.10 | Moderate diffuse-ownership signal |
| `age` | 0.05 | Weakest — old code is sometimes also stable code |

A runtime `assert` in the engine fails fast if any contributor edits the weights and breaks
the sum-to-1.0 invariant.

## Score formula

```
norm_i  = min(1.0, raw_i / cap_i)              # per feature
score   = clamp(0, 1, Σ_i w_i * norm_i) * 100  # final, integer 0–100
```

Each feature's `contribution = w_i * norm_i` is returned in the score breakdown so any
reviewer can verify the math.

## Endpoint

`GET /v1/runs/{run_id}/risk-map?refresh=false`

1. Returns cached scores from `file_risk_scores` if any rows exist for the run.
2. Otherwise computes scores live using the run's findings + workspace git.
3. `refresh=true` forces a recompute even if cache is present.

Response shape:

```json
{
  "run_id": 42,
  "cached": false,
  "persisted": 7,
  "weights": {"complexity": 0.20, ...},
  "caps": {"complexity": 40, ...},
  "total_files": 7,
  "files": [
    {
      "file_path": "src/auth.py",
      "score": 78,
      "features": {
        "complexity": 31.0, "churn_90d": 14, "age_days": 412,
        "author_count": 4, "test_coverage_gap": 0,
        "high_finding_count": 2, "loc": 318
      },
      "contributions": {
        "complexity": 0.155, "churn": 0.056, "age": 0.019,
        "authors": 0.04, "coverage_gap": 0.0, "high_density": 0.189
      }
    }
  ]
}
```

## Database

Migration `0015` creates `file_risk_scores`:
- One row per `(run_id, file_path)` with a unique constraint
- Index on `(run_id, score)` for top-N queries
- Cached forever per run (no TTL — `refresh=true` is the invalidation lever)

## What it does NOT do (v5.0.0 A3 scope)

- **No ML.** Explicitly. See section above for why.
- **No semantic risk understanding.** Two files with identical features will get
  identical scores even if one is `vendor/typo-squat.py` and the other is `core/auth.py`.
  Use OWASP heatmap + finding severity together for the security view.
- **No cross-file impact propagation.** A high-risk file does not lift its neighbours'
  scores. Future work (Phase B): graph-aware propagation.
- **No author-trust adjustment.** Tracking per-author commit fault rates is a Phase B item
  (future work (Phase B — public launch)).

## Performance

- Per-file score: O(1).
- Whole-repo: O(N) over files-with-findings. Dominated by radon parse + git subprocess.
- Each subprocess call has a 10s timeout. Worst-case: ~30 ms/file in a healthy repo.

## Testing

`TESTS/test_risk_predictor.py` ships 31 tests covering:

- Weight invariants (sum, key set, dominance order)
- Normalization edges (zero, max, binary coverage gap, density-per-100-LOC)
- Score computation (zero, max, range, contribution math, monotonicity)
- `score_files` end-to-end with a temp git repo
- Endpoint behaviour (cached / compute / refresh-forces-recompute)
