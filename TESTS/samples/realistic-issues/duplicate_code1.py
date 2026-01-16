"""
Test file 1 for code duplication
Triggers: DUP-001
"""

def validate_email_format(email):
    """Email validation - duplicated in file 2"""
    if not email:
        return False
    if '@' not in email:
        return False
    if '.' not in email.split('@')[1]:
        return False
    if len(email) < 5:
        return False
    if email.count('@') != 1:
        return False
    return True


def send_welcome_email(user):
    """Send email - duplicated logic"""
    email = user['email']
    subject = "Welcome!"
    body = f"Hello {user['name']}, welcome to our platform!"
    
    # Email sending logic (duplicated)
    import smtplib
    from email.mime.text import MIMEText
    
    msg = MIMEText(body)
    msg['Subject'] = subject
    msg['From'] = 'noreply@example.com'
    msg['To'] = email
    
    return msg


def calculate_discount(price, user_type):
    """Discount calculation - duplicated"""
    if user_type == 'premium':
        discount = price * 0.20
    elif user_type == 'gold':
        discount = price * 0.15
    elif user_type == 'silver':
        discount = price * 0.10
    else:
        discount = 0
    
    final_price = price - discount
    return final_price
