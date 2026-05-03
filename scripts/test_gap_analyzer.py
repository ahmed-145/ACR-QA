#!/usr/bin/env python3
"""
ACR-QA Test Gap Analyzer
Identifies source functions/classes that lack corresponding test coverage.
No competitor does this well — this is a market differentiator.

Usage:
    python scripts/test_gap_analyzer.py --target CORE/
    python scripts/test_gap_analyzer.py --target CORE/ --test-dir TESTS/
    python scripts/test_gap_analyzer.py --target CORE/ --format json
"""

import argparse
import ast
import json
import logging
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path

logger = logging.getLogger(__name__)

sys.path.insert(0, str(Path(__file__).parent.parent))

from CORE import __version__  # noqa: E402

# ─── Data Models ──────────────────────────────────────────────────────────


@dataclass
class SourceSymbol:
    """A function or class defined in source code."""

    name: str
    qualified_name: str  # e.g., "QualityGate.evaluate"
    file_path: str
    line: int
    kind: str  # "function" or "class"
    is_private: bool
    is_dunder: bool
    complexity: str = "unknown"  # simple/medium/complex based on line count


@dataclass
class TestMapping:
    """Maps a source symbol to its test coverage status."""

    symbol: SourceSymbol
    is_tested: bool = False
    test_file: str = ""
    test_functions: list = field(default_factory=list)


# ─── AST Extraction ──────────────────────────────────────────────────────


def extract_symbols(file_path: str) -> list[SourceSymbol]:
    """
    Extract all functions and classes from a Python file using AST.

    Returns:
        List of SourceSymbol objects
    """
    try:
        with open(file_path, encoding="utf-8", errors="ignore") as f:
            source = f.read()
    except (OSError, UnicodeDecodeError):
        return []

    try:
        tree = ast.parse(source, filename=file_path)
    except SyntaxError:
        return []

    symbols = []

    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef) or isinstance(node, ast.AsyncFunctionDef):
            # Check if it's a method inside a class
            parent_class = _find_parent_class(tree, node)
            if parent_class:
                qualified = f"{parent_class}.{node.name}"
            else:
                qualified = node.name

            # Estimate complexity
            body_lines = (node.end_lineno or node.lineno) - node.lineno
            if body_lines <= 5:
                complexity = "simple"
            elif body_lines <= 20:
                complexity = "medium"
            else:
                complexity = "complex"

            symbols.append(
                SourceSymbol(
                    name=node.name,
                    qualified_name=qualified,
                    file_path=str(file_path),
                    line=node.lineno,
                    kind="function",
                    is_private=node.name.startswith("_") and not node.name.startswith("__"),
                    is_dunder=node.name.startswith("__") and node.name.endswith("__"),
                    complexity=complexity,
                )
            )

        elif isinstance(node, ast.ClassDef):
            symbols.append(
                SourceSymbol(
                    name=node.name,
                    qualified_name=node.name,
                    file_path=str(file_path),
                    line=node.lineno,
                    kind="class",
                    is_private=node.name.startswith("_"),
                    is_dunder=False,
                    complexity="complex",
                )
            )

    return symbols


def _find_parent_class(tree: ast.Module, target_node: ast.AST) -> str | None:
    """Find the parent class name for a method node."""
    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef):
            for child in ast.walk(node):
                if child is target_node:
                    return node.name
    return None


# ─── Test Discovery ──────────────────────────────────────────────────────


def discover_test_symbols(test_dir: str) -> dict[str, set[str]]:
    """
    Discover all test functions and what they reference.

    Returns:
        Dict of { test_file: set of referenced names }
    """
    test_map = {}
    test_path = Path(test_dir)

    if not test_path.exists():
        return test_map

    for test_file in test_path.rglob("test_*.py"):
        try:
            with open(test_file, encoding="utf-8", errors="ignore") as f:
                source = f.read()
        except (OSError, UnicodeDecodeError):
            continue

        try:
            tree = ast.parse(source, filename=str(test_file))
        except SyntaxError:
            continue

        # Collect all names referenced in the test file
        referenced = set()

        for node in ast.walk(tree):
            # Capture test function names (test_calculate_foo → "calculate_foo")
            if isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef):
                if node.name.startswith("test_"):
                    # Extract the subject: test_calculate_total → calculate_total
                    subject = node.name[5:]  # Remove "test_"
                    referenced.add(subject)
                    # Also try the full test name
                    referenced.add(node.name)

            # Capture class names referenced in test classes
            # e.g., TestQualityGate → QualityGate
            if isinstance(node, ast.ClassDef):
                if node.name.startswith("Test"):
                    subject_class = node.name[4:]  # Remove "Test"
                    referenced.add(subject_class)

                    # Also extract method subjects within test classes
                    for item in node.body:
                        if isinstance(item, ast.FunctionDef | ast.AsyncFunctionDef):
                            if item.name.startswith("test_"):
                                referenced.add(item.name[5:])

            # Capture direct function calls
            if isinstance(node, ast.Call):
                if isinstance(node.func, ast.Name):
                    referenced.add(node.func.id)
                elif isinstance(node.func, ast.Attribute):
                    referenced.add(node.func.attr)

            # Capture imports from source modules
            if isinstance(node, ast.ImportFrom):
                if node.names:
                    for alias in node.names:
                        referenced.add(alias.name)

        # Also do a simple text search for function/class names
        # This catches references in strings, comments, and fixtures
        words = set(re.findall(r"\b([A-Za-z_][A-Za-z0-9_]*)\b", source))
        referenced.update(words)

        test_map[str(test_file)] = referenced

    return test_map


# ─── Gap Analysis ─────────────────────────────────────────────────────────


def analyze_gaps(
    target_dir: str,
    test_dir: str,
    include_private: bool = False,
    include_dunder: bool = False,
) -> list[TestMapping]:
    """
    Analyze test coverage gaps for source code.

    Args:
        target_dir: Directory containing source code
        test_dir: Directory containing test files
        include_private: Include _private functions
        include_dunder: Include __dunder__ methods

    Returns:
        List of TestMapping objects
    """
    target_path = Path(target_dir)
    mappings = []

    # Discover all test references
    test_symbols = discover_test_symbols(test_dir)
    all_test_refs = set()
    for refs in test_symbols.values():
        all_test_refs.update(refs)

    # Scan source files
    for source_file in target_path.rglob("*.py"):
        # Skip test files, __init__, __pycache__
        rel = str(source_file.relative_to(target_path))
        if rel.startswith("test_") or "/__pycache__/" in str(source_file) or "__pycache__" in rel:
            continue

        symbols = extract_symbols(str(source_file))

        for sym in symbols:
            # Filter private/dunder
            if sym.is_private and not include_private:
                continue
            if sym.is_dunder and not include_dunder:
                continue

            # Check if this symbol is tested
            is_tested = False
            matching_tests = []

            # Check multiple naming conventions
            check_names = {
                sym.name,
                sym.name.lower(),
                sym.qualified_name,
                sym.qualified_name.replace(".", "_"),
            }

            # For class methods, also check method name alone
            if "." in sym.qualified_name:
                method_name = sym.qualified_name.split(".")[-1]
                check_names.add(method_name)

            for test_file, refs in test_symbols.items():
                # Normalize references to lowercase for comparison
                lower_refs = {r.lower() for r in refs}

                for name in check_names:
                    if name.lower() in lower_refs:
                        is_tested = True
                        matching_tests.append(test_file)
                        break

            mappings.append(
                TestMapping(
                    symbol=sym,
                    is_tested=is_tested,
                    test_file=matching_tests[0] if matching_tests else "",
                    test_functions=matching_tests,
                )
            )

    return mappings


# ─── Report Generation ────────────────────────────────────────────────────


def generate_report(mappings: list[TestMapping], format: str = "text") -> str:
    """Generate a test gap report."""
    untested = [m for m in mappings if not m.is_tested]
    tested = [m for m in mappings if m.is_tested]
    total = len(mappings)

    if format == "json":
        return json.dumps(
            {
                "version": __version__,
                "total_symbols": total,
                "tested": len(tested),
                "untested": len(untested),
                "coverage_pct": round(len(tested) / total * 100, 1) if total > 0 else 0,
                "gaps": [
                    {
                        "name": m.symbol.qualified_name,
                        "file": m.symbol.file_path,
                        "line": m.symbol.line,
                        "kind": m.symbol.kind,
                        "complexity": m.symbol.complexity,
                    }
                    for m in untested
                ],
                "tested_symbols": [
                    {
                        "name": m.symbol.qualified_name,
                        "file": m.symbol.file_path,
                        "test_file": m.test_file,
                    }
                    for m in tested
                ],
            },
            indent=2,
        )

    # Text report
    lines = []
    coverage_pct = round(len(tested) / total * 100, 1) if total > 0 else 0

    lines.append(f"📊 ACR-QA Test Gap Analysis Report (v{__version__})")
    lines.append("=" * 65)
    lines.append(f"  Total symbols: {total}")
    lines.append(f"  Tested:        {len(tested)} ✅")
    lines.append(f"  Untested:      {len(untested)} ❌")
    lines.append(f"  Coverage:      {coverage_pct}%")
    lines.append("")

    if not untested:
        lines.append("🎉 All public symbols have test coverage!")
        return "\n".join(lines)

    # Group untested by file
    by_file: dict[str, list[TestMapping]] = {}
    for m in untested:
        by_file.setdefault(m.symbol.file_path, []).append(m)

    lines.append("─" * 65)
    lines.append("Untested Symbols:")
    lines.append("")

    for file_path in sorted(by_file.keys()):
        items = by_file[file_path]
        lines.append(f"  📁 {file_path}")

        for m in sorted(items, key=lambda x: x.symbol.line):
            icon = "🔶" if m.symbol.complexity == "complex" else "🔸"
            lines.append(
                f"    {icon} {m.symbol.kind} {m.symbol.qualified_name} "
                f"(line {m.symbol.line}, {m.symbol.complexity})"
            )

        lines.append("")

    # Priority recommendations
    complex_untested = [m for m in untested if m.symbol.complexity == "complex"]
    if complex_untested:
        lines.append("─" * 65)
        lines.append("⚠️  Priority: Complex untested symbols (test these first):")
        for m in complex_untested[:10]:
            lines.append(f"  🔴 {m.symbol.qualified_name} in {m.symbol.file_path}")

    lines.append("")
    return "\n".join(lines)


# ─── API Data (for Flask endpoint) ────────────────────────────────────────


def get_test_gap_data(target_dir: str = ".", test_dir: str = "TESTS") -> dict:
    """
    Get test gap data for the Flask API endpoint.

    Returns:
        Dict with gap analysis data
    """
    mappings = analyze_gaps(target_dir, test_dir)
    untested = [m for m in mappings if not m.is_tested]
    tested = [m for m in mappings if m.is_tested]
    total = len(mappings)

    return {
        "total_symbols": total,
        "tested": len(tested),
        "untested": len(untested),
        "coverage_pct": round(len(tested) / total * 100, 1) if total > 0 else 0,
        "gaps": [
            {
                "name": m.symbol.qualified_name,
                "file": m.symbol.file_path,
                "line": m.symbol.line,
                "kind": m.symbol.kind,
                "complexity": m.symbol.complexity,
            }
            for m in untested
        ],
        "priority_gaps": [
            {
                "name": m.symbol.qualified_name,
                "file": m.symbol.file_path,
                "line": m.symbol.line,
            }
            for m in untested
            if m.symbol.complexity == "complex"
        ][:10],
    }


# ─── Quality Gate Integration ─────────────────────────────────────────────


def check_test_gap_gate(
    target_dir: str,
    test_dir: str,
    max_untested: int = 10,
    max_complex_untested: int = 0,
) -> dict:
    """
    Quality gate check for test coverage gaps.

    Args:
        max_untested: Maximum allowed untested public symbols
        max_complex_untested: Maximum allowed untested complex symbols
    """
    mappings = analyze_gaps(target_dir, test_dir)
    untested = [m for m in mappings if not m.is_tested]
    complex_untested = [m for m in untested if m.symbol.complexity == "complex"]

    checks = []

    untested_ok = len(untested) <= max_untested
    checks.append(
        {
            "name": "Untested Symbols",
            "passed": untested_ok,
            "actual": len(untested),
            "threshold": max_untested,
            "message": f"{len(untested)} untested symbols (max: {max_untested})",
        }
    )

    complex_ok = len(complex_untested) <= max_complex_untested
    checks.append(
        {
            "name": "Complex Untested",
            "passed": complex_ok,
            "actual": len(complex_untested),
            "threshold": max_complex_untested,
            "message": f"{len(complex_untested)} complex untested symbols (max: {max_complex_untested})",
        }
    )

    passed = all(c["passed"] for c in checks)

    return {
        "passed": passed,
        "status": "✅ PASSED" if passed else "❌ FAILED",
        "checks": checks,
    }


# ─── Main CLI ─────────────────────────────────────────────────────────────


def main():
    parser = argparse.ArgumentParser(description="ACR-QA Test Gap Analyzer — find untested code")
    parser.add_argument("--target", "-t", default="CORE/", help="Target source directory to analyze (default: CORE/)")
    parser.add_argument("--test-dir", "-d", default="TESTS/", help="Test directory to search (default: TESTS/)")
    parser.add_argument("--format", "-f", choices=["text", "json"], default="text", help="Output format")
    parser.add_argument("--include-private", action="store_true", help="Include _private functions in analysis")
    parser.add_argument("--include-dunder", action="store_true", help="Include __dunder__ methods in analysis")
    parser.add_argument("--gate", action="store_true", help="Run as quality gate check (exit 1 if failed)")
    parser.add_argument("--max-untested", type=int, default=10, help="Quality gate: max untested symbols (default: 10)")
    parser.add_argument(
        "--max-complex-untested", type=int, default=0, help="Quality gate: max complex untested symbols (default: 0)"
    )
    args = parser.parse_args()

    if args.gate:
        result = check_test_gap_gate(
            args.target,
            args.test_dir,
            max_untested=args.max_untested,
            max_complex_untested=args.max_complex_untested,
        )
        logger.info(f"\n🚦 Test Gap Gate: {result['status']}")
        for c in result["checks"]:
            icon = "✅" if c["passed"] else "❌"
            logger.info(f"  {icon} {c['message']}")

        if not result["passed"]:
            sys.exit(1)
    else:
        mappings = analyze_gaps(
            args.target,
            args.test_dir,
            include_private=args.include_private,
            include_dunder=args.include_dunder,
        )
        report = generate_report(mappings, format=args.format)
        logger.info(report)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    main()
