import pytest

from yt_stats_wrangler.utils.polars_utils import to_polars_df

test_data = [
    {"videoId": "abc123", "title": "Test Video 1"},
    {"videoId": "def456", "title": "Test Video 2"},
]

def test_to_polars_df_creates_polars_dataframe():
    try:
        import polars as pl
    except ImportError:
        pytest.skip("Polars not installed")

    df = to_polars_df(test_data)
    assert isinstance(df, pl.DataFrame)
    assert df[0, "videoId"] == "abc123"