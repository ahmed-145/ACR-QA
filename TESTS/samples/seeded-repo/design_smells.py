"""
Sample file with design smells
"""

class GodClass:
    """Large class with too many responsibilities - violates SRP"""
    
    def __init__(self):
        self.users = []
        self.orders = []
        self.inventory = []
        self.payments = []
        self.shipping = []
        self.notifications = []
        self.analytics = []
        self.cache = {}
        self.config = {}
        self.logger = None
        self.db_connection = None
        self.api_client = None
        self.email_service = None
        self.sms_service = None
        self.file_storage = None
    
    def add_user(self): pass
    def remove_user(self): pass
    def update_user(self): pass
    def authenticate_user(self): pass
    def authorize_user(self): pass
    def create_order(self): pass
    def cancel_order(self): pass
    def process_payment(self): pass
    def refund_payment(self): pass
    def update_inventory(self): pass
    def check_stock(self): pass
    def reserve_stock(self): pass
    def ship_order(self): pass
    def track_shipment(self): pass
    def send_email(self): pass
    def send_sms(self): pass
    def log_activity(self): pass
    def generate_report(self): pass
    def export_data(self): pass
    def import_data(self): pass
    def backup_database(self): pass
    def restore_database(self): pass
    def clear_cache(self): pass
    def update_config(self): pass

def too_many_parameters(name, age, email, phone, address, city, state, zip_code):
    """Function with too many parameters - hard to use API"""
    return {
        'name': name,
        'age': age,
        'email': email,
        'phone': phone,
        'address': address,
        'city': city,
        'state': state,
        'zip_code': zip_code
    }

def mutable_default_danger(items=[]):
    """Mutable default argument - classic Python pitfall"""
    items.append('new_item')
    return items

def another_mutable_default(config={}):
    """Another mutable default"""
    config['key'] = 'value'
    return config