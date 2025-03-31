import os
import pytest

from yt_stats_wrangler.utils.pyspark_utils import to_spark_df

def _pyspark_installed():
    try:
        import pyspark  # noqa: F401
        return True
    except ImportError:
        return False

# Sample test data
test_data = [
    {"videoId": "abc123", "title": "Test Video 1"},
    {"videoId": "def456", "title": "Test Video 2"},
]

# Skip if JAVA_HOME is not set or PySpark is not installed
skip_if_no_java_or_pyspark = pytest.mark.skipif(
    "JAVA_HOME" not in os.environ or not _pyspark_installed(),
    reason="Skipping PySpark test because JAVA_HOME is not set or PySpark is not installed"
)

@skip_if_no_java_or_pyspark
def test_to_spark_df_creates_pyspark_dataframe():
    try:
        from pyspark.sql import DataFrame
    except ImportError:
        pytest.skip("PySpark not installed")

    df = to_spark_df(test_data)
    assert df.count() == 2
    assert "videoId" in df.columns