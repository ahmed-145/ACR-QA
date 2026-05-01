#!/usr/bin/env python3
"""
ACR-QA Scale Benchmark — measures scan time vs. codebase size.

Usage:
    python3 scripts/scale_benchmark.py [--target /path/to/dir] [--sizes 10 50 100]

Generates synthetic JS files (or uses real targets) and reports:
    - Files scanned
    - Wall time (seconds)
    - Findings count
    - Files/second rate
"""

import argparse
import logging
import sys
import tempfile
import time
from pathlib import Path

# ── Add project root to path so CORE imports work ──────────────────────────
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from CORE.adapters.js_adapter import JavaScriptAdapter  # noqa: E402

# ── Synthetic JS file templates ─────────────────────────────────────────────
_JS_TEMPLATES = [
    # Safe file (no findings expected)
    "const express = require('express');\nconst router = express.Router();\nrouter.get('/ping', (req, res) => res.json({ ok: true }));\nmodule.exports = router;\n",
    # Has eval (SECURITY-001)
    "const userCode = req.body.code;\neval(userCode);  // dangerous\n",
    # Has console.log (STYLE-007)
    "function helper(x) {\n  console.log('debug:', x);\n  return x * 2;\n}\nmodule.exports = helper;\n",
    # Has var (STYLE-017)
    "var result = 0;\nfor (var i = 0; i < 10; i++) { result += i; }\nconsole.log(result);\n",
]

logger = logging.getLogger(__name__)


def _generate_synthetic_project(target_dir: Path, num_files: int) -> None:
    """Create a synthetic JS project with num_files .js files."""
    target_dir.mkdir(parents=True, exist_ok=True)
    (target_dir / "package.json").write_text('{"name": "benchmark-project", "version": "1.0.0", "dependencies": {}}\n')
    for i in range(num_files):
        template = _JS_TEMPLATES[i % len(_JS_TEMPLATES)]
        (target_dir / f"module_{i:04d}.js").write_text(template)


def _run_benchmark(target_dir: str, label: str) -> dict:
    """Run a single benchmark pass and return metrics."""
    adapter = JavaScriptAdapter(target_dir=target_dir)
    # Monkey-patch npm audit since it adds unpredictable network latency (breaking the ratio)
    adapter._run_npm_audit = lambda *args, **kwargs: None
    js_files = [
        f
        for ext in (".js", ".ts", ".jsx", ".tsx", ".ejs")
        for f in Path(target_dir).rglob(f"*{ext}")
        if "node_modules" not in str(f)
    ]
    num_files = len(js_files)

    with tempfile.TemporaryDirectory() as out_dir:
        start = time.perf_counter()
        results = adapter.run_tools(output_dir=out_dir)
        elapsed = time.perf_counter() - start

    # Count findings (ESLint + Semgrep)
    findings = adapter.get_all_findings(results)
    num_findings = len(findings)
    rate = num_files / elapsed if elapsed > 0 else 0

    return {
        "label": label,
        "files": num_files,
        "findings": num_findings,
        "elapsed_s": round(elapsed, 2),
        "files_per_sec": round(rate, 1),
    }


def main() -> None:
    """Main entry point for benchmark script."""
    parser = argparse.ArgumentParser(description="ACR-QA Scale Benchmark")
    parser.add_argument(
        "--target",
        default=None,
        help="Real target directory to benchmark (skips synthetic generation)",
    )
    parser.add_argument(
        "--sizes",
        nargs="+",
        type=int,
        default=[10, 50, 100],
        help="Number of synthetic files to benchmark at each size (default: 10 50 100)",
    )
    args = parser.parse_args()

    logger.info("=" * 60)
    logger.info("ACR-QA Scale Benchmark")
    logger.info("=" * 60)
    logger.info(f"{'Label':<30} {'Files':>6} {'Findings':>9} {'Time(s)':>8} {'Files/s':>8}")
    logger.info("-" * 60)

    results = []

    if args.target:
        # Benchmark real directory
        r = _run_benchmark(args.target, Path(args.target).name)
        results.append(r)
        logger.info(
            f"{r['label']:<30} {r['files']:>6} {r['findings']:>9} {r['elapsed_s']:>8.2f} {r['files_per_sec']:>8.1f}"
        )
    else:
        # Benchmark synthetic projects of increasing sizes
        for size in args.sizes:
            with tempfile.TemporaryDirectory() as tmp:
                synthetic_dir = Path(tmp) / f"project_{size}"
                _generate_synthetic_project(synthetic_dir, size)
                label = f"{size} synthetic JS files"
                r = _run_benchmark(str(synthetic_dir), label)
                results.append(r)
                logger.info(
                    f"{r['label']:<30} {r['files']:>6} {r['findings']:>9} {r['elapsed_s']:>8.2f} {r['files_per_sec']:>8.1f}"
                )

    logger.info("=" * 60)
    if len(results) >= 2:
        # Check for roughly linear scaling
        r0, r_last = results[0], results[-1]
        if r0["elapsed_s"] > 0 and r_last["elapsed_s"] > 0:
            size_ratio = r_last["files"] / r0["files"] if r0["files"] > 0 else 1
            time_ratio = r_last["elapsed_s"] / r0["elapsed_s"]
            logger.info(f"\nScalability: {size_ratio:.0f}× files → {time_ratio:.1f}× time")
            if time_ratio < size_ratio * 1.5:
                logger.info("✅ Roughly linear scaling observed.")
            else:
                logger.error("⚠️  Superlinear scaling — tool startup overhead dominates at this scale.")


if __name__ == "__main__":
    main()
