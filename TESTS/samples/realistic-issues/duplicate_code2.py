"""
Test file 2 for code duplication
Contains exact duplicates from file 1
Triggers: DUP-001
"""

def check_email_validity(email_address):
    """Email validation - DUPLICATE of validate_email_format"""
    if not email_address:
        return False
    if '@' not in email_address:
        return False
    if '.' not in email_address.split('@')[1]:
        return False
    if len(email_address) < 5:
        return False
    if email_address.count('@') != 1:
        return False
    return True


def send_notification_email(recipient):
    """Send email - DUPLICATE logic"""
    email = recipient['email']
    subject = "Notification"
    body = f"Hello {recipient['name']}, you have a new notification!"
    
    # Email sending logic (DUPLICATED)
    import smtplib
    from email.mime.text import MIMEText
    
    msg = MIMEText(body)
    msg['Subject'] = subject
    msg['From'] = 'noreply@example.com'
    msg['To'] = email
    
    return msg


def apply_user_discount(amount, membership):
    """Discount calculation - DUPLICATE"""
    if membership == 'premium':
        discount = amount * 0.20
    elif membership == 'gold':
        discount = amount * 0.15
    elif membership == 'silver':
        discount = amount * 0.10
    else:
        discount = 0
    
    total = amount - discount
    return total
