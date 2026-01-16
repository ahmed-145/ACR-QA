"""
Test file demonstrating high cyclomatic complexity
Triggers: COMPLEXITY-001 (complexity > 10)
"""

def validate_user_input(data):
    """
    COMPLEXITY-001: Very high cyclomatic complexity
    Too many nested conditions and branches
    """
    if data is None:
        return False
    
    if not isinstance(data, dict):
        return False
    
    if 'username' not in data:
        return False
    else:
        if len(data['username']) < 3:
            return False
        if len(data['username']) > 20:
            return False
        if not data['username'].isalnum():
            return False
    
    if 'email' not in data:
        return False
    else:
        if '@' not in data['email']:
            return False
        if '.' not in data['email']:
            return False
        parts = data['email'].split('@')
        if len(parts) != 2:
            return False
        if len(parts[0]) < 1:
            return False
        if len(parts[1]) < 3:
            return False
    
    if 'password' in data:
        pwd = data['password']
        if len(pwd) < 8:
            return False
        if not any(c.isupper() for c in pwd):
            return False
        if not any(c.islower() for c in pwd):
            return False
        if not any(c.isdigit() for c in pwd):
            return False
    
    return True  # Complexity: ~20


def process_order(order, user, inventory, payment):
    """
    COMPLEXITY-001: High complexity with nested loops and conditions
    """
    if not order or not user:
        return None
    
    total = 0
    for item in order.get('items', []):
        if item['id'] not in inventory:
            if item['type'] == 'physical':
                return {'error': 'out of stock'}
            else:
                if item['digital']:
                    total += item['price']
                else:
                    return {'error': 'invalid item'}
        else:
            if inventory[item['id']] > 0:
                total += item['price']
                inventory[item['id']] -= 1
            else:
                if item['backorder']:
                    total += item['price'] * 1.1
                else:
                    return {'error': 'out of stock'}
    
    if payment['method'] == 'card':
        if payment['amount'] < total:
            return {'error': 'insufficient funds'}
        elif payment['amount'] > total:
            return {'success': True, 'change': payment['amount'] - total}
        else:
            return {'success': True}
    elif payment['method'] == 'cash':
        if payment['amount'] < total:
            return {'error': 'insufficient funds'}
        else:
            return {'success': True, 'change': payment['amount'] - total}
    else:
        return {'error': 'invalid payment method'}
