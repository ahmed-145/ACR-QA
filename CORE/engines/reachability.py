"""
ACR-QA Feature 9 — Call Graph Reachability Engine
Performs static call graph analysis to identify unreachable functions and
reduce false positives by penalising findings in dead code.

Entry-point detection:
    Flask/FastAPI routes  — @app.route / @app.get / @app.post / @router.*
    __main__ blocks       — functions called directly under if __name__ == "__main__"
    Celery tasks          — @app.task / @celery_app.task / @shared_task

Confidence penalty for unreachable findings: -20 points
"""

from __future__ import annotations

import ast
from collections import deque
from dataclasses import dataclass, field
from pathlib import Path

_ROUTE_ATTRS = frozenset({"route", "get", "post", "put", "patch", "delete", "head", "options"})
_TASK_ATTRS = frozenset({"task", "shared_task"})

_UNREACHABLE_PENALTY = -20


@dataclass
class CallGraphResult:
    file_path: str
    reachable: set[str] = field(default_factory=set)
    unreachable: set[str] = field(default_factory=set)
    entry_points: list[str] = field(default_factory=list)

    def is_function_reachable(self, func_name: str) -> bool:
        if func_name in self.reachable:
            return True
        if func_name in self.unreachable:
            return False
        return True  # unknown → safe default (do not penalise)

    def penalty_for(self, func_name: str | None) -> int:
        if func_name is None:
            return 0
        if func_name in self.unreachable:
            return _UNREACHABLE_PENALTY
        return 0

    def to_dict(self) -> dict:
        return {
            "file_path": self.file_path,
            "entry_points": sorted(self.entry_points),
            "reachable_functions": sorted(self.reachable),
            "unreachable_functions": sorted(self.unreachable),
        }


def _is_route_decorator(node: ast.expr) -> bool:
    """Return True if the decorator looks like a route/endpoint decorator."""
    if isinstance(node, ast.Call):
        node = node.func
    if isinstance(node, ast.Attribute):
        return node.attr in _ROUTE_ATTRS
    return False


def _is_task_decorator(node: ast.expr) -> bool:
    """Return True if the decorator looks like a Celery task decorator."""
    if isinstance(node, ast.Call):
        node = node.func
    if isinstance(node, ast.Attribute):
        return node.attr in _TASK_ATTRS
    if isinstance(node, ast.Name):
        return node.id in _TASK_ATTRS
    return False


def _detect_entry_points(source: str) -> set[str]:
    """
    Parse *source* and return names of functions that are entry points:
    Flask/FastAPI routes, Celery tasks, or functions called in __main__.
    """
    if not source.strip():
        return set()

    try:
        tree = ast.parse(source)
    except SyntaxError:
        return set()

    entry_points: set[str] = set()

    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef):
            for dec in node.decorator_list:
                if _is_route_decorator(dec) or _is_task_decorator(dec):
                    entry_points.add(node.name)
                    break

        # Functions called directly inside `if __name__ == "__main__":` blocks
        if isinstance(node, ast.If):
            test = node.test
            is_main = (
                isinstance(test, ast.Compare)
                and isinstance(test.left, ast.Name)
                and test.left.id == "__name__"
                and len(test.ops) == 1
                and isinstance(test.ops[0], ast.Eq)
                and len(test.comparators) == 1
                and isinstance(test.comparators[0], ast.Constant)
                and test.comparators[0].value == "__main__"
            )
            if is_main:
                for stmt in ast.walk(node):
                    if isinstance(stmt, ast.Call):
                        if isinstance(stmt.func, ast.Name):
                            entry_points.add(stmt.func.id)

    return entry_points


def _build_call_graph(source: str) -> dict[str, set[str]]:
    """
    Return a mapping of function_name → set of function names it calls directly.
    Only tracks calls to names defined in the same file (simple name calls).
    """
    graph: dict[str, set[str]] = {}

    try:
        tree = ast.parse(source)
    except SyntaxError:
        return graph

    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef):
            calls: set[str] = set()
            for child in ast.walk(node):
                if child is node:
                    continue
                if isinstance(child, ast.Call):
                    if isinstance(child.func, ast.Name):
                        calls.add(child.func.id)
                    elif isinstance(child.func, ast.Attribute):
                        # e.g. self.helper() — record the attribute name too
                        calls.add(child.func.attr)
            graph[node.name] = calls

    return graph


def _all_function_names(source: str) -> set[str]:
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return set()
    names: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef):
            names.add(node.name)
    return names


def _reachable_from(entry_points: set[str], graph: dict[str, set[str]]) -> set[str]:
    """BFS from entry points through the call graph."""
    visited: set[str] = set()
    queue: deque[str] = deque(entry_points)
    while queue:
        fn = queue.popleft()
        if fn in visited:
            continue
        visited.add(fn)
        for callee in graph.get(fn, set()):
            if callee not in visited:
                queue.append(callee)
    return visited


def get_function_at_line(source: str, line: int) -> str | None:
    """
    Return the name of the innermost function definition that contains *line*.
    Returns None if the line is at module level or the source is unparseable.
    """
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return None

    best: ast.FunctionDef | ast.AsyncFunctionDef | None = None
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef):
            end_line = getattr(node, "end_lineno", node.lineno)
            if node.lineno <= line <= end_line:
                # Pick the innermost (highest start line)
                if best is None or node.lineno > best.lineno:
                    best = node

    return best.name if best else None


class CallGraphReachability:
    """Static call graph analyser for a single Python file."""

    def analyze(self, file_path: str) -> CallGraphResult:
        path = Path(file_path)
        if not path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")

        source = path.read_text(encoding="utf-8")
        # Let SyntaxError propagate — callers should know the file is unparseable
        ast.parse(source)

        all_fns = _all_function_names(source)
        entry_pts = _detect_entry_points(source)
        graph = _build_call_graph(source)

        reachable = _reachable_from(entry_pts, graph) & all_fns

        if entry_pts:
            unreachable = all_fns - reachable
        else:
            # No entry points detected (library file) — treat everything as unknown
            unreachable = set()

        return CallGraphResult(
            file_path=file_path,
            reachable=reachable,
            unreachable=unreachable,
            entry_points=sorted(entry_pts & all_fns),
        )

    def apply_to_finding(
        self,
        file_path: str,
        function_name: str | None,
        finding: dict,
    ) -> dict:
        """
        Analyse *file_path* and adjust *finding*'s confidence score based on
        whether *function_name* is reachable. Returns a new dict (does not mutate).
        """
        result = dict(finding)

        try:
            cg = self.analyze(file_path)
        except (FileNotFoundError, SyntaxError):
            result["reachability_status"] = "UNKNOWN"
            return result

        if not cg.entry_points:
            result["reachability_status"] = "UNKNOWN"
            return result

        if function_name is None:
            result["reachability_status"] = "UNKNOWN"
            return result

        if cg.is_function_reachable(function_name) and function_name not in cg.unreachable:
            result["reachability_status"] = "REACHABLE"
        else:
            result["reachability_status"] = "UNREACHABLE"
            penalty = cg.penalty_for(function_name)
            result["confidence_score"] = result.get("confidence_score", 0) + penalty

        return result

    def enrich_findings(
        self,
        findings: list[dict],
        target_dir: str | None = None,
    ) -> list[dict]:
        """
        Enrich a list of pipeline findings with reachability status and penalty.
        Only Python files are analysed; non-Python findings pass through as UNKNOWN.
        Per-file analysis is cached — each file is parsed at most once.
        """
        cg_cache: dict[str, CallGraphResult | None] = {}
        src_cache: dict[str, str] = {}
        enriched: list[dict] = []

        for finding in findings:
            file_path = finding.get("file_path") or finding.get("file", "")

            if not file_path or not file_path.endswith(".py"):
                enriched.append({**finding, "reachability_status": "UNKNOWN"})
                continue

            # Resolve to absolute path when target_dir is given
            abs_path = file_path
            if target_dir and not Path(file_path).is_absolute():
                abs_path = str(Path(target_dir) / file_path)

            # Parse + analyse the file once
            if abs_path not in cg_cache:
                try:
                    cg_cache[abs_path] = self.analyze(abs_path)
                    src_cache[abs_path] = Path(abs_path).read_text(encoding="utf-8")
                except (FileNotFoundError, SyntaxError):
                    cg_cache[abs_path] = None
                    src_cache[abs_path] = ""

            cg = cg_cache[abs_path]
            if cg is None or not cg.entry_points:
                enriched.append({**finding, "reachability_status": "UNKNOWN"})
                continue

            # Locate the containing function from the finding's line number
            line = int(finding.get("line_number") or finding.get("line") or 0)
            func_name = get_function_at_line(src_cache[abs_path], line) if line else None

            result = dict(finding)
            if func_name is None:
                result["reachability_status"] = "UNKNOWN"
                result["reachability_penalty"] = 0
            elif func_name in cg.unreachable:
                result["reachability_status"] = "UNREACHABLE"
                result["reachability_penalty"] = _UNREACHABLE_PENALTY
                result["confidence_score"] = max(0, int(result.get("confidence_score") or 50) + _UNREACHABLE_PENALTY)
            else:
                result["reachability_status"] = "REACHABLE"
                result["reachability_penalty"] = 0

            enriched.append(result)

        return enriched
