"""
Test file for jscpd duplication detection
This file contains duplicated code patterns that jscpd should detect
"""


# =============================================================================
# EXAMPLE 1: Exact duplicate function (will be copied in file 2)
# =============================================================================

def calculate_order_total(items):
    """Calculate total price of items in an order"""
    total = 0
    tax_rate = 0.08
    
    for item in items:
        item_price = item['price'] * item['quantity']
        total += item_price
    
    tax = total * tax_rate
    final_total = total + tax
    
    return final_total


# =============================================================================
# EXAMPLE 2: Another duplicate function (will be copied in file 2)
# =============================================================================

def validate_user_input(username, email, password):
    """Validate user registration data"""
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
# EXAMPLE 3: Data processing duplicate (will be copied in file 2)
# =============================================================================

def process_customer_data(customers):
    """Process and clean customer data"""
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
# EXAMPLE 4: Database query duplicate (will be copied in file 2)
# =============================================================================

def get_user_orders(user_id, db_connection):
    """Fetch all orders for a specific user"""
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
# EXAMPLE 5: Configuration loading duplicate (will be copied in file 2)
# =============================================================================

def load_app_config(config_file):
    """Load application configuration from file"""
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