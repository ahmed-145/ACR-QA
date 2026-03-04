#!/usr/bin/env python3
"""
ACR-QA Auto-fix Engine
Generates code fixes for common issues
"""

import re
from typing import Dict, List, Optional


class AutoFixEngine:
    """Generate automatic fixes for common code issues"""

    def __init__(self):
        self.fixable_rules = {
            "IMPORT-001": self.fix_unused_import,
            "VAR-001": self.fix_unused_variable,
            "STRING-001": self.fix_fstring_conversion,
            "BOOL-001": self.fix_boolean_comparison,
            "TYPE-001": self.add_type_hints,
            "EXCEPT-001": self.fix_bare_except,
            "SECURITY-027": self.fix_eval_usage,
            "DEAD-001": self.fix_dead_code,
        }

    def can_fix(self, rule_id: str) -> bool:
        """Check if a rule can be auto-fixed"""
        return rule_id in self.fixable_rules

    def get_fix_confidence(self, rule_id: str) -> float:
        """Return confidence score for a fix rule (0.0-1.0)"""
        confidence_map = {
            "IMPORT-001": 0.95,  # Very reliable
            "VAR-001": 0.85,  # Reliable (underscore prefix)
            "STRING-001": 0.90,  # Reliable
            "BOOL-001": 0.95,  # Very reliable
            "TYPE-001": 0.60,  # Less reliable (type inference)
            "EXCEPT-001": 0.90,  # Reliable (except Exception)
            "SECURITY-027": 0.80,  # Reliable (eval → ast.literal_eval)
            "DEAD-001": 0.85,  # Reliable (comment out)
        }
        return confidence_map.get(rule_id, 0.5)

    def generate_fix(self, finding: Dict) -> Optional[Dict]:
        """
        Generate a fix for a finding

        Returns:
            {
                "file": str,
                "line": int,
                "original": str,
                "fixed": str,
                "description": str
            }
        """
        rule_id = finding.get("canonical_rule_id")

        if not self.can_fix(rule_id):
            return None

        fix_func = self.fixable_rules[rule_id]
        return fix_func(finding)

    def fix_unused_import(self, finding: Dict) -> Dict:
        """Remove unused import statement"""
        file_path = finding["file_path"]
        line_num = finding["line"]

        # Read file
        with open(file_path) as f:
            lines = f.readlines()

        original_line = lines[line_num - 1]

        return {
            "file": file_path,
            "line": line_num,
            "original": original_line.rstrip(),
            "fixed": "",  # Remove the line
            "description": f"Remove unused import on line {line_num}",
        }

    def fix_unused_variable(self, finding: Dict) -> Dict:
        """Remove or prefix unused variable with underscore"""
        file_path = finding["file_path"]
        line_num = finding["line"]

        with open(file_path) as f:
            lines = f.readlines()

        original_line = lines[line_num - 1]

        # Extract variable name from message (handles both quoted and unquoted forms)
        # Patterns: "variable 'x'", "unused variable x", "Local variable `x`"
        match = re.search(r"variable\s+'(\w+)'", finding["message"])
        if not match:
            match = re.search(r"variable\s+`(\w+)`", finding["message"])
        if not match:
            match = re.search(r"variable\s+(\w+)", finding["message"])
        if not match:
            return None

        var_name = match.group(1)

        # Prefix with underscore to indicate intentionally unused
        # Use regex to handle variable at any position (including start of line)
        fixed_line = re.sub(
            r"\b" + re.escape(var_name) + r"(\s*=)",
            f"_{var_name}\\1",
            original_line,
            count=1,
        )

        return {
            "file": file_path,
            "line": line_num,
            "original": original_line.rstrip(),
            "fixed": fixed_line.rstrip(),
            "description": f"Prefix unused variable '{var_name}' with underscore",
        }

    def fix_fstring_conversion(self, finding: Dict) -> Dict:
        """Convert % formatting to f-strings"""
        file_path = finding["file_path"]
        line_num = finding["line"]

        with open(file_path) as f:
            lines = f.readlines()

        original_line = lines[line_num - 1]

        # Simple conversion: "text %s" % var -> f"text {var}"
        # This is a simplified version
        match = re.search(r'"([^"]*%s[^"]*)" % (\w+)', original_line)
        if match:
            template, var = match.groups()
            fixed_template = template.replace("%s", f"{{{var}}}")
            fixed_line = original_line.replace(match.group(0), f'f"{fixed_template}"')

            return {
                "file": file_path,
                "line": line_num,
                "original": original_line.rstrip(),
                "fixed": fixed_line.rstrip(),
                "description": "Convert % formatting to f-string",
            }

        return None

    def fix_boolean_comparison(self, finding: Dict) -> Dict:
        """Simplify boolean comparisons"""
        file_path = finding["file_path"]
        line_num = finding["line"]

        with open(file_path) as f:
            lines = f.readlines()

        original_line = lines[line_num - 1]

        # if x == True: -> if x:
        # if x == False: -> if not x:
        fixed_line = original_line
        fixed_line = re.sub(r"if (\w+) == True:", r"if \1:", fixed_line)
        fixed_line = re.sub(r"if (\w+) == False:", r"if not \1:", fixed_line)

        if fixed_line != original_line:
            return {
                "file": file_path,
                "line": line_num,
                "original": original_line.rstrip(),
                "fixed": fixed_line.rstrip(),
                "description": "Simplify boolean comparison",
            }

        return None

    def add_type_hints(self, finding: Dict) -> Dict:
        """Add basic type hints to function"""
        file_path = finding["file_path"]
        line_num = finding["line"]

        with open(file_path) as f:
            lines = f.readlines()

        original_line = lines[line_num - 1]

        # Simple case: def func(param): -> def func(param: Any):
        if "def " in original_line and ":" in original_line:
            # Add -> None for functions without return type
            if "->" not in original_line:
                fixed_line = original_line.replace("):", ") -> None:")

                return {
                    "file": file_path,
                    "line": line_num,
                    "original": original_line.rstrip(),
                    "fixed": fixed_line.rstrip(),
                    "description": "Add return type hint",
                }

        return None

    def fix_bare_except(self, finding: Dict) -> Dict:
        """Replace bare except with except Exception"""
        file_path = finding["file_path"]
        line_num = finding["line"]

        with open(file_path) as f:
            lines = f.readlines()

        original_line = lines[line_num - 1]

        # Replace bare "except:" with "except Exception:"
        if re.search(r"^\s*except\s*:", original_line):
            fixed_line = re.sub(r"except\s*:", "except Exception:", original_line)

            return {
                "file": file_path,
                "line": line_num,
                "original": original_line.rstrip(),
                "fixed": fixed_line.rstrip(),
                "description": "Replace bare except with except Exception",
            }

        return None

    def fix_eval_usage(self, finding: Dict) -> Dict:
        """Replace eval() with ast.literal_eval() for safer evaluation"""
        file_path = finding["file_path"]
        line_num = finding["line"]

        with open(file_path) as f:
            lines = f.readlines()

        original_line = lines[line_num - 1]

        # Replace eval( with ast.literal_eval(
        if "eval(" in original_line and "literal_eval" not in original_line:
            fixed_line = original_line.replace("eval(", "ast.literal_eval(")

            return {
                "file": file_path,
                "line": line_num,
                "original": original_line.rstrip(),
                "fixed": fixed_line.rstrip(),
                "description": "Replace eval() with ast.literal_eval() for safety",
            }

        return None

    def fix_dead_code(self, finding: Dict) -> Dict:
        """Remove dead/unreachable code"""
        file_path = finding["file_path"]
        line_num = finding["line"]

        with open(file_path) as f:
            lines = f.readlines()

        original_line = lines[line_num - 1]

        # Mark dead code line for removal
        return {
            "file": file_path,
            "line": line_num,
            "original": original_line.rstrip(),
            "fixed": "",  # Empty = remove line
            "description": f"Remove dead/unreachable code",
        }


def apply_fixes(fixes: List[Dict]) -> Dict[str, List[str]]:
    """
    Apply fixes to files

    Returns:
        Dict mapping file paths to list of changes made
    """
    changes_by_file = {}

    for fix in fixes:
        file_path = fix["file"]

        # Read file
        with open(file_path) as f:
            lines = f.readlines()

        # Apply fix
        line_idx = fix["line"] - 1

        if fix["fixed"] == "":
            # Remove line
            lines.pop(line_idx)
        else:
            # Replace line
            lines[line_idx] = fix["fixed"] + "\n"

        # Write back
        with open(file_path, "w") as f:
            f.writelines(lines)

        # Track changes
        if file_path not in changes_by_file:
            changes_by_file[file_path] = []
        changes_by_file[file_path].append(fix["description"])

    return changes_by_file


def verify_fix(fix_result: Dict) -> Dict:
    """
    N3: Fix Verification Testing

    After autofix generates a fix, re-run the linting tool on the fixed code
    to verify the issue is actually resolved.

    Args:
        fix_result: Dict from generate_fix() with 'file', 'line', 'original', 'fixed'

    Returns:
        Dict with verification result: 'verified' (bool), 'remaining_issues' (list)
    """
    import subprocess
    import tempfile
    import os

    filepath = fix_result.get("file", "")
    line = fix_result.get("line", 0)
    original = fix_result.get("original", "")
    fixed = fix_result.get("fixed", "")

    if not filepath or not os.path.exists(filepath):
        return {"verified": False, "error": "File not found", "remaining_issues": []}

    try:
        # Read original file
        with open(filepath) as f:
            lines = f.readlines()

        # Apply fix to temp copy
        temp_lines = lines.copy()
        line_idx = line - 1
        if 0 <= line_idx < len(temp_lines):
            if fixed == "":
                temp_lines.pop(line_idx)
            else:
                temp_lines[line_idx] = fixed + "\n"

        # Write to temp file
        suffix = os.path.splitext(filepath)[1] or ".py"
        with tempfile.NamedTemporaryFile(mode="w", suffix=suffix, delete=False) as tmp:
            tmp.writelines(temp_lines)
            tmp_path = tmp.name

        # Run ruff on temp file
        try:
            result = subprocess.run(
                ["ruff", "check", tmp_path, "--output-format=json", "--quiet"],
                capture_output=True,
                text=True,
                timeout=10,
            )
            import json

            issues = json.loads(result.stdout) if result.stdout.strip() else []

            # Check if the specific rule is still flagged at the same line
            remaining = [i for i in issues if i.get("location", {}).get("row") == line]

            return {
                "verified": len(remaining) == 0,
                "total_remaining_issues": len(issues),
                "same_line_issues": len(remaining),
                "remaining_issues": remaining[:5],
            }
        except subprocess.TimeoutExpired:
            return {"verified": False, "error": "Verification timed out"}
        finally:
            os.unlink(tmp_path)

    except Exception as e:
        return {"verified": False, "error": str(e), "remaining_issues": []}


if __name__ == "__main__":
    # Example usage
    engine = AutoFixEngine()

    # Test finding
    finding = {
        "canonical_rule_id": "IMPORT-001",
        "file_path": "test.py",
        "line": 5,
        "message": "Unused import 'os'",
    }

    fix = engine.generate_fix(finding)
    if fix:
        print(f"Generated fix: {fix}")
        verification = verify_fix(fix)
        print(f"Verification: {verification}")
