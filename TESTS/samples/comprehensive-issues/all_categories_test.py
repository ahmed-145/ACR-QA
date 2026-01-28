"""
ACR-QA Comprehensive Test File
Triggers ALL rule categories for balanced testing
"""

import os
import sys
import pickle
import subprocess
from typing import List, Dict, Optional


# ===========================================================
# SECURITY ISSUES (Should trigger 10+ security findings)
# ===========================================================

# SECURITY-001: Dangerous eval()
def process_user_expression(user_input: str):
    """SECURITY-001: eval() with user input is dangerous"""
    result = eval(user_input)  # DANGEROUS!
    return result


# SECURITY-008: Unsafe pickle
def load_user_data(data: bytes):
    """SECURITY-008: Pickle can execute arbitrary code"""
    return pickle.loads(data)  # VULNERABLE!


# SECURITY-021: Shell injection
def run_command(user_cmd: str):
    """SECURITY-021: shell=True with user input"""
    subprocess.run(user_cmd, shell=True)  # INJECTION RISK!


# SECURITY-027: SQL Injection
def get_user_by_name(conn, username: str):
    """SECURITY-027: SQL injection vulnerability"""
    query = f"SELECT * FROM users WHERE name = '{username}'"  # INJECTION!
    return conn.execute(query)


# HARDCODE-001: Hardcoded secrets
API_KEY = "sk-1234567890abcdef"  # EXPOSED SECRET!
DATABASE_PASSWORD = "admin123"  # EXPOSED PASSWORD!
SECRET_TOKEN = "ghp_xxxxxxxxxxxx"  # GITHUB TOKEN!


# INPUT-001: Missing input validation  
def set_user_age(user, age):
    """INPUT-001: No validation on user input"""
    user.age = age  # What if age is -5 or 999?


# LOG-001: Logging sensitive data
import logging
def log_user_login(username, password):
    """LOG-001: Logging passwords is dangerous"""
    logging.info(f"User {username} logged in with password {password}")  # BAD!


# ===========================================================
# BEST PRACTICE ISSUES
# ===========================================================

# PATTERN-001: Mutable default argument
def append_to_list(item, items=[]):
    """PATTERN-001: Mutable default argument"""
    items.append(item)  # BUG! All calls share the same list
    return items


# EXCEPT-001: Bare except clause
def risky_operation():
    """EXCEPT-001: Bare except catches everything"""
    try:
        do_something()
    except:  # BAD! Catches KeyboardInterrupt, SystemExit
        pass


# ERROR-001: Silent exception
def silent_failure():
    """ERROR-001: Exception caught but not logged"""
    try:
        risky_call()
    except Exception:
        pass  # Silent failure - debugging nightmare!


# RESOURCE-001: File not closed
def read_config():
    """RESOURCE-001: File opened without context manager"""
    f = open('config.txt')  # Not closed if exception!
    data = f.read()
    return data


# ASYNC-001: Missing await
async def fetch_data():
    """ASYNC-001: Forgot to await async call"""
    result = async_api_call()  # Missing await!
    return result


# ===========================================================
# DESIGN ISSUES
# ===========================================================

# SOLID-001: Too many parameters
def create_user(name, email, phone, address, city, country, postal_code,
                company, job_title, department, manager, start_date):
    """SOLID-001: Way too many parameters (12)"""
    print(f"Creating user {name}")


# COMPLEXITY-001: High cyclomatic complexity
def complex_validation(data):
    """COMPLEXITY-001: Too many branches (complexity > 15)"""
    if not data:
        return False
    if "name" not in data:
        return False
    if len(data["name"]) < 1:
        return False
    if len(data["name"]) > 100:
        return False
    if "email" not in data:
        return False
    if "@" not in data["email"]:
        return False
    if "." not in data["email"]:
        return False
    if "age" in data:
        if data["age"] < 0:
            return False
        if data["age"] > 150:
            return False
    if "phone" in data:
        if len(data["phone"]) < 7:
            return False
        if len(data["phone"]) > 15:
            return False
    return True


# GLOBAL-001: Global variable modification
counter = 0
def increment_counter():
    """GLOBAL-001: Modifying global state"""
    global counter
    counter += 1  # Hidden side effect!


# ===========================================================
# PERFORMANCE ISSUES
# ===========================================================

# PERF-001: Inefficient loop
def process_items(items):
    """PERF-001: len() called every iteration"""
    for i in range(len(items)):  # len() called repeatedly
        print(items[i])


# PERF-002: String concatenation in loop
def build_message(names: List[str]) -> str:
    """PERF-002: O(n²) string concatenation"""
    result = ""
    for name in names:
        result += f"Hello, {name}!\n"  # Creates new string each time!
    return result


# ===========================================================
# CONCURRENCY ISSUES
# ===========================================================

# THREAD-001: Race condition
shared_counter = 0
def unsafe_increment():
    """THREAD-001: No lock on shared state"""
    global shared_counter
    shared_counter += 1  # Race condition in threads!


# ===========================================================
# STYLE ISSUES (for completeness)
# ===========================================================

# NAMING-001: Bad variable names
def calculate(x, y, z, a, b, c):
    """NAMING-001: Unclear single-letter names"""
    t = x + y  # What is t?
    r = z * a  # What is r?
    return t + r + b + c


# MAGIC-001: Magic numbers
def apply_discount(price):
    """MAGIC-001: Magic numbers without constants"""
    if price > 100:
        return price * 0.85  # What is 0.85?
    return price * 0.95  # What is 0.95?


# PRINT-001: Debug print statements
def debug_function(data):
    """PRINT-001: Print statements in production code"""
    print(f"DEBUG: data = {data}")  # Should use logging!
    print(f"Processing...")
    return process(data)


# ===========================================================
# DEAD CODE / UNUSED (for vulture)
# ===========================================================

def unused_helper():
    """This function is never called anywhere"""
    pass


unused_variable = 42
another_unused = "never used"


# Helper stubs for the examples above
def do_something(): pass
def risky_call(): pass
async def async_api_call(): pass
def process(x): return x
