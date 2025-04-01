from typing import List, Dict, Optional, Union

def to_polars_df(data: List[Dict]):
    """
    Converts a list of dictionaries into a Polars DataFrame.
    Requires `polars` to be installed.
    """
    try:
        import polars as pl
    except ImportError:
        raise ImportError("Install Polars with: pip install polars")

    return pl.DataFrame(data)
