"""
Sample file with bad practices for testing
"""
import os
import sqlite3

def unsafe_query(user_input):
    """SQL injection vulnerability"""
    conn = sqlite3.connect('test.db')
    cursor = conn.cursor()
    # BAD: String concatenation in SQL
    query = "SELECT * FROM users WHERE name = '" + user_input + "'"
    cursor.execute(query)
    return cursor.fetchall()

def eval_danger(user_code):
    """Dangerous use of eval"""
    # BAD: eval on user input
    result = eval(user_code)
    return result

def hardcoded_secrets():
    """Hardcoded credentials"""
    # BAD: Hardcoded password
    password = "admin123"
    api_key = "sk-1234567890abcdef"
    return password, api_key

class InsecureRandom:
    """Uses weak random for security"""
    import random
    
    def generate_token(self):
        # BAD: random is not cryptographically secure
        return ''.join(str(self.random.randint(0, 9)) for _ in range(10))
# Duplicate function for testing jscpd
def unsafe_query_duplicate(user_input):
    """SQL injection vulnerability - DUPLICATE"""
    conn = sqlite3.connect('test.db')
    cursor = conn.cursor()
    query = "SELECT * FROM users WHERE name = '" + user_input + "'"
    cursor.execute(query)
    return cursor.fetchall()
