from yt_stats_wrangler.utils.helpers import current_commit_time, format_column_friendly_string, format_dict_keys

def test_current_commit_time():
    result = current_commit_time("videoTest")
    assert isinstance(result, dict)
    assert "videoTest_commit_time" in result

def test_format_column_friendly_string_cases():
    # Default is now 'upper'
    assert format_column_friendly_string("VideoId") == "VIDEO_ID"
    assert format_column_friendly_string("videoId") == "VIDEO_ID"
    assert format_column_friendly_string("Published At") == "PUBLISHED_AT"

    # Explicit case overrides
    assert format_column_friendly_string("VideoId", case="lower") == "video_id"
    assert format_column_friendly_string("videoId", case = "lower") == "video_id"
    assert format_column_friendly_string("videoId", case="mixed") == "video_Id"

def test_format_dict_keys_output():
    
    raw = [
        {"videoId": "123", "publishedAt": "today"},
        {"videoId": "456", "publishedAt": "yesterday"}
    ]
    # Test lower case transformation
    formatted = format_dict_keys(raw, case="lower")
    assert all("video_id" in d and "published_at" in d for d in formatted)
    assert formatted[0]["video_id"] == "123"

    # Test upper case transformation
    formatted = format_dict_keys(raw, case="upper")
    assert all("VIDEO_ID" in d and "PUBLISHED_AT" in d for d in formatted)
    assert formatted[0]["VIDEO_ID"] == "123"

    # Test mixed case (original capitalization with underscores inserted)
    formatted = format_dict_keys(raw, case="mixed")
    assert all("video_Id" in d and "published_At" in d for d in formatted)
    assert formatted[0]["video_Id"] == "123"
