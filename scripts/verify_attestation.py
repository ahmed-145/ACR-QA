#!/usr/bin/env python3
"""
acrqa verify — CLI tool to verify a scan provenance attestation.

Usage:
    python scripts/verify_attestation.py --run-id 42
    python scripts/verify_attestation.py --run-id 42 --json

Fetches the attestation bundle from the DB and verifies the ECDSA-P256 signature.
Exits 0 if valid, 1 if invalid or not found.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))


def main() -> None:
    parser = argparse.ArgumentParser(description="Verify ACR-QA scan attestation")
    parser.add_argument("--run-id", type=int, required=True, help="Run ID to verify")
    parser.add_argument("--json", action="store_true", dest="as_json", help="Output JSON")
    args = parser.parse_args()

    try:
        from CORE.engines.attestation import AttestationEngine, load_bundle_from_db
        from DATABASE.database import Database

        db = Database()
        bundle = load_bundle_from_db(args.run_id, db)

        if bundle is None:
            _out({"error": f"No attestation found for run {args.run_id}", "valid": False}, args.as_json)
            sys.exit(1)

        engine = AttestationEngine()
        valid = engine.verify(bundle)
        predicate = bundle.get("attestation", {}).get("predicate", {})
        algorithms = [s["algorithm"] for s in bundle.get("signatures", [])]

        result = {
            "run_id": args.run_id,
            "valid": valid,
            "repo_name": predicate.get("repo_name", ""),
            "scan_timestamp": predicate.get("scan_timestamp", ""),
            "findings_count": predicate.get("findings_count", 0),
            "verified_exploitable": predicate.get("verified_exploitable", 0),
            "acrqa_version": predicate.get("acrqa_version", ""),
            "signature_algorithms": algorithms,
            "post_quantum": "Dilithium3" in algorithms,
        }

        _out(result, args.as_json)

        if not valid:
            print("❌ Signature INVALID", file=sys.stderr)
            sys.exit(1)

        print(f"✅ Attestation VALID — run {args.run_id} signed by ACR-QA {result['acrqa_version']}")

    except Exception as exc:
        _out({"error": str(exc), "valid": False}, args.as_json)
        sys.exit(1)


def _out(data: dict, as_json: bool) -> None:
    if as_json:
        print(json.dumps(data, indent=2))


if __name__ == "__main__":
    main()
