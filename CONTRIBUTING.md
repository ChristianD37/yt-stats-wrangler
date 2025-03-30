# Contributing to yt-stats-wrangler

yt-stats-wrangler is an open-source project that anyone can contribute to. Please read below to learn a bit 
more about best practice when contributing to the package. Cheers!

---

## Development Setup

To run and test the code locally:

1. **Clone the repository**
```bash
git clone https://github.com/ChristianD37/yt-stats-wrangler.git
cd yt-stats-wrangler
```

1. **Create and activate a virtual environment**
```bash
python -m venv yt_venv
yt_venv\Scripts\activate  # Windows
# OR
source yt_venv/bin/activate  # macOS/Linux
```

3. **Install the package in editable mode**
```bash
pip install -e .
```

4. **Install development dependencies**
```bash
pip install -r requirements-dev.txt
```

5. **Set environment variables**

You'll need to generate a Youtube API V3 Key to use and test the package. Please refer to the [official API documentation] (https://developers.google.com/youtube/v3/getting-started) on getting an access key for YouTube API v3

6. **Run the test suite and ensure all tests pass**

```bash
pytest tests/ -v
```

## Testing the package

All tests live in the tests/ directory.
We use `pytest` for unit testing. Make sure tests pass before submitting PRs.

## Branching Strategy

Create a personal branch: dev/your-github-username

Please work off the `development` branch. Submit pull requests into `development`, not `main`. `main` is reserved for stable, production-ready releases.

### Submitting a Pull Request (PR)

+ Push your changes to your personal branch.
+ Open a PR into development.
+ Use a clear title and description.
+ Reference any issues or feature requests (e.g., Fixes #12).
+ Confirm that all tests pass before requesting a review.