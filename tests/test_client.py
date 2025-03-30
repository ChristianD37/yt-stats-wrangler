import os
import pytest
from yt_stats_wrangler.api.client import YouTubeDataClient

# Use the CDCodes channel ID to test the client and ensure it's interfacing with the API

# CDCodes channel will be used for testing API access
TEST_CHANNEL_ID = 'UCB2mKxxXPK3X8SJkAc-db3A'


@pytest.fixture(scope="module")
def yt_client():
    # Test that the client is able to connect with a valid API Key
    api_key = os.getenv("YOUTUBE_API_V3_KEY")
    if not api_key:
        pytest.skip("YOUTUBE_API_V3_KEY environment variable not set")
    return YouTubeDataClient(api_key=api_key)

def test_initialization(yt_client):
    assert yt_client.youtube is not None

def test_quota_initial_state(yt_client):
    yt_client.reset_quota_used()
    assert yt_client.quota_used == 0
    assert yt_client.max_quota == -1  # default unlimited

    # Test that the client finds the uploads playlist
def test_get_uploads_playlist_id(yt_client):
    playlist_id = yt_client.get_uploads_playlist_id(TEST_CHANNEL_ID)
    assert playlist_id.startswith("UU")  # Upload playlists usually start with 'UU'

    # Test that videos are being found on the channel
def test_get_all_video_details(yt_client):
    videos = yt_client.get_all_video_details(TEST_CHANNEL_ID)
    assert isinstance(videos, list)
    assert len(videos) > 0
    assert "videoId" in videos[0]

    # Test that stats are correctly returned
def test_get_video_stats(yt_client):
    videos = yt_client.get_all_video_details(TEST_CHANNEL_ID)
    video_ids = [v["videoId"] for v in videos[:5]]  # Limit to 5 for test
    stats = yt_client.get_video_stats(video_ids)

    assert isinstance(stats, list)
    assert len(stats) > 0
    assert isinstance(stats[0], dict)
    assert "videoId" in stats[0]
    assert "viewCount" in stats[0] or "view_count" in stats[0]

def test_get_video_comments(yt_client):
    videos = yt_client.get_all_video_details(TEST_CHANNEL_ID)
    video_id = videos[0]["videoId"]  # Just one video to limit quota usage

    comments = yt_client.get_top_level_video_comments(video_id)

    assert isinstance(comments, list)
    if comments:  # Some videos may have comments disabled
        assert isinstance(comments[0], dict)
        assert "videoId" in comments[0]
        assert "author" in comments[0]
        assert "text" in comments[0]
        assert "publishedAt" in comments[0]
        assert "likeCount" in comments[0]
        assert "videoTopLevelComments_commit_time" in comments[0]


def test_quota_check_with_unlimited(yt_client):
    yt_client.reset_quota_used()
    yt_client.set_max_quota(-1)
    assert yt_client.check_quota() is True
    yt_client.quota_used = 9999
    assert yt_client.check_quota() is True

def test_quota_check_with_limit(yt_client):
    yt_client.reset_quota_used()
    yt_client.set_max_quota(5)

    yt_client.quota_used = 4
    assert yt_client.check_quota() is True

    yt_client.quota_used = 5
    assert yt_client.check_quota() is False

def test_quota_blocks_api_call(yt_client):
    yt_client.reset_quota_used()
    yt_client.set_max_quota(0)  # no calls allowed

    result = yt_client.get_all_video_details(TEST_CHANNEL_ID)
    assert result == [] or len(result) == 0
    assert yt_client.quota_used == 0

def test_get_top_level_comments_for_video_ids(yt_client):
    yt_client.reset_quota_used()
    yt_client.set_max_quota(-1)  # unlimited for testing

    # One known valid video ID (from CDcodes channel)
    valid_id = "Q6CCdCBVypg"  # You can replace with a known-valid ID if needed
    invalid_id = "invalid_video_id_123456"

    video_ids = [valid_id, invalid_id]
    comments = yt_client.get_top_level_comments_for_video_ids(video_ids)

    #  Check structure
    assert isinstance(comments, list)

    #  At least the valid one should return some comments
    assert any(comment["videoId"] == valid_id for comment in comments)

    #  The invalid one should be tracked in failed_ids
    assert hasattr(yt_client, "failed_ids_for_comments")
    assert invalid_id in yt_client.failed_ids_for_comments