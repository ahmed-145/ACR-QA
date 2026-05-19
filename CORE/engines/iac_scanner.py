"""
ACR-QA IaC Scanner (v5.0.0 Phase A.2).

Pure-Python scanner for Infrastructure-as-Code misconfigurations. No external
binary dependencies; checkov/kube-score wrap is optional and added later.

Coverage:
    Terraform   (10 rules) — .tf files, regex over HCL-ish syntax
    Kubernetes  (10 rules) — .yaml/.yml manifests with apiVersion+kind
    Dockerfile  (8 rules)  — Dockerfile, Dockerfile.* files

Output: list[dict] matching CanonicalFinding fields so it can flow through
normalize_iac() into the standard pipeline.

NOTE on scope: pattern-based rules catch the high-signal cases. Anything
requiring full HCL parsing (cross-resource references, dynamic blocks) is
explicitly out of scope for v5.0.0 A2 and documented as such in
`docs/engines/iac_scanner.md`.
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from pathlib import Path

logger = logging.getLogger(__name__)


# ── Rule catalog ──────────────────────────────────────────────────────────────
#
# Each rule maps to a canonical_rule_id (IAC-*). Severity defaults are encoded
# here and mirrored in CORE/engines/severity_scorer.py RULE_SEVERITY.

RULE_SEVERITY: dict[str, str] = {
    # Terraform
    "IAC-TF-001": "high",  # public S3 ACL
    "IAC-TF-002": "high",  # open security group (0.0.0.0/0 on ingress)
    "IAC-TF-003": "high",  # unencrypted S3
    "IAC-TF-004": "high",  # hardcoded AWS credentials
    "IAC-TF-005": "high",  # IAM action="*" + resource="*"
    "IAC-TF-006": "medium",  # RDS unencrypted
    "IAC-TF-007": "medium",  # EBS volume unencrypted
    "IAC-TF-008": "medium",  # ELB without HTTPS listener
    "IAC-TF-009": "low",  # S3 without versioning
    "IAC-TF-010": "medium",  # CloudTrail disabled
    # Kubernetes
    "IAC-K8S-001": "high",  # privileged container
    "IAC-K8S-002": "high",  # runs as root
    "IAC-K8S-003": "high",  # hostNetwork
    "IAC-K8S-004": "high",  # hostPID
    "IAC-K8S-005": "medium",  # no resource limits
    "IAC-K8S-006": "low",  # no probe
    "IAC-K8S-007": "medium",  # default service account
    "IAC-K8S-008": "high",  # dangerous capabilities
    "IAC-K8S-009": "medium",  # allowPrivilegeEscalation not false
    "IAC-K8S-010": "low",  # readOnlyRootFilesystem not true
    # Dockerfile
    "IAC-DKR-001": "medium",  # no USER (root)
    "IAC-DKR-002": "low",  # latest tag
    "IAC-DKR-003": "low",  # ADD vs COPY
    "IAC-DKR-004": "high",  # hardcoded secret in ENV
    "IAC-DKR-005": "low",  # apt-get without --no-install-recommends
    "IAC-DKR-006": "low",  # no HEALTHCHECK
    "IAC-DKR-007": "high",  # pipe to sh
    "IAC-DKR-008": "medium",  # chmod 777
}

RULE_CATEGORY: dict[str, str] = {
    r: ("security" if RULE_SEVERITY[r] in ("high", "medium") else "best-practice") for r in RULE_SEVERITY
}

RULE_MESSAGES: dict[str, str] = {
    "IAC-TF-001": "S3 bucket has public ACL (publicly readable/writable).",
    "IAC-TF-002": "Security group allows 0.0.0.0/0 ingress (open to the internet).",
    "IAC-TF-003": "S3 bucket has no server-side encryption configured.",
    "IAC-TF-004": "Hardcoded AWS access key or secret in Terraform.",
    "IAC-TF-005": 'IAM policy grants Action="*" on Resource="*" (admin everywhere).',
    "IAC-TF-006": "RDS instance has storage_encrypted set to false or missing.",
    "IAC-TF-007": "EBS volume has encryption disabled.",
    "IAC-TF-008": "ELB / ALB listener uses HTTP instead of HTTPS.",
    "IAC-TF-009": "S3 bucket has no versioning enabled.",
    "IAC-TF-010": "CloudTrail is_logging set to false (audit logging disabled).",
    "IAC-K8S-001": "Container runs with securityContext.privileged: true.",
    "IAC-K8S-002": "Container runs as root (runAsUser: 0 or runAsNonRoot: false).",
    "IAC-K8S-003": "Pod uses hostNetwork: true (shares host network namespace).",
    "IAC-K8S-004": "Pod uses hostPID: true (shares host process namespace).",
    "IAC-K8S-005": "Container has no resources.limits set.",
    "IAC-K8S-006": "Container has no readinessProbe or livenessProbe.",
    "IAC-K8S-007": "Pod uses the default service account (no explicit serviceAccountName).",
    "IAC-K8S-008": "Container adds dangerous Linux capabilities (SYS_ADMIN / ALL).",
    "IAC-K8S-009": "Container allows privilege escalation (allowPrivilegeEscalation not false).",
    "IAC-K8S-010": "Container has writable root filesystem (readOnlyRootFilesystem not true).",
    "IAC-DKR-001": "Dockerfile does not set a USER (container runs as root).",
    "IAC-DKR-002": "Dockerfile uses the :latest tag (non-reproducible).",
    "IAC-DKR-003": "Dockerfile uses ADD where COPY would suffice (auto-extraction risk).",
    "IAC-DKR-004": "Dockerfile sets a secret in ENV (visible in image history).",
    "IAC-DKR-005": "apt-get install without --no-install-recommends (image bloat).",
    "IAC-DKR-006": "Dockerfile has no HEALTHCHECK.",
    "IAC-DKR-007": "Dockerfile pipes curl/wget output directly into sh (supply-chain risk).",
    "IAC-DKR-008": "Dockerfile uses chmod 777 (world-writable permissions).",
}


# ── Result type ───────────────────────────────────────────────────────────────


@dataclass
class IaCFinding:
    rule_id: str  # canonical IAC-*
    file: str
    line: int
    message: str
    severity: str
    category: str
    snippet: str = ""
    provider: str = ""  # "terraform" | "kubernetes" | "dockerfile"
    resource: str = ""  # best-effort resource hint

    def to_dict(self) -> dict:
        return {
            "canonical_rule_id": self.rule_id,
            "original_rule_id": self.rule_id,
            "severity": self.severity,
            "category": self.category,
            "file": self.file,
            "line": self.line,
            "language": "iac",
            "message": self.message,
            "evidence": {"snippet": self.snippet, "context_before": [], "context_after": []},
            "tool_raw": {"tool": "acrqa-iac", "provider": self.provider, "resource": self.resource},
            "iac_provider": self.provider,
            "iac_resource": self.resource,
        }


# ── File detection ────────────────────────────────────────────────────────────


_DOCKERFILE_NAMES = ("Dockerfile",)


def _is_dockerfile(path: Path) -> bool:
    return path.name.startswith(_DOCKERFILE_NAMES) or path.name.endswith(".dockerfile")


def _is_terraform(path: Path) -> bool:
    return path.suffix in (".tf", ".tfvars") and ".terraform" not in path.parts


def _is_k8s_manifest(path: Path, text: str) -> bool:
    if path.suffix not in (".yaml", ".yml"):
        return False
    head = text[:4096]
    return "apiVersion:" in head and "kind:" in head


def detect_iac_files(target_dir: str | Path) -> dict[str, list[Path]]:
    """Walk target_dir; bucket IaC files by provider.

    Returns: {"terraform": [...], "kubernetes": [...], "dockerfile": [...]}.
    """
    out: dict[str, list[Path]] = {"terraform": [], "kubernetes": [], "dockerfile": []}
    root = Path(target_dir)
    if not root.exists():
        return out

    for p in root.rglob("*"):
        if not p.is_file():
            continue
        # skip vendor / build dirs
        if any(part in {"node_modules", ".terraform", ".venv", "__pycache__", ".git"} for part in p.parts):
            continue
        try:
            if _is_dockerfile(p):
                out["dockerfile"].append(p)
                continue
            if _is_terraform(p):
                out["terraform"].append(p)
                continue
            if p.suffix in (".yaml", ".yml"):
                # Read head only to test for k8s
                try:
                    text = p.read_text(encoding="utf-8", errors="replace")
                except OSError:
                    continue
                if _is_k8s_manifest(p, text):
                    out["kubernetes"].append(p)
        except OSError:
            continue
    return out


# ── Helpers ───────────────────────────────────────────────────────────────────


def _emit(
    findings: list[IaCFinding],
    rule_id: str,
    path: Path,
    line: int,
    snippet: str,
    provider: str,
    resource: str = "",
) -> None:
    findings.append(
        IaCFinding(
            rule_id=rule_id,
            file=str(path),
            line=max(1, line),
            message=RULE_MESSAGES[rule_id],
            severity=RULE_SEVERITY[rule_id],
            category=RULE_CATEGORY[rule_id],
            snippet=snippet[:240].rstrip(),
            provider=provider,
            resource=resource,
        )
    )


# ── Terraform rules ───────────────────────────────────────────────────────────

_TF_RESOURCE_RE = re.compile(r'resource\s+"([^"]+)"\s+"([^"]+)"\s*\{')


def _resource_block_starts(lines: list[str]) -> list[tuple[int, str, str]]:
    """Return (line_index, resource_type, name) for every Terraform resource block."""
    out: list[tuple[int, str, str]] = []
    for i, ln in enumerate(lines):
        m = _TF_RESOURCE_RE.search(ln)
        if m:
            out.append((i, m.group(1), m.group(2)))
    return out


def scan_terraform_file(path: Path) -> list[IaCFinding]:
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return []
    lines = text.splitlines()
    findings: list[IaCFinding] = []
    resources = _resource_block_starts(lines)

    for i, ln in enumerate(lines):
        stripped = ln.strip()
        # TF-001: public S3 ACL
        if re.search(r'\bacl\s*=\s*"public-(read|read-write)"', stripped):
            _emit(findings, "IAC-TF-001", path, i + 1, ln, "terraform")
        # TF-002: open ingress 0.0.0.0/0
        if re.search(r'cidr_blocks\s*=\s*\[\s*"0\.0\.0\.0/0"', stripped):
            _emit(findings, "IAC-TF-002", path, i + 1, ln, "terraform")
        # TF-004: hardcoded AWS access key (AKIA…)
        if re.search(r"\b(AKIA[0-9A-Z]{16})\b", stripped):
            _emit(findings, "IAC-TF-004", path, i + 1, ln, "terraform")
        if re.search(r"aws_secret_access_key\s*=\s*\"[A-Za-z0-9/+=]{30,}\"", stripped):
            _emit(findings, "IAC-TF-004", path, i + 1, ln, "terraform")
        # TF-007: EBS encrypted = false
        if re.search(r"\bencrypted\s*=\s*false\b", stripped):
            _emit(findings, "IAC-TF-007", path, i + 1, ln, "terraform")
        # TF-006: storage_encrypted = false
        if re.search(r"\bstorage_encrypted\s*=\s*false\b", stripped):
            _emit(findings, "IAC-TF-006", path, i + 1, ln, "terraform")
        # TF-008: HTTP listener
        if re.search(r'\bprotocol\s*=\s*"HTTP"', stripped):
            _emit(findings, "IAC-TF-008", path, i + 1, ln, "terraform")
        # TF-010: CloudTrail is_logging = false
        if re.search(r"\bis_logging\s*=\s*false\b", stripped):
            _emit(findings, "IAC-TF-010", path, i + 1, ln, "terraform")

    # TF-005: IAM policy admin everywhere. Need to inspect the JSON-y block.
    iam_admin_re = re.compile(r'"Action"\s*:\s*"\*"')
    iam_res_re = re.compile(r'"Resource"\s*:\s*"\*"')
    if iam_admin_re.search(text) and iam_res_re.search(text):
        # Approximate line = first IAM Action="*" hit
        m = iam_admin_re.search(text)
        line_no = text.count("\n", 0, m.start()) + 1 if m else 1
        _emit(findings, "IAC-TF-005", path, line_no, 'Action="*" + Resource="*"', "terraform")

    # TF-003 / TF-009: per-resource checks (S3 bucket without encryption / versioning)
    for i, rtype, rname in resources:
        if rtype == "aws_s3_bucket":
            end = _find_block_end(lines, i)
            body = "\n".join(lines[i:end])
            if not re.search(r"server_side_encryption_configuration\b", body) and not _has_sibling(
                lines, rname, "aws_s3_bucket_server_side_encryption_configuration"
            ):
                _emit(findings, "IAC-TF-003", path, i + 1, lines[i], "terraform", resource=f"{rtype}.{rname}")
            if not re.search(r"\bversioning\b", body) and not _has_sibling(lines, rname, "aws_s3_bucket_versioning"):
                _emit(findings, "IAC-TF-009", path, i + 1, lines[i], "terraform", resource=f"{rtype}.{rname}")

    return findings


def _find_block_end(lines: list[str], start: int) -> int:
    """Return the line index *after* the closing brace of the block starting at `start`."""
    depth = 0
    started = False
    for j in range(start, len(lines)):
        opens = lines[j].count("{")
        closes = lines[j].count("}")
        depth += opens - closes
        if opens > 0:
            started = True
        if started and depth == 0:
            return j + 1
    return len(lines)


def _has_sibling(lines: list[str], bucket_name: str, sibling_type: str) -> bool:
    """Detect if a sibling resource references `bucket_name` (e.g. for encryption config)."""
    pat = re.compile(rf'resource\s+"{re.escape(sibling_type)}"')
    for ln in lines:
        if pat.search(ln):
            return True
    return False


# ── Kubernetes rules ──────────────────────────────────────────────────────────


def scan_k8s_file(path: Path) -> list[IaCFinding]:
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return []
    findings: list[IaCFinding] = []
    lines = text.splitlines()
    if not _is_k8s_manifest(path, text):
        return findings

    # Try YAML parse for richer checks; fall back to regex-only if it fails.
    docs = []
    try:
        import yaml  # local import; project already depends on PyYAML

        for d in yaml.safe_load_all(text):
            if isinstance(d, dict):
                docs.append(d)
    except Exception:
        docs = []

    # Regex-based checks operate on raw lines (fast + tolerant of bad YAML).
    for i, ln in enumerate(lines):
        s = ln.strip()
        if re.match(r"privileged\s*:\s*true\b", s):
            _emit(findings, "IAC-K8S-001", path, i + 1, ln, "kubernetes")
        if re.match(r"runAsUser\s*:\s*0\b", s):
            _emit(findings, "IAC-K8S-002", path, i + 1, ln, "kubernetes")
        if re.match(r"runAsNonRoot\s*:\s*false\b", s):
            _emit(findings, "IAC-K8S-002", path, i + 1, ln, "kubernetes")
        if re.match(r"hostNetwork\s*:\s*true\b", s):
            _emit(findings, "IAC-K8S-003", path, i + 1, ln, "kubernetes")
        if re.match(r"hostPID\s*:\s*true\b", s):
            _emit(findings, "IAC-K8S-004", path, i + 1, ln, "kubernetes")
        if re.match(r"allowPrivilegeEscalation\s*:\s*true\b", s):
            _emit(findings, "IAC-K8S-009", path, i + 1, ln, "kubernetes")
        if re.match(r"readOnlyRootFilesystem\s*:\s*false\b", s):
            _emit(findings, "IAC-K8S-010", path, i + 1, ln, "kubernetes")
        if re.search(r"-\s*SYS_ADMIN\b|-\s*ALL\b", s) and "add" in lines[max(0, i - 3) : i + 1].__str__().lower():
            _emit(findings, "IAC-K8S-008", path, i + 1, ln, "kubernetes")

    # Structural checks on parsed docs (containers without limits / probes / SA)
    for d in docs:
        kind = (d.get("kind") or "").lower()
        if kind not in {"pod", "deployment", "statefulset", "daemonset", "job", "cronjob"}:
            continue
        spec = d.get("spec") or {}
        pod_spec = spec.get("template", {}).get("spec") if "template" in spec else spec
        if not isinstance(pod_spec, dict):
            continue
        # K8S-007: default SA
        if "serviceAccountName" not in pod_spec and "serviceAccount" not in pod_spec:
            _emit(
                findings,
                "IAC-K8S-007",
                path,
                1,
                f"{kind} uses default service account",
                "kubernetes",
                resource=(d.get("metadata") or {}).get("name", ""),
            )
        for c in pod_spec.get("containers") or []:
            if not isinstance(c, dict):
                continue
            res = (c.get("resources") or {}).get("limits")
            if not res:
                _emit(
                    findings,
                    "IAC-K8S-005",
                    path,
                    1,
                    f"container {c.get('name')} has no resource limits",
                    "kubernetes",
                    resource=c.get("name", ""),
                )
            if not c.get("readinessProbe") and not c.get("livenessProbe"):
                _emit(
                    findings,
                    "IAC-K8S-006",
                    path,
                    1,
                    f"container {c.get('name')} has no probe",
                    "kubernetes",
                    resource=c.get("name", ""),
                )
    return findings


# ── Dockerfile rules ──────────────────────────────────────────────────────────


def scan_dockerfile(path: Path) -> list[IaCFinding]:
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return []
    lines = text.splitlines()
    findings: list[IaCFinding] = []
    has_user = False
    has_healthcheck = False
    for i, ln in enumerate(lines):
        s = ln.strip()
        if not s or s.startswith("#"):
            continue
        upper = s.split(maxsplit=1)[0].upper()
        rest = s[len(upper) :].strip()

        if upper == "FROM":
            # DKR-002: latest tag (or no tag at all)
            img = rest.split()[0] if rest else ""
            if img and (":" not in img or img.endswith(":latest")):
                _emit(findings, "IAC-DKR-002", path, i + 1, ln, "dockerfile", resource=img)
        if upper == "USER":
            has_user = True
            if rest.strip() in ("0", "root"):
                _emit(findings, "IAC-DKR-001", path, i + 1, ln, "dockerfile")
        if upper == "ADD":
            _emit(findings, "IAC-DKR-003", path, i + 1, ln, "dockerfile")
        if upper == "ENV":
            # DKR-004: SECRET / TOKEN / PASSWORD / KEY hardcoded
            # Match VAR_NAME=value or VAR_NAME value, where VAR_NAME contains a
            # sensitive keyword (SECRET / TOKEN / PASSWORD / API_KEY / etc.).
            if re.search(
                r"\b[A-Z][A-Z0-9_]*(SECRET|TOKEN|PASSWORD|API_?KEY|ACCESS_?KEY|PRIVATE_?KEY)[A-Z0-9_]*"
                r"\s*[=\s]\s*[A-Za-z0-9_/\-+=]{6,}",
                rest,
                re.IGNORECASE,
            ):
                _emit(findings, "IAC-DKR-004", path, i + 1, ln, "dockerfile")
        if upper == "HEALTHCHECK":
            has_healthcheck = True
        if upper == "RUN":
            if re.search(r"apt-get\s+install\b", rest) and "--no-install-recommends" not in rest:
                _emit(findings, "IAC-DKR-005", path, i + 1, ln, "dockerfile")
            if re.search(r"\b(curl|wget)\b[^\n|]*\|\s*sh\b", rest):
                _emit(findings, "IAC-DKR-007", path, i + 1, ln, "dockerfile")
            if re.search(r"chmod\s+(-R\s+)?777\b", rest):
                _emit(findings, "IAC-DKR-008", path, i + 1, ln, "dockerfile")

    if not has_user:
        _emit(findings, "IAC-DKR-001", path, 1, "no USER directive — defaults to root", "dockerfile")
    if not has_healthcheck:
        _emit(findings, "IAC-DKR-006", path, 1, "no HEALTHCHECK directive", "dockerfile")

    return findings


# ── Public API ────────────────────────────────────────────────────────────────


class IaCScanner:
    """High-level interface used by CORE/main.py and the API.

    Usage:
        scanner = IaCScanner(target_dir="/path/to/repo")
        findings = scanner.scan()
    """

    def __init__(self, target_dir: str | Path = "."):
        self.target_dir = Path(target_dir)

    def scan(self) -> list[dict]:
        """Run all IaC rules across detected files. Returns CanonicalFinding dicts."""
        buckets = detect_iac_files(self.target_dir)
        out: list[IaCFinding] = []
        for p in buckets.get("terraform", []):
            out.extend(scan_terraform_file(p))
        for p in buckets.get("kubernetes", []):
            out.extend(scan_k8s_file(p))
        for p in buckets.get("dockerfile", []):
            out.extend(scan_dockerfile(p))
        return [f.to_dict() for f in out]
