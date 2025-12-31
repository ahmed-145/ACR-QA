"""
Test file for jscpd duplication detection - DUPLICATE FILE
This file contains the SAME functions as duplicate_code_example1.py
jscpd should detect all 5 duplications
"""


# =============================================================================
# DUPLICATE 1: Exact same function from file 1
# =============================================================================

def calculate_invoice_total(items):
    """Calculate total price of items in an invoice"""
    total = 0
    tax_rate = 0.08
    
    for item in items:
        item_price = item['price'] * item['quantity']
        total += item_price
    
    tax = total * tax_rate
    final_total = total + tax
    
    return final_total


# =============================================================================
# DUPLICATE 2: Same validation logic from file 1
# =============================================================================

def check_registration_data(username, email, password):
    """Check if registration data is valid"""
    errors = []
    
    # Check username
    if not username or len(username) < 3:
        errors.append("Username must be at least 3 characters")
    
    if not username.isalnum():
        errors.append("Username must be alphanumeric")
    
    # Check email
    if not email or '@' not in email:
        errors.append("Invalid email address")
    
    # Check password
    if not password or len(password) < 8:
        errors.append("Password must be at least 8 characters")
    
    if not any(char.isdigit() for char in password):
        errors.append("Password must contain at least one number")
    
    if not any(char.isupper() for char in password):
        errors.append("Password must contain at least one uppercase letter")
    
    return errors


# =============================================================================
# DUPLICATE 3: Same data processing from file 1
# =============================================================================

def clean_user_data(customers):
    """Clean and process user data"""
    processed = []
    
    for customer in customers:
        # Clean and normalize data
        name = customer.get('name', '').strip().title()
        email = customer.get('email', '').strip().lower()
        phone = customer.get('phone', '').replace('-', '').replace(' ', '')
        
        # Create cleaned record
        cleaned = {
            'name': name,
            'email': email,
            'phone': phone,
            'status': 'active'
        }
        
        processed.append(cleaned)
    
    return processed


# =============================================================================
# DUPLICATE 4: Same database query from file 1
# =============================================================================

def fetch_customer_orders(user_id, db_connection):
    """Get all orders for a customer"""
    cursor = db_connection.cursor()
    
    query = """
        SELECT 
            orders.id,
            orders.order_date,
            orders.total_amount,
            orders.status
        FROM orders
        WHERE orders.user_id = ?
        ORDER BY orders.order_date DESC
    """
    
    cursor.execute(query, (user_id,))
    results = cursor.fetchall()
    
    orders = []
    for row in results:
        order = {
            'id': row[0],
            'date': row[1],
            'amount': row[2],
            'status': row[3]
        }
        orders.append(order)
    
    return orders


# =============================================================================
# DUPLICATE 5: Same config loading from file 1
# =============================================================================

def read_config_file(config_file):
    """Read configuration from JSON file"""
    import json
    
    try:
        with open(config_file, 'r') as f:
            config = json.load(f)
        
        # Set defaults
        config.setdefault('host', 'localhost')
        config.setdefault('port', 8080)
        config.setdefault('debug', False)
        config.setdefault('log_level', 'INFO')
        
        return config
        
    except FileNotFoundError:
        print(f"Config file {config_file} not found")
        return None
    except json.JSONDecodeError:
        print(f"Invalid JSON in {config_file}")
        return None