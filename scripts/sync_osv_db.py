#!/usr/bin/env python3
"""Download OSV vulnerability snapshots for offline use.

Downloads ecosystem-specific advisory archives from
https://osv-vulnerabilities.storage.googleapis.com/ and extracts
individual JSON files to the local snapshot directory.

Usage:
    python scripts/sync_osv_db.py
    python scripts/sync_osv_db.py --ecosystems PyPI npm Go
    OSV_SNAPSHOT_DIR=/data/osv python scripts/sync_osv_db.py

Snapshot directory default: ~/.acrqa/osv-snapshot/
"""

from __future__ import annotations

import argparse
import io
import json
import logging
import os
import sys
import zipfile
from pathlib import Path

import httpx

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
logger = logging.getLogger(__name__)

_OSV_BASE = "https://osv-vulnerabilities.storage.googleapis.com"
_DEFAULT_ECOSYSTEMS = ["PyPI", "npm", "Go", "crates.io", "Maven", "RubyGems"]
_DEFAULT_SNAPSHOT_DIR = Path.home() / ".acrqa" / "osv-snapshot"


def _snapshot_dir() -> Path:
    env = os.getenv("OSV_SNAPSHOT_DIR")
    return Path(env) if env else _DEFAULT_SNAPSHOT_DIR


def download_ecosystem(ecosystem: str, target_dir: Path, client: httpx.Client) -> int:
    """Download and extract one ecosystem's OSV archive. Returns advisory count."""
    url = f"{_OSV_BASE}/{ecosystem}/all.zip"
    logger.info(f"  Downloading {ecosystem} → {url}")
    try:
        resp = client.get(url, follow_redirects=True, timeout=120.0)
        resp.raise_for_status()
    except Exception as e:
        logger.warning(f"  ✗ {ecosystem}: {e}")
        return 0

    count = 0
    with zipfile.ZipFile(io.BytesIO(resp.content)) as zf:
        for name in zf.namelist():
            if not name.endswith(".json"):
                continue
            data = zf.read(name)
            # Use OSV ID as filename for deterministic naming
            try:
                osv_id = json.loads(data).get("id", name.replace("/", "_"))
            except Exception:
                osv_id = name.replace("/", "_")
            out_path = target_dir / f"{osv_id}.json"
            out_path.write_bytes(data)
            count += 1
    logger.info(f"  ✓ {ecosystem}: {count} advisories")
    return count


def main() -> int:
    parser = argparse.ArgumentParser(description="Sync OSV advisory snapshots for offline use")
    parser.add_argument(
        "--ecosystems",
        nargs="+",
        default=_DEFAULT_ECOSYSTEMS,
        metavar="ECO",
        help=f"Ecosystems to sync (default: {' '.join(_DEFAULT_ECOSYSTEMS)})",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=_snapshot_dir(),
        help="Directory to write advisory JSONs (default: ~/.acrqa/osv-snapshot/)",
    )
    args = parser.parse_args()

    target: Path = args.output_dir
    target.mkdir(parents=True, exist_ok=True)
    logger.info(f"OSV snapshot dir: {target}")

    total = 0
    with httpx.Client() as client:
        for eco in args.ecosystems:
            total += download_ecosystem(eco, target, client)

    logger.info(f"\n✅ Done — {total} total advisories written to {target}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
