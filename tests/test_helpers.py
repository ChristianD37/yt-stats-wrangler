from yt_stats_wrangler.utils.helpers import current_commit_time

def test_current_commit_time():
    result = current_commit_time("videoTest")
    assert isinstance(result, dict)
    assert "videoTest_commit_time" in result