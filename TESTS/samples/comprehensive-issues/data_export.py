"""
Data Export Module with Dead Code
Triggers: DEAD-001, VAR-001, IMPORT-001
"""
import os  # IMPORT-001: Never used
import sys  # IMPORT-001: Never used
import json
from datetime import datetime
from typing import List, Dict


def export_users_to_csv(users: List[Dict]):
    """Active function"""
    output = []
    for user in users:
        output.append(f"{user['id']},{user['name']},{user['email']}")
    return "\n".join(output)


def unused_export_function(data):
    """
    DEAD-001: This function is never called anywhere
    """
    return json.dumps(data)


def format_user_data(user: Dict):
    """Function with unused variables"""
    user_id = user['id']  # Used
    username = user['name']  # Used
    
    created_at = user.get('created_at')  # VAR-001: Never used
    last_login = user.get('last_login')  # VAR-001: Never used
    email_verified = user.get('email_verified', False)  # VAR-001: Never used
    
    return f"{user_id}: {username}"


class UnusedExporter:
    """
    DEAD-001: This class is never instantiated
    """
    def __init__(self):
        self.format = 'json'
    
    def export(self, data):
        return json.dumps(data)


def another_dead_function(x: int, y: int) -> int:
    """
    DEAD-001: Another unused function
    """
    temp = x + y  # VAR-001: Unused variable
    result = x * y
    return result