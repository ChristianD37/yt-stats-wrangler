from typing import List, Dict, Optional, Union

def to_spark_df(data: List[Dict]):
    """
    Converts a list of dictionaries into a PySpark DataFrame.
    Requires `pyspark` to be installed.
    """
    try:
        from pyspark.sql import SparkSession
    except ImportError:
        raise ImportError("Install PySpark with: pip install pyspark")

    spark = SparkSession.builder.getOrCreate()
    return spark.createDataFrame(data)