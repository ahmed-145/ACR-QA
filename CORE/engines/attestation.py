"""
Scan Provenance Attestation Engine — Feature 13 (v3.6.0).

Generates SLSA-grade attestations for completed scans, signed with:
  - ECDSA-P256 (primary, via `cryptography` — always available)
  - Dilithium3 post-quantum (bonus, via `dilithium-py` — graceful degradation)

Attestation format is SLSA-compatible JSON:
  {
    "predicateType": "https://acrqa.io/scan/v1",
    "subject": {"name": "<repo>", "digest": {"sha1": "<commit>"}},
    "predicate": { scan metadata },
    "signatures": [{"algorithm": "ECDSA-P256", "signature": "<hex>", "key_id": "..."}]
  }

Key management:
  - Set ACRQA_SIGNING_KEY env var to a PEM-encoded ECDSA private key for stable key_id.
  - Without the env var, an ephemeral key is generated per process (suitable for dev/demo).

Verification:
  - `AttestationEngine().verify(bundle)` returns True if the ECDSA signature is valid.
  - The CLI wrapper is in scripts/verify_attestation.py.
"""

from __future__ import annotations

import hashlib
import json
import logging
import os
import time

import cryptography.exceptions
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import ec

logger = logging.getLogger(__name__)

PREDICATE_TYPE = "https://acrqa.io/scan/v1"
ATTESTATION_VERSION = "1"


# ---------------------------------------------------------------------------
# Key management
# ---------------------------------------------------------------------------


def _load_or_generate_key() -> ec.EllipticCurvePrivateKey:
    """Return signing key from ACRQA_SIGNING_KEY env var, or a fresh ephemeral one."""
    pem = os.getenv("ACRQA_SIGNING_KEY", "").strip()
    if pem:
        try:
            key = serialization.load_pem_private_key(pem.encode(), password=None)
            if not isinstance(key, ec.EllipticCurvePrivateKey):
                raise TypeError("Expected ECDSA key")
            return key
        except (ValueError, TypeError) as exc:
            logger.warning("Could not load ACRQA_SIGNING_KEY, generating ephemeral key: %s", exc)
    return ec.generate_private_key(ec.SECP256R1())


def _key_id(private_key: ec.EllipticCurvePrivateKey) -> str:
    """Return first 16 hex chars of SHA-256 of the DER-encoded public key."""
    pub_der = private_key.public_key().public_bytes(
        serialization.Encoding.DER,
        serialization.PublicFormat.SubjectPublicKeyInfo,
    )
    return hashlib.sha256(pub_der).hexdigest()[:16]


# ---------------------------------------------------------------------------
# Attestation dataclass helpers
# ---------------------------------------------------------------------------


def build_predicate(run_id: int | str, scan_result: dict) -> dict:
    """Build the SLSA predicate dict from a completed scan result."""
    from CORE import __version__

    return {
        "acrqa_version": __version__,
        "attestation_version": ATTESTATION_VERSION,
        "run_id": str(run_id),
        "repo_name": scan_result.get("repo_name", ""),
        "commit_sha": scan_result.get("commit_sha", ""),
        "scan_timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "findings_count": scan_result.get("total_findings", 0),
        "high_count": scan_result.get("high_count", 0),
        "medium_count": scan_result.get("medium_count", 0),
        "low_count": scan_result.get("low_count", 0),
        "reachability_enabled": scan_result.get("reachability_enabled", False),
        "verified_exploitable": scan_result.get("verified_exploitable", 0),
        "suppressed_by_embedding": scan_result.get("suppressed_by_embedding", 0),
    }


def build_attestation(run_id: int | str, scan_result: dict) -> dict:
    """Return an unsigned SLSA-style attestation envelope."""
    return {
        "predicateType": PREDICATE_TYPE,
        "subject": {
            "name": scan_result.get("repo_name", ""),
            "digest": {"sha1": scan_result.get("commit_sha", "unknown")},
        },
        "predicate": build_predicate(run_id, scan_result),
    }


# ---------------------------------------------------------------------------
# Engine
# ---------------------------------------------------------------------------


class AttestationEngine:
    """Signs and verifies scan attestations."""

    def __init__(self) -> None:
        self._key = _load_or_generate_key()
        self._kid = _key_id(self._key)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def sign(self, attestation: dict) -> dict:
        """
        Sign an attestation envelope. Returns a bundle:
          { "attestation": {...}, "signatures": [{algorithm, signature, key_id}] }

        Always includes ECDSA-P256. Adds Dilithium3 if dilithium-py is installed.
        """
        payload = _canonical_payload(attestation)
        sigs = [self._sign_ecdsa(payload)]

        pq_sig = self._sign_dilithium3(payload)
        if pq_sig:
            sigs.append(pq_sig)

        return {"attestation": attestation, "signatures": sigs}

    def verify(self, bundle: dict) -> bool:
        """Verify the ECDSA-P256 signature in the bundle. Returns True if valid."""
        attestation = bundle.get("attestation", {})
        payload = _canonical_payload(attestation)

        for sig_entry in bundle.get("signatures", []):
            if sig_entry.get("algorithm") != "ECDSA-P256":
                continue
            try:
                sig_bytes = bytes.fromhex(sig_entry["signature"])
                self._key.public_key().verify(sig_bytes, payload, ec.ECDSA(hashes.SHA256()))
                return True
            except (ValueError, TypeError, cryptography.exceptions.InvalidSignature):
                return False
        return False

    def attest_scan(self, run_id: int | str, scan_result: dict, db) -> dict | None:
        """
        Generate, sign, and persist an attestation for a completed scan.
        Never raises — returns None on any failure so the pipeline continues.
        """
        try:
            attestation = build_attestation(run_id, scan_result)
            bundle = self.sign(attestation)
            bundle_json = json.dumps(bundle, sort_keys=True)

            ecdsa: dict = next((s for s in bundle["signatures"] if s["algorithm"] == "ECDSA-P256"), {})
            db.store_attestation(
                run_id=int(run_id),
                attestation_json=bundle_json,
                signature=ecdsa.get("signature", ""),
                key_id=ecdsa.get("key_id", ""),
            )
            logger.info(
                "Attestation stored for run %s (key_id=%s, pq=%s)",
                run_id,
                self._kid,
                any(s["algorithm"] == "Dilithium3" for s in bundle["signatures"]),
            )
            return bundle
        except Exception as exc:
            logger.warning("Attestation failed (non-fatal): %s", exc)
            return None

    def public_key_pem(self) -> str:
        """Return PEM-encoded public key for out-of-band distribution."""
        return (
            self._key.public_key()
            .public_bytes(
                serialization.Encoding.PEM,
                serialization.PublicFormat.SubjectPublicKeyInfo,
            )
            .decode()
        )

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _sign_ecdsa(self, payload: bytes) -> dict:
        sig = self._key.sign(payload, ec.ECDSA(hashes.SHA256()))
        return {
            "algorithm": "ECDSA-P256",
            "signature": sig.hex(),
            "key_id": self._kid,
        }

    def _sign_dilithium3(self, payload: bytes) -> dict | None:
        try:
            from dilithium_py.dilithium import Dilithium3

            pk, sk = Dilithium3.keygen()
            sig = Dilithium3.sign(sk, payload)
            return {
                "algorithm": "Dilithium3",
                "signature": sig.hex(),
                "key_id": hashlib.sha256(pk).hexdigest()[:16],
            }
        except ImportError:
            return None
        except Exception as exc:
            logger.debug("Dilithium3 signing failed: %s", exc)
            return None


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _canonical_payload(attestation: dict) -> bytes:
    """Deterministic JSON encoding for signing."""
    return json.dumps(attestation, sort_keys=True, separators=(",", ":")).encode()


def load_bundle_from_db(run_id: int, db) -> dict | None:
    """Retrieve stored attestation bundle for a run, or None if not found."""
    row = db.get_attestation(run_id)
    if not row:
        return None
    try:
        return json.loads(row["attestation_json"])
    except Exception as exc:
        logger.debug("get_attestation: JSON parse failed for run %s: %s", run_id, exc)
        return None
