"""
Unused Code Examples - Dead Code Detection

This file contains code that's defined but never used.
Vulture should detect all of these unused items.

IMPORTANT: We intentionally DON'T use any of this code!
"""

# ==============================================================================
# UNUSED IMPORTS
# ==============================================================================

# Example 1: Completely unused imports
import sys          # UNUSED: Never referenced
import json         # UNUSED: Never referenced
import datetime     # UNUSED: Never referenced
import re           # UNUSED: Never referenced
from pathlib import Path  # UNUSED: Never referenced


# Example 2: Partially unused imports
from collections import OrderedDict, defaultdict, Counter
# OrderedDict is UNUSED
# defaultdict and Counter are also UNUSED now!


# Example 3: Import with alias, never used
import numpy as np  # UNUSED: Never use 'np'
import pandas as pd  # UNUSED: Never use 'pd'


# ==============================================================================
# UNUSED VARIABLES
# ==============================================================================

# Example 4: Module-level unused variable
UNUSED_CONSTANT = "never_used anywhere"  # UNUSED
MAX_RETRIES = 5  # UNUSED
API_VERSION = "v2"  # UNUSED


# Example 5: Local unused variables in function
def calculate_total(price, quantity, tax_rate):
    """Function with unused local variables"""
    
    # Used variable
    subtotal = price * quantity
    
    # UNUSED variables
    discount = 0.10  # UNUSED: Calculated but never used
    shipping_cost = 5.99  # UNUSED: Never used
    processing_fee = 2.50  # UNUSED: Never used
    
    # Note: tax_rate parameter is also UNUSED!
    
    return subtotal


# Example 6: Multiple unused variables
def process_order():
    """Many unused variables"""
    order_id = 12345  # UNUSED
    customer_name = "John"  # UNUSED
    order_date = "2024-01-01"  # UNUSED
    status = "pending"  # UNUSED
    
    # Only this is used
    total = 100
    return total


# ==============================================================================
# UNUSED FUNCTIONS
# ==============================================================================

# Example 7: Completely unused function
def calculate_discount(price, percentage):
    """UNUSED: This function is never called"""
    return price * (percentage / 100)


# Example 8: Another unused function
def format_phone_number(phone):
    """UNUSED: Nobody calls this"""
    return f"({phone[:3]}) {phone[3:6]}-{phone[6:]}"


# Example 9: Unused helper function
def validate_email(email):
    """UNUSED: Email validation that's never used"""
    return '@' in email and '.' in email


# Example 10: Unused utility function
def reverse_string(text):
    """UNUSED: Never called anywhere"""
    return text[::-1]


# Example 11: Dead function from old code
def legacy_calculation(x, y, z):
    """UNUSED: Old function that's no longer needed"""
    result = (x + y) * z / 2
    return result


# ==============================================================================
# UNUSED CLASSES
# ==============================================================================

# Example 12: Completely unused class
class UserProfile:
    """UNUSED: This class is never instantiated"""
    def __init__(self, name, age):
        self.name = name
        self.age = age
    
    def get_info(self):
        return f"{self.name}, {self.age}"


# Example 13: Another unused class
class ShoppingCart:
    """UNUSED: Never created anywhere"""
    def __init__(self):
        self.items = []
    
    def add_item(self, item):
        self.items.append(item)
    
    def get_total(self):
        return sum(item['price'] for item in self.items)


# Example 14: Unused exception class
class CustomValidationError(Exception):
    """UNUSED: Custom exception that's never raised"""
    pass


# ==============================================================================
# UNUSED METHODS IN USED CLASS
# ==============================================================================

# Example 15: Class with some unused methods
class DataProcessor:
    """This class itself is unused, all methods unused"""
    
    def __init__(self, data):
        self.data = data
    
    def process(self):
        """UNUSED: This method is never called"""
        return self.data.upper()
    
    def validate(self):
        """UNUSED: Never called"""
        return len(self.data) > 0
    
    def format(self):
        """UNUSED: Never called"""
        return self.data.strip()
    
    def analyze(self):
        """UNUSED: Never called"""
        return len(self.data)


# ==============================================================================
# UNUSED PARAMETERS
# ==============================================================================

# Example 16: Function with unused parameters
def send_email(to_address, subject, body, cc=None, bcc=None, priority=None):
    """
    UNUSED parameters: cc, bcc, priority
    These are never used in the function body
    """
    message = f"To: {to_address}\nSubject: {subject}\n\n{body}"
    # cc, bcc, and priority are completely ignored!
    return message


# Example 17: Method with unused self attributes
class ConfigManager:
    """UNUSED class"""
    def __init__(self):
        self.settings = {}
        self.cache = {}  # UNUSED attribute: never accessed
        self.history = []  # UNUSED attribute: never accessed
    
    def get_setting(self, key):
        # Only uses self.settings, never touches cache or history
        return self.settings.get(key)


# ==============================================================================
# UNUSED CODE BLOCKS
# ==============================================================================

# Example 18: Commented out code (dead code)
def calculate_price(base_price):
    """Function with commented dead code"""
    
    # Old calculation (no longer used)
    # discount = base_price * 0.1
    # tax = base_price * 0.08
    # total = base_price - discount + tax
    
    # New simple calculation
    return base_price * 1.1


# Example 19: Unreachable code
def check_value(x):
    """Contains unreachable code"""
    if x > 0:
        return "positive"
    else:
        return "non-positive"
    
    # UNREACHABLE: Code after return
    print("This never executes")  # UNUSED
    x = x + 1  # UNUSED


# ==============================================================================
# UNUSED PROPERTIES
# ==============================================================================

# Example 20: Unused property
class Product:
    """UNUSED class"""
    def __init__(self, name, price):
        self._name = name
        self._price = price
    
    @property
    def name(self):
        """UNUSED: Property that's never accessed"""
        return self._name
    
    @property
    def discounted_price(self):
        """UNUSED: Property that's never accessed"""
        return self._price * 0.9
    
    @property
    def tax_amount(self):
        """UNUSED: Property that's never accessed"""
        return self._price * 0.08


# ==============================================================================
# UNUSED LAMBDA FUNCTIONS
# ==============================================================================

# Example 21: Unused lambda
square = lambda x: x ** 2  # UNUSED: Never called
double = lambda x: x * 2   # UNUSED: Never called
is_even = lambda x: x % 2 == 0  # UNUSED: Never called


# ==============================================================================
# UNUSED LIST COMPREHENSIONS
# ==============================================================================

# Example 22: Result never used
def waste_computation():
    """Creates values but never uses them"""
    data = [1, 2, 3, 4, 5]
    
    # UNUSED: Result is calculated but never used
    squares = [x ** 2 for x in data]
    
    # UNUSED: Generator created but never consumed
    evens = (x for x in data if x % 2 == 0)
    
    return "done"


# ==============================================================================
# UNUSED GLOBAL VARIABLES
# ==============================================================================

# Example 23: Global variables never accessed
GLOBAL_CONFIG = {"debug": True}  # UNUSED
GLOBAL_COUNTER = 0  # UNUSED
GLOBAL_CACHE = {}  # UNUSED


# ==============================================================================
# UNUSED TYPE HINTS / ALIASES
# ==============================================================================

# Example 24: Type aliases never used
from typing import List, Dict, Tuple, Optional

UserID = int  # UNUSED type alias
UserData = Dict[str, str]  # UNUSED type alias
Coordinates = Tuple[float, float]  # UNUSED type alias


# ==============================================================================
# NOTE: We intentionally DO NOT use ANY of this code!
# This ensures Vulture finds everything.
# ==============================================================================

# DO NOT ADD ANY CALLS HERE - everything should be unused!