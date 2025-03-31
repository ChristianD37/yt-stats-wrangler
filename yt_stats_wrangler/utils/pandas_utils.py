def to_pandas_df(data: list[dict]):
    """
    Convert a list of dictionaries into a pandas DataFrame.
    Returns an empty DataFrame if the list is empty.
    """
    try:
        import pandas as pd
    except ImportError:
        raise ImportError(
            "Optional dependency 'pandas' is not installed. Install it with:\n"
            "pip install yt-stats-wrangler[pandas]"
        )

    return pd.DataFrame(data) if data else pd.DataFrame()


def pandas_reorder_columns(df, priority_cols: list):
    """
    Reorders DataFrame columns to move priority columns to the front.
    This is specified by a list passed in by the user.
    """
    try:
        import pandas as pd
    except ImportError:
        raise ImportError(
            "Optional dependency 'pandas' is not installed. Install it with:\n"
            "pip install yt-stats-wrangler[pandas]"
        )

    existing = [col for col in priority_cols if col in df.columns]
    remaining = [col for col in df.columns if col not in existing]
    return df[existing + remaining]


def pandas_parse_datetime_column(df, columns: list):
    """
    Converts specified columns into a pandas-friendly datetime column.
    """
    try:
        import pandas as pd
    except ImportError:
        raise ImportError(
            "Optional dependency 'pandas' is not installed. Install it with:\n"
            "pip install yt-stats-wrangler[pandas]"
        )

    for column in columns:
        if column in df.columns:
            df[column] = pd.to_datetime(df[column], errors='coerce')
    return df