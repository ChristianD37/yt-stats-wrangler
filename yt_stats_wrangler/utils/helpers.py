import re
from datetime import datetime


def current_commit_time(prefix: str) -> str:
    """Used to create a customized commit time for each API call"""
    return {f"{prefix}_commit_time": str(datetime.now())}

def format_column_friendly_string(name: str, case: str = 'upper') -> str:
    """Helper function to format column names in a more column-friendly format for the user"""
    if case not in ('lower', 'upper', 'mixed'):
        raise ValueError(f"Invalid case option '{case}'. Choose from 'lower', 'upper', or 'mixed'.")
    # Insert underscore between lowercase-uppercase (e.g., camelCase → camel_Case)
    name = re.sub(r'(?<=[a-z])(?=[A-Z])', '_', name)
    # Replace spaces with underscores
    name = name.replace(" ", "_")
    # Apply casing
    if case =='lower': return name.lower()
    elif case == 'upper': return name.upper()
    else: return  name

def format_dict_keys(data: list[dict], case: str = 'lower') -> list[dict]:
    '''Applies string formatting from format_column_friendly_string method to each of the keys in the dictionary'''
    return [
        {format_column_friendly_string(k, case): v for k, v in item.items()}
        for item in data
    ]
    