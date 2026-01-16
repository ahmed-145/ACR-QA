"""
Style Violations Test File
Triggers: Ruff style rules (E501, D100, N802, etc.)
"""
import os
import sys
import json  # F401: Unused import

# Missing module docstring would be D100, but we have one above

def thisIsABadFunctionName(x, y):  # N802: Function name should be lowercase
    """This function has a very long line that exceeds the 88 character limit and should trigger the E501 rule from Ruff linter."""
    unused_variable = 42  # F841: Unused variable
    very_long_variable_name_that_goes_on_and_on = "This is a very long line that definitely exceeds 88 characters and should be caught by Ruff"
    return x + y


class badClassName:  # N801: Class name should be PascalCase
    def __init__(self):
        pass


def function_without_docstring(a, b, c):  # D103: Missing function docstring
    return a + b + c


def another_function_with_extremely_long_line_that_should_trigger_style_warning():
    """Another function."""
    result = "This is an extremely long string literal that goes way beyond the 88 character line limit and should definitely be caught by Ruff's E501 rule"
    return result


# Trailing whitespace on next line    
x = 1

def MixedCaseFunction():  # N802: Should be lowercase
    """Bad naming convention."""
    MyVariable = 10  # N806: Variable should be lowercase
    return MyVariable
