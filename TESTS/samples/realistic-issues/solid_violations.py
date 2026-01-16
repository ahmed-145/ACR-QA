"""
Test file demonstrating SOLID principle violations
Triggers: SOLID-001 (too many parameters)
"""

def create_user_account(username, password, email, phone, address, 
                       city, state, zipcode, country, birthdate):
    """
    SOLID-001: Too many parameters (10 parameters)
    This violates Single Responsibility Principle
    """
    print(f"Creating account for {username}")
    return {
        'username': username,
        'password': password,
        'email': email,
        'phone': phone,
        'address': address,
        'city': city,
        'state': state,
        'zipcode': zipcode,
        'country': country,
        'birthdate': birthdate
    }


def process_payment(user_id, amount, currency, payment_method, 
                   card_number, cvv, expiry, billing_address):
    """
    SOLID-001: Another function with too many parameters (8 parameters)
    """
    pass
