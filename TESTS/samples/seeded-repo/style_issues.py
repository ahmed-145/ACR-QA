"""
Sample file with PEP8 style violations
"""

# BAD: Inconsistent naming
def Calculate_Total(Price,quantity):
    """Missing spaces, wrong case"""
    Total=Price*quantity
    return Total

# BAD: Line too long
def process_data(data):
    result = data['field1'] + data['field2'] + data['field3'] + data['field4'] + data['field5'] + data['field6'] + data['field7']
    return result

# BAD: Multiple statements on one line
def quick_check(x): return x > 0; print("checked")

# BAD: Trailing whitespace and blank lines with whitespace
class BadFormatting:
    
    def method_one(self):
        pass
        
    
    def method_two(self):
        pass


# BAD: Missing whitespace around operators
def calculate(a,b,c):
    result=a+b*c
    return result