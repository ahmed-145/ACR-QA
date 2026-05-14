"""Supply Chain + SBOM Engine.

Parses dependency lockfiles, queries OSV for CVEs (live or offline),
fetches GitHub health signals, scores each dependency 0–100, and emits
CycloneDX 1.4 SBOM JSON.

Risk formula (higher = riskier):
  score = min(100,
      cve_score             # 0-40  (10 per CRITICAL, 7 per HIGH, 3 per MEDIUM)
    + age_score             # 0-20  (years since last commit, capped at 20)
    + contributors_score    # 0-15  (inverse: few contributors = high risk)
    + stars_score           # 0-10  (inverse: low stars = high risk)
    + archived_score        # 25 if archived, else 0
    + license_score         # 10 if no license detected
  )
"""

from __future__ import annotations

import json
import logging
import os
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

# ── Constants ─────────────────────────────────────────────────────────────────

GITHUB_API = "https://api.github.com"
OSV_API = "https://api.osv.dev/v1/query"
_GITHUB_TOKEN = os.getenv("GITHUB_TOKEN", "")

# Risk thresholds
RISK_HIGH = 70
RISK_MEDIUM = 40


# ── Lockfile parsers ──────────────────────────────────────────────────────────


def parse_requirements_txt(content: str) -> list[dict[str, str]]:
    """Parse requirements.txt / requirements-*.txt into [{name, version}]."""
    deps: list[dict[str, str]] = []
    for line in content.splitlines():
        line = line.strip()
        if not line or line.startswith("#") or line.startswith("-"):
            continue
        # Handle extras and env markers: requests[security]>=2.0 ; python_version>"3"
        line = re.split(r"\s*;\s*", line)[0].strip()
        # Strip extras
        name_part = re.split(r"[>=<!~\[]", line)[0].strip()
        if not name_part:
            continue
        # Extract version from ==x.y.z
        ver_match = re.search(r"==([^\s,]+)", line)
        version = ver_match.group(1) if ver_match else "unknown"
        deps.append({"name": name_part, "version": version, "ecosystem": "PyPI"})
    return deps


def parse_package_json(content: str) -> list[dict[str, str]]:
    """Parse package.json dependencies + devDependencies."""
    try:
        data = json.loads(content)
    except json.JSONDecodeError:
        return []
    deps: list[dict[str, str]] = []
    for section in ("dependencies", "devDependencies", "peerDependencies"):
        for name, ver_spec in data.get(section, {}).items():
            # Strip semver prefixes: ^1.0.0 → 1.0.0
            version = re.sub(r"^[\^~>=<]", "", str(ver_spec)).strip()
            deps.append({"name": name, "version": version, "ecosystem": "npm"})
    return deps


def parse_go_mod(content: str) -> list[dict[str, str]]:
    """Parse go.mod require block into [{name, version}]."""
    deps: list[dict[str, str]] = []
    in_require = False
    for line in content.splitlines():
        line = line.strip()
        if line.startswith("require ("):
            in_require = True
            continue
        if in_require and line == ")":
            in_require = False
            continue
        if in_require or line.startswith("require "):
            # require github.com/foo/bar v1.2.3
            parts = re.split(r"\s+", line.replace("require ", "").strip())
            if len(parts) >= 2:
                deps.append({"name": parts[0], "version": parts[1].lstrip("v"), "ecosystem": "Go"})
    return deps


def parse_pipfile_lock(content: str) -> list[dict[str, str]]:
    """Parse Pipfile.lock into [{name, version}]."""
    try:
        data = json.loads(content)
    except json.JSONDecodeError:
        return []
    deps: list[dict[str, str]] = []
    for section in ("default", "develop"):
        for name, meta in data.get(section, {}).items():
            raw_ver = str(meta.get("version", "unknown"))
            version = raw_ver[2:] if raw_ver.startswith("==") else raw_ver
            deps.append({"name": name, "version": version, "ecosystem": "PyPI"})
    return deps


def parse_lockfile(file_path: str | Path) -> list[dict[str, str]]:
    """Auto-detect lockfile type and parse it."""
    path = Path(file_path)
    try:
        content = path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return []
    name = path.name.lower()
    if name in ("requirements.txt",) or name.startswith("requirements") and name.endswith(".txt"):
        return parse_requirements_txt(content)
    if name == "package.json":
        return parse_package_json(content)
    if name == "go.mod":
        return parse_go_mod(content)
    if name == "pipfile.lock":
        return parse_pipfile_lock(content)
    return []


def find_lockfiles(target_dir: str | Path) -> list[Path]:
    """Recursively find all supported lockfiles under target_dir."""
    root = Path(target_dir)
    patterns = ["requirements*.txt", "package.json", "go.mod", "Pipfile.lock"]
    found: list[Path] = []
    _SKIP_DIRS = {"node_modules", ".venv", "venv", "__pycache__", ".git", "dist", "build"}
    for pattern in patterns:
        for p in root.rglob(pattern):
            if _SKIP_DIRS.intersection(set(p.relative_to(root).parts)):
                continue
            found.append(p)
    return found


# ── OSV query ─────────────────────────────────────────────────────────────────


def query_osv_live(package_name: str, version: str, ecosystem: str) -> list[dict]:
    """Query OSV.dev API for CVEs affecting package@version."""
    try:
        import httpx

        payload = {"version": version, "package": {"name": package_name, "ecosystem": ecosystem}}
        resp = httpx.post(OSV_API, json=payload, timeout=10)
        if resp.status_code == 200:
            return resp.json().get("vulns", [])
    except Exception as e:
        logger.debug(f"OSV live query failed for {package_name}: {e}")
    return []


def query_osv_offline(package_name: str, version: str, snapshot_dir: str | None = None) -> list[dict]:
    """Query local OSV snapshot for CVEs."""
    from CORE.engines.osv_offline import OsvOfflineReader

    reader = OsvOfflineReader(snapshot_dir)
    return reader.query(package_name, version)


def query_osv(package_name: str, version: str, ecosystem: str, mode: str = "auto") -> list[dict]:
    """Query OSV in live, offline, or auto mode."""
    if mode == "offline":
        return query_osv_offline(package_name, version)
    if mode == "live":
        return query_osv_live(package_name, version, ecosystem)
    # auto: try offline first (fast + no network), fall back to live
    offline = query_osv_offline(package_name, version)
    if offline:
        return offline
    acrqa_mode = os.getenv("ACRQA_MODE", "cloud").lower()
    if acrqa_mode == "offline":
        return offline
    return query_osv_live(package_name, version, ecosystem)


# ── GitHub health signals ─────────────────────────────────────────────────────


def _github_headers() -> dict[str, str]:
    headers = {"Accept": "application/vnd.github+json", "X-GitHub-Api-Version": "2022-11-28"}
    if _GITHUB_TOKEN:
        headers["Authorization"] = f"Bearer {_GITHUB_TOKEN}"
    return headers


def fetch_github_signals(package_name: str, ecosystem: str) -> dict[str, Any]:
    """Fetch stars, last_commit_days, contributors, archived from GitHub.

    Returns a dict with keys: stars, last_commit_days, contributors, archived, repo_url.
    Returns empty dict if the package has no obvious GitHub mapping or on error.
    """
    repo_slug = _resolve_github_slug(package_name, ecosystem)
    if not repo_slug:
        return {}
    url = f"{GITHUB_API}/repos/{repo_slug}"
    try:
        import httpx

        resp = httpx.get(url, headers=_github_headers(), timeout=8)
        if resp.status_code != 200:
            return {}
        data = resp.json()
        pushed_at = data.get("pushed_at", "")
        last_commit_days = 0
        if pushed_at:
            try:
                dt = datetime.fromisoformat(pushed_at.replace("Z", "+00:00"))
                last_commit_days = (datetime.now(timezone.utc) - dt).days  # noqa: UP017
            except ValueError:
                pass

        # Contributors count via contributors_url (lightweight: just the first page header)
        contributors = _fetch_contributor_count(repo_slug)

        return {
            "stars": data.get("stargazers_count", 0),
            "last_commit_days": last_commit_days,
            "contributors": contributors,
            "archived": data.get("archived", False),
            "license": (data.get("license") or {}).get("spdx_id", ""),
            "repo_url": data.get("html_url", ""),
        }
    except Exception as e:
        logger.debug(f"GitHub fetch failed for {repo_slug}: {e}")
        return {}


def _fetch_contributor_count(repo_slug: str) -> int:
    """Return contributor count from GitHub API (capped at 500 to avoid pagination)."""
    try:
        import httpx

        url = f"{GITHUB_API}/repos/{repo_slug}/contributors?per_page=1&anon=true"
        resp = httpx.get(url, headers=_github_headers(), timeout=8)
        if resp.status_code == 200:
            # If Link header present, parse last page number
            link = resp.headers.get("Link", "")
            m = re.search(r'page=(\d+)>; rel="last"', link)
            if m:
                return min(int(m.group(1)), 500)
            return len(resp.json())
    except Exception:
        pass
    return 0


def _resolve_github_slug(package_name: str, ecosystem: str) -> str | None:
    """Best-effort: resolve a package name to owner/repo."""
    # Go modules already are github.com/owner/repo
    if ecosystem == "Go" and package_name.startswith("github.com/"):
        parts = package_name.split("/")
        if len(parts) >= 3:
            return f"{parts[1]}/{parts[2]}"
    # PyPI / npm: many packages embed their GitHub URL
    # Without a lookup API we can't reliably resolve these offline
    return None


# ── Risk scoring ──────────────────────────────────────────────────────────────

_SEVERITY_SCORES = {"CRITICAL": 10, "HIGH": 7, "MEDIUM": 3, "LOW": 1}


def score_dependency(cves: list[dict], github: dict[str, Any]) -> int:
    """Compute 0–100 risk score for a dependency."""
    # CVE component (0–40)
    cve_score = 0
    for vuln in cves:
        sev = _extract_severity(vuln)
        cve_score += _SEVERITY_SCORES.get(sev, 2)
    cve_score = min(40, cve_score)

    # Age component (0–20): 1 point per 100 days since last commit, cap 20
    last_commit_days = github.get("last_commit_days", 0)
    age_score = min(20, last_commit_days // 100)

    # Contributors (0–15): inverse — fewer contributors = higher risk
    contributors = github.get("contributors", 0)
    if contributors == 0:
        contributors_score = 15
    elif contributors < 3:
        contributors_score = 10
    elif contributors < 10:
        contributors_score = 5
    else:
        contributors_score = 0

    # Stars (0–10): inverse — low stars = higher risk
    stars = github.get("stars", 0)
    if stars == 0:
        stars_score = 10
    elif stars < 100:
        stars_score = 7
    elif stars < 1000:
        stars_score = 3
    else:
        stars_score = 0

    # Archived flag (0 or 25)
    archived_score = 25 if github.get("archived") else 0

    # License (0 or 10)
    license_score = 10 if not github.get("license") else 0

    return min(100, cve_score + age_score + contributors_score + stars_score + archived_score + license_score)


def _extract_severity(vuln: dict) -> str:
    """Extract the highest severity string from an OSV advisory."""
    # OSV severity array
    for sev_entry in vuln.get("severity", []):
        score_str = sev_entry.get("score", "")
        # CVSS string like "CVSS:3.1/AV:N/AC:L/.../CR:H"
        if "CRITICAL" in score_str.upper():
            return "CRITICAL"
        if "HIGH" in score_str.upper():
            return "HIGH"
        if "MEDIUM" in score_str.upper():
            return "MEDIUM"
    # database_specific sometimes has severity
    for affected in vuln.get("affected", []):
        for sev in affected.get("database_specific", {}).get("severity", []):
            s = str(sev).upper()
            if s in _SEVERITY_SCORES:
                return s
    # fallback: check aliases for CVE CVSS base score pattern
    return "MEDIUM"


# ── CycloneDX SBOM builder ────────────────────────────────────────────────────


def build_cyclonedx_sbom(
    run_id: int,
    repo_name: str,
    dependencies: list[dict[str, Any]],
) -> dict[str, Any]:
    """Build a CycloneDX 1.4 SBOM dict from enriched dependency records."""
    components = []
    for dep in dependencies:
        comp: dict[str, Any] = {
            "type": "library",
            "name": dep["name"],
            "version": dep.get("version", "unknown"),
            "purl": _make_purl(dep),
        }
        if dep.get("cves"):
            comp["vulnerabilities"] = [
                {
                    "id": v.get("id", ""),
                    "description": v.get("summary", ""),
                    "ratings": [{"severity": _extract_severity(v).lower()}],
                }
                for v in dep["cves"][:5]  # cap at 5 per component
            ]
        if dep.get("repo_url"):
            comp["externalReferences"] = [{"type": "vcs", "url": dep["repo_url"]}]
        components.append(comp)

    return {
        "bomFormat": "CycloneDX",
        "specVersion": "1.4",
        "version": 1,
        "serialNumber": f"urn:uuid:acrqa-run-{run_id}",
        "metadata": {
            "timestamp": datetime.now(timezone.utc).isoformat(),  # noqa: UP017
            "component": {"type": "application", "name": repo_name},
            "tools": [{"name": "ACR-QA", "version": "4.0.0"}],
        },
        "components": components,
    }


def _make_purl(dep: dict) -> str:
    """Generate a Package URL (purl) for a dependency."""
    ecosystem_map = {"PyPI": "pypi", "npm": "npm", "Go": "golang"}
    ptype = ecosystem_map.get(dep.get("ecosystem", ""), "generic")
    name = dep["name"].lower().replace("_", "-")
    version = dep.get("version", "unknown")
    return f"pkg:{ptype}/{name}@{version}"


# ── SupplyChainEngine ─────────────────────────────────────────────────────────


class SupplyChainEngine:
    """Scan a repository for dependency vulnerabilities and health signals.

    Usage:
        engine = SupplyChainEngine()
        result = engine.scan(target_dir="/path/to/repo", run_id=42, repo_name="foo/bar")
        # result["dependencies"] — enriched dep list
        # result["sbom"]        — CycloneDX 1.4 dict
        # result["summary"]     — counts by risk level
    """

    def __init__(self, osv_mode: str = "auto", github_enabled: bool = True) -> None:
        self.osv_mode = osv_mode
        self.github_enabled = github_enabled

    def scan(
        self,
        target_dir: str | Path,
        run_id: int = 0,
        repo_name: str = "unknown",
        lockfiles: list[Path] | None = None,
    ) -> dict[str, Any]:
        """Full supply-chain scan.  Returns dict with dependencies, sbom, summary."""
        if lockfiles is None:
            lockfiles = find_lockfiles(target_dir)

        raw_deps: list[dict[str, str]] = []
        for lf in lockfiles:
            raw_deps.extend(parse_lockfile(lf))

        # Deduplicate by (name, version, ecosystem)
        seen: set[tuple[str, str, str]] = set()
        unique_deps: list[dict[str, str]] = []
        for dep in raw_deps:
            key = (dep["name"], dep.get("version", ""), dep.get("ecosystem", ""))
            if key not in seen:
                seen.add(key)
                unique_deps.append(dep)

        enriched = [self._enrich(dep) for dep in unique_deps]

        sbom = build_cyclonedx_sbom(run_id, repo_name, enriched)
        summary = self._summarize(enriched)

        return {
            "dependencies": enriched,
            "sbom": sbom,
            "summary": summary,
            "lockfiles_scanned": [str(lf) for lf in lockfiles],
        }

    def _enrich(self, dep: dict[str, str]) -> dict[str, Any]:
        """Add CVE data, GitHub signals, and risk score to a dependency."""
        name = dep["name"]
        version = dep.get("version", "unknown")
        ecosystem = dep.get("ecosystem", "PyPI")

        cves = query_osv(name, version, ecosystem, mode=self.osv_mode)

        github: dict[str, Any] = {}
        if self.github_enabled:
            github = fetch_github_signals(name, ecosystem)

        risk_score = score_dependency(cves, github)
        risk_level = "high" if risk_score >= RISK_HIGH else "medium" if risk_score >= RISK_MEDIUM else "low"

        return {
            **dep,
            "cves": cves,
            "cve_count": len(cves),
            "risk_score": risk_score,
            "risk_level": risk_level,
            "stars": github.get("stars"),
            "last_commit_days": github.get("last_commit_days"),
            "contributors": github.get("contributors"),
            "archived": github.get("archived"),
            "license": github.get("license"),
            "repo_url": github.get("repo_url"),
        }

    @staticmethod
    def _summarize(deps: list[dict[str, Any]]) -> dict[str, Any]:
        high = sum(1 for d in deps if d.get("risk_level") == "high")
        medium = sum(1 for d in deps if d.get("risk_level") == "medium")
        low = sum(1 for d in deps if d.get("risk_level") == "low")
        total_cves = sum(d.get("cve_count", 0) for d in deps)
        return {
            "total_dependencies": len(deps),
            "high_risk": high,
            "medium_risk": medium,
            "low_risk": low,
            "total_cves": total_cves,
        }
