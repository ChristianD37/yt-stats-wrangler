# Changelog

All notable changes to this project are documented here.

---

## [0.4.2] - 2026-05-12

### Added
- `topicCategories` field on channel stats output: YouTube-assigned Wikipedia-backed topic URLs (e.g. `https://en.wikipedia.org/wiki/Music`), sourced from `topicDetails` part. No additional quota cost.
- `brandingKeywords` field on channel stats output: space-separated keyword string set by the channel creator, sourced from `brandingSettings` part. No additional quota cost.
- Both fields are returned by `get_channel_statistics()` and `get_channel_statistics_for_channels()`.

### Note
- `categoryId` and `tags` were already captured in `get_video_stats()` — no change needed there.

---

## [0.4.1] - 2026-05-06

### Added
- `QuotaExceededError` exception raised when YouTube returns 403 with reason `quotaExceeded`, `dailyLimitExceeded`, or `rateLimitExceeded`. Exposes `keys_remaining: bool` so callers can decide whether to continue iterating.
- `_quota_exceeded()` helper for parsing the 403 error body reason field.
- README section documenting quota exhaustion behavior and `QuotaExceededError` usage.
- `get_playlist_id_from_api` parameter on `get_all_video_details_for_channel()` and `get_all_video_details_for_channels()`. Defaults to `False`, which derives the uploads playlist ID directly from the channel ID (`UC` → `UU` prefix swap) without an API call, saving 1 quota unit per channel. Set to `True` to use the original API-based lookup.

### Fixed
- Quota-exhausted API keys now correctly trigger automatic rotation to the next configured key. Previously, 403 quotaExceeded errors were caught generically and the in-memory `quota_used` counter never incremented, so `check_quota()` kept reporting healthy state and rotation never fired. This caused multi-key clients to silently grind to a halt on a single spent key while a fresh sibling sat unused.
- Batch methods (`get_all_video_details_for_channels`, `get_channel_statistics_for_channels`, `get_top_level_comments_for_video_ids`, `get_all_comments_for_video_ids`, `get_channel_ids_from_handles`, `get_channel_ids_from_handles_v2`) now break their loops cleanly when all configured keys are exhausted, instead of pointlessly iterating through every remaining item.

---

## [0.3.1] - 2026-04-29

### Fixed
- Restored missing `__init__.py` files in `yt_stats_wrangler/api/` and `yt_stats_wrangler/utils/`. Without them, `find_packages()` excluded both subpackages from the installed distribution, causing `ModuleNotFoundError: No module named 'yt_stats_wrangler.api'` on a fresh install.
- Added `tests/test_package_structure.py` to catch this class of packaging regression in CI.

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
