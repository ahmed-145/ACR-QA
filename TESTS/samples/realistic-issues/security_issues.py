"""
Test file demonstrating security vulnerabilities
Triggers: SECURITY-001 (dangerous eval, SQL injection)
"""

def execute_user_command(user_input):
    """
    SECURITY-001: Dangerous use of eval()
    Allows arbitrary code execution
    """
    result = eval(user_input)  # DANGEROUS!
    return result


def get_user_data(user_id):
    """
    SECURITY-001: SQL injection vulnerability
    User input directly concatenated into SQL query
    """
    import sqlite3
    conn = sqlite3.connect('users.db')
    cursor = conn.cursor()
    
    # VULNERABLE: SQL injection possible
    query = "SELECT * FROM users WHERE id = " + user_id
    cursor.execute(query)
    return cursor.fetchall()


def search_products(search_term):
    """
    SECURITY-001: Another SQL injection
    """
    query = f"SELECT * FROM products WHERE name LIKE '%{search_term}%'"
    return query
