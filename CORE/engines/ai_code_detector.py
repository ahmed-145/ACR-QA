#!/usr/bin/env python3
"""
ACR-QA AI-Generated Code Detector
Heuristic-based detection of AI-generated code patterns
"""

import ast
import re
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).parent.parent.parent))


class AICodeDetector:
    """
    Detect patterns commonly found in AI-generated code.

    Uses heuristic signals:
    1. Generic variable names (x, y, temp, result, data, value)
    2. Overly uniform comment style
    3. Boilerplate docstrings
    4. Repetitive structure patterns
    5. Common AI code templates
    """

    # Generic names AI tends to use
    GENERIC_NAMES = {
        "data",
        "result",
        "value",
        "temp",
        "item",
        "element",
        "obj",
        "output",
        "input_data",
        "response",
        "ret",
        "val",
        "res",
        "lst",
        "arr",
        "dict_data",
        "my_list",
        "my_dict",
        "my_var",
    }

    # Boilerplate docstring phrases
    BOILERPLATE_PHRASES = [
        r"this function",
        r"this method",
        r"this class",
        r"initialize the",
        r"returns the",
        r"takes .+ as (input|parameter|argument)",
        r"args:\s*\n\s+\w+",
        r"parameters:\s*\n\s+\w+",
    ]

    # AI template patterns
    AI_PATTERNS = [
        r"# TODO: (?:implement|add|fix|update)",
        r"pass\s*#\s*(?:placeholder|stub|implement)",
        r"raise NotImplementedError\([\"\'].*not implemented[\"\']\)",
        r'print\(f?["\'](?:Debug|Error|Warning):',
    ]

    def __init__(self, threshold: float = 0.5):
        """
        Initialize detector.

        Args:
            threshold: Score threshold (0-1) above which code is flagged as AI-generated
        """
        self.threshold = threshold

    def analyze_file(self, filepath: str) -> dict[str, Any]:
        """
        Analyze a single file for AI-generated code indicators.

        Returns:
            Dict with score (0-1), signals found, and confidence level
        """
        try:
            with open(filepath, encoding="utf-8", errors="replace") as f:
                content = f.read()
        except Exception as e:
            return {"score": 0, "error": str(e), "signals": [], "confidence": "none"}

        if not content.strip():
            return {"score": 0, "signals": [], "confidence": "none"}

        signals = []
        lines = content.split("\n")

        # Signal 1: Generic variable names
        generic_score = self._check_generic_names(content)
        if generic_score > 0.3:
            signals.append(
                {
                    "type": "generic_names",
                    "score": generic_score,
                    "detail": "High usage of generic variable names",
                }
            )

        # Signal 2: Uniform comment density
        comment_score = self._check_comment_uniformity(lines)
        if comment_score > 0.4:
            signals.append(
                {
                    "type": "uniform_comments",
                    "score": comment_score,
                    "detail": "Unusually uniform comment distribution",
                }
            )

        # Signal 3: Boilerplate docstrings
        boilerplate_score = self._check_boilerplate_docs(content)
        if boilerplate_score > 0.3:
            signals.append(
                {
                    "type": "boilerplate_docs",
                    "score": boilerplate_score,
                    "detail": "Contains common AI boilerplate docstrings",
                }
            )

        # Signal 4: AI template patterns
        template_score = self._check_ai_patterns(content)
        if template_score > 0.2:
            signals.append(
                {
                    "type": "ai_templates",
                    "score": template_score,
                    "detail": "Contains patterns typical of AI-generated code",
                }
            )

        # Signal 5: Function length uniformity
        uniformity_score = self._check_function_uniformity(content, filepath)
        if uniformity_score > 0.4:
            signals.append(
                {
                    "type": "uniform_functions",
                    "score": uniformity_score,
                    "detail": "Functions have suspiciously uniform length",
                }
            )

        # Calculate overall score (weighted average)
        if signals:
            weights = {
                "generic_names": 0.2,
                "uniform_comments": 0.15,
                "boilerplate_docs": 0.25,
                "ai_templates": 0.25,
                "uniform_functions": 0.15,
            }
            total_weight = sum(weights.get(s["type"], 0.1) for s in signals)
            overall_score = sum(
                s["score"] * weights.get(s["type"], 0.1) for s in signals
            ) / max(total_weight, 0.01)
        else:
            overall_score = 0

        # Determine confidence
        if len(signals) >= 3:
            confidence = "high"
        elif len(signals) >= 2:
            confidence = "medium"
        elif len(signals) >= 1:
            confidence = "low"
        else:
            confidence = "none"

        return {
            "file": filepath,
            "score": round(overall_score, 3),
            "is_ai_generated": overall_score >= self.threshold,
            "confidence": confidence,
            "signals": signals,
            "signal_count": len(signals),
        }

    def _check_generic_names(self, content: str) -> float:
        """Check for generic variable names."""
        try:
            tree = ast.parse(content)
        except SyntaxError:
            return 0

        all_names = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Name):
                all_names.append(node.id)
            elif isinstance(node, ast.FunctionDef):
                for arg in node.args.args:
                    all_names.append(arg.arg)

        if not all_names:
            return 0

        generic_count = sum(1 for n in all_names if n.lower() in self.GENERIC_NAMES)
        return min(1.0, generic_count / max(len(all_names), 1) * 3)

    def _check_comment_uniformity(self, lines: list[str]) -> float:
        """Check if comments are suspiciously uniform in density."""
        comment_lines = [
            i for i, line in enumerate(lines) if line.strip().startswith("#")
        ]

        if len(comment_lines) < 5:
            return 0

        # Calculate gaps between comments
        gaps = [
            comment_lines[i + 1] - comment_lines[i]
            for i in range(len(comment_lines) - 1)
        ]

        if not gaps:
            return 0

        avg_gap = sum(gaps) / len(gaps)
        if avg_gap == 0:
            return 0

        # Low variance in gaps = suspicious uniformity
        variance = sum((g - avg_gap) ** 2 for g in gaps) / len(gaps)
        cv = (variance**0.5) / max(avg_gap, 0.01)  # Coefficient of variation

        # Low CV = high uniformity = suspicious
        if cv < 0.3:
            return 0.8
        elif cv < 0.5:
            return 0.5
        elif cv < 0.8:
            return 0.2
        return 0

    def _check_boilerplate_docs(self, content: str) -> float:
        """Check for boilerplate docstring patterns."""
        matches = 0
        for pattern in self.BOILERPLATE_PHRASES:
            if re.search(pattern, content, re.IGNORECASE):
                matches += 1

        return min(1.0, matches / max(len(self.BOILERPLATE_PHRASES) * 0.3, 1))

    def _check_ai_patterns(self, content: str) -> float:
        """Check for common AI code generation patterns."""
        matches = 0
        for pattern in self.AI_PATTERNS:
            found = re.findall(pattern, content, re.IGNORECASE)
            matches += len(found)

        return min(1.0, matches / 3)  # 3+ matches = max score

    def _check_function_uniformity(self, content: str, filepath: str) -> float:
        """Check if functions have suspiciously similar lengths."""
        if not filepath.endswith(".py"):
            return 0

        try:
            tree = ast.parse(content)
        except SyntaxError:
            return 0

        func_lengths = []
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef):
                end_line = getattr(node, "end_lineno", node.lineno + 5)
                length = end_line - node.lineno
                func_lengths.append(length)

        if len(func_lengths) < 3:
            return 0

        avg_len = sum(func_lengths) / len(func_lengths)
        if avg_len == 0:
            return 0

        variance = sum((l - avg_len) ** 2 for l in func_lengths) / len(func_lengths)
        cv = (variance**0.5) / max(avg_len, 0.01)

        if cv < 0.2:
            return 0.9
        elif cv < 0.4:
            return 0.5
        elif cv < 0.6:
            return 0.2
        return 0

    def analyze_directory(
        self, directory: str, extensions: list[str] = None
    ) -> dict[str, Any]:
        """
        Analyze all files in a directory.

        Args:
            directory: Path to directory
            extensions: File extensions to check (default: ['.py'])

        Returns:
            Dict with overall results and per-file analysis
        """
        if extensions is None:
            extensions = [".py"]

        dir_path = Path(directory)
        results = []

        for ext in extensions:
            for filepath in dir_path.rglob(f"*{ext}"):
                if "__pycache__" in str(filepath) or ".venv" in str(filepath):
                    continue
                result = self.analyze_file(str(filepath))
                results.append(result)

        # Overall statistics
        flagged = [r for r in results if r.get("is_ai_generated", False)]

        return {
            "directory": directory,
            "total_files": len(results),
            "flagged_files": len(flagged),
            "flagged_percentage": round(len(flagged) / max(len(results), 1) * 100, 1),
            "files": results,
        }


if __name__ == "__main__":
    detector = AICodeDetector(threshold=0.4)

    if len(sys.argv) > 1:
        target = sys.argv[1]
    else:
        target = "TESTS/samples/comprehensive-issues"

    if Path(target).is_file():
        result = detector.analyze_file(target)
        print(f"\n📊 AI Code Analysis: {target}")
        print(f"   Score: {result['score']:.1%}")
        print(f"   AI Generated: {'⚠️ Yes' if result['is_ai_generated'] else '✅ No'}")
        print(f"   Confidence: {result['confidence']}")
        for signal in result["signals"]:
            print(f"   • {signal['detail']} ({signal['score']:.1%})")
    else:
        results = detector.analyze_directory(target)
        print(f"\n📊 AI Code Analysis: {target}")
        print(f"   Files analyzed: {results['total_files']}")
        print(
            f"   Flagged: {results['flagged_files']} ({results['flagged_percentage']}%)"
        )
        for r in results["files"]:
            if r.get("is_ai_generated"):
                print(f"   ⚠️  {r['file']} — score: {r['score']:.1%}")
