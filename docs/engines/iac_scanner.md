# IaC Scanner Engine

**Module:** `CORE/engines/iac_scanner.py`
**Introduced:** v5.0.0 Phase A.2 (May 19, 2026)
**Status:** GA — pure-Python; checkov / kube-score wrap optional (Phase B).

## Scope

| Provider | Files matched | Rules |
|---|---|---|
| Terraform | `*.tf`, `*.tfvars` | 10 (`IAC-TF-001` … `IAC-TF-010`) |
| Kubernetes | `*.yaml` / `*.yml` containing both `apiVersion:` and `kind:` | 10 (`IAC-K8S-001` … `IAC-K8S-010`) |
| Dockerfile | `Dockerfile*`, `*.dockerfile` | 8 (`IAC-DKR-001` … `IAC-DKR-008`) |

`node_modules`, `.terraform`, `.venv`, `__pycache__`, `.git` are skipped.

## Rule catalog (summary)

| Rule | Severity | What it catches |
|---|---|---|
| IAC-TF-001 | high | `acl = "public-read"` / `"public-read-write"` |
| IAC-TF-002 | high | Security group with `cidr_blocks = ["0.0.0.0/0"]` |
| IAC-TF-003 | high | `aws_s3_bucket` with no SSE configuration |
| IAC-TF-004 | high | Hardcoded `AKIA…` access key or 30+ char secret |
| IAC-TF-005 | high | IAM policy with `Action="*"` AND `Resource="*"` |
| IAC-TF-006 | medium | `storage_encrypted = false` |
| IAC-TF-007 | medium | `encrypted = false` (EBS) |
| IAC-TF-008 | medium | `protocol = "HTTP"` on a listener |
| IAC-TF-009 | low | `aws_s3_bucket` with no versioning |
| IAC-TF-010 | medium | `is_logging = false` on CloudTrail |
| IAC-K8S-001 | high | `securityContext.privileged: true` |
| IAC-K8S-002 | high | `runAsUser: 0` or `runAsNonRoot: false` |
| IAC-K8S-003 | high | `hostNetwork: true` |
| IAC-K8S-004 | high | `hostPID: true` |
| IAC-K8S-005 | medium | No `resources.limits` on a container |
| IAC-K8S-006 | low | No readiness/liveness probe |
| IAC-K8S-007 | medium | Pod uses the default service account |
| IAC-K8S-008 | high | Adds `SYS_ADMIN` / `ALL` capability |
| IAC-K8S-009 | medium | `allowPrivilegeEscalation: true` |
| IAC-K8S-010 | low | `readOnlyRootFilesystem` not `true` |
| IAC-DKR-001 | medium | No `USER` directive (defaults to root) |
| IAC-DKR-002 | low | `FROM image:latest` (or no tag) |
| IAC-DKR-003 | low | `ADD` where `COPY` would suffice |
| IAC-DKR-004 | high | Hardcoded `*_SECRET / *_TOKEN / *_KEY` in `ENV` |
| IAC-DKR-005 | low | `apt-get install` without `--no-install-recommends` |
| IAC-DKR-006 | low | No `HEALTHCHECK` |
| IAC-DKR-007 | high | `curl|wget …| sh` (supply-chain risk) |
| IAC-DKR-008 | medium | `chmod 777` or `chmod -R 777` |

## How it works

The scanner is **pattern-based**:

1. `IaCScanner.scan()` walks `target_dir`, buckets files by provider.
2. Per-file scanners (`scan_terraform_file`, `scan_k8s_file`, `scan_dockerfile`) apply
   regex / YAML-structural rules over the source.
3. Each hit produces an `IaCFinding` with file, line, severity, snippet, `iac_provider`,
   and best-effort `iac_resource`.
4. `IaCFinding.to_dict()` emits a CanonicalFinding-shaped dict; `normalize_iac()`
   wraps each into a real `CanonicalFinding` for the pipeline.

## What it does NOT do (v5.0.0 A2 scope)

- **No full HCL parsing.** Cross-resource references (`var.x`, `data.x`) are not resolved.
  Findings are evaluated per literal line.
- **No `terraform plan` execution.** Static-only; we never invoke the Terraform CLI.
- **No JSON-encoded Kubernetes manifests.** Only YAML.
- **No CloudFormation YAML.** Phase B target.
- **No GitHub Actions YAML scanning.** Phase B target (per plan v3 Drop-First).
- **No checkov / kube-score wrap.** Pure-Python rules only in A2; subprocess wrap of
  `checkov` and `kube-score` is a Phase B addition (it requires extra deps and CI
  network access).

## Endpoint

`POST /v1/scans/iac` — runs the scanner against a workspace-relative path. Guard:
the requested path must resolve inside the current working directory (no traversal,
no absolute paths above CWD).

Response shape:

```json
{
  "target_dir": "/abs/path",
  "total": 27,
  "by_provider": {"terraform": 10, "kubernetes": 11, "dockerfile": 6},
  "by_severity": {"high": 14, "medium": 8, "low": 5},
  "findings": [...]
}
```

## Database

Migration `0013` adds two nullable columns to `findings`:

- `iac_provider` (`String(32)`): `terraform` / `kubernetes` / `dockerfile`.
- `iac_resource` (`String(256)`): best-effort resource hint, e.g. `aws_s3_bucket.public`.

`Database.update_finding_iac(finding_id, provider, resource)` populates them after
`insert_finding`, mirroring how `update_finding_reachability` works.

## Testing

`TESTS/test_iac_scanner.py` (52 tests) and `TESTS/test_iac_scan_endpoint.py` (6 tests).
Sample fixtures live in `TESTS/samples/iac-issues/`:

- `terraform/main.tf` — exercises all 10 TF rules
- `k8s/deployment.yaml` — exercises all 10 K8S rules
- `docker/Dockerfile` — exercises all 8 DKR rules
