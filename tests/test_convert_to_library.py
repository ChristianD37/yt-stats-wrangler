import pytest
from yt_stats_wrangler.utils.helpers import convert_to_library

# Sample test data
test_data = [
    {"videoId": "abc123", "title": "Test Video 1"},
    {"videoId": "def456", "title": "Test Video 2"},
]

def test_convert_to_library_raw():
    result = convert_to_library(test_data, output_format="raw")
    assert isinstance(result, list)
    assert isinstance(result[0], dict)
    assert result[0]["videoId"] == "abc123"

def test_convert_to_library_pandas():
    result = convert_to_library(test_data, output_format="pandas")
    assert hasattr(result, "head")  # basic DataFrame check
    assert result.iloc[0]["videoId"] == "abc123"

def test_convert_to_library_polars():
    try:
        import polars as pl
    except ImportError:
        pytest.skip("Polars not installed")

    result = convert_to_library(test_data, output_format="polars")
    assert isinstance(result, pl.DataFrame)
    assert result[0, "videoId"] == "abc123"

def test_convert_to_library_pyspark():
    try:
        from pyspark.sql import DataFrame
    except ImportError:
        pytest.skip("PySpark not installed")

    result = convert_to_library(test_data, output_format="pyspark")
    assert isinstance(result.schema["videoId"].dataType.simpleString(), str)
    assert result.filter("videoId = 'abc123'").count() == 1

def test_convert_to_library_invalid_format():
    with pytest.raises(ValueError, match="Invalid output_format 'excel'"):
        convert_to_library(test_data, output_format="excel")