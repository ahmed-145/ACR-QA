"""
Task 12.2 — Property-based tests using Hypothesis.

Tests schema invariants across millions of generated inputs.
Finds edge cases the developer didn't think of.
Run with: pytest TESTS/test_property_based.py -v
"""

import sys
from pathlib import Path

from hypothesis import HealthCheck, assume, given, settings
from hypothesis import strategies as st

sys.path.insert(0, str(Path(__file__).parent.parent))

from CORE.engines.normalizer import RULE_MAPPING, CanonicalFinding, normalize_bandit, normalize_ruff, normalize_semgrep

# ─── Strategies ──────────────────────────────────────────────────────────────

valid_severities = st.sampled_from(["low", "medium", "high", "critical"])
valid_categories = st.sampled_from(
    [
        "security",
        "style",
        "design",
        "performance",
        "complexity",
        "dead_code",
        "import",
        "type_safety",
    ]
)
file_paths = st.one_of(
    st.just("test.py"),
    st.just("app/main.py"),
    st.just("src/utils.js"),
    st.just("pkg/server.go"),
    st.builds(
        lambda name, ext: f"{name}{ext}",
        name=st.text(alphabet="abcdefghijklmnopqrstuvwxyz_/", min_size=1, max_size=30).filter(
            lambda s: s.strip("/") and not s.startswith("/")
        ),
        ext=st.sampled_from([".py", ".js", ".ts", ".go"]),
    ),
)
line_numbers = st.integers(min_value=0, max_value=100_000)
text_messages = st.text(min_size=1, max_size=500)
rule_ids = st.one_of(
    st.sampled_from(list(RULE_MAPPING.keys())),
    st.text(
        alphabet="ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-_",
        min_size=2,
        max_size=20,
    ),
)


# ─── CanonicalFinding invariants ─────────────────────────────────────────────


class TestCanonicalFindingInvariants:
    """
    Property: CanonicalFinding.create() must always produce a valid object
    regardless of what rule_id, severity, category are passed.
    No input combination should crash the factory.
    """

    @given(
        rule_id=rule_ids,
        file=file_paths,
        line=line_numbers,
        severity=valid_severities,
        category=valid_categories,
        message=text_messages,
    )
    @settings(
        max_examples=500,
        suppress_health_check=[HealthCheck.too_slow],
        deadline=None,
    )
    def test_create_never_raises(self, rule_id, file, line, severity, category, message):
        """CanonicalFinding.create() must never raise for valid severities/categories."""
        finding = CanonicalFinding.create(
            rule_id=rule_id,
            file=file,
            line=line,
            severity=severity,
            category=category,
            message=message,
            tool_name="test_tool",
            tool_output={},
        )
        assert finding is not None

    @given(
        rule_id=rule_ids,
        file=file_paths,
        line=line_numbers,
        severity=valid_severities,
        category=valid_categories,
        message=text_messages,
    )
    @settings(max_examples=300, suppress_health_check=[HealthCheck.too_slow], deadline=None)
    def test_canonical_rule_id_never_empty(self, rule_id, file, line, severity, category, message):
        """canonical_rule_id must always be set — never empty or None."""
        finding = CanonicalFinding.create(
            rule_id=rule_id,
            file=file,
            line=line,
            severity=severity,
            category=category,
            message=message,
            tool_name="test_tool",
            tool_output={},
        )
        assert finding.canonical_rule_id
        assert len(finding.canonical_rule_id) > 0

    @given(
        rule_id=rule_ids,
        file=file_paths,
        line=line_numbers,
        severity=valid_severities,
        category=valid_categories,
        message=text_messages,
    )
    @settings(max_examples=300, suppress_health_check=[HealthCheck.too_slow], deadline=None)
    def test_severity_always_valid(self, rule_id, file, line, severity, category, message):
        """Severity must always be one of the valid values after creation."""
        finding = CanonicalFinding.create(
            rule_id=rule_id,
            file=file,
            line=line,
            severity=severity,
            category=category,
            message=message,
            tool_name="test_tool",
            tool_output={},
        )
        assert finding.severity in ("low", "medium", "high", "critical")

    @given(
        rule_id=rule_ids,
        file=file_paths,
        line=line_numbers,
        severity=valid_severities,
        category=valid_categories,
        message=text_messages,
    )
    @settings(max_examples=300, suppress_health_check=[HealthCheck.too_slow], deadline=None)
    def test_to_dict_always_serializable(self, rule_id, file, line, severity, category, message):
        """to_dict() must always return a dict with required keys."""
        finding = CanonicalFinding.create(
            rule_id=rule_id,
            file=file,
            line=line,
            severity=severity,
            category=category,
            message=message,
            tool_name="test_tool",
            tool_output={},
        )
        d = finding.to_dict()
        assert isinstance(d, dict)
        for key in ("original_rule_id", "canonical_rule_id", "file", "line", "severity", "message"):
            assert key in d

    @given(
        rule_id=rule_ids,
        file=file_paths,
        line=line_numbers,
        severity=valid_severities,
        category=valid_categories,
        message=text_messages,
    )
    @settings(max_examples=200, suppress_health_check=[HealthCheck.too_slow], deadline=None)
    def test_unknown_rule_maps_to_custom(self, rule_id, file, line, severity, category, message):
        """Unknown rule IDs must map to CUSTOM-<id>, never to an empty string."""
        assume(rule_id not in RULE_MAPPING)
        finding = CanonicalFinding.create(
            rule_id=rule_id,
            file=file,
            line=line,
            severity=severity,
            category=category,
            message=message,
            tool_name="test_tool",
            tool_output={},
        )
        assert finding.canonical_rule_id.startswith("CUSTOM-")

    @given(
        rule_id=st.sampled_from(list(RULE_MAPPING.keys())),
        file=file_paths,
        line=line_numbers,
        severity=valid_severities,
        category=valid_categories,
        message=text_messages,
    )
    @settings(max_examples=200, suppress_health_check=[HealthCheck.too_slow], deadline=None)
    def test_known_rule_never_maps_to_custom(self, rule_id, file, line, severity, category, message):
        """Known rule IDs must NEVER produce a CUSTOM-* canonical ID."""
        finding = CanonicalFinding.create(
            rule_id=rule_id,
            file=file,
            line=line,
            severity=severity,
            category=category,
            message=message,
            tool_name="test_tool",
            tool_output={},
        )
        assert not finding.canonical_rule_id.startswith("CUSTOM-"), (
            f"Rule {rule_id!r} is in RULE_MAPPING but produced CUSTOM-* ID: " f"{finding.canonical_rule_id!r}"
        )

    @given(
        file=file_paths,
        line=line_numbers,
        severity=valid_severities,
        category=valid_categories,
        message=text_messages,
    )
    @settings(max_examples=200, suppress_health_check=[HealthCheck.too_slow], deadline=None)
    def test_language_detected_from_extension(self, file, line, severity, category, message):
        """Language must be detected from file extension — never empty for .py/.js/.ts/.go."""
        finding = CanonicalFinding.create(
            rule_id="F401",
            file=file,
            line=line,
            severity=severity,
            category=category,
            message=message,
            tool_name="ruff",
            tool_output={},
        )
        ext = Path(file).suffix.lower()
        expected = {".py": "python", ".js": "javascript", ".ts": "typescript", ".go": "go"}
        if ext in expected:
            assert finding.language == expected[ext], (
                f"File {file!r} with ext {ext!r} should have language " f"{expected[ext]!r}, got {finding.language!r}"
            )


# ─── Normalizer parser invariants ────────────────────────────────────────────


class TestNormalizerParserInvariants:
    """
    Property: normalizer functions must NEVER raise — they must always return
    a list (possibly empty) regardless of what garbage input they receive.
    """

    @given(
        data=st.dictionaries(
            keys=st.text(min_size=0, max_size=100),
            values=st.one_of(
                st.lists(
                    st.dictionaries(
                        keys=st.text(max_size=20),
                        values=st.one_of(st.text(max_size=50), st.integers(), st.none()),
                    )
                ),
                st.text(),
                st.integers(),
                st.none(),
            ),
            max_size=20,
        )
    )
    @settings(max_examples=500, suppress_health_check=[HealthCheck.too_slow], deadline=None)
    def test_normalize_ruff_never_raises(self, data):
        """normalize_ruff() must never raise — always returns a list."""
        result = normalize_ruff(data)
        assert isinstance(result, list)

    @given(
        data=st.one_of(
            st.just({}),
            st.just([]),
            st.just(None),
            st.dictionaries(
                keys=st.text(max_size=20),
                values=st.lists(
                    st.dictionaries(
                        keys=st.text(max_size=20),
                        values=st.one_of(st.text(max_size=100), st.integers(), st.none()),
                    ),
                    max_size=10,
                ),
                max_size=10,
            ),
        )
    )
    @settings(max_examples=300, suppress_health_check=[HealthCheck.too_slow], deadline=None)
    def test_normalize_bandit_never_raises(self, data):
        """normalize_bandit() must never raise — always returns a list."""
        result = normalize_bandit(data)
        assert isinstance(result, list)

    @given(
        data=st.one_of(
            st.just({}),
            st.just([]),
            st.just(None),
            st.dictionaries(
                keys=st.just("results"),
                values=st.lists(
                    st.dictionaries(
                        keys=st.text(max_size=20),
                        values=st.one_of(st.text(max_size=100), st.integers(), st.none(), st.lists(st.text())),
                    ),
                    max_size=10,
                ),
                max_size=1,
            ),
        )
    )
    @settings(max_examples=300, suppress_health_check=[HealthCheck.too_slow], deadline=None)
    def test_normalize_semgrep_never_raises(self, data):
        """normalize_semgrep() must never raise — always returns a list."""
        result = normalize_semgrep(data)
        assert isinstance(result, list)

    @given(
        results=st.lists(
            st.dictionaries(
                keys=st.text(max_size=20),
                values=st.one_of(st.text(max_size=100), st.integers(), st.none()),
                max_size=10,
            ),
            max_size=50,
        )
    )
    @settings(max_examples=300, suppress_health_check=[HealthCheck.too_slow], deadline=None)
    def test_normalize_ruff_all_results_are_findings(self, results):
        """Every element returned by normalize_ruff() must be a CanonicalFinding."""
        output = normalize_ruff({"results": results})
        for item in output:
            assert isinstance(item, CanonicalFinding)

    @given(
        st.lists(
            st.dictionaries(
                keys=st.text(max_size=20),
                values=st.one_of(st.text(max_size=100), st.integers(), st.none()),
                max_size=10,
            ),
            max_size=50,
        )
    )
    @settings(max_examples=300, suppress_health_check=[HealthCheck.too_slow], deadline=None)
    def test_normalize_bandit_all_results_are_findings(self, results):
        """Every element returned by normalize_bandit() must be a CanonicalFinding."""
        output = normalize_bandit({"results": results})
        for item in output:
            assert isinstance(item, CanonicalFinding)


# ─── Rule mapping invariants ──────────────────────────────────────────────────


class TestRuleMappingInvariants:
    """Property: RULE_MAPPING values must always be well-formed canonical IDs."""

    def test_all_canonical_ids_have_prefix(self):
        """Every canonical ID must have a dash separating prefix and number."""
        valid_prefixes = {
            "SECURITY",
            "STYLE",
            "DESIGN",
            "NAMING",
            "IMPORT",
            "TYPE",
            "COMPLEXITY",
            "DEAD",
            "VAR",
            "EXCEPT",
            "PATTERN",
            "ASYNC",
            "HARDCODE",
            "DUP",
            "ERROR",
            "BEST-PRACTICE",
            "SOLID",
            "ASSERT",
        }
        for rule_id, canonical_id in RULE_MAPPING.items():
            parts = canonical_id.rsplit("-", 1)
            assert len(parts) == 2, f"Canonical ID {canonical_id!r} (from {rule_id!r}) has no dash"
            prefix = parts[0]
            assert prefix in valid_prefixes, f"Canonical ID {canonical_id!r} has unknown prefix {prefix!r}"

    def test_all_canonical_ids_end_with_number(self):
        """Every canonical ID must end with a numeric suffix."""
        for rule_id, canonical_id in RULE_MAPPING.items():
            suffix = canonical_id.rsplit("-", 1)[-1]
            assert suffix.isdigit(), f"Canonical ID {canonical_id!r} (from {rule_id!r}) doesn't end with a number"

    def test_no_custom_star_in_mapping(self):
        """RULE_MAPPING must never map to CUSTOM-* — those are for unknown rules only."""
        for rule_id, canonical_id in RULE_MAPPING.items():
            assert not canonical_id.startswith("CUSTOM-"), (
                f"Rule {rule_id!r} maps to CUSTOM-* ID {canonical_id!r} — " "this should not be in the explicit mapping"
            )

    def test_no_empty_values(self):
        """RULE_MAPPING values must never be empty strings."""
        for rule_id, canonical_id in RULE_MAPPING.items():
            assert canonical_id, f"Rule {rule_id!r} maps to empty string"

    def test_no_empty_keys(self):
        """RULE_MAPPING keys must never be empty strings."""
        for rule_id in RULE_MAPPING:
            assert rule_id, "RULE_MAPPING has an empty key"
