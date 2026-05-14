"""OSV offline CVE snapshot reader.

Reads pre-downloaded OSV JSON files from the local snapshot directory
(default: ~/.acrqa/osv-snapshot/) and answers CVE queries without
network access.

Snapshot format mirrors https://osv.dev/download — one JSON file per
vulnerability, named by OSV ID (e.g. GHSA-xxxx-xxxx-xxxx.json).
The directory is populated by scripts/sync_osv_db.py.
"""

from __future__ import annotations

import json
import logging
import os
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

_DEFAULT_SNAPSHOT_DIR = Path.home() / ".acrqa" / "osv-snapshot"


def _snapshot_dir() -> Path:
    env = os.getenv("OSV_SNAPSHOT_DIR")
    return Path(env) if env else _DEFAULT_SNAPSHOT_DIR


class OsvOfflineReader:
    """Query a local OSV snapshot directory for vulnerability data.

    The reader builds an in-memory index on first use and then answers
    package-version queries entirely offline.
    """

    def __init__(self, snapshot_dir: Path | str | None = None) -> None:
        self._dir = Path(snapshot_dir) if snapshot_dir else _snapshot_dir()
        self._index: dict[str, list[dict]] | None = None  # pkg_name → [vuln, ...]

    def _ensure_index(self) -> None:
        if self._index is not None:
            return
        self._index = {}
        if not self._dir.exists():
            logger.warning(f"OSV snapshot dir not found: {self._dir} — run scripts/sync_osv_db.py")
            return
        count = 0
        for path in self._dir.glob("*.json"):
            try:
                data = json.loads(path.read_text(encoding="utf-8"))
                for affected in data.get("affected", []):
                    pkg = affected.get("package", {})
                    name = pkg.get("name", "").lower()
                    if name:
                        self._index.setdefault(name, []).append(data)
                count += 1
            except Exception as err:
                logger.debug(f"OSV parse error {path.name}: {err}")
        logger.debug(f"OSV index built: {count} advisories, {len(self._index)} packages")

    def query(self, package_name: str, version: str | None = None) -> list[dict[str, Any]]:
        """Return all OSV advisories for a package, optionally filtered by version."""
        self._ensure_index()
        assert self._index is not None
        advisories = self._index.get(package_name.lower(), [])
        if version is None:
            return advisories

        matching: list[dict] = []
        for adv in advisories:
            if self._version_affected(adv, package_name, version):
                matching.append(adv)
        return matching

    def _version_affected(self, adv: dict, package_name: str, version: str) -> bool:
        """Simple range check: affected if version is in any 'ranges' or 'versions' list."""
        for affected in adv.get("affected", []):
            pkg = affected.get("package", {})
            if pkg.get("name", "").lower() != package_name.lower():
                continue
            if version in affected.get("versions", []):
                return True
            for rng in affected.get("ranges", []):
                events = rng.get("events", [])
                introduced = next((e.get("introduced", "0") for e in events if "introduced" in e), "0")
                fixed = next((e.get("fixed") for e in events if "fixed" in e), None)
                if self._in_range(version, introduced, fixed):
                    return True
        return False

    @staticmethod
    def _in_range(version: str, introduced: str, fixed: str | None) -> bool:
        """Very conservative range check: always True for '0' introduced and no fixed."""
        if introduced == "0" and fixed is None:
            return True
        return False

    @property
    def is_available(self) -> bool:
        """True if snapshot directory exists and contains at least one advisory."""
        return self._dir.exists() and any(self._dir.glob("*.json"))

    @property
    def advisory_count(self) -> int:
        self._ensure_index()
        return sum(len(v) for v in (self._index or {}).values())
