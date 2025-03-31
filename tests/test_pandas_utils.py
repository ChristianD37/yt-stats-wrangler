import pytest
import pandas as pd
from yt_stats_wrangler.utils.pandas_utils import to_pandas_df, pandas_reorder_columns, pandas_parse_datetime_column

def test_to_pandas_df_creates_dataframe():
    data = [{"a": 1, "b": 2}, {"a": 3, "b": 4}]
    df = to_pandas_df(data)
    assert not df.empty
    assert df.shape == (2, 2)

def test_to_pandas_df_handles_empty_input():
    df = to_pandas_df([])
    assert df.empty

def test_reorder_columns_moves_priority_to_front():
    data = {
        "b": [1, 2],
        "a": [3, 4],
        "c": [5, 6]
    }
    df = pd.DataFrame(data)
    priority = ["a", "c"]

    reordered = pandas_reorder_columns(df, priority)

    # Check that priority columns are first and order is preserved
    assert reordered.columns.tolist() == ["a", "c", "b"]

def test_parse_datetime_column_converts_valid_dates():
    data = {
        "created_at": ["2023-01-01", "2023-02-15"],
        "updated_at": ["not a date", "2023-03-10"]
    }
    df = pd.DataFrame(data)

    result = pandas_parse_datetime_column(df, ["created_at", "updated_at"])

    # created_at should be valid datetimes
    assert pd.api.types.is_datetime64_any_dtype(result["created_at"])
    assert pd.notnull(result["created_at"]).all()

    # updated_at should contain at least one NaT from bad input
    assert pd.api.types.is_datetime64_any_dtype(result["updated_at"])
    assert result["updated_at"].isna().sum() == 1


