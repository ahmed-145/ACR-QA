"""
Universal Finding Normalizer for ACR-QA v2.0
Converts tool-specific outputs to canonical schema
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))


import uuid
import json
from typing import Dict, Any, List, Optional
from pathlib import Path

# Universal Rule Mapping: Tool-specific → Canonical
RULE_MAPPING = {
    # Ruff rules → Universal IDs
    'F401': 'IMPORT-001',           # Unused import
    'F841': 'VAR-001',              # Unused variable
    'PLR0913': 'SOLID-001',         # Too many parameters
    'B006': 'PATTERN-001',          # Mutable default argument
    'E501': 'STYLE-001',            # Line too long
    'D100': 'STYLE-002',            # Missing docstring (module)
    'D101': 'STYLE-002',            # Missing docstring (class)
    'D102': 'STYLE-002',            # Missing docstring (method)
    'D103': 'STYLE-002',            # Missing docstring (function)
    'N801': 'NAMING-001',           # Bad class name
    'N802': 'NAMING-001',           # Bad function name
    'N803': 'NAMING-001',           # Bad argument name
    'N806': 'NAMING-001',           # Bad variable name
    
    # Semgrep rules → Universal IDs
    'dangerous-eval-usage': 'SECURITY-001',
    'mutable-default-argument': 'PATTERN-001',
    
    # Vulture → Universal IDs  
    'unused-code': 'DEAD-001',
    'unused-import': 'IMPORT-001',
    'unused-variable': 'VAR-001',
    'unused-function': 'DEAD-001',
    'unused-class': 'DEAD-001',
    
    # jscpd → Universal IDs
    'code-duplication': 'DUP-001'
}

# Severity Mapping: Tool-specific → Canonical (high/medium/low)
SEVERITY_MAPPING = {
    'error': 'high',
    'warning': 'medium',
    'info': 'low',
    # Semgrep
    'ERROR': 'high',
    'WARNING': 'medium',
    'INFO': 'low'
}

# Category Mapping
CATEGORY_MAPPING = {
    'security': 'security',
    'best-practice': 'best-practice',
    'style-or-practice': 'style',
    'style': 'style',
    'dead-code': 'dead-code',
    'duplication': 'duplication',
    'design': 'design'
}


class CanonicalFinding:
    """Universal finding format following ACR-QA canonical schema"""
    
    def __init__(self,
                 rule_id: str,
                 file: str,
                 line: int,
                 severity: str,
                 category: str,
                 message: str,
                 tool_name: str,
                 tool_output: Dict[str, Any],
                 column: int = 0):
        
        self.finding_id = str(uuid.uuid4())
        
        # Map to canonical rule ID
        self.canonical_rule_id = RULE_MAPPING.get(rule_id, f"CUSTOM-{rule_id}")
        self.original_rule_id = rule_id
        
        # Map to canonical severity
        self.severity = SEVERITY_MAPPING.get(severity, 'low')
        self.original_severity = severity
        
        # Map to canonical category
        self.category = CATEGORY_MAPPING.get(category, category)
        
        self.file = file
        self.line = line
        self.column = column
        self.language = self._detect_language(file)
        self.message = message
        
        # Evidence (will be filled by extract_evidence method)
        self.evidence = {
            'snippet': '',
            'context_before': [],
            'context_after': []
        }
        
        # Preserve original for audit
        self.tool_raw = {
            'tool_name': tool_name,
            'original_rule_id': rule_id,
            'original_severity': severity,
            'original_output': tool_output
        }
    
    def _detect_language(self, file_path: str) -> str:
        """Detect language from file extension"""
        ext = Path(file_path).suffix.lower()
        language_map = {
            '.py': 'python',
            '.js': 'javascript',
            '.ts': 'typescript',
            '.java': 'java',
            '.cpp': 'cpp',
            '.c': 'c',
            '.go': 'go',
            '.rs': 'rust',
            '.rb': 'ruby',
            '.php': 'php',
            '.sh': 'shell'
        }
        return language_map.get(ext, 'unknown')
    
    def extract_evidence(self, context_lines: int = 3):
        """Extract code snippet and context"""
        try:
            from CORE.utils.code_extractor import extract_code_snippet
            
            # Get snippet with context
            full_snippet = extract_code_snippet(self.file, self.line, context_lines)
            
            # Parse snippet into parts
            lines = full_snippet.split('\n')
            
            context_before = []
            context_after = []
            snippet = ''
            
            for line in lines:
                if '>>>' in line:
                    # This is the issue line
                    snippet = line.split('|', 1)[1].strip() if '|' in line else line
                elif '|' in line:
                    line_num_str, code = line.split('|', 1)
                    line_num = int(line_num_str.strip())
                    
                    if line_num < self.line:
                        context_before.append(code.rstrip())
                    elif line_num > self.line:
                        context_after.append(code.rstrip())
            
            self.evidence = {
                'snippet': snippet,
                'context_before': context_before[-3:] if context_before else [],  # Last 3
                'context_after': context_after[:3] if context_after else []        # First 3
            }
            
        except Exception as e:
            # Fallback: just use the message
            self.evidence = {
                'snippet': f'# Line {self.line}',
                'context_before': [],
                'context_after': []
            }
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization"""
        return {
            'finding_id': self.finding_id,
            'canonical_rule_id': self.canonical_rule_id,
            'original_rule_id': self.original_rule_id,
            'severity': self.severity,
            'category': self.category,
            'file': self.file,
            'line': self.line,
            'column': self.column,
            'language': self.language,
            'message': self.message,
            'evidence': self.evidence,
            'tool_raw': self.tool_raw
        }


def normalize_ruff(ruff_json: List[Dict]) -> List[CanonicalFinding]:
    """Convert Ruff findings to canonical format"""
    findings = []
    
    for item in ruff_json:
        finding = CanonicalFinding(
            rule_id=item.get('code', 'UNKNOWN'),
            file=item.get('filename', 'unknown'),
            line=item.get('location', {}).get('row', 0),
            column=item.get('location', {}).get('column', 0),
            severity='warning',  # Ruff doesn't specify severity
            category='style',
            message=item.get('message', ''),
            tool_name='ruff',
            tool_output=item
        )
        finding.extract_evidence()
        findings.append(finding)
    
    return findings


def normalize_semgrep(semgrep_json: Dict) -> List[CanonicalFinding]:
    """Convert Semgrep findings to canonical format"""
    findings = []
    
    results = semgrep_json.get('results', [])
    
    for item in results:
        # Extract rule ID from check_id (e.g., "services.semgrep.dangerous-eval-usage")
        check_id = item.get('check_id', '')
        rule_id = check_id.split('.')[-1] if '.' in check_id else check_id
        
        finding = CanonicalFinding(
            rule_id=rule_id,
            file=item.get('path', 'unknown'),
            line=item.get('start', {}).get('line', 0),
            column=item.get('start', {}).get('col', 0),
            severity=item.get('extra', {}).get('severity', 'WARNING'),
            category=item.get('extra', {}).get('metadata', {}).get('category', 'security'),
            message=item.get('extra', {}).get('message', ''),
            tool_name='semgrep',
            tool_output=item
        )
        finding.extract_evidence()
        findings.append(finding)
    
    return findings


def normalize_vulture(vulture_txt: str) -> List[CanonicalFinding]:
    """Convert Vulture text output to canonical format"""
    findings = []
    
    for line in vulture_txt.strip().split('\n'):
        if not line or line.startswith('#'):
            continue
        
        # Format: filepath:line: message (confidence%)
        parts = line.split(':', 2)
        if len(parts) < 3:
            continue
        
        filepath = parts[0].strip()
        try:
            lineno = int(parts[1].strip())
        except ValueError:
            lineno = 0
        
        message = parts[2].strip()
        
        # Determine rule type from message
        rule_id = 'unused-code'
        if 'import' in message.lower():
            rule_id = 'unused-import'
        elif 'variable' in message.lower():
            rule_id = 'unused-variable'
        elif 'function' in message.lower():
            rule_id = 'unused-function'
        elif 'class' in message.lower():
            rule_id = 'unused-class'
        
        finding = CanonicalFinding(
            rule_id=rule_id,
            file=filepath,
            line=lineno,
            column=0,
            severity='info',
            category='dead-code',
            message=message,
            tool_name='vulture',
            tool_output={'raw_line': line}
        )
        finding.extract_evidence()
        findings.append(finding)
    
    return findings


def normalize_jscpd(jscpd_json: Dict) -> List[CanonicalFinding]:
    """Convert jscpd findings to canonical format"""
    findings = []
    
    duplicates = jscpd_json.get('duplicates', [])
    
    for dup in duplicates:
        first_file = dup.get('firstFile', {})
        second_file = dup.get('secondFile', {})
        
        message = (
            f"Duplicate code block: {dup.get('lines', 0)} lines, "
            f"{dup.get('tokens', 0)} tokens. "
            f"Also found in {second_file.get('name', 'unknown')} "
            f"at line {second_file.get('start', 0)}"
        )
        
        finding = CanonicalFinding(
            rule_id='code-duplication',
            file=first_file.get('name', 'unknown'),
            line=first_file.get('start', 0),
            column=0,
            severity='info',
            category='duplication',
            message=message,
            tool_name='jscpd',
            tool_output=dup
        )
        finding.extract_evidence()
        findings.append(finding)
    
    return findings


def normalize_all(outputs_dir: str = 'outputs') -> List[CanonicalFinding]:
    """
    Load and normalize all tool outputs from directory
    
    Args:
        outputs_dir: Directory containing tool output files
        
    Returns:
        List of CanonicalFinding objects
    """
    all_findings = []
    outputs_path = Path(outputs_dir)
    
    # Load and normalize Ruff
    ruff_file = outputs_path / 'ruff.json'
    if ruff_file.exists():
        try:
            with open(ruff_file) as f:
                content = f.read().strip()
                if content:  # Only parse if not empty
                    ruff_data = json.loads(content)
                    all_findings.extend(normalize_ruff(ruff_data))
                    print(f"  Normalized {len(normalize_ruff(ruff_data))} Ruff findings")
        except json.JSONDecodeError:
            print(f"  Warning: Could not parse {ruff_file}")
        except Exception as e:
            print(f"  Error processing Ruff: {e}")
    
    # Load and normalize Semgrep
    semgrep_file = outputs_path / 'semgrep.json'
    if semgrep_file.exists():
        try:
            with open(semgrep_file) as f:
                semgrep_data = json.load(f)
                semgrep_findings = normalize_semgrep(semgrep_data)
                all_findings.extend(semgrep_findings)
                print(f"  Normalized {len(semgrep_findings)} Semgrep findings")
        except Exception as e:
            print(f"  Error processing Semgrep: {e}")
    
    # Load and normalize Vulture
    vulture_file = outputs_path / 'vulture.txt'
    if vulture_file.exists():
        try:
            with open(vulture_file) as f:
                vulture_data = f.read()
                vulture_findings = normalize_vulture(vulture_data)
                all_findings.extend(vulture_findings)
                print(f"  Normalized {len(vulture_findings)} Vulture findings")
        except Exception as e:
            print(f"  Error processing Vulture: {e}")
    
    # Load and normalize jscpd
    jscpd_file = outputs_path / 'jscpd.json'
    if jscpd_file.exists():
        try:
            with open(jscpd_file) as f:
                jscpd_data = json.load(f)
                jscpd_findings = normalize_jscpd(jscpd_data)
                all_findings.extend(jscpd_findings)
                print(f"  Normalized {len(jscpd_findings)} jscpd findings")
        except Exception as e:
            print(f"  Error processing jscpd: {e}")
    
    print(f"\n  Total canonical findings: {len(all_findings)}")
    return all_findings


if __name__ == '__main__':
    # Test normalization
    print("Testing normalizer...")
    findings = normalize_all()
    
    if findings:
        print(f"\nSample canonical finding:")
        print(json.dumps(findings[0].to_dict(), indent=2))