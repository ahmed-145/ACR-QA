"""
Test file demonstrating unused code
Triggers: IMPORT-001, VAR-001, DEAD-001
"""

import os  # IMPORT-001: Unused import
import sys  # IMPORT-001: Unused import
import json
from datetime import datetime


def calculate_total(items):
    """Function with unused variables"""
    total = 0
    count = 0  # VAR-001: Unused variable
    max_price = 0  # VAR-001: Unused variable
    
    for item in items:
        total += item['price']
    
    return total


def unused_helper():
    """
    DEAD-001: This function is never called
    """
    return "I'm never used!"


def another_unused_function(x, y):
    """
    DEAD-001: Another dead function
    """
    temp_var = x + y  # VAR-001: Unused variable
    return x * y


class UnusedClass:
    """
    DEAD-001: This class is never instantiated
    """
    def __init__(self):
        self.value = 42
