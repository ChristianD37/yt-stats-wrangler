# yt-stats-wrangler

A flexible and easy-to-use Python package to collect and wrangle YouTube video and channel statistics using the **YouTube Data API v3**.

Built with extensibility and usability in mind, `yt-stats-wrangler` supports a range of outputs (raw JSON, pandas, polars) and offers features for analyzing video metadata, statistics, and comments.

You'll need a developer key for the YouTube API V3 to use this package. To generate an API key for your google developer account, please see the [official YouTube API v3 documentation](https://developers.google.com/youtube/v3/getting-started) for more information

---

## Features

- Gather public video metadata for one or more YouTube channels
- Collect video statistics (views, likes, comments, etc.)
- Retrieve top-level comments from videos
- Output to multiple formats: `raw`, `pandas`, `polars`
- Flexible column formatting: `raw`, `lower_case`, `UPPER_CASE`, `mixedCase`
- Quota tracking support for efficient API usage
- Optional DataFrame utilities (reordering, parsing datetime)

More coming soon!

---

## Installation

```bash
pip install yt-stats-wrangler
```

`yt-stats-wrangler` is designed to work independent of any data libraries in python for users who prefer a lightweight solution. `pandas`, `polars` and `pyspark` are treated as oiptional dependencies. To use this package with those libraries, ensure they are installed in your enviornment or specify their installation like below:

To use with pandas:
```bash
pip install yt-stats-wrangler[pandas]
```

To use with polars:
```bash
pip install yt-stats-wrangler[polars]
```

---

## Quick Start

The following example is a quick start in gathering all videos present on the  [CDCodes YouTube channel](https://www.youtube.com/@cdcodes), and outputting the results into a pandas dataframe with formatted column names.

```python
from yt_stats_wrangler.api.client import YouTubeDataClient
import os

# Get your API key (recommended to store as environment variable)
api_key = os.getenv("YOUTUBE_API_V3_KEY")
client = YouTubeDataClient(api_key=api_key, max_quota=10000) # set to -1 for unlimited

# Get all videos from a channel
videos = client.get_all_video_details_for_channel(
    channel_id="UCB2mKxxXPK3X8SJkAc-db3A",
    key_format="upper",        # Format dictionary keys
    output_format="pandas"     # Output as pandas DataFrame
)

print(videos.head())
```

---

## Supported Methods

| Method | Description |
|--------|-------------|
| `get_all_video_details_for_channel(channel_id)` | Fetch video metadata for a single channel |
| `get_all_video_details_for_channels(channel_ids)` | Fetch video metadata for multiple channels |
| `get_video_stats(video_ids)` | Get public statistics for one or more videos |
| `get_top_level_video_comments(video_id)` | Get top-level comments for a video |
| `get_top_level_comments_for_video_ids(video_ids)` | Get top-level comments for multiple videos |

---

## Output Formats

You can return data in one of the following formats:
- `raw`: List of dictionaries (default)
- `pandas`: Requires optional pandas dependency
- `polars`: Requires optional polars dependency

---

## Column Formatting

For user-friendly keys, pass the `key_format` argument:
- `raw`: Keep keys as-is from the API (default)
- `lower`: lowercase with underscores to separate words
- `upper`: UPPERCASE with underscores to separate words
- `mixed`: camel_Case with underscores to separate words

---

## Development & Contributing

Please see the (contribution documentation)[https://github.com/ChristianD37/yt-stats-wrangler/blob/main/CONTRIBUTING.md] for best practice on contributing to the package.


## License

This project has an MIT license. You're welcome to build on this package, integrate it into your own data pipelines, or extend it for custom use cases (e.g., adding other output formats or integrating it into production systems). Just make sure to preserve the license file and give credit in your derived works.  It is open source, open to new contributors and can be used for any purpose (personal, academic, commercial, etc.)
---

## Author

Created and maintained by **Christian Dueñas**  
GitHub: [@ChristianD37](https://github.com/ChristianD37)



---

## Example Notebooks

Check out examples of the package at work in the  [`example_notebooks directory`](https://github.com/ChristianD37/yt-stats-wrangler/tree/main/example_notebooks).

