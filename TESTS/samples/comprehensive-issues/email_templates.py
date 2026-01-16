"""
Email Template Generator with Style Issues
Triggers: STYLE-001, STYLE-002, NAMING-001, F401, PLR0913
"""
import os  # F401: Unused import
import sys  # F401: Unused import
from typing import Dict


# STYLE-001: Line too long (>88 chars)
def generate_welcome_email_with_user_info_and_personalization_and_marketing_links_and_tracking(username, email, plan):
    """
    NAMING-001: Bad parameter names
    PLR0913: Too many parameters (if we add more)
    """
    # STYLE-001: Line exceeds 88 characters
    return f"Welcome {username}! Your email is {email} and your plan is {plan}. Click here to verify: https://example.com/verify?token=abc123&user={username}&email={email}&plan={plan}&referral=marketing&campaign=welcome&source=web&medium=email"


def send_notification(user):
    # STYLE-002: Missing docstring for public function
    subject = "Notification"
    body = f"Hello {user['name']}"
    unused_var = "never used"  # F841: Unused variable
    return {'subject': subject, 'body': body}


# STYLE-001: Line exceeds 88 characters
very_long_variable_name_that_describes_something_but_is_way_too_long_and_violates_line_length = "This is a very long string that demonstrates a line length violation in Python code and should trigger Ruff's E501 rule"


def x(a, b, c):  # STYLE-002: Missing docstring, NAMING-001: Bad names
    """Missing type hints"""
    return a + b + c


class badClassName:  # NAMING-001: Class name should be PascalCase
    """STYLE-002: Missing class docstring"""
    def __init__(self):
        pass


def another_function_with_many_params(
    param1, param2, param3, param4, param5, param6, param7
):  # PLR0913: Too many parameters (>5)
    """Function with too many parameters"""
    pass