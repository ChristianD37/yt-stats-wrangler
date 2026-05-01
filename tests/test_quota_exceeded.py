"""Regression tests for 403 quotaExceeded detection and key rotation behaviour."""
import json
import pytest
from unittest.mock import MagicMock, patch
from googleapiclient.errors import HttpError

from yt_stats_wrangler.api.client import (
    YouTubeDataClient,
    QuotaExceededError,
    _quota_exceeded,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_http_error(status: int, reason: str) -> HttpError:
    """Build a fake HttpError with the given status and quota reason."""
    content = json.dumps({
        "error": {
            "errors": [{"reason": reason, "domain": "youtube.quota"}]
        }
    }).encode()
    resp = MagicMock()
    resp.status = status
    return HttpError(resp=resp, content=content)


def _make_client(api_key="fake_key", max_quota=10000) -> YouTubeDataClient:
    """Create a client without actually calling the YouTube API."""
    with patch("yt_stats_wrangler.api.client.build"):
        return YouTubeDataClient(api_key=api_key, max_quota=max_quota)


# ---------------------------------------------------------------------------
# 1. _quota_exceeded() detection
# ---------------------------------------------------------------------------

def test_quota_exceeded_detects_quotaExceeded():
    assert _quota_exceeded(_make_http_error(403, "quotaExceeded")) is True

def test_quota_exceeded_detects_dailyLimitExceeded():
    assert _quota_exceeded(_make_http_error(403, "dailyLimitExceeded")) is True

def test_quota_exceeded_detects_rateLimitExceeded():
    assert _quota_exceeded(_make_http_error(403, "rateLimitExceeded")) is True

def test_quota_exceeded_ignores_unrelated_403():
    assert _quota_exceeded(_make_http_error(403, "commentsDisabled")) is False

def test_quota_exceeded_ignores_non_403():
    assert _quota_exceeded(_make_http_error(404, "quotaExceeded")) is False

def test_quota_exceeded_ignores_non_http_error():
    assert _quota_exceeded(ValueError("oops")) is False


# ---------------------------------------------------------------------------
# 2. Single-call method propagates QuotaExceededError
# ---------------------------------------------------------------------------

def test_single_call_raises_quota_exceeded_error():
    client = _make_client(max_quota=10000)
    client.youtube.channels().list.return_value.execute.side_effect = (
        _make_http_error(403, "quotaExceeded")
    )
    with pytest.raises(QuotaExceededError):
        client.get_channel_statistics("UCfake")


# ---------------------------------------------------------------------------
# 3. Multi-key client rotates on quota error, keys_remaining=True
# ---------------------------------------------------------------------------

def test_multi_key_rotation_on_quota_error():
    with patch("yt_stats_wrangler.api.client.build"):
        client = YouTubeDataClient(api_key=["key1", "key2"], max_quota=10000)

    client.youtube.channels().list.return_value.execute.side_effect = (
        _make_http_error(403, "quotaExceeded")
    )
    with pytest.raises(QuotaExceededError) as exc_info:
        client.get_channel_statistics("UCfake")

    assert exc_info.value.keys_remaining is True
    # Current key should have been marked fully spent
    assert client._quota_per_key[0] == 10000


# ---------------------------------------------------------------------------
# 4. Single-key client raises with keys_remaining=False
# ---------------------------------------------------------------------------

def test_single_key_raises_keys_remaining_false():
    client = _make_client(max_quota=10000)
    client.youtube.channels().list.return_value.execute.side_effect = (
        _make_http_error(403, "quotaExceeded")
    )
    with pytest.raises(QuotaExceededError) as exc_info:
        client.get_channel_statistics("UCfake")

    assert exc_info.value.keys_remaining is False


# ---------------------------------------------------------------------------
# 5. Loop method breaks cleanly when keys_remaining=False
# ---------------------------------------------------------------------------

def test_loop_breaks_when_all_keys_exhausted():
    client = _make_client(max_quota=10000)

    call_count = 0

    def fake_get_details(channel_id, key_format="raw", published_after=None):
        nonlocal call_count
        call_count += 1
        raise QuotaExceededError("all keys exhausted", keys_remaining=False)

    client.get_all_video_details_for_channel = fake_get_details

    result = client.get_all_video_details_for_channels(
        ["UC1", "UC2", "UC3"], output_format="raw"
    )

    assert result == []
    assert call_count == 1  # loop must have broken after first failure


# ---------------------------------------------------------------------------
# 6. Loop method continues when keys_remaining=True
# ---------------------------------------------------------------------------

def test_loop_continues_when_key_rotated():
    client = _make_client(max_quota=10000)

    calls = []

    def fake_get_details(channel_id, key_format="raw", published_after=None):
        calls.append(channel_id)
        if channel_id == "UC1":
            raise QuotaExceededError("rotated to next key", keys_remaining=True)
        return [{"channelId": channel_id, "videoId": "vid1"}]

    client.get_all_video_details_for_channel = fake_get_details

    result = client.get_all_video_details_for_channels(
        ["UC1", "UC2", "UC3"], output_format="raw"
    )

    # UC1 raised with keys_remaining=True — loop should continue to UC2 and UC3
    assert "UC1" in calls
    assert "UC2" in calls
    assert "UC3" in calls
    assert len(result) == 2  # UC2 and UC3 each returned one video
