"""
Tests for CORE/engines/reachability.py — Feature 9 (Call Graph FP Reduction)
Target: 90%+ coverage. Pure AST analysis — no mocks needed.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from CORE.engines.reachability import (
    CallGraphReachability,
    CallGraphResult,
    _build_call_graph,
    _detect_entry_points,
)

FIXTURE_DIR = Path(__file__).parent / "fixtures" / "reachability"


# ── Helpers ───────────────────────────────────────────────────────────────────


def _analyze(filename: str) -> CallGraphResult:
    engine = CallGraphReachability()
    return engine.analyze(str(FIXTURE_DIR / filename))


# ── CallGraphResult unit tests ────────────────────────────────────────────────


class TestCallGraphResult:
    def _make(self, reachable, unreachable, entry_points=None):
        return CallGraphResult(
            file_path="test.py",
            reachable=set(reachable),
            unreachable=set(unreachable),
            entry_points=list(entry_points or []),
        )

    def test_is_function_reachable_true(self):
        r = self._make(["execute_query"], [])
        assert r.is_function_reachable("execute_query") is True

    def test_is_function_reachable_false(self):
        r = self._make([], ["orphan_function"])
        assert r.is_function_reachable("orphan_function") is False

    def test_is_function_reachable_unknown_returns_true(self):
        # Unknown functions (not in either set) are assumed reachable — safe default
        r = self._make([], [])
        assert r.is_function_reachable("unknown_func") is True

    def test_penalty_for_unreachable(self):
        r = self._make([], ["dead_helper"])
        assert r.penalty_for("dead_helper") == -20

    def test_penalty_for_reachable_is_zero(self):
        r = self._make(["process_input"], [])
        assert r.penalty_for("process_input") == 0

    def test_penalty_for_none_is_zero(self):
        r = self._make([], [])
        assert r.penalty_for(None) == 0

    def test_penalty_for_unknown_is_zero(self):
        r = self._make([], [])
        assert r.penalty_for("mystery") == 0

    def test_to_dict_keys(self):
        r = self._make(["fn_a"], ["fn_b"], ["fn_a"])
        d = r.to_dict()
        assert "reachable_functions" in d
        assert "unreachable_functions" in d
        assert "entry_points" in d
        assert "file_path" in d

    def test_to_dict_values_are_sorted_lists(self):
        r = self._make(["b", "a"], ["d", "c"])
        d = r.to_dict()
        assert d["reachable_functions"] == ["a", "b"]
        assert d["unreachable_functions"] == ["c", "d"]


# ── Flask fixture ─────────────────────────────────────────────────────────────


class TestFlaskFixture:
    @pytest.fixture(autouse=True)
    def result(self):
        self.r = _analyze("flask_app.py")

    def test_entry_point_detected(self):
        assert "vuln_route" in self.r.entry_points

    def test_reachable_functions(self):
        for fn in ("vuln_route", "process_input", "execute_query"):
            assert self.r.is_function_reachable(fn), f"{fn} should be reachable"

    def test_unreachable_functions(self):
        for fn in ("orphan_function", "dead_helper"):
            assert not self.r.is_function_reachable(fn), f"{fn} should be unreachable"

    def test_unreachable_have_penalty(self):
        for fn in ("orphan_function", "dead_helper"):
            assert self.r.penalty_for(fn) == -20

    def test_reachable_have_no_penalty(self):
        assert self.r.penalty_for("execute_query") == 0


# ── Standalone (__main__) fixture ─────────────────────────────────────────────


class TestStandaloneFixture:
    @pytest.fixture(autouse=True)
    def result(self):
        self.r = _analyze("standalone.py")

    def test_main_is_entry_point(self):
        assert "main" in self.r.entry_points

    def test_reachable_functions(self):
        for fn in ("main", "called_from_main"):
            assert self.r.is_function_reachable(fn), f"{fn} should be reachable"

    def test_unreachable_functions(self):
        for fn in ("never_called", "also_dead"):
            assert not self.r.is_function_reachable(fn), f"{fn} should be unreachable"

    def test_unreachable_penalty(self):
        assert self.r.penalty_for("also_dead") == -20


# ── Celery fixture ────────────────────────────────────────────────────────────


class TestCeleryFixture:
    @pytest.fixture(autouse=True)
    def result(self):
        self.r = _analyze("celery_tasks.py")

    def test_task_is_entry_point(self):
        assert "process_job" in self.r.entry_points

    def test_reachable_functions(self):
        for fn in ("process_job", "task_helper"):
            assert self.r.is_function_reachable(fn), f"{fn} should be reachable"

    def test_unreachable_functions(self):
        assert not self.r.is_function_reachable("orphan_task_helper")

    def test_unreachable_penalty(self):
        assert self.r.penalty_for("orphan_task_helper") == -20


# ── Internal helpers ──────────────────────────────────────────────────────────


class TestDetectEntryPoints:
    def test_flask_route_decorator(self):
        code = """
from flask import Flask
app = Flask(__name__)

@app.route("/")
def index(): pass

def helper(): pass
"""
        eps = _detect_entry_points(code)
        assert "index" in eps
        assert "helper" not in eps

    def test_main_block(self):
        code = """
def main(): pass
def unused(): pass

if __name__ == "__main__":
    main()
"""
        eps = _detect_entry_points(code)
        assert "main" in eps

    def test_celery_task_decorator(self):
        code = """
from celery import Celery
app = Celery()

@app.task
def run_job(): pass

def dead(): pass
"""
        eps = _detect_entry_points(code)
        assert "run_job" in eps
        assert "dead" not in eps

    def test_fastapi_route_decorator(self):
        code = """
from fastapi import FastAPI
app = FastAPI()

@app.get("/items")
async def list_items(): pass

def internal(): pass
"""
        eps = _detect_entry_points(code)
        assert "list_items" in eps
        assert "internal" not in eps

    def test_empty_file(self):
        assert _detect_entry_points("") == set()

    def test_no_entry_points(self):
        code = "def helper(): return 1\ndef another(): return 2\n"
        assert _detect_entry_points(code) == set()


class TestBuildCallGraph:
    def test_direct_call(self):
        code = """
def a():
    b()

def b():
    pass
"""
        graph = _build_call_graph(code)
        assert "b" in graph.get("a", set())

    def test_chained_calls(self):
        code = """
def a():
    b()

def b():
    c()

def c():
    pass
"""
        graph = _build_call_graph(code)
        assert "b" in graph["a"]
        assert "c" in graph["b"]

    def test_no_calls(self):
        code = """
def isolated():
    x = 1
    return x
"""
        graph = _build_call_graph(code)
        assert graph.get("isolated", set()) == set()

    def test_returns_dict(self):
        graph = _build_call_graph("def f(): pass\n")
        assert isinstance(graph, dict)


# ── Engine integration ────────────────────────────────────────────────────────


class TestCallGraphReachabilityEngine:
    def test_analyze_returns_result(self, tmp_path):
        f = tmp_path / "simple.py"
        f.write_text("def a(): b()\ndef b(): pass\n")
        r = CallGraphReachability().analyze(str(f))
        assert isinstance(r, CallGraphResult)

    def test_analyze_nonexistent_file_raises(self):
        with pytest.raises(FileNotFoundError):
            CallGraphReachability().analyze("/nonexistent/file.py")

    def test_analyze_syntax_error_raises(self, tmp_path):
        f = tmp_path / "bad.py"
        f.write_text("def (broken:")
        with pytest.raises(SyntaxError):
            CallGraphReachability().analyze(str(f))

    def test_apply_to_finding_reachable(self, tmp_path):
        f = tmp_path / "app.py"
        f.write_text(
            "from flask import Flask\napp = Flask(__name__)\n"
            "@app.route('/')\ndef index(): helper()\n"
            "def helper(): pass\n"
        )
        engine = CallGraphReachability()
        result = engine.apply_to_finding(str(f), function_name="helper", finding={"confidence_score": 80})
        assert result["confidence_score"] == 80
        assert result.get("reachability_status") == "REACHABLE"

    def test_apply_to_finding_unreachable(self, tmp_path):
        f = tmp_path / "app.py"
        f.write_text(
            "from flask import Flask\napp = Flask(__name__)\n"
            "@app.route('/')\ndef index(): pass\n"
            "def dead(): pass\n"
        )
        engine = CallGraphReachability()
        result = engine.apply_to_finding(str(f), function_name="dead", finding={"confidence_score": 80})
        assert result["confidence_score"] == 60
        assert result.get("reachability_status") == "UNREACHABLE"

    def test_apply_to_finding_no_entry_points(self, tmp_path):
        # File with no entry points — all functions treated as potentially reachable
        f = tmp_path / "lib.py"
        f.write_text("def helper(): pass\ndef another(): pass\n")
        engine = CallGraphReachability()
        result = engine.apply_to_finding(str(f), function_name="helper", finding={"confidence_score": 70})
        assert result["confidence_score"] == 70
        assert result.get("reachability_status") == "UNKNOWN"

    def test_apply_to_finding_none_function(self, tmp_path):
        f = tmp_path / "app.py"
        f.write_text("@app.route('/')\ndef index(): pass\n")
        engine = CallGraphReachability()
        result = engine.apply_to_finding(str(f), function_name=None, finding={"confidence_score": 50})
        assert result["confidence_score"] == 50
