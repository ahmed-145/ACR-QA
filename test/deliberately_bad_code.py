"""
Deliberately Bad Python Code — ACR-QA God Mode Live Test
=========================================================
This file intentionally violates multiple ACR-QA rules to test the full pipeline:
    - 4 high-severity security issues
    - 1 medium design smell
    - 3 low style/dead-code issues

DO NOT USE THIS CODE IN PRODUCTION.
"""

import os, sys  # noqa: E401 — multiple imports on one line (IMPORT-002)
import pickle
import subprocess

# ── SECURITY-005 / HARDCODE-001: Hardcoded password ───────────────────────
DB_PASSWORD = "admin123"
SECRET_KEY = "super-secret-key-do-not-share"
API_TOKEN = "ghp_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"

# ── SECURITY-001: eval() on user-controlled input ─────────────────────────
def evaluate_user_expression(user_input):
    result = eval(user_input)  # Dangerous: arbitrary code execution
    return result


# ── SECURITY-027: Raw SQL string formatting (SQL injection) ───────────────
def get_user_by_name(conn, username):
    cursor = conn.cursor()
    query = "SELECT * FROM users WHERE username = '%s'" % username  # SQL injection
    cursor.execute(query)
    return cursor.fetchall()


# ── SECURITY-021: subprocess with shell=True (command injection) ──────────
def run_system_command(user_cmd):
    output = subprocess.Popen(user_cmd, shell=True, stdout=subprocess.PIPE)
    return output.communicate()[0]


# ── SECURITY-008: Unsafe pickle deserialization ───────────────────────────
def load_user_session(serialized_data):
    session = pickle.loads(serialized_data)  # Arbitrary code execution via pickle
    return session


# ── SOLID-001: Function with 8 parameters (too many params) ───────────────
def create_user_account(username, password, email, phone, address, city, country, role):
    # This function does too much — violates Single Responsibility Principle
    user_data = {
        "username": username,
        "password": password,
        "email": email,
        "phone": phone,
        "address": address,
        "city": city,
        "country": country,
        "role": role,
    }
    return user_data


# ── EXCEPT-001: Bare except ───────────────────────────────────────────────
def connect_to_database(host, port):
    try:
        import psycopg2
        conn = psycopg2.connect(host=host, port=port, password=DB_PASSWORD)
        return conn
    except:  # noqa — intentionally bare for testing
        return None


# ── VAR-001: Unused variables ─────────────────────────────────────────────
def process_data(items):
    unused_result = []        # Never used
    another_unused = "hello"  # Never used
    total = 0
    for item in items:
        total += item
    return total


# ── SECURITY-018: yaml.load without Loader (code execution via YAML) ──────
def parse_config(yaml_string):
    import yaml
    config = yaml.load(yaml_string)  # Should use yaml.safe_load
    return config


if __name__ == "__main__":
    # Entry point — intentionally insecure for testing
    user_cmd = sys.argv[1] if len(sys.argv) > 1 else "echo hello"
    run_system_command(user_cmd)
