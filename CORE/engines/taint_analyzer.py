"""Inter-procedural taint analysis engine.

Tracks user-controlled data from HTTP/env sources to dangerous sinks.
Supports cross-function propagation (call-graph taint) and sanitizer
recognition to reduce false positives.
"""

from __future__ import annotations

import ast
import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

logger = logging.getLogger(__name__)

_CONFIG_DIR = Path(__file__).parent.parent.parent / "config"


def _load_sources() -> list[dict]:
    path = _CONFIG_DIR / "taint_sources.yml"
    with open(path) as f:
        return yaml.safe_load(f)["sources"]


def _load_sinks() -> list[dict]:
    path = _CONFIG_DIR / "taint_sinks.yml"
    with open(path) as f:
        return yaml.safe_load(f)["sinks"]


def _load_sanitizers() -> set[str]:
    """Return the set of all sanitizer pattern strings."""
    path = _CONFIG_DIR / "taint_sanitizers.yml"
    try:
        with open(path) as f:
            raw = yaml.safe_load(f)
        patterns: set[str] = set()
        for entry in raw.get("sanitizers", []):
            for p in entry.get("patterns", []):
                patterns.add(p)
                # Also index by bare function name for quick suffix matching
                patterns.add(p.rsplit(".", 1)[-1])
        return patterns
    except FileNotFoundError:
        return set()


@dataclass
class TaintInfo:
    source: str
    steps: list[str] = field(default_factory=list)

    def hop(self, step: str) -> TaintInfo:
        return TaintInfo(source=self.source, steps=self.steps + [step])


class _FunctionTaintVisitor(ast.NodeVisitor):
    """Intra-procedural taint visitor (one function scope)."""

    def __init__(
        self,
        source_patterns: set[str],
        sinks_by_name: dict[str, dict],
        filepath: str,
        sanitizer_patterns: set[str] | None = None,
        call_graph: dict[str, ast.FunctionDef | ast.AsyncFunctionDef] | None = None,
        initial_tainted: dict[str, TaintInfo] | None = None,
        depth: int = 0,
    ) -> None:
        self._source_patterns = source_patterns
        self._sinks = sinks_by_name
        self._sanitizer_patterns = sanitizer_patterns if sanitizer_patterns is not None else set()
        self._filepath = filepath
        # Call graph: local function name → AST node (for inter-procedural)
        self._call_graph = call_graph or {}
        # Functions whose return value is tainted (from internal sources)
        self._taint_returning: set[str] = set()
        # Recursion depth guard (prevents infinite loops on recursive calls)
        self._depth = depth
        # variable name → TaintInfo
        self._tainted: dict[str, TaintInfo] = dict(initial_tainted or {})
        self.findings: list[dict] = []

    # ── source detection ──────────────────────────────────────────────────────

    def _extract_source(self, node: ast.expr) -> TaintInfo | None:
        """Return TaintInfo if node is a taint source, else None."""
        if isinstance(node, ast.Attribute):
            full = self._attr_chain(node)
            for pat in self._source_patterns:
                if full == pat or full.startswith(pat + "."):
                    return TaintInfo(source=pat, steps=[ast.unparse(node)])

        if isinstance(node, ast.Subscript):
            # request.form["key"] — subscript access on a source object
            inner = self._extract_source(node.value)
            if inner:
                return inner.hop(ast.unparse(node))

        if isinstance(node, ast.Call):
            func = node.func
            if isinstance(func, ast.Attribute):
                full = self._attr_chain(func)
                for pat in self._source_patterns:
                    if full == pat or full.startswith(pat + "."):
                        return TaintInfo(source=pat, steps=[ast.unparse(node)])
            # os.getenv as bare name after `from os import getenv`
            if isinstance(func, ast.Name) and func.id == "getenv":
                return TaintInfo(source="os.environ", steps=[ast.unparse(node)])
        return None

    @staticmethod
    def _attr_chain(node: ast.expr) -> str:
        parts: list[str] = []
        while isinstance(node, ast.Attribute):
            parts.append(node.attr)
            node = node.value
        if isinstance(node, ast.Name):
            parts.append(node.id)
        return ".".join(reversed(parts))

    # ── propagation ───────────────────────────────────────────────────────────

    def _propagate(self, node: ast.expr) -> TaintInfo | None:
        """Return TaintInfo if node carries taint from a tracked variable."""
        if isinstance(node, ast.Name):
            return self._tainted.get(node.id)

        if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Add | ast.Mod):
            left = self._propagate(node.left)
            right = self._propagate(node.right)
            if left:
                return left.hop(ast.unparse(node))
            if right:
                return right.hop(ast.unparse(node))

        if isinstance(node, ast.JoinedStr):
            for part in ast.walk(node):
                if isinstance(part, ast.Name):
                    t = self._tainted.get(part.id)
                    if t:
                        return t.hop(ast.unparse(node))

        if isinstance(node, ast.Call):
            # If this is a sanitizer call, drop taint regardless of args
            if self._is_sanitizer(node.func):
                return None
            # Function known to return taint from its own internal sources
            func_name: str | None = None
            if isinstance(node.func, ast.Name):
                func_name = node.func.id
            elif isinstance(node.func, ast.Attribute):
                func_name = node.func.attr
            if func_name and func_name in self._taint_returning:
                return TaintInfo(source=f"{func_name}()", steps=[ast.unparse(node)])
            # method call on a tainted object: tainted_var.strip()
            if isinstance(node.func, ast.Attribute):
                base = self._propagate(node.func.value)
                if base:
                    return base.hop(ast.unparse(node))
            # tainted arg passed through benign function: str(tainted)
            for arg in node.args:
                t = self._propagate(arg)
                if t:
                    return t.hop(ast.unparse(node))

        if isinstance(node, ast.Subscript):
            t = self._propagate(node.value)
            if t:
                return t.hop(ast.unparse(node))

        if isinstance(node, ast.IfExp):
            t = self._propagate(node.body) or self._propagate(node.orelse)
            if t:
                return t

        return None

    # ── visitors ──────────────────────────────────────────────────────────────

    def visit_Assign(self, node: ast.Assign) -> None:
        taint = self._extract_source(node.value) or self._propagate(node.value)
        for target in node.targets:
            if isinstance(target, ast.Name):
                if taint:
                    self._tainted[target.id] = taint.hop(ast.unparse(node))
                else:
                    self._tainted.pop(target.id, None)
        self.generic_visit(node)

    def visit_AugAssign(self, node: ast.AugAssign) -> None:
        taint = self._propagate(node.value)
        if taint and isinstance(node.target, ast.Name):
            existing = self._tainted.get(node.target.id)
            base = existing or taint
            self._tainted[node.target.id] = base.hop(ast.unparse(node))
        self.generic_visit(node)

    def visit_AnnAssign(self, node: ast.AnnAssign) -> None:
        if node.value is not None:
            taint = self._extract_source(node.value) or self._propagate(node.value)
            if isinstance(node.target, ast.Name):
                if taint:
                    self._tainted[node.target.id] = taint.hop(ast.unparse(node))
                else:
                    self._tainted.pop(node.target.id, None)
        self.generic_visit(node)

    def visit_Call(self, node: ast.Call) -> None:
        sink_name = self._get_sink_name(node.func)
        if sink_name and sink_name in self._sinks:
            for arg in node.args:
                taint = self._extract_source(arg) or self._propagate(arg)
                if taint:
                    self._emit_finding(node, sink_name, taint)
            for kw in node.keywords:
                if kw.value is not None:
                    taint = self._extract_source(kw.value) or self._propagate(kw.value)
                    if taint:
                        self._emit_finding(node, sink_name, taint)
        else:
            # Inter-procedural: if tainted args are passed to a local function,
            # recurse into that function to find transitive sink hits.
            tainted_args = []
            for arg in node.args:
                t = self._extract_source(arg) or self._propagate(arg)
                if t:
                    tainted_args.append(t)
            if tainted_args and self._depth < 5:
                result = self._resolve_interprocedural(node, tainted_args)
                # If callee propagates taint to return, mark call result as tainted
                if result is not None:
                    # Assign to a synthetic variable for subsequent propagation
                    self._tainted[f"__ret_{ast.unparse(node.func)}"] = result
        self.generic_visit(node)

    def _is_sanitizer(self, func: ast.expr) -> bool:
        """Return True if this call is a known sanitizer that drops taint."""
        if isinstance(func, ast.Name):
            return func.id in self._sanitizer_patterns
        if isinstance(func, ast.Attribute):
            chain = self._attr_chain(func)
            # Match full chain (e.g. "html.escape") or bare name (e.g. "escape")
            return chain in self._sanitizer_patterns or func.attr in self._sanitizer_patterns
        return False

    def _resolve_interprocedural(self, node: ast.Call, tainted_args: list[TaintInfo]) -> TaintInfo | None:
        """
        If the call targets a locally-defined function and we have tainted args,
        re-analyze that function with the tainted parameters to check for sink
        hits inside it. Returns TaintInfo if the callee propagates taint to
        its return value (conservative approximation).
        """
        if self._depth >= 5:
            # Depth guard: treat deep calls as opaque taint propagators
            return tainted_args[0].hop(f"→ {ast.unparse(node)} [depth limit]") if tainted_args else None

        func_name: str | None = None
        if isinstance(node.func, ast.Name):
            func_name = node.func.id
        elif isinstance(node.func, ast.Attribute):
            func_name = node.func.attr

        if func_name is None or func_name not in self._call_graph:
            return None

        callee = self._call_graph[func_name]
        # Map positional args to parameter names
        params = [arg.arg for arg in callee.args.args]
        initial: dict[str, TaintInfo] = {}
        for i, t in enumerate(tainted_args):
            if i < len(params):
                initial[params[i]] = t.hop(f"{func_name}({params[i]})")

        if not initial:
            return None

        # Recurse into callee
        sub = _FunctionTaintVisitor(
            source_patterns=self._source_patterns,
            sinks_by_name=self._sinks,
            filepath=self._filepath,
            sanitizer_patterns=self._sanitizer_patterns,
            call_graph=self._call_graph,
            initial_tainted=initial,
            depth=self._depth + 1,
        )
        sub._taint_returning = self._taint_returning
        sub.visit(callee)
        # Collect sink findings from callee
        self.findings.extend(sub.findings)

        # Check if callee returns taint (conservative: yes if any return stmt propagates)
        for child in ast.walk(callee):
            if isinstance(child, ast.Return) and child.value is not None:
                if sub._propagate(child.value) is not None:
                    return tainted_args[0].hop(f"return {func_name}()")
        return None

    def _get_sink_name(self, func: ast.expr) -> str | None:
        if isinstance(func, ast.Name):
            return func.id if func.id in self._sinks else None
        if isinstance(func, ast.Attribute):
            # cursor.execute → "execute"; subprocess.run → "subprocess"
            if func.attr in self._sinks:
                return func.attr
            chain = self._attr_chain(func)
            for name in self._sinks:
                if chain.startswith(name):
                    return name
        return None

    def _emit_finding(self, node: ast.Call, sink_name: str, taint: TaintInfo) -> None:
        sink_meta = self._sinks[sink_name]
        hops = len(taint.steps)
        path = taint.steps + [f"→ {ast.unparse(node)}"]
        self.findings.append(
            {
                "tool": "taint_analyzer",
                "canonical_rule_id": sink_meta["canonical_rule_id"],
                "cwe": sink_meta["cwe"],
                "severity": sink_meta["severity"],
                "file": self._filepath,
                "line": node.lineno,
                "message": (
                    f"Taint flow detected: {taint.source} → {sink_name}() " f"({hops} hop{'s' if hops != 1 else ''})"
                ),
                "taint_source": taint.source,
                "taint_path": path,
                "taint_confidence": max(0.4, 0.95 - 0.1 * max(0, hops - 1)),
            }
        )


def _build_call_graph(
    tree: ast.AST,
) -> dict[str, ast.FunctionDef | ast.AsyncFunctionDef]:
    """Build a map of function names to their AST nodes."""
    graph: dict[str, ast.FunctionDef | ast.AsyncFunctionDef] = {}
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef):
            graph[node.name] = node
    return graph


def _compute_taint_returning_functions(
    call_graph: dict[str, ast.FunctionDef | ast.AsyncFunctionDef],
    source_patterns: set[str],
    sinks_by_name: dict[str, dict],
    sanitizer_patterns: set[str],
    filepath: str,
) -> set[str]:
    """Pre-analysis pass: identify functions that return a tainted value.

    These functions produce taint from internal sources (e.g. request.args)
    even when called with no tainted arguments. Used by the inter-procedural
    visitor to mark call-site return values as tainted.
    """
    taint_returning: set[str] = set()
    for func_name, func_node in call_graph.items():
        sub = _FunctionTaintVisitor(
            source_patterns=source_patterns,
            sinks_by_name=sinks_by_name,
            filepath=filepath,
            sanitizer_patterns=sanitizer_patterns,
            call_graph={},  # flat — no recursion in summary pass
            depth=99,  # prevent further inter-procedural calls
        )
        sub.visit(func_node)
        # Check every return statement: does the returned value carry taint?
        for child in ast.walk(func_node):
            if isinstance(child, ast.Return) and child.value is not None:
                tainted = sub._extract_source(child.value) or sub._propagate(child.value)
                if tainted is not None:
                    taint_returning.add(func_name)
                    break
    return taint_returning


class TaintAnalyzer:
    """Public interface: analyze a file or directory for taint flows.

    Supports inter-procedural analysis (taint across function calls) and
    sanitizer recognition (drops taint at bleach.clean, shlex.quote, etc.).
    """

    def __init__(self) -> None:
        sources = _load_sources()
        self._source_patterns: set[str] = set()
        for s in sources:
            self._source_patterns.update(s["patterns"])

        sinks_raw = _load_sinks()
        self._sinks_by_name: dict[str, dict] = {s["name"]: s for s in sinks_raw}

        self._sanitizer_patterns: set[str] = _load_sanitizers()

    def analyze_file(self, filepath: str | Path) -> list[dict[str, Any]]:
        filepath = Path(filepath)
        try:
            source = filepath.read_text(encoding="utf-8", errors="replace")
            tree = ast.parse(source, filename=str(filepath))
        except SyntaxError:
            return []

        # Build call graph + function summaries for inter-procedural analysis
        call_graph = _build_call_graph(tree)
        taint_returning = _compute_taint_returning_functions(
            call_graph,
            self._source_patterns,
            self._sinks_by_name,
            self._sanitizer_patterns,
            str(filepath),
        )

        all_findings: list[dict] = []
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef):
                visitor = _FunctionTaintVisitor(
                    source_patterns=self._source_patterns,
                    sinks_by_name=self._sinks_by_name,
                    filepath=str(filepath),
                    sanitizer_patterns=self._sanitizer_patterns,
                    call_graph=call_graph,
                    depth=0,
                )
                visitor._taint_returning = taint_returning
                visitor.visit(node)
                all_findings.extend(visitor.findings)

        # deduplicate within file: same line + rule
        seen: set[tuple] = set()
        unique: list[dict] = []
        for f in all_findings:
            key = (f["file"], f["line"], f["canonical_rule_id"])
            if key not in seen:
                seen.add(key)
                unique.append(f)
        return unique

    def analyze_directory(self, target_dir: str | Path) -> list[dict[str, Any]]:
        target_dir = Path(target_dir)
        findings: list[dict] = []
        for py_file in target_dir.rglob("*.py"):
            try:
                findings.extend(self.analyze_file(py_file))
            except Exception as err:
                logger.debug(f"Taint analysis skipped {py_file}: {err}")
        return findings

    def enrich_findings(
        self,
        findings: list[dict[str, Any]],
        target_dir: str | Path,
    ) -> list[dict[str, Any]]:
        """Generate new taint findings and merge with existing pipeline findings."""
        new_findings = self.analyze_directory(target_dir)
        if new_findings:
            logger.info(f"      - Taint Analyzer: {len(new_findings)} taint flow(s) detected")
        return findings + new_findings
