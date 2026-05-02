"""
ACR-QA Cryptographic Bill of Materials (CBoM) Scanner
Inventories all cryptographic usage and flags non-quantum-safe algorithms.

Quantum safety classification based on NIST PQC standards (2024):
- UNSAFE:  MD5, SHA1, DES, 3DES, RC4, RSA, ECDSA, DH, DSA (broken or quantum-vulnerable)
- WARN:    SHA256, SHA384, SHA512, AES-128, HMAC-SHA1 (classical-safe, not quantum-safe)
- SAFE:    AES-256, SHA3, BLAKE2, BLAKE3, Argon2, bcrypt, scrypt (quantum-resistant)
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path

# ---------------------------------------------------------------------------
# Algorithm registry
# ---------------------------------------------------------------------------

ALGO_REGISTRY: dict[str, dict] = {
    # Python hashlib
    "md5": {"quantum_safe": False, "category": "hash", "replacement": "SHA3-256 or BLAKE2b"},
    "sha1": {"quantum_safe": False, "category": "hash", "replacement": "SHA-256 or SHA3-256"},
    "sha224": {"quantum_safe": False, "category": "hash", "replacement": "SHA3-256"},
    "sha256": {"quantum_safe": "warn", "category": "hash", "replacement": "SHA3-256 for post-quantum"},
    "sha384": {"quantum_safe": "warn", "category": "hash", "replacement": "SHA3-384 for post-quantum"},
    "sha512": {"quantum_safe": "warn", "category": "hash", "replacement": "SHA3-512 for post-quantum"},
    "sha3_256": {"quantum_safe": True, "category": "hash", "replacement": None},
    "sha3_384": {"quantum_safe": True, "category": "hash", "replacement": None},
    "sha3_512": {"quantum_safe": True, "category": "hash", "replacement": None},
    "blake2b": {"quantum_safe": True, "category": "hash", "replacement": None},
    "blake2s": {"quantum_safe": True, "category": "hash", "replacement": None},
    # Symmetric encryption
    "des": {"quantum_safe": False, "category": "symmetric", "replacement": "AES-256-GCM"},
    "3des": {"quantum_safe": False, "category": "symmetric", "replacement": "AES-256-GCM"},
    "triple_des": {"quantum_safe": False, "category": "symmetric", "replacement": "AES-256-GCM"},
    "rc4": {"quantum_safe": False, "category": "symmetric", "replacement": "ChaCha20-Poly1305"},
    "aes_128": {"quantum_safe": "warn", "category": "symmetric", "replacement": "AES-256 for post-quantum"},
    "aes_256": {"quantum_safe": True, "category": "symmetric", "replacement": None},
    "chacha20": {"quantum_safe": True, "category": "symmetric", "replacement": None},
    # Asymmetric / key exchange
    "rsa": {"quantum_safe": False, "category": "asymmetric", "replacement": "CRYSTALS-Kyber (ML-KEM)"},
    "ecdsa": {"quantum_safe": False, "category": "asymmetric", "replacement": "CRYSTALS-Dilithium (ML-DSA)"},
    "ecdh": {"quantum_safe": False, "category": "asymmetric", "replacement": "CRYSTALS-Kyber (ML-KEM)"},
    "dh": {"quantum_safe": False, "category": "asymmetric", "replacement": "CRYSTALS-Kyber (ML-KEM)"},
    "dsa": {"quantum_safe": False, "category": "asymmetric", "replacement": "CRYSTALS-Dilithium (ML-DSA)"},
    # Password hashing / KDF
    "bcrypt": {"quantum_safe": True, "category": "kdf", "replacement": None},
    "scrypt": {"quantum_safe": True, "category": "kdf", "replacement": None},
    "argon2": {"quantum_safe": True, "category": "kdf", "replacement": None},
    "pbkdf2": {"quantum_safe": "warn", "category": "kdf", "replacement": "Argon2id for new systems"},
    "pbkdf2_sha256": {"quantum_safe": "warn", "category": "kdf", "replacement": "Argon2id for new systems"},
    # MAC
    "hmac_sha1": {"quantum_safe": False, "category": "mac", "replacement": "HMAC-SHA256 or HMAC-SHA3"},
    "hmac_sha256": {"quantum_safe": "warn", "category": "mac", "replacement": "HMAC-SHA3 for post-quantum"},
    "hmac_sha512": {"quantum_safe": "warn", "category": "mac", "replacement": "HMAC-SHA3-512 for post-quantum"},
    # JWT
    "jwt_none": {"quantum_safe": False, "category": "jwt", "replacement": "HS256 minimum, prefer RS256+"},
    "jwt_hs256": {"quantum_safe": "warn", "category": "jwt", "replacement": "EdDSA or post-quantum sig"},
    "jwt_rs256": {"quantum_safe": False, "category": "jwt", "replacement": "EdDSA or post-quantum sig"},
}


# ---------------------------------------------------------------------------
# Detection patterns  (Python + JS/TS)
# ---------------------------------------------------------------------------

PYTHON_PATTERNS: list[tuple[str, str]] = [
    # hashlib.new('md5') or hashlib.md5(
    (r"hashlib\.new\(['\"](\w+)['\"]", "hashlib.new"),
    (
        r"hashlib\.(md5|sha1|sha224|sha256|sha384|sha512|sha3_256|sha3_384|sha3_512|blake2b|blake2s)\s*\(",
        "hashlib.direct",
    ),
    # hmac.new(..., digestmod=hashlib.sha1)
    (r"hmac\.new\(.*digestmod\s*=\s*hashlib\.(sha\w+|md5)", "hmac.new"),
    # from Crypto.Cipher import AES / DES
    (r"from\s+Crypto\.Cipher\s+import\s+(\w+)", "pycryptodome"),
    (r"from\s+cryptography\.hazmat\.primitives\s+import\s+(\w+)", "cryptography-lib"),
    (r"from\s+cryptography\.hazmat\.primitives\.asymmetric\s+import\s+(\w+)", "cryptography-asymmetric"),
    # RSA / ECDSA / DSA imports
    (r"(?:import|from)\s+(rsa|ecdsa|dsa)\b", "crypto-lib-import"),
    # bcrypt / argon2 / scrypt / pbkdf2
    (r"\b(bcrypt|argon2|scrypt|pbkdf2)\b", "kdf-usage"),
    # JWT
    (r"jwt\.decode\(.*algorithms\s*=\s*\[([^\]]+)\]", "jwt-decode"),
    (r"jwt\.encode\(.*algorithm\s*=\s*['\"](\w+)['\"]", "jwt-encode"),
]

JS_PATTERNS: list[tuple[str, str]] = [
    # crypto.createHash('md5')
    (r"crypto\.createHash\(['\"](\w+)['\"]", "node-crypto-hash"),
    # crypto.createCipheriv / createCipher
    (r"crypto\.createCipher(?:iv)?\(['\"]([^'\"]+)['\"]", "node-crypto-cipher"),
    # crypto.createSign / createVerify
    (r"crypto\.create(?:Sign|Verify)\(['\"]([^'\"]+)['\"]", "node-crypto-sign"),
    # crypto.generateKeyPair('rsa'...)
    (r"crypto\.generateKeyPair\(['\"](\w+)['\"]", "node-crypto-keygen"),
    # subtle.digest('SHA-1'...)
    (r"subtle\.digest\(['\"]([^'\"]+)['\"]", "webcrypto-digest"),
    (r"subtle\.(?:encrypt|decrypt)\(\s*\{\s*name\s*:\s*['\"]([^'\"]+)['\"]", "webcrypto-cipher"),
    (r"subtle\.(?:sign|verify)\(\s*\{\s*name\s*:\s*['\"]([^'\"]+)['\"]", "webcrypto-sign"),
    # require('crypto'), require('node:crypto')
    (r"require\(['\"](?:node:)?crypto['\"]\)", "crypto-require"),
    # bcrypt / argon2 / jwt
    (r"\b(bcrypt|argon2|scrypt)\b", "kdf-js"),
    (r"jwt\.sign\(.*algorithm\s*:\s*['\"](\w+)['\"]", "jwt-sign"),
    (r"jwt\.verify\(.*algorithms\s*:\s*\[([^\]]+)\]", "jwt-verify"),
]


# ---------------------------------------------------------------------------
# Data model
# ---------------------------------------------------------------------------


@dataclass
class CryptoUsage:
    file_path: str
    line_number: int
    line_content: str
    algorithm: str  # normalised algorithm name
    raw_match: str  # what the regex captured
    detection_pattern: str  # which pattern fired
    quantum_safe: bool | str  # True / False / "warn"
    category: str  # hash / symmetric / asymmetric / kdf / mac / jwt
    replacement: str | None  # recommended replacement (None if already safe)
    language: str  # "python" | "javascript" | "typescript"

    @property
    def severity(self) -> str:
        if self.quantum_safe is False:
            return "high"
        if self.quantum_safe == "warn":
            return "medium"
        return "low"

    @property
    def rule_id(self) -> str:
        return (
            "CRYPTO-001"
            if self.quantum_safe is False
            else ("CRYPTO-002" if self.quantum_safe == "warn" else "CRYPTO-003")
        )

    def to_finding(self) -> dict:
        """Convert to ACR-QA canonical finding format for pipeline integration."""
        msg_parts = [f"Cryptographic algorithm detected: {self.algorithm.upper()}"]
        if self.quantum_safe is False:
            msg_parts.append("NOT quantum-safe.")
        elif self.quantum_safe == "warn":
            msg_parts.append("Classical-safe but not post-quantum-safe.")
        else:
            msg_parts.append("Quantum-safe.")
        if self.replacement:
            msg_parts.append(f"Consider: {self.replacement}.")

        return {
            "tool": "cbom",
            "rule_id": self.rule_id,
            "canonical_rule_id": self.rule_id,
            "canonical_severity": self.severity,
            "severity": self.severity,
            "category": "security",
            "file": self.file_path,
            "line": self.line_number,
            "line_number": self.line_number,
            "message": " ".join(msg_parts),
            "language": self.language,
            "cbom_metadata": {
                "algorithm": self.algorithm,
                "quantum_safe": self.quantum_safe,
                "category": self.category,
                "replacement": self.replacement,
                "detection_pattern": self.detection_pattern,
                "raw_match": self.raw_match,
            },
        }


@dataclass
class CBoMReport:
    scanned_files: int = 0
    total_usages: int = 0
    unsafe_count: int = 0  # quantum_safe == False
    warn_count: int = 0  # quantum_safe == "warn"
    safe_count: int = 0  # quantum_safe == True
    usages: list[CryptoUsage] = field(default_factory=list)
    algorithms_found: dict[str, int] = field(default_factory=dict)  # algo → count

    def add(self, usage: CryptoUsage) -> None:
        self.usages.append(usage)
        self.total_usages += 1
        self.algorithms_found[usage.algorithm] = self.algorithms_found.get(usage.algorithm, 0) + 1
        if usage.quantum_safe is False:
            self.unsafe_count += 1
        elif usage.quantum_safe == "warn":
            self.warn_count += 1
        else:
            self.safe_count += 1

    def summary(self) -> dict:
        return {
            "scanned_files": self.scanned_files,
            "total_usages": self.total_usages,
            "unsafe_count": self.unsafe_count,
            "warn_count": self.warn_count,
            "safe_count": self.safe_count,
            "algorithms_found": self.algorithms_found,
            "quantum_safe_percentage": round(
                (self.safe_count / self.total_usages * 100) if self.total_usages else 0, 1
            ),
        }


# ---------------------------------------------------------------------------
# Scanner
# ---------------------------------------------------------------------------


class CBoMScanner:
    """
    Scans Python and JavaScript/TypeScript source files for cryptographic
    API usage and classifies each finding by quantum-safety status.

    No external dependencies — uses stdlib re + pathlib only.
    """

    SUPPORTED_EXTENSIONS = {
        ".py": "python",
        ".js": "javascript",
        ".ts": "typescript",
        ".mjs": "javascript",
        ".cjs": "javascript",
    }

    EXCLUDE_DIRS = {
        "node_modules",
        ".venv",
        "venv",
        "__pycache__",
        ".git",
        "htmlcov",
        "dist",
        "build",
        ".mypy_cache",
        "tmp_repos",
    }

    def __init__(self, target_dir: str = "."):
        self.target_dir = Path(target_dir)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def scan(self) -> CBoMReport:
        """Scan target_dir and return a CBoMReport."""
        report = CBoMReport()

        for path in self._iter_source_files():
            language = self.SUPPORTED_EXTENSIONS[path.suffix]
            try:
                text = path.read_text(encoding="utf-8", errors="replace")
            except OSError:
                continue

            report.scanned_files += 1
            for usage in self._scan_file(path, text, language):
                report.add(usage)

        return report

    def scan_file(self, file_path: str) -> list[CryptoUsage]:
        """Scan a single file. Used by pipeline for incremental scans."""
        path = Path(file_path)
        language = self.SUPPORTED_EXTENSIONS.get(path.suffix)
        if not language:
            return []
        try:
            text = path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            return []
        return self._scan_file(path, text, language)

    def to_findings(self, report: CBoMReport) -> list[dict]:
        """Convert CBoMReport usages to ACR-QA canonical finding dicts."""
        return [u.to_finding() for u in report.usages]

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _iter_source_files(self):
        for path in self.target_dir.rglob("*"):
            if not path.is_file():
                continue
            if path.suffix not in self.SUPPORTED_EXTENSIONS:
                continue
            if any(excl in path.parts for excl in self.EXCLUDE_DIRS):
                continue
            yield path

    def _scan_file(self, path: Path, text: str, language: str) -> list[CryptoUsage]:
        usages: list[CryptoUsage] = []
        lines = text.splitlines()
        patterns = PYTHON_PATTERNS if language == "python" else JS_PATTERNS

        for lineno, line in enumerate(lines, start=1):
            stripped = line.strip()
            # Skip comments
            if stripped.startswith("#") or stripped.startswith("//"):
                continue

            for pattern, detection_name in patterns:
                for match in re.finditer(pattern, line, re.IGNORECASE):
                    raw = match.group(1) if match.lastindex else match.group(0)
                    algo = self._normalise_algo(raw)
                    if algo is None:
                        continue
                    info = ALGO_REGISTRY.get(
                        algo,
                        {
                            "quantum_safe": "warn",
                            "category": "unknown",
                            "replacement": "Review manually",
                        },
                    )
                    usages.append(
                        CryptoUsage(
                            file_path=str(path),
                            line_number=lineno,
                            line_content=line.rstrip(),
                            algorithm=algo,
                            raw_match=raw,
                            detection_pattern=detection_name,
                            quantum_safe=info["quantum_safe"],
                            category=info["category"],
                            replacement=info["replacement"],
                            language=language,
                        )
                    )

        return usages

    def _normalise_algo(self, raw: str) -> str | None:
        """Map raw regex capture to a registry key. Returns None to skip."""
        s = raw.lower().strip().strip("'\"").replace("-", "_").replace(" ", "_")

        # Direct registry hit
        if s in ALGO_REGISTRY:
            return s

        # Fuzzy mappings
        mapping = {
            "sha_1": "sha1",
            "sha_256": "sha256",
            "sha_384": "sha384",
            "sha_512": "sha512",
            "sha_224": "sha224",
            "sha3_256": "sha3_256",
            "sha3_384": "sha3_384",
            "sha3_512": "sha3_512",
            "aes_128_cbc": "aes_128",
            "aes_128_gcm": "aes_128",
            "aes_256_cbc": "aes_256",
            "aes_256_gcm": "aes_256",
            "des_ede3": "3des",
            "des_ede3_cbc": "3des",
            "hmac_sha_1": "hmac_sha1",
            "hmac_sha_256": "hmac_sha256",
            "rs256": "jwt_rs256",
            "hs256": "jwt_hs256",
            "none": "jwt_none",
            "aes": "aes_256",  # generic AES → assume 256 (conservative/safe default)
            "rsa_oaep": "rsa",
            "rsa_pss": "rsa",
            "rsa_pkcs1v15": "rsa",
            "ecdsa_with_sha256": "ecdsa",
        }
        if s in mapping:
            return mapping[s]

        # Prefix matches (e.g. "sha256withrsaencryption")
        for prefix, canonical in [
            ("sha3_", "sha3_256"),
            ("blake2", "blake2b"),
            ("aes_128", "aes_128"),
            ("aes_256", "aes_256"),
            ("rsa", "rsa"),
            ("ecdsa", "ecdsa"),
            ("ecdh", "ecdh"),
            ("pbkdf2", "pbkdf2"),
            ("bcrypt", "bcrypt"),
            ("argon2", "argon2"),
            ("scrypt", "scrypt"),
            ("hmac", "hmac_sha256"),
        ]:
            if s.startswith(prefix):
                return canonical

        return None  # Unknown algo — skip silently
