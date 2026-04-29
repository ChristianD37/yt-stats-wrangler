# Changelog

All notable changes to this project are documented here.

---

## [0.3.0] - 2026-04-29

### Added
- `get_channel_id_from_handle_v2()` and `get_channel_ids_from_handles_v2()` using `channels.list(forHandle=...)` — 1 quota unit per handle vs 100 for the search-based v1 methods.
- `published_after` parameter on `get_all_video_details_for_channel()` and `get_all_video_details_for_channels()` to short-circuit pagination for incremental collection runs.
- API key rotation: `api_key` now accepts a `List[str]`; when one key's quota is exhausted the client automatically rotates to the next available key.
- `get_all_quota_used()` method to inspect per-key quota consumption.
- `tenacity` retry with exponential backoff on transient HTTP 500/503 errors via internal `_execute()` helper.

### Changed
- `get_channel_statistics_for_channels()` now batches up to 50 channel IDs per API call (1 unit per 50 channels, down from 1 unit per channel).
- `current_commit_time()` now produces UTC-aware ISO 8601 timestamps (`datetime.now(timezone.utc).isoformat()`).
- `get_channel_id_from_handle()` and `get_channel_ids_from_handles()` marked as deprecated in favour of v2 equivalents.
- `reset_quota_used()` now resets counters for all configured keys and reverts to the first key.
- `tenacity` added as a core dependency.
- Example notebook updated with v2 handle methods, `published_after` usage, and key rotation examples.

---

## [0.2.0] - 2025-04-01

### Added
- `get_channel_statistics()` and `get_channel_statistics_for_channels()` methods for fetching subscriber counts, total views, and total posts.
- `get_channel_id_from_handle()` and `get_channel_ids_from_handles()` for resolving YouTube handles to channel IDs.
- `get_all_video_comments()` for retrieving both top-level and nested comments.
- `get_replies_to_comment()` helper method to support nested comment extraction.
- `get_all_comments_for_video_ids()` for gathering all comments across multiple videos.
- Comment ID and parent ID now included in comment output.
- Tests for all new methods.
- Documentation added to method table in README, including quota estimates.

### Changed
- `get_channel_statistics()` now returns a single dictionary instead of a list of one item.
- Improved formatting of comment and channel output keys.
- `convert_to_library()` now consistently handles different output formats (raw, pandas, polars).
- Expanded README with clearer examples and testing setup.

---

## [0.1.1] - 2025-03-31

### Fixed
- Corrected PEP 625 naming issue in source distribution for PyPI (renamed from `yt-stats-wrangler` to `yt_stats_wrangler`).

---

## [0.1.0] - 2025-03-30

### Added
- Initial release.
- Core functionality for:
  - Fetching video metadata
  - Fetching video statistics
  - Fetching top-level comments (single or multiple videos)
- Output support for `raw`, `pandas`, `polars`, and optional `pyspark`.
- Quota management and enforcement within API client.
- Test suite with Pytest.
- Example Jupyter notebook: `example_notebooks/example_usage.ipynb`.
