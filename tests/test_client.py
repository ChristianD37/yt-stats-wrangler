import os
import pytest
from yt_stats_wrangler.api.client import YouTubeDataClient

# Use the CDCodes channel ID to test the client and ensure it's interfacing with the API

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