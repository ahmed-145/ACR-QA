"""
Severity Scoring Engine for ACR-QA v2.0
Maps canonical rule IDs to severity levels following PRD guidelines
"""

from typing import Dict, Any

class SeverityScorer:
    """
    Assigns severity based on canonical rule ID and context
    
    Severity Guidelines (from PRD):
    - HIGH: Security vulnerabilities, crashes, data loss risks
    - MEDIUM: Design smells, maintainability issues, performance problems
    - LOW: Style violations, minor best practices
    """
    
    # Canonical Rule ID → Base Severity Mapping
    RULE_SEVERITY = {
        # HIGH: Security & Critical Bugs
        'SECURITY-001': 'high',      # eval() usage
        'SECURITY-002': 'high',      # SQL injection
        'SECURITY-003': 'high',      # XSS vulnerabilities
        'SECURITY-004': 'high',      # Unsafe deserialization
        'SECURITY-005': 'high',      # Hardcoded secrets
        
        # MEDIUM: Design & Maintainability
        'SOLID-001': 'medium',       # Too many parameters
        'COMPLEXITY-001': 'medium',  # High cyclomatic complexity
        'DUP-001': 'medium',         # Code duplication
        'PATTERN-001': 'medium',     # Mutable default arguments
        'DEAD-001': 'low',           # Unused code (low unless large)
        
        # LOW: Style & Minor Issues
        'IMPORT-001': 'low',         # Unused imports
        'VAR-001': 'low',            # Unused variables
        'STYLE-001': 'low',          # Line too long
        'STYLE-002': 'low',          # Missing docstring
        'NAMING-001': 'low',         # Bad naming
    }
    
    # Context-based severity adjustments
    COMPLEXITY_THRESHOLDS = {
        'high': 20,      # CC > 20 = high severity
        'medium': 10,    # CC > 10 = medium severity
        'low': 0         # CC <= 10 = low severity
    }
    
    def __init__(self):
        pass
    
    def score(self, canonical_rule_id: str, finding_dict: Dict[str, Any]) -> str:
        """
        Determine severity for a finding
        
        Args:
            canonical_rule_id: Canonical rule ID (e.g., "SECURITY-001")
            finding_dict: Full finding dictionary with context
            
        Returns:
            Severity string: "high", "medium", or "low"
        """
        # Get base severity from rule mapping
        base_severity = self.RULE_SEVERITY.get(canonical_rule_id, 'low')
        
        # Apply context-based adjustments
        severity = self._apply_context_adjustments(
            base_severity, 
            canonical_rule_id, 
            finding_dict
        )
        
        return severity
    
    def _apply_context_adjustments(
        self, 
        base_severity: str, 
        canonical_rule_id: str, 
        finding: Dict[str, Any]
    ) -> str:
        """Apply context-specific severity adjustments"""
        
        # COMPLEXITY-001: Adjust based on actual complexity value
        if canonical_rule_id == 'COMPLEXITY-001':
            complexity = self._extract_complexity(finding)
            
            if complexity and complexity > self.COMPLEXITY_THRESHOLDS['high']:
                return 'high'
            elif complexity and complexity > self.COMPLEXITY_THRESHOLDS['medium']:
                return 'medium'
            else:
                return 'low'
        
        # DEAD-001: Large unused functions are medium priority
        if canonical_rule_id == 'DEAD-001':
            message = finding.get('message', '').lower()
            
            # Check if it's a large unused class or function
            if 'class' in message:
                return 'medium'  # Unused classes = medium
            elif 'function' in message and len(finding.get('evidence', {}).get('snippet', '')) > 100:
                return 'medium'  # Large unused functions = medium
        
        # DUP-001: Large duplications are higher priority
        if canonical_rule_id == 'DUP-001':
            tokens = self._extract_duplication_size(finding)
            
            if tokens and tokens > 200:
                return 'high'   # Massive duplication = high
            elif tokens and tokens > 100:
                return 'medium'
        
        # Default: use base severity
        return base_severity
    
    def _extract_complexity(self, finding: Dict[str, Any]) -> int:
        """Extract cyclomatic complexity from Radon output"""
        try:
            raw_output = finding.get('tool_raw', {}).get('original_output', {})
            return raw_output.get('complexity', 0)
        except:
            # Fallback: parse from message
            message = finding.get('message', '')
            if 'complexity of ' in message:
                try:
                    # Extract "complexity of 15" → 15
                    parts = message.split('complexity of ')
                    if len(parts) > 1:
                        complexity_str = parts[1].split('.')[0].split()[0]
                        return int(complexity_str)
                except:
                    pass
            return 0
    
    def _extract_duplication_size(self, finding: Dict[str, Any]) -> int:
        """Extract token count from duplication finding"""
        try:
            raw_output = finding.get('tool_raw', {}).get('original_output', {})
            return raw_output.get('tokens', 0)
        except:
            # Fallback: parse from message
            message = finding.get('message', '')
            if 'tokens' in message:
                try:
                    # Extract "50 tokens" → 50
                    parts = message.split('tokens')
                    if len(parts) > 0:
                        token_str = parts[0].split()[-1]
                        return int(token_str)
                except:
                    pass
            return 0
    
    def get_severity_priority(self, severity: str) -> int:
        """
        Get numeric priority for sorting (lower = higher priority)
        Used for ordering PR comments and dashboard views
        """
        priority_map = {
            'high': 1,
            'medium': 2,
            'low': 3
        }
        return priority_map.get(severity, 99)


# Convenience function for quick scoring
def score_severity(canonical_rule_id: str, finding_dict: Dict[str, Any]) -> str:
    """Quick severity scoring without instantiating scorer"""
    scorer = SeverityScorer()
    return scorer.score(canonical_rule_id, finding_dict)


# Test the scorer
if __name__ == '__main__':
    print("Testing Severity Scorer...\n")
    
    scorer = SeverityScorer()
    
    # Test cases
    test_cases = [
        {
            'name': 'High Complexity (CC=25)',
            'rule_id': 'COMPLEXITY-001',
            'finding': {
                'message': 'Function has cyclomatic complexity of 25',
                'tool_raw': {'original_output': {'complexity': 25}}
            },
            'expected': 'high'
        },
        {
            'name': 'Medium Complexity (CC=15)',
            'rule_id': 'COMPLEXITY-001',
            'finding': {
                'message': 'Function has cyclomatic complexity of 15',
                'tool_raw': {'original_output': {'complexity': 15}}
            },
            'expected': 'medium'
        },
        {
            'name': 'Security Issue',
            'rule_id': 'SECURITY-001',
            'finding': {'message': 'Dangerous eval() usage'},
            'expected': 'high'
        },
        {
            'name': 'Too Many Parameters',
            'rule_id': 'SOLID-001',
            'finding': {'message': 'Function has 8 parameters'},
            'expected': 'medium'
        },
        {
            'name': 'Unused Import',
            'rule_id': 'IMPORT-001',
            'finding': {'message': 'Unused import: os'},
            'expected': 'low'
        },
        {
            'name': 'Large Duplication',
            'rule_id': 'DUP-001',
            'finding': {
                'message': 'Duplicate code: 250 tokens',
                'tool_raw': {'original_output': {'tokens': 250}}
            },
            'expected': 'high'
        }
    ]
    
    passed = 0
    failed = 0
    
    for test in test_cases:
        result = scorer.score(test['rule_id'], test['finding'])
        status = "✓" if result == test['expected'] else "✗"
        
        if result == test['expected']:
            passed += 1
        else:
            failed += 1
        
        print(f"{status} {test['name']}")
        print(f"   Rule: {test['rule_id']}")
        print(f"   Expected: {test['expected']}, Got: {result}")
        print()
    
    print(f"Results: {passed} passed, {failed} failed")