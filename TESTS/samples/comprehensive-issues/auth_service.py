"""
Authentication Service with Multiple Issues
Triggers: SECURITY-001, SOLID-001, COMPLEXITY-001, PATTERN-001
"""
import hashlib
import sqlite3
from typing import Dict, Any, Optional, List, Tuple


def authenticate_user(username: str, password: str, email: str, phone: str,
                     session_id: str, ip_address: str, user_agent: str,
                     remember_me: bool, two_factor_code: Optional[str] = None):
    """
    SOLID-001: Too many parameters (9 parameters)
    Should use a config object or dataclass
    """
    print(f"Authenticating {username}")
    
    # SECURITY-001: SQL Injection vulnerability
    query = f"SELECT * FROM users WHERE username = '{username}' AND password = '{password}'"
    
    conn = sqlite3.connect('users.db')
    cursor = conn.cursor()
    cursor.execute(query)  # VULNERABLE!
    
    return cursor.fetchone()


def validate_and_process_user_input(data: Dict[str, Any]):
    """
    COMPLEXITY-001: Cyclomatic complexity > 20
    Too many nested conditions
    """
    if not data:
        return {'error': 'No data provided'}
    
    if 'username' not in data:
        return {'error': 'Username required'}
    else:
        username = data['username']
        if len(username) < 3:
            return {'error': 'Username too short'}
        elif len(username) > 20:
            return {'error': 'Username too long'}
        elif not username.isalnum():
            if '-' in username or '_' in username:
                pass
            else:
                return {'error': 'Invalid username characters'}
    
    if 'email' not in data:
        return {'error': 'Email required'}
    else:
        email = data['email']
        if '@' not in email:
            return {'error': 'Invalid email'}
        else:
            parts = email.split('@')
            if len(parts) != 2:
                return {'error': 'Invalid email format'}
            elif len(parts[0]) < 1:
                return {'error': 'Email username empty'}
            elif len(parts[1]) < 3:
                return {'error': 'Email domain too short'}
            elif '.' not in parts[1]:
                return {'error': 'Email domain invalid'}
    
    if 'password' in data:
        pwd = data['password']
        if len(pwd) < 8:
            return {'error': 'Password too short'}
        else:
            has_upper = False
            has_lower = False
            has_digit = False
            has_special = False
            
            for char in pwd:
                if char.isupper():
                    has_upper = True
                elif char.islower():
                    has_lower = True
                elif char.isdigit():
                    has_digit = True
                elif char in '!@#$%^&*':
                    has_special = True
            
            if not has_upper:
                return {'error': 'Password needs uppercase'}
            elif not has_lower:
                return {'error': 'Password needs lowercase'}
            elif not has_digit:
                return {'error': 'Password needs digit'}
            elif not has_special:
                return {'error': 'Password needs special char'}
    
    return {'success': True}


def store_user_sessions(session_id: str, sessions: Dict = {}):
    """
    PATTERN-001: Mutable default argument
    All calls share the same dictionary!
    """
    sessions[session_id] = True
    return sessions

# Add to any test file to trigger Ruff rules

import os  # F401: Unused import

def bad_function(x,y,z):  # Missing spaces, missing docstring
    very_long_line = "this is a very long line that exceeds 88 characters and should trigger E501 rule from Ruff linter"
    unused = 42  # F841: Unused variable
    return x+y+z

class badName:  # N801: Bad class name (should be PascalCase)
    pass

class AuthManager:
    """Authentication manager with security issues"""
    
    def validate_token(self, token: str):
        """SECURITY-001: Dangerous eval() usage"""
        # NEVER DO THIS! Allows arbitrary code execution
        result = eval(token)
        return result
    
    def hash_password(self, password: str, salt: str = "default_salt"):
        """Weak: hardcoded salt"""
        return hashlib.md5(f"{password}{salt}".encode()).hexdigest()