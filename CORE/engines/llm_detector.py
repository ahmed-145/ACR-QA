"""
LLM-Augmented Detection Engine (Phase 1 — GO_BIG_LLM_DETECTION_PLAN.md).

Additive detection source: LLM finds what static rules miss, then exploit-gating
keeps precision. Never replaces rule-based findings; union = rule_findings ∪ llm_findings.

Pipeline:
  LLMDetector.detect_repo(repo_dir)
    → per Python file: prompt Groq llama-3.3-70b → parse JSON candidates
    → CWE-family normalize → deduplicate → emit raw LLMFinding list

  LLMDetector.gate_findings(raw_findings, repo_dir, gt=None)
    → second-opinion gating (2nd Groq call: "confirm this finding?")
    → returns gated findings (≥90% precision target, per plan Phase 2)

Usage in benchmark:
  detector = LLMDetector()
  raw = detector.detect_repo(repo_dir)
  gated = detector.gate_findings(raw, repo_dir)

Integration with CanonicalFinding pipeline:
  Each finding has tool_raw={"tool_name": "llm_detector", "source": "llm",
  "gated": bool, "confidence": 0.0-1.0}. Use canonical_rule_id="LLM-DETECT"
  until the finding is confirmed, then map CWE → SECURITY-* via CANONICAL_CWE.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import time
from dataclasses import dataclass
from pathlib import Path

_ROOT = Path(__file__).parent.parent.parent
_CACHE = _ROOT / "DATA" / "proto_llm_cache"
_CACHE.mkdir(parents=True, exist_ok=True)

MAX_FILE_CHARS = 12_000
_MODEL = "llama-3.3-70b-versatile"
LINE_TOL = 10

# CWE → RealVuln family map (loaded once)
_CWE_FAM: dict[str, str] = {}
_fam_loaded = False

# CWE → canonical SECURITY-* ID mapping (for CanonicalFinding integration)
CANONICAL_CWE_MAP: dict[str, str] = {
    "CWE-89": "SECURITY-027",
    "CWE-79": "SECURITY-045",
    "CWE-78": "SECURITY-021",
    "CWE-94": "SECURITY-001",
    "CWE-22": "SECURITY-049",
    "CWE-918": "SECURITY-046",
    "CWE-611": "SECURITY-043",
    "CWE-1336": "SECURITY-031",
    "CWE-502": "SECURITY-008",
    "CWE-601": "SECURITY-048",
    "CWE-798": "SECURITY-005",
    "CWE-259": "SECURITY-005",
    "CWE-327": "SECURITY-009",
    "CWE-295": "SECURITY-013",
    "CWE-347": "SECURITY-047",
    "CWE-16": "SECURITY-082",
    "CWE-352": "SECURITY-084",
    "CWE-1004": "SECURITY-087",
    "CWE-614": "SECURITY-088",
}

_DETECT_PROMPT = """\
You are a security code auditor. Analyze the following Python file for \
SECURITY VULNERABILITIES ONLY (SQL injection, XSS, command injection, SSRF, \
path traversal, insecure deserialization, SSTI, hardcoded secrets, weak crypto, \
open redirect, XXE, CSRF).

Return ONLY a valid JSON array, no prose, no markdown fences. Each item:
{{"line": <int>, "cwe": "CWE-XX", "severity": "high"|"medium"|"low", "why": "<30 words max>"}}

If no vulnerabilities, return []. Be precise on the line number. Focus on real, \
exploitable flaws a developer MUST fix — not style issues.
File: {fname}

```python
{code}
```"""

_GATE_PROMPT = """\
You are a security code reviewer confirming a finding.

Finding: {finding_desc}
File: {fname}
Code context (lines {start}–{end}):
```python
{context}
```

Is this a real, exploitable security vulnerability? Answer ONLY with:
YES <confidence 0.0-1.0> <one-line reason>
NO <one-line reason>"""


# ---------------------------------------------------------------------------
# Data types
# ---------------------------------------------------------------------------


@dataclass
class LLMFinding:
    file: str
    line: int
    cwe: str
    cwe_family: str
    severity: str
    why: str
    gated: bool = False
    gate_confidence: float = 0.0
    canonical_rule_id: str = "LLM-DETECT"

    def to_canonical_dict(self) -> dict:
        """Produce a dict compatible with the CanonicalFinding pipeline."""
        return {
            "canonical_rule_id": CANONICAL_CWE_MAP.get(self.cwe, "SECURITY-001"),
            "canonical_severity": self.severity,
            "file": self.file,
            "file_path": self.file,
            "line": self.line,
            "message": f"LLM-detected {self.cwe}: {self.why}",
            "tool_raw": {
                "tool_name": "llm_detector",
                "source": "llm",
                "cwe": self.cwe,
                "cwe_family": self.cwe_family,
                "gated": self.gated,
                "gate_confidence": self.gate_confidence,
                "original_output": {"why": self.why},
            },
        }


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _load_cwe_families() -> dict[str, str]:
    global _CWE_FAM, _fam_loaded
    if _fam_loaded:
        return _CWE_FAM
    fam_file = _ROOT / "TESTS" / "evaluation" / "realvuln" / "config" / "cwe-families.json"
    if fam_file.exists():
        d = json.loads(fam_file.read_text())
        for fam, info in d.get("families", {}).items():
            for cwe in info.get("cwes", []):
                _CWE_FAM[cwe.upper()] = fam
    _fam_loaded = True
    return _CWE_FAM


def _cwe_family(cwe: str) -> str:
    fam = _load_cwe_families()
    return fam.get(cwe.upper(), "unknown")


def _load_keys() -> list[str]:
    keys: list[str] = []
    # Try environment variables first (allows GitHub Actions to pass secrets directly)
    for k, v in os.environ.items():
        if k.startswith("GROQ_API_KEY"):  # NOSONAR
            val = v.strip().strip('"').strip("'")
            if val and "your" not in val.lower() and len(val) > 10:
                keys.append(val)
    # Fallback to .env file
    if not keys:
        env = _ROOT / ".env"
        if env.exists():
            for line in env.read_text().splitlines():
                m = re.match(r"\s*(GROQ_API_KEY_\d+)\s*=\s*(.+)", line)
                if m:
                    k = m.group(2).strip().strip('"').strip("'")
                    if k and "your" not in k.lower() and len(k) > 10:
                        keys.append(k)
    return keys


_KEY_IDX = 0


def _groq_call(prompt: str, keys: list[str], max_tokens: int = 1024) -> str:
    global _KEY_IDX
    if not keys:
        raise RuntimeError("No GROQ_API_KEY_* found in environment or .env")
    try:
        from groq import Groq
    except ImportError as e:
        raise RuntimeError("groq package not installed: pip install groq") from e

    key = keys[_KEY_IDX % len(keys)]
    _KEY_IDX += 1
    client = Groq(api_key=key)
    for attempt in range(3):
        try:
            resp = client.chat.completions.create(
                model=_MODEL,
                messages=[{"role": "user", "content": prompt}],
                max_tokens=max_tokens,
                temperature=0.1,
            )
            return resp.choices[0].message.content or ""
        except Exception as exc:
            if attempt == 2:
                raise RuntimeError(f"Groq call failed after 3 attempts: {exc}") from exc
            time.sleep(2**attempt)
    return ""


def _parse_llm_json(text: str) -> list[dict]:
    """Extract JSON array from LLM response, tolerating markdown fences."""
    text = text.strip()
    # Strip markdown fences
    text = re.sub(r"```(?:json)?\s*", "", text).strip()
    text = re.sub(r"```\s*$", "", text).strip()
    # Find first [ ... ] block
    m = re.search(r"\[.*\]", text, re.DOTALL)
    if not m:
        return []
    try:
        return json.loads(m.group(0))
    except json.JSONDecodeError:
        return []


def _file_hash(code: str) -> str:
    return hashlib.sha256(code.encode()).hexdigest()[:16]


# ---------------------------------------------------------------------------
# Main engine
# ---------------------------------------------------------------------------


class LLMDetector:
    """
    Additive LLM detection engine. Wire as a third detection source alongside
    Bandit and Semgrep. Never replaces static findings; always additive.

    Precision strategy (Phase 2): gate through second-opinion LLM confirm call.
    Without gating: ~80% FP, +9pp recall union lift.
    With gating: target ≥90% precision at ≥6pp recall lift (held-out measured).
    """

    def __init__(self, use_cache: bool = True, gate: bool = True) -> None:
        self._keys = _load_keys()
        self._use_cache = use_cache
        self._gate = gate

    def available(self) -> bool:
        return len(self._keys) > 0

    # ------------------------------------------------------------------
    # Phase 1 — raw detection (high recall, high FP)
    # ------------------------------------------------------------------

    def _read_code(self, path: Path) -> str | None:
        try:
            return path.read_text(encoding="utf-8", errors="replace")  # NOSONAR
        except OSError:
            return None

    def _cache_get(self, cache_file: Path) -> list | None:
        try:
            return json.loads(cache_file.read_text())  # NOSONAR
        except Exception:
            return None

    def _cache_put(self, cache_file: Path, raw: list) -> None:
        try:
            cache_file.write_text(json.dumps(raw))  # NOSONAR
        except OSError:
            pass

    def detect_file(self, file_path: str, code: str | None = None) -> list[LLMFinding]:
        """Detect vulnerabilities in a single Python file."""
        path = Path(file_path)
        if code is None:
            code = self._read_code(path)
            if code is None:
                return []

        if len(code.strip()) < 20:
            return []

        # Cache check using hash of file path to avoid variable-based path injection alerts
        cache_key = _file_hash(code[:MAX_FILE_CHARS])
        safe_fname = hashlib.sha256(file_path.encode()).hexdigest()[:16]  # NOSONAR
        cache_file = _CACHE / f"{safe_fname}_{cache_key}.json"
        if self._use_cache and cache_file.exists():
            cached = self._cache_get(cache_file)
            if cached is not None:
                return self._parse_raw(str(path), cached)

        prompt = _DETECT_PROMPT.format(fname=path.name, code=code[:MAX_FILE_CHARS])
        try:
            resp = _groq_call(prompt, self._keys, max_tokens=1024)
        except RuntimeError:
            return []

        raw = _parse_llm_json(resp)
        if self._use_cache:
            self._cache_put(cache_file, raw)

        return self._parse_raw(str(path), raw)

    def detect_repo(self, repo_dir: str) -> list[LLMFinding]:
        """Detect across all Python files in a repo directory."""
        findings: list[LLMFinding] = []
        repo = Path(repo_dir)
        repo_resolved = repo.resolve()
        py_files = sorted(repo.rglob("*.py"))
        # Skip test/migration/vendor files
        py_files = [
            f for f in py_files if not any(p in f.parts for p in ("test", "tests", "migrations", "vendor", ".venv"))
        ]
        for py_file in py_files[:30]:  # cap to avoid Groq rate limits
            resolved_py = py_file.resolve()
            if not resolved_py.is_relative_to(repo_resolved):
                continue
            try:
                code = resolved_py.read_text(encoding="utf-8", errors="replace")  # NOSONAR
            except OSError:
                continue
            for finding in self.detect_file(str(py_file), code):
                # Normalise file path relative to repo_dir
                try:
                    finding.file = str(py_file.relative_to(repo_dir))
                except ValueError:
                    pass
                findings.append(finding)
        return findings

    # ------------------------------------------------------------------
    # Phase 2 — gating for precision
    # ------------------------------------------------------------------

    def gate_findings(self, findings: list[LLMFinding], repo_dir: str) -> list[LLMFinding]:
        """
        Gate raw LLM findings through a second-opinion LLM call.
        Returns findings where the 2nd model confirms the vulnerability.
        Target: cut ~80% FP rate → ≥90% precision while retaining ≥6pp recall lift.
        """
        if not findings:
            return []
        gated: list[LLMFinding] = []
        for f in findings:
            confidence = self._gate_finding(f, repo_dir)
            f.gate_confidence = confidence
            if confidence >= 0.6:
                f.gated = True
                gated.append(f)
        return gated

    def _gate_finding(self, finding: LLMFinding, repo_dir: str) -> float:
        """Return gating confidence 0.0–1.0 via second-opinion LLM call."""
        repo_resolved = Path(repo_dir).resolve()
        file_path = (repo_resolved / finding.file).resolve()
        if not file_path.exists():
            file_path = Path(finding.file).resolve()
        if not file_path.is_relative_to(repo_resolved) and not file_path.is_relative_to(Path.cwd().resolve()):
            return 0.0
        try:
            code_lines = file_path.read_text(encoding="utf-8", errors="replace").splitlines()  # NOSONAR
        except OSError:
            return 0.0

        start = max(0, finding.line - 6)
        end = min(len(code_lines), finding.line + 5)
        context = "\n".join(f"{start + i + 1}: {ln}" for i, ln in enumerate(code_lines[start:end]))

        prompt = _GATE_PROMPT.format(
            finding_desc=f"{finding.cwe} — {finding.why}",
            fname=finding.file,
            start=start + 1,
            end=end,
            context=context,
        )
        try:
            resp = _groq_call(prompt, self._keys, max_tokens=120)
        except RuntimeError:
            return 0.0

        resp = resp.strip().upper()
        if resp.startswith("YES"):
            # Extract confidence if present
            m = re.search(r"YES\s+(0\.\d+|1\.0|1)", resp)
            return float(m.group(1)) if m else 0.75
        return 0.0

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _parse_raw(self, file_path: str, raw: list[dict]) -> list[LLMFinding]:
        findings: list[LLMFinding] = []
        seen: set[tuple] = set()
        for item in raw:
            if not isinstance(item, dict):
                continue
            cwe = str(item.get("cwe", "")).upper()
            if not re.match(r"CWE-\d+", cwe):
                continue
            line = int(item.get("line", 0) or 0)
            if line <= 0:
                continue
            sev = str(item.get("severity", "medium")).lower()
            if sev not in ("high", "medium", "low"):
                sev = "medium"
            key = (cwe, line // 3)  # dedup within 3-line band
            if key in seen:
                continue
            seen.add(key)
            findings.append(
                LLMFinding(
                    file=file_path,
                    line=line,
                    cwe=cwe,
                    cwe_family=_cwe_family(cwe),
                    severity=sev,
                    why=str(item.get("why", ""))[:120],
                )
            )
        return findings
