def login(username, password):
    # SECURITY-001: SQL injection vulnerability
    query = f"SELECT * FROM users WHERE username = '{username}' AND password = '{password}'"
    return execute_query(query)

def execute_code(user_input):
    # SECURITY-001: Dangerous eval usage
    result = eval(user_input)
    return result
