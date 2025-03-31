import re
from datetime import datetime


def current_commit_time(prefix: str) -> str:
    """Used to create a customized commit time for each API call"""
    return {f"{prefix}_commit_time": str(datetime.now())}

def format_column_friendly_string(name: str, case: str = 'upper') -> str:
    """Helper function to format column names in a more column-friendly format for the user. Adds underscores between
    capitalization, and then allows the user to specify their preferred method of character case."""
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

def format_dict_keys(data: list[dict], case: str = 'upper') -> list[dict]:
    '''Applies string formatting from format_column_friendly_string method to each of the keys in the dictionary'''
    return [
        {format_column_friendly_string(k, case): v for k, v in item.items()}
        for item in data
    ]

def convert_to_library(data: list[dict], output_format: str = "raw"):
    """
    Converts a list of dictionaries to a specified data format from a popular python data library.

    Supported formats:
    - 'raw': returns list of dictionaries (default). This is the JSON format returned by YouTube API v3
    - 'pandas': returns as a pandas DataFrame

    Future formats (not yet implemented):
    - 'polars'
    - 'pyspark'
    """
    if output_format == "raw":
        return data

    if output_format == "pandas":
        from yt_stats_wrangler.utils.pandas_utils import to_pandas_df
        return to_pandas_df(data)

    if output_format == "polars":
        from yt_stats_wrangler.utils.polars_utils import to_polars_df
        return to_polars_df(data)

    if output_format == "pyspark":
        from yt_stats_wrangler.utils.pyspark_utils import to_spark_df
        return to_spark_df(data)

    raise ValueError(
        f"Invalid output_format '{output_format}'. Choose from: 'raw', 'pandas', 'polars', 'pyspark'."
    )
    