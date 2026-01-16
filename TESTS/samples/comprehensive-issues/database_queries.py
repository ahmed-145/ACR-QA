"""
Database Query Builder with Security Issues
Triggers: SECURITY-001 (multiple SQL injection vulnerabilities)
"""
import sqlite3


def search_users_by_name(search_term: str):
    """
    SECURITY-001: SQL injection vulnerability
    User input directly in query
    """
    conn = sqlite3.connect('app.db')
    cursor = conn.cursor()
    
    # VULNERABLE: User input concatenated directly
    query = f"SELECT * FROM users WHERE name LIKE '%{search_term}%'"
    cursor.execute(query)
    
    return cursor.fetchall()


def delete_user_account(user_id: str):
    """
    SECURITY-001: Another SQL injection
    """
    query = "DELETE FROM users WHERE id = " + user_id
    conn = sqlite3.connect('app.db')
    conn.execute(query)
    conn.commit()


def update_user_email(user_id: int, new_email: str):
    """
    SECURITY-001: SQL injection in UPDATE statement
    """
    query = f"UPDATE users SET email = '{new_email}' WHERE id = {user_id}"
    conn = sqlite3.connect('app.db')
    conn.execute(query)
    conn.commit()


def execute_custom_query(table_name: str, conditions: str):
    """
    SECURITY-001: Allows arbitrary SQL execution
    """
    query = f"SELECT * FROM {table_name} WHERE {conditions}"
    conn = sqlite3.connect('app.db')
    return conn.execute(query).fetchall()