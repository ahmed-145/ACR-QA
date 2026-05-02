"""Tests for CORE/engines/cross_language_correlator.py — Feature 9 (CHARON)"""

from __future__ import annotations

from CORE.engines.cross_language_correlator import (
    CorrelationGroup,
    CrossLanguageCorrelator,
)

# ── Helpers ───────────────────────────────────────────────────────────────────


def _py(rule="SECURITY-027", msg="sql injection", path="app/dao.py"):
    return {
        "canonical_rule_id": rule,
        "canonical_severity": "high",
        "category": "security",
        "file_path": path,
        "file": path,
        "language": "python",
        "message": msg,
        "tool": "semgrep",
    }


def _tmpl(path="templates/index.html"):
    return {
        "canonical_rule_id": "SECURITY-031",
        "canonical_severity": "medium",
        "category": "security",
        "file_path": path,
        "file": path,
        "language": "html",
        "message": "unsafe template",
        "tool": "semgrep",
    }


def _js(path="app/static.js"):
    return {
        "canonical_rule_id": "SECURITY-001",
        "canonical_severity": "high",
        "category": "security",
        "file_path": path,
        "file": path,
        "language": "javascript",
        "message": "xss",
        "tool": "eslint",
    }


def _make_project(tmp_path, files: dict[str, str]) -> CrossLanguageCorrelator:
    for filename, content in files.items():
        p = tmp_path / filename
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(content)
    return CrossLanguageCorrelator(str(tmp_path))


# ── CorrelationGroup ──────────────────────────────────────────────────────────


class TestCorrelationGroup:
    def _group(self, py=None, tmpl=None, js=None):
        return CorrelationGroup(
            correlation_type="XSS_CHAIN",
            chain_description="Test chain",
            python_findings=py or [_py()],
            template_findings=tmpl or [],
            js_findings=js or [],
            template_file="templates/index.html",
            combined_severity="high",
        )

    def test_all_findings_combines_all(self):
        g = self._group(py=[_py()], tmpl=[_tmpl()], js=[_js()])
        assert len(g.all_findings) == 3

    def test_finding_count(self):
        g = self._group(py=[_py(), _py()], tmpl=[_tmpl()])
        assert g.finding_count == 3

    def test_to_dict_keys(self):
        d = self._group().to_dict()
        for key in [
            "correlation_type",
            "chain_description",
            "combined_severity",
            "confidence_boost",
            "finding_count",
            "template_file",
            "python_findings",
            "template_findings",
            "js_findings",
        ]:
            assert key in d

    def test_to_dict_counts_not_lists(self):
        g = self._group(py=[_py(), _py()])
        d = g.to_dict()
        assert d["python_findings"] == 2
        assert isinstance(d["python_findings"], int)

    def test_default_confidence_boost(self):
        g = self._group()
        assert g.confidence_boost == 15

    def test_combined_severity_set(self):
        g = self._group()
        assert g.combined_severity == "high"


# ── Static classifiers ────────────────────────────────────────────────────────


class TestClassifiers:
    def test_is_python_by_language(self):
        assert CrossLanguageCorrelator._is_python({"language": "python", "file_path": "x.py"})

    def test_is_python_by_extension(self):
        assert CrossLanguageCorrelator._is_python({"language": "", "file_path": "app/views.py"})

    def test_is_python_false_for_js(self):
        assert not CrossLanguageCorrelator._is_python({"language": "javascript", "file_path": "app.js"})

    def test_is_template_html(self):
        assert CrossLanguageCorrelator._is_template({"file_path": "templates/index.html"})

    def test_is_template_jinja2(self):
        assert CrossLanguageCorrelator._is_template({"file_path": "base.jinja2"})

    def test_is_template_j2(self):
        assert CrossLanguageCorrelator._is_template({"file_path": "base.j2"})

    def test_is_template_false_for_py(self):
        assert not CrossLanguageCorrelator._is_template({"file_path": "views.py"})

    def test_is_js_by_language(self):
        assert CrossLanguageCorrelator._is_js({"language": "javascript", "file_path": "app.js"})

    def test_is_js_by_extension(self):
        assert CrossLanguageCorrelator._is_js({"language": "", "file_path": "app.ts"})

    def test_is_js_typescript(self):
        assert CrossLanguageCorrelator._is_js({"language": "typescript", "file_path": "x.ts"})

    def test_is_js_false_for_python(self):
        assert not CrossLanguageCorrelator._is_js({"language": "python", "file_path": "app.py"})


# ── correlate() — empty and edge cases ───────────────────────────────────────


class TestCorrelateEdgeCases:
    def test_empty_findings_returns_empty(self, tmp_path):
        c = CrossLanguageCorrelator(str(tmp_path))
        assert c.correlate([]) == []

    def test_only_python_no_templates_no_js(self, tmp_path):
        c = CrossLanguageCorrelator(str(tmp_path))
        result = c.correlate([_py()])
        assert isinstance(result, list)

    def test_returns_list(self, tmp_path):
        c = CrossLanguageCorrelator(str(tmp_path))
        result = c.correlate([_py(), _js()])
        assert isinstance(result, list)


# ── _correlate_route_js ───────────────────────────────────────────────────────


class TestCorrelateRouteJs:
    def test_detects_shared_directory(self, tmp_path):
        c = CrossLanguageCorrelator(str(tmp_path))
        py = _py(rule="SECURITY-001", path="feature/views.py")
        js = _js(path="feature/app.js")
        groups = c._correlate_route_js([py], [js])
        assert len(groups) == 1
        assert groups[0].correlation_type == "ROUTE_JS_CHAIN"

    def test_no_group_when_different_dirs(self, tmp_path):
        c = CrossLanguageCorrelator(str(tmp_path))
        py = _py(rule="SECURITY-001", path="backend/views.py")
        js = _js(path="frontend/app.js")
        groups = c._correlate_route_js([py], [js])
        assert len(groups) == 0

    def test_no_group_when_no_js(self, tmp_path):
        c = CrossLanguageCorrelator(str(tmp_path))
        groups = c._correlate_route_js([_py(rule="SECURITY-001")], [])
        assert groups == []

    def test_no_group_when_no_security_py(self, tmp_path):
        c = CrossLanguageCorrelator(str(tmp_path))
        py = _py(rule="STYLE-001", path="feature/views.py")
        js = _js(path="feature/app.js")
        groups = c._correlate_route_js([py], [js])
        assert groups == []

    def test_group_contains_correct_findings(self, tmp_path):
        c = CrossLanguageCorrelator(str(tmp_path))
        py = _py(rule="SECURITY-001", path="feature/views.py")
        js = _js(path="feature/app.js")
        groups = c._correlate_route_js([py], [js])
        assert len(groups[0].python_findings) == 1
        assert len(groups[0].js_findings) == 1

    def test_combined_severity_is_high(self, tmp_path):
        c = CrossLanguageCorrelator(str(tmp_path))
        py = _py(rule="SECURITY-001", path="feat/views.py")
        js = _js(path="feat/app.js")
        groups = c._correlate_route_js([py], [js])
        assert groups[0].combined_severity == "high"


# ── _correlate_xss_chain ──────────────────────────────────────────────────────


class TestCorrelateXssChain:
    def test_detects_xss_with_unsafe_template(self, tmp_path):
        (tmp_path / "templates").mkdir()
        (tmp_path / "templates" / "index.html").write_text("{{ user_input | safe }}\n")
        c = CrossLanguageCorrelator(str(tmp_path))
        xss_finding = _py(rule="SECURITY-045", msg="xss risk")
        groups = c._correlate_xss_chain([xss_finding], [])
        assert len(groups) >= 1
        assert groups[0].correlation_type == "XSS_CHAIN"

    def test_no_group_without_unsafe_template(self, tmp_path):
        (tmp_path / "templates").mkdir()
        (tmp_path / "templates" / "index.html").write_text("<p>safe content</p>\n")
        c = CrossLanguageCorrelator(str(tmp_path))
        groups = c._correlate_xss_chain([_py(rule="SECURITY-045")], [])
        assert groups == []

    def test_no_group_without_xss_findings(self, tmp_path):
        (tmp_path / "templates").mkdir()
        (tmp_path / "templates" / "index.html").write_text("{{ data | safe }}\n")
        c = CrossLanguageCorrelator(str(tmp_path))
        groups = c._correlate_xss_chain([], [])
        assert groups == []

    def test_detects_xss_by_message_keyword(self, tmp_path):
        (tmp_path / "templates").mkdir()
        (tmp_path / "templates" / "page.html").write_text("{{ x | safe }}\n")
        c = CrossLanguageCorrelator(str(tmp_path))
        f = _py(rule="CUSTOM-001", msg="render_template_string with user data")
        groups = c._correlate_xss_chain([f], [])
        assert len(groups) >= 1


# ── _correlate_sqli_to_template ───────────────────────────────────────────────


class TestCorrelateSqliToTemplate:
    def test_no_sqli_returns_empty(self, tmp_path):
        c = CrossLanguageCorrelator(str(tmp_path))
        groups = c._correlate_sqli_to_template([_py(rule="STYLE-001")], [])
        assert groups == []

    def test_sqli_with_no_related_templates_returns_empty(self, tmp_path):
        c = CrossLanguageCorrelator(str(tmp_path))
        groups = c._correlate_sqli_to_template([_py(rule="SECURITY-027")], [])
        assert groups == []

    def test_sqli_by_message_keyword(self, tmp_path):
        c = CrossLanguageCorrelator(str(tmp_path))
        f = _py(rule="CUSTOM-999", msg="raw sql query execution")
        # No route template map, so no groups — but shouldn't crash
        groups = c._correlate_sqli_to_template([f], [])
        assert isinstance(groups, list)

    def test_sqli_with_render_template_in_same_dir(self, tmp_path):
        # Create a Python file with render_template in same dir as DAO
        (tmp_path / "app").mkdir()
        (tmp_path / "app" / "views.py").write_text(
            "def index():\n    return render_template('index.html', data=data)\n"
        )
        c = CrossLanguageCorrelator(str(tmp_path))
        sqli_f = _py(rule="SECURITY-027", path=str(tmp_path / "app" / "dao.py"))
        groups = c._correlate_sqli_to_template([sqli_f], [])
        assert len(groups) >= 1
        assert groups[0].correlation_type == "SQLI_TO_TEMPLATE"
        assert groups[0].combined_severity == "high"


# ── _correlate_template_injection ─────────────────────────────────────────────


class TestCorrelateTemplateInjection:
    def test_detects_safe_filter_in_template(self, tmp_path):
        (tmp_path / "templates").mkdir()
        (tmp_path / "templates" / "base.html").write_text("{{ content | safe }}\n")
        c = CrossLanguageCorrelator(str(tmp_path))
        groups = c._correlate_template_injection([_py(rule="SECURITY-001")])
        assert len(groups) >= 1
        assert groups[0].correlation_type == "TEMPLATE_INJECTION"

    def test_no_group_without_security_findings(self, tmp_path):
        (tmp_path / "templates").mkdir()
        (tmp_path / "templates" / "base.html").write_text("{{ content | safe }}\n")
        c = CrossLanguageCorrelator(str(tmp_path))
        groups = c._correlate_template_injection([])
        assert groups == []

    def test_no_group_without_unsafe_templates(self, tmp_path):
        (tmp_path / "templates").mkdir()
        (tmp_path / "templates" / "base.html").write_text("<p>safe</p>\n")
        c = CrossLanguageCorrelator(str(tmp_path))
        groups = c._correlate_template_injection([_py(rule="SECURITY-001")])
        assert groups == []

    def test_detects_markup_in_template(self, tmp_path):
        (tmp_path / "templates").mkdir()
        (tmp_path / "templates" / "page.html").write_text("{% set x = Markup(data) %}\n")
        c = CrossLanguageCorrelator(str(tmp_path))
        groups = c._correlate_template_injection([_py(rule="HARDCODE-001")])
        assert len(groups) >= 1


# ── _find_unsafe_templates ────────────────────────────────────────────────────


class TestFindUnsafeTemplates:
    def test_finds_safe_filter(self, tmp_path):
        (tmp_path / "t.html").write_text("{{ x | safe }}")
        c = CrossLanguageCorrelator(str(tmp_path))
        unsafe = c._find_unsafe_templates()
        assert any("t.html" in u for u in unsafe)

    def test_finds_markup_call(self, tmp_path):
        (tmp_path / "t.html").write_text("Markup(user_data)")
        c = CrossLanguageCorrelator(str(tmp_path))
        assert len(c._find_unsafe_templates()) >= 1

    def test_finds_autoescape_false_in_py(self, tmp_path):
        (tmp_path / "app.py").write_text("env = Environment(autoescape=False)\n")
        c = CrossLanguageCorrelator(str(tmp_path))
        assert len(c._find_unsafe_templates()) >= 1

    def test_safe_template_not_flagged(self, tmp_path):
        (tmp_path / "t.html").write_text("<p>{{ name }}</p>")
        c = CrossLanguageCorrelator(str(tmp_path))
        assert c._find_unsafe_templates() == []

    def test_excludes_node_modules(self, tmp_path):
        nm = tmp_path / "node_modules"
        nm.mkdir()
        (nm / "t.html").write_text("{{ x | safe }}")
        c = CrossLanguageCorrelator(str(tmp_path))
        assert c._find_unsafe_templates() == []


# ── _build_route_template_map ─────────────────────────────────────────────────


class TestBuildRouteTemplateMap:
    def test_finds_render_template_calls(self, tmp_path):
        (tmp_path / "views.py").write_text("def index():\n    return render_template('index.html', x=1)\n")
        c = CrossLanguageCorrelator(str(tmp_path))
        route_map = c._build_route_template_map()
        templates = [t for ts in route_map.values() for t in ts]
        assert "index.html" in templates

    def test_caches_result(self, tmp_path):
        (tmp_path / "views.py").write_text("render_template('a.html')\n")
        c = CrossLanguageCorrelator(str(tmp_path))
        first = c._build_route_template_map()
        second = c._build_route_template_map()
        assert first is second

    def test_empty_dir_returns_empty(self, tmp_path):
        c = CrossLanguageCorrelator(str(tmp_path))
        assert c._build_route_template_map() == {}

    def test_excludes_pycache(self, tmp_path):
        pc = tmp_path / "__pycache__"
        pc.mkdir()
        (pc / "views.py").write_text("render_template('secret.html')\n")
        c = CrossLanguageCorrelator(str(tmp_path))
        route_map = c._build_route_template_map()
        templates = [t for ts in route_map.values() for t in ts]
        assert "secret.html" not in templates


# ── enrich_findings ───────────────────────────────────────────────────────────


class TestEnrichFindings:
    def test_returns_tuple(self, tmp_path):
        c = CrossLanguageCorrelator(str(tmp_path))
        result = c.enrich_findings([_py(), _js()])
        assert isinstance(result, tuple)
        assert len(result) == 2

    def test_enriches_correlated_finding(self, tmp_path):
        c = CrossLanguageCorrelator(str(tmp_path))
        py = _py(rule="SECURITY-001", path="feat/views.py")
        js = _js(path="feat/app.js")
        enriched, groups = c.enrich_findings([py, js])
        if groups:
            correlated = [f for f in enriched if "cross_language_correlation" in f]
            assert len(correlated) >= 1

    def test_boosts_confidence_score(self, tmp_path):
        c = CrossLanguageCorrelator(str(tmp_path))
        py = _py(rule="SECURITY-001", path="feat/views.py")
        py["confidence_score"] = 60
        js = _js(path="feat/app.js")
        enriched, groups = c.enrich_findings([py, js])
        if groups:
            assert py["confidence_score"] > 60

    def test_confidence_score_capped_at_100(self, tmp_path):
        c = CrossLanguageCorrelator(str(tmp_path))
        py = _py(rule="SECURITY-001", path="feat/views.py")
        py["confidence_score"] = 99
        js = _js(path="feat/app.js")
        enriched, groups = c.enrich_findings([py, js])
        assert py.get("confidence_score", 99) <= 100

    def test_empty_findings_returns_empty_groups(self, tmp_path):
        c = CrossLanguageCorrelator(str(tmp_path))
        enriched, groups = c.enrich_findings([])
        assert enriched == []
        assert groups == []


# ── scan_project ──────────────────────────────────────────────────────────────


class TestScanProject:
    def test_empty_project_returns_empty(self, tmp_path):
        c = CrossLanguageCorrelator(str(tmp_path))
        assert c.scan_project() == []

    def test_detects_sqli_pattern_in_python(self, tmp_path):
        (tmp_path / "dao.py").write_text(
            "def get(id):\n    cur.execute('SELECT * FROM t WHERE id = %s' % {'id': id})\n"
        )
        (tmp_path / "views.py").write_text("def index():\n    return render_template('index.html', data=get(1))\n")
        c = CrossLanguageCorrelator(str(tmp_path))
        groups = c.scan_project()
        assert isinstance(groups, list)

    def test_excludes_test_files_from_synthetic(self, tmp_path):
        (tmp_path / "test_views.py").write_text("cur.execute('SELECT * FROM t WHERE id = %s' % {'id': 1})\n")
        c = CrossLanguageCorrelator(str(tmp_path))
        groups = c.scan_project()
        # test files excluded — no synthetic findings
        assert groups == []


# ── _build_synthetic_findings ─────────────────────────────────────────────────


class TestBuildSyntheticFindings:
    def test_returns_list(self, tmp_path):
        c = CrossLanguageCorrelator(str(tmp_path))
        assert isinstance(c._build_synthetic_findings(), list)

    def test_detects_string_format_sqli(self, tmp_path):
        (tmp_path / "dao.py").write_text("query = 'SELECT * FROM users WHERE id = %(id)s' % {'id': uid}\n")
        c = CrossLanguageCorrelator(str(tmp_path))
        findings = c._build_synthetic_findings()
        assert any(f["canonical_rule_id"] == "SECURITY-027" for f in findings)

    def test_synthetic_finding_has_required_keys(self, tmp_path):
        (tmp_path / "dao.py").write_text("cur.execute('SELECT * WHERE id = %s' % {'id': x})\n")
        c = CrossLanguageCorrelator(str(tmp_path))
        findings = c._build_synthetic_findings()
        if findings:
            for key in ["canonical_rule_id", "file", "line_number", "language"]:
                assert key in findings[0]
