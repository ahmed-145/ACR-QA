"""
Test file demonstrating anti-patterns
Triggers: PATTERN-001 (mutable default arguments)
"""

def add_item_to_cart(item, cart=[]):
    """
    PATTERN-001: Mutable default argument
    All calls share the same list!
    """
    cart.append(item)
    return cart


def track_user_visits(user_id, visits={}):
    """
    PATTERN-001: Mutable default argument with dict
    """
    if user_id not in visits:
        visits[user_id] = 0
    visits[user_id] += 1
    return visits


def configure_settings(options={}):
    """
    PATTERN-001: Another mutable default
    """
    options['timestamp'] = '2025-01-01'
    return options
