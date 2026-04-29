"""Regression tests: ensure all submodules are importable post-install."""


def test_api_subpackage_importable():
    from yt_stats_wrangler.api import client  # noqa: F401


def test_utils_subpackage_importable():
    from yt_stats_wrangler.utils import helpers  # noqa: F401
    from yt_stats_wrangler.utils import pandas_utils  # noqa: F401
