"""
Subscription Management with Duplications
Triggers: DUP-001 (duplicates payment_processor logic)
"""


def calculate_subscription_price(base_price: float, tier: str):
    """
    DUP-001: DUPLICATE of calculate_discount_premium from payment_processor.py
    """
    if tier == 'premium':
        discount = base_price * 0.25
    elif tier == 'gold':
        discount = base_price * 0.20
    elif tier == 'silver':
        discount = base_price * 0.15
    elif tier == 'bronze':
        discount = base_price * 0.10
    else:
        discount = 0
    
    final_price = base_price - discount
    tax = final_price * 0.08
    total = final_price + tax
    
    return total


def validate_credit_card_details(card_num: str, security_code: str, exp_date: str,
                                name_on_card: str, zip_code: str, country_code: str):
    """
    DUP-001: Near-duplicate of validate_payment_card from payment_processor.py
    """
    if len(card_num) != 16:
        return False
    
    if len(security_code) != 3:
        return False
    
    return True


def create_subscription(user_id: int, plan_id: int, payment_method: str,
                       billing_cycle: str, auto_renew: bool, start_date: str,
                       promo_code: str = None):
    """
    SOLID-001: Too many parameters (7 parameters)
    """
    print(f"Creating subscription for user {user_id}")
    return {'status': 'created'}