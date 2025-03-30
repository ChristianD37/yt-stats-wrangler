try:
    import pandas as pd
except ImportError as e:
    raise ImportError(
        "Optional dependency 'pandas' is not installed.\n"
        "Install it with: pip install yt-stats-wrangler[pandas]"
    ) from e

def list_of_dicts_to_df(data: list[dict]) -> pd.DataFrame:
    """
    Convert a list of dictionaries into a pandas DataFrame.
    Returns an empty DataFrame if the list is empty.
    """
    return pd.DataFrame(data) if data else pd.DataFrame()

def reorder_columns(df: pd.DataFrame, priority_cols: list) -> pd.DataFrame:
    """Reorders DataFrame columns to move priority columns to the front.
    This is specified by a list passed in by the user"""
    existing = [col for col in priority_cols if col in df.columns]
    remaining = [col for col in df.columns if col not in existing]
    return df[existing + remaining]

def parse_datetime_column(df: pd.DataFrame, columns : list) -> pd.DataFrame:
    """Converts specified columns into a pandas-friendly datetime column."""
    for column in columns:
        if column in df.columns:
            df[column] = pd.to_datetime(df[column], errors='coerce')
    return df