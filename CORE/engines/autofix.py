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
        }
    
    def can_fix(self, rule_id: str) -> bool:
        """Check if a rule can be auto-fixed"""
        return rule_id in self.fixable_rules
    
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
            "description": f"Remove unused import on line {line_num}"
        }
    
    def fix_unused_variable(self, finding: Dict) -> Dict:
        """Remove or prefix unused variable with underscore"""
        file_path = finding["file_path"]
        line_num = finding["line"]
        
        with open(file_path) as f:
            lines = f.readlines()
        
        original_line = lines[line_num - 1]
        
        # Extract variable name from message
        match = re.search(r"variable '(\w+)'", finding["message"])
        if not match:
            return None
        
        var_name = match.group(1)
        
        # Prefix with underscore to indicate intentionally unused
        fixed_line = original_line.replace(f" {var_name} =", f" _{var_name} =")
        
        return {
            "file": file_path,
            "line": line_num,
            "original": original_line.rstrip(),
            "fixed": fixed_line.rstrip(),
            "description": f"Prefix unused variable '{var_name}' with underscore"
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
                "description": "Convert % formatting to f-string"
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
        fixed_line = re.sub(r'if (\w+) == True:', r'if \1:', fixed_line)
        fixed_line = re.sub(r'if (\w+) == False:', r'if not \1:', fixed_line)
        
        if fixed_line != original_line:
            return {
                "file": file_path,
                "line": line_num,
                "original": original_line.rstrip(),
                "fixed": fixed_line.rstrip(),
                "description": "Simplify boolean comparison"
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
                    "description": "Add return type hint"
                }
        
        return None


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


if __name__ == "__main__":
    # Example usage
    engine = AutoFixEngine()
    
    # Test finding
    finding = {
        "canonical_rule_id": "IMPORT-001",
        "file_path": "test.py",
        "line": 5,
        "message": "Unused import 'os'"
    }
    
    fix = engine.generate_fix(finding)
    if fix:
        print(f"Generated fix: {fix}")
