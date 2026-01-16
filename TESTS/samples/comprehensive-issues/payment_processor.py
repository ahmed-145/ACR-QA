"""
Payment Processing with Duplicated Logic
Triggers: DUP-001, COMPLEXITY-001, SOLID-001
"""


def calculate_discount_premium(price: float, user_type: str):
    """Discount calculation - will be duplicated in file 3"""
    if user_type == 'premium':
        discount = price * 0.25
    elif user_type == 'gold':
        discount = price * 0.20
    elif user_type == 'silver':
        discount = price * 0.15
    elif user_type == 'bronze':
        discount = price * 0.10
    else:
        discount = 0
    
    final_price = price - discount
    tax = final_price * 0.08
    total = final_price + tax
    
    return total


def validate_payment_card(card_number: str, cvv: str, expiry: str,
                         cardholder: str, billing_zip: str, billing_country: str):
    """
    SOLID-001: Too many parameters (6 parameters)
    """
    if len(card_number) != 16:
        return False
    
    if len(cvv) != 3:
        return False
    
    return True


def process_complex_payment(order, user, payment, inventory, shipping, tax_info):
    """
    COMPLEXITY-001: High complexity with nested conditions
    """
    if not order or not user or not payment:
        return {'error': 'Missing required data'}
    
    total = 0
    items_processed = []
    
    for item in order.get('items', []):
        if item['id'] not in inventory:
            if item['type'] == 'physical':
                if shipping['method'] == 'standard':
                    return {'error': 'Item unavailable for standard shipping'}
                elif shipping['method'] == 'express':
                    if inventory.get(f"warehouse_{item['id']}", 0) > 0:
                        total += item['price'] * 1.15
                        items_processed.append(item)
                    else:
                        return {'error': 'Item out of stock'}
                else:
                    return {'error': 'Invalid shipping method'}
            elif item['type'] == 'digital':
                total += item['price']
                items_processed.append(item)
            else:
                return {'error': 'Unknown item type'}
        else:
            if inventory[item['id']]['stock'] > 0:
                price = item['price']
                if user['member_level'] == 'premium':
                    price *= 0.8
                elif user['member_level'] == 'gold':
                    price *= 0.85
                total += price
                items_processed.append(item)
            else:
                if item['allow_backorder']:
                    total += item['price'] * 1.1
                    items_processed.append(item)
                else:
                    return {'error': f'Item {item["id"]} out of stock'}
    
    # Apply taxes
    if tax_info['apply_tax']:
        if tax_info['country'] == 'US':
            if tax_info['state'] in ['CA', 'NY', 'TX']:
                total *= 1.08
            else:
                total *= 1.05
        elif tax_info['country'] == 'EU':
            total *= 1.20
    
    return {'success': True, 'total': total, 'items': items_processed}