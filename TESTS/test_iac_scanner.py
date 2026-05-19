"""Unit tests for the IaC Scanner engine (v5.0.0 Phase A.2)."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

from CORE.engines.iac_scanner import (
    RULE_MESSAGES,
    RULE_SEVERITY,
    IaCScanner,
    detect_iac_files,
    scan_dockerfile,
    scan_k8s_file,
    scan_terraform_file,
)
from CORE.engines.normalizer import RULE_MAPPING, normalize_iac

SAMPLES = Path(__file__).parent / "samples" / "iac-issues"


# ── Catalog integrity ─────────────────────────────────────────────────────────


class TestCatalog:
    def test_rule_messages_cover_rule_severity(self):
        assert set(RULE_MESSAGES) == set(RULE_SEVERITY)

    def test_28_canonical_rules(self):
        assert len(RULE_SEVERITY) == 28

    def test_all_rules_have_canonical_mapping(self):
        for rid in RULE_SEVERITY:
            assert rid in RULE_MAPPING, f"{rid} missing from normalizer.RULE_MAPPING"
            assert RULE_MAPPING[rid] == rid

    def test_severities_are_valid(self):
        for sev in RULE_SEVERITY.values():
            assert sev in {"high", "medium", "low"}


# ── File detection ────────────────────────────────────────────────────────────


class TestDetectIacFiles:
    def test_detects_terraform(self):
        buckets = detect_iac_files(SAMPLES)
        assert any(p.name == "main.tf" for p in buckets["terraform"])

    def test_detects_k8s_manifest(self):
        buckets = detect_iac_files(SAMPLES)
        assert any(p.name == "deployment.yaml" for p in buckets["kubernetes"])

    def test_detects_dockerfile(self):
        buckets = detect_iac_files(SAMPLES)
        assert any(p.name == "Dockerfile" for p in buckets["dockerfile"])

    def test_ignores_node_modules_and_venv(self, tmp_path: Path):
        (tmp_path / "node_modules").mkdir()
        (tmp_path / "node_modules" / "a.tf").write_text('resource "aws_s3_bucket" "x" {}')
        (tmp_path / ".terraform").mkdir()
        (tmp_path / ".terraform" / "b.tf").write_text('resource "x" "y" {}')
        buckets = detect_iac_files(tmp_path)
        assert buckets["terraform"] == []

    def test_missing_dir_returns_empty(self):
        buckets = detect_iac_files("/nonexistent/__nope__")
        assert buckets == {"terraform": [], "kubernetes": [], "dockerfile": []}

    def test_non_k8s_yaml_is_skipped(self, tmp_path: Path):
        # Plain YAML without apiVersion/kind isn't K8s
        (tmp_path / "settings.yaml").write_text("name: x\nport: 8080\n")
        buckets = detect_iac_files(tmp_path)
        assert buckets["kubernetes"] == []


# ── Terraform rules ───────────────────────────────────────────────────────────


def _rule_set(findings) -> set[str]:
    return {f.rule_id for f in findings}


class TestTerraformRules:
    @pytest.fixture
    def findings(self):
        return scan_terraform_file(SAMPLES / "terraform" / "main.tf")

    def test_finds_public_s3_acl(self, findings):
        assert "IAC-TF-001" in _rule_set(findings)

    def test_finds_open_security_group(self, findings):
        assert "IAC-TF-002" in _rule_set(findings)

    def test_finds_unencrypted_s3(self, findings):
        # public bucket has no SSE config
        assert "IAC-TF-003" in _rule_set(findings)

    def test_finds_hardcoded_aws_key(self, findings):
        assert "IAC-TF-004" in _rule_set(findings)

    def test_finds_iam_admin_everywhere(self, findings):
        assert "IAC-TF-005" in _rule_set(findings)

    def test_finds_rds_unencrypted(self, findings):
        assert "IAC-TF-006" in _rule_set(findings)

    def test_finds_ebs_unencrypted(self, findings):
        assert "IAC-TF-007" in _rule_set(findings)

    def test_finds_http_listener(self, findings):
        assert "IAC-TF-008" in _rule_set(findings)

    def test_finds_s3_no_versioning(self, findings):
        assert "IAC-TF-009" in _rule_set(findings)

    def test_finds_cloudtrail_disabled(self, findings):
        assert "IAC-TF-010" in _rule_set(findings)

    def test_terraform_findings_have_provider(self, findings):
        for f in findings:
            assert f.provider == "terraform"
            assert f.file.endswith("main.tf")
            assert f.line >= 1

    def test_missing_file_returns_empty(self, tmp_path: Path):
        assert scan_terraform_file(tmp_path / "missing.tf") == []

    def test_clean_terraform_has_no_findings(self, tmp_path: Path):
        # Encrypted + private bucket
        (tmp_path / "good.tf").write_text(
            'resource "aws_s3_bucket" "x" {\n'
            '  bucket = "private"\n'
            '  acl    = "private"\n'
            '  server_side_encryption_configuration { rule { apply_server_side_encryption_by_default { sse_algorithm = "AES256" } } }\n'
            "  versioning { enabled = true }\n"
            "}\n"
        )
        out = scan_terraform_file(tmp_path / "good.tf")
        assert _rule_set(out).isdisjoint({"IAC-TF-001", "IAC-TF-003", "IAC-TF-009"})


# ── Kubernetes rules ──────────────────────────────────────────────────────────


class TestKubernetesRules:
    @pytest.fixture
    def findings(self):
        return scan_k8s_file(SAMPLES / "k8s" / "deployment.yaml")

    def test_finds_privileged(self, findings):
        assert "IAC-K8S-001" in _rule_set(findings)

    def test_finds_root(self, findings):
        assert "IAC-K8S-002" in _rule_set(findings)

    def test_finds_hostnetwork(self, findings):
        assert "IAC-K8S-003" in _rule_set(findings)

    def test_finds_hostpid(self, findings):
        assert "IAC-K8S-004" in _rule_set(findings)

    def test_finds_no_resource_limits(self, findings):
        assert "IAC-K8S-005" in _rule_set(findings)

    def test_finds_no_probe(self, findings):
        assert "IAC-K8S-006" in _rule_set(findings)

    def test_finds_default_sa(self, findings):
        assert "IAC-K8S-007" in _rule_set(findings)

    def test_finds_sys_admin_capability(self, findings):
        assert "IAC-K8S-008" in _rule_set(findings)

    def test_finds_priv_escalation(self, findings):
        assert "IAC-K8S-009" in _rule_set(findings)

    def test_finds_readonly_root_false(self, findings):
        assert "IAC-K8S-010" in _rule_set(findings)

    def test_non_k8s_yaml_returns_empty(self, tmp_path: Path):
        (tmp_path / "not-k8s.yaml").write_text("name: x\nport: 8080\n")
        assert scan_k8s_file(tmp_path / "not-k8s.yaml") == []

    def test_findings_have_kubernetes_provider(self, findings):
        for f in findings:
            assert f.provider == "kubernetes"


# ── Dockerfile rules ──────────────────────────────────────────────────────────


class TestDockerfileRules:
    @pytest.fixture
    def findings(self):
        return scan_dockerfile(SAMPLES / "docker" / "Dockerfile")

    def test_finds_no_user(self, findings):
        # sample has no USER, should detect (file-level)
        assert "IAC-DKR-001" in _rule_set(findings)

    def test_finds_latest_tag(self, findings):
        assert "IAC-DKR-002" in _rule_set(findings)

    def test_finds_add_directive(self, findings):
        assert "IAC-DKR-003" in _rule_set(findings)

    def test_finds_hardcoded_secret_env(self, findings):
        assert "IAC-DKR-004" in _rule_set(findings)

    def test_finds_apt_get_no_recommends(self, findings):
        assert "IAC-DKR-005" in _rule_set(findings)

    def test_finds_no_healthcheck(self, findings):
        assert "IAC-DKR-006" in _rule_set(findings)

    def test_finds_pipe_to_sh(self, findings):
        assert "IAC-DKR-007" in _rule_set(findings)

    def test_finds_chmod_777(self, findings):
        assert "IAC-DKR-008" in _rule_set(findings)

    def test_user_root_explicit(self, tmp_path: Path):
        (tmp_path / "Dockerfile").write_text("FROM alpine:3.20\nUSER root\nHEALTHCHECK CMD ls\n")
        out = scan_dockerfile(tmp_path / "Dockerfile")
        assert "IAC-DKR-001" in _rule_set(out)

    def test_clean_dockerfile_no_findings(self, tmp_path: Path):
        (tmp_path / "Dockerfile").write_text(
            "FROM alpine:3.20\n"
            "USER app\n"
            "COPY app /app\n"
            "HEALTHCHECK CMD wget --spider http://localhost\n"
            'CMD ["/app"]\n'
        )
        out = scan_dockerfile(tmp_path / "Dockerfile")
        assert _rule_set(out) == set()


# ── Top-level IaCScanner ──────────────────────────────────────────────────────


class TestIaCScannerEntrypoint:
    def test_scan_returns_dicts(self):
        scanner = IaCScanner(target_dir=SAMPLES)
        out = scanner.scan()
        assert isinstance(out, list)
        assert all(isinstance(d, dict) for d in out)
        assert len(out) >= 20  # 10 TF + 10 K8S + 8 DKR ≈ 28

    def test_scan_emits_iac_resource_metadata(self):
        scanner = IaCScanner(target_dir=SAMPLES)
        out = scanner.scan()
        # at least one finding should have a non-empty iac_provider
        providers = {d["iac_provider"] for d in out}
        assert providers >= {"terraform", "kubernetes", "dockerfile"}

    def test_scan_zero_findings_on_empty_dir(self, tmp_path: Path):
        assert IaCScanner(target_dir=tmp_path).scan() == []

    def test_scan_zero_findings_on_missing_dir(self):
        assert IaCScanner(target_dir="/nonexistent/__nope__").scan() == []


# ── Normalizer integration ────────────────────────────────────────────────────


class TestNormalizeIaC:
    def test_normalize_iac_returns_canonical_findings(self):
        scanner = IaCScanner(target_dir=SAMPLES)
        out = scanner.scan()
        cfs = normalize_iac(out)
        assert len(cfs) > 0
        # every canonical_rule_id should be IAC-*
        assert all(cf.canonical_rule_id.startswith("IAC-") for cf in cfs)
        # no CUSTOM-* leakage
        assert not any(cf.canonical_rule_id.startswith("CUSTOM-") for cf in cfs)

    def test_normalize_iac_empty_list(self):
        assert normalize_iac([]) == []

    def test_normalize_iac_skips_malformed(self):
        out = normalize_iac([{"not": "a finding"}, "garbage", 123])
        assert out == []
