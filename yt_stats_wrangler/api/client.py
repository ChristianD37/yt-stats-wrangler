# Main client interface for interacting with Google's Youtube API V3
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
import isodate
import datetime
import json
from typing import List, Dict, Optional, Union
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception

# Import helper functions within the package
from yt_stats_wrangler.utils.helpers import current_commit_time, format_dict_keys, convert_to_library


class QuotaExceededError(Exception):
    """Raised when a YouTube API call returns 403 quotaExceeded.

    Attributes:
        keys_remaining (bool): True if a sibling key is still viable
            after rotation. False means all configured keys are spent
            and any active loop in the caller should abort.
    """
    def __init__(self, message: str, keys_remaining: bool = False):
        super().__init__(message)
        self.keys_remaining = keys_remaining


_QUOTA_REASONS = {"quotaExceeded", "dailyLimitExceeded", "rateLimitExceeded"}


def _is_retryable_error(exc: Exception) -> bool:
    """Return True for transient 5xx HTTP errors that warrant a retry."""
    return isinstance(exc, HttpError) and exc.resp.status in (500, 503)


def _quota_exceeded(exc: Exception) -> bool:
    """True if exc is a YouTube 403 caused by quota / rate-limit exhaustion."""
    if not isinstance(exc, HttpError):
        return False
    if exc.resp.status != 403:
        return False
    try:
        body = json.loads(exc.content.decode())
        reasons = {e.get("reason") for e in body.get("error", {}).get("errors", [])}
        return bool(reasons & _QUOTA_REASONS)
    except Exception:
        return False


class YouTubeDataClient:
    def __init__(self, api_key: Union[str, List[str]], max_quota: int = -1):
        if isinstance(api_key, str):
            self._api_keys = [api_key]
        else:
            self._api_keys = list(api_key)
        self._key_index = 0
        self._quota_per_key = [0] * len(self._api_keys)
        self.max_quota = max_quota  # -1 defaults to no API call limit
        self.youtube = build("youtube", "v3", developerKey=self._api_keys[0])

    @property
    def api_key(self) -> str:
        """The currently active API key."""
        return self._api_keys[self._key_index]

    @property
    def quota_used(self) -> int:
        """Quota used by the currently active API key."""
        return self._quota_per_key[self._key_index]

    @quota_used.setter
    def quota_used(self, value: int):
        self._quota_per_key[self._key_index] = value

    def _rotate_key(self) -> bool:
        """Switch to the next API key that still has remaining quota.
        Returns True if a usable key was found, False if all keys are exhausted."""
        for i in range(1, len(self._api_keys)):
            next_index = (self._key_index + i) % len(self._api_keys)
            if self.max_quota == -1 or self._quota_per_key[next_index] < self.max_quota:
                self._key_index = next_index
                self.youtube = build("youtube", "v3", developerKey=self._api_keys[next_index])
                print(f"API key rotated ({self._key_index + 1} of {len(self._api_keys)}).")
                return True
        return False

    def _execute(self, request) -> dict:
        """Execute an API request with:
          - exponential backoff retry on transient 5xx errors
          - explicit detection + rotation on 403 quotaExceeded
        """
        @retry(
            retry=retry_if_exception(_is_retryable_error),
            wait=wait_exponential(multiplier=1, min=2, max=60),
            stop=stop_after_attempt(3),
            reraise=True,
        )
        def _run():
            return request.execute()

        try:
            return _run()
        except HttpError as exc:
            if not _quota_exceeded(exc):
                raise

            # Server says this key is spent — sync our in-memory counter.
            if self.max_quota != -1:
                self._quota_per_key[self._key_index] = self.max_quota

            # Try rotating to a sibling key with budget remaining.
            rotated = len(self._api_keys) > 1 and self._rotate_key()
            msg = (
                f"Key {self._key_index + 1} hit 403 quotaExceeded; "
                f"{'rotated to next key' if rotated else 'all keys exhausted'}."
            )
            raise QuotaExceededError(msg, keys_remaining=rotated) from exc

    def check_quota(self, units: int = 1) -> bool:
        """Check if calling the next API would exceed the quota. If it would,
        and multiple keys are configured, attempt to rotate to the next key."""
        if self.max_quota == -1:
            return True
        if self.quota_used + units <= self.max_quota:
            return True
        # Try rotating to a key with remaining quota
        if len(self._api_keys) > 1 and self._rotate_key():
            return True
        print(f"Quota limit reached on all keys ({self.quota_used + units} would exceed max of {self.max_quota}).")
        return False

    def get_channel_id_from_handle(self, handle: str) -> Optional[str]:
        """
        Retrieve the channel ID associated with a given YouTube handle (e.g., '@cdcodes').

        Note: This method uses the search endpoint, which consumes **100 quota units** per call.
        Prefer get_channel_id_from_handle_v2 which costs only 1 unit.
        """
        if not self.check_quota(units=100):
            print("Quota exhausted. Cannot perform search.")
            return None

        try:
            request = self.youtube.search().list(
                part="snippet",
                q=handle,
                type="channel",
                maxResults=1
            )
            response = self._execute(request)
            self.quota_used += 100

            if response.get("items"):
                return response["items"][0]["id"]["channelId"]

        except Exception as e:
            print(f"Error retrieving channel ID for handle {handle}: {e}")

        return None

    def get_channel_id_from_handle_v2(self, handle: str) -> Optional[str]:
        """
        Retrieve the channel ID for a YouTube handle using channels.list(forHandle=...).
        Costs 1 quota unit vs 100 for the search-based get_channel_id_from_handle.
        """
        if not self.check_quota():
            print("Quota exhausted. Cannot resolve handle.")
            return None
        try:
            request = self.youtube.channels().list(part="id", forHandle=handle)
            response = self._execute(request)
            self.quota_used += 1
            if response.get("items"):
                return response["items"][0]["id"]
        except Exception as e:
            print(f"Error retrieving channel ID for handle {handle}: {e}")
        return None

    def get_channel_ids_from_handles(self, handles: List[str], print_current_handle = True) -> List[str]:
        """Takes a list of YouTube handles and returns the corresponding list of channel IDs.
        Uses the search endpoint (100 units/handle). Prefer get_channel_ids_from_handles_v2."""
        channel_ids = []
        self.failed_handles = []

        for handle in handles:
            if not self.check_quota():
                print("Quota limit reached. Stopping handle conversion.")
                break

            if print_current_handle: print(f"Resolving handle: {handle}")
            try:
                channel_id = self.get_channel_id_from_handle(handle)
                if channel_id:
                    channel_ids.append(channel_id)
                else:
                    self.failed_handles.append(handle)

            except QuotaExceededError as exc:
                print(f"  {exc}")
                if not exc.keys_remaining:
                    break
                continue

            except Exception as e:
                print(f"Error resolving handle {handle}: {e}")
                self.failed_handles.append(handle)

        return channel_ids

    def get_channel_ids_from_handles_v2(self, handles: List[str], print_current_handle: bool = True) -> List[str]:
        """Takes a list of YouTube handles and returns the corresponding list of channel IDs.
        Uses channels.list(forHandle=...) at 1 unit/handle — 100x cheaper than get_channel_ids_from_handles."""
        channel_ids = []
        self.failed_handles = []

        for handle in handles:
            if not self.check_quota():
                print("Quota limit reached. Stopping handle conversion.")
                break

            if print_current_handle: print(f"Resolving handle: {handle}")
            try:
                channel_id = self.get_channel_id_from_handle_v2(handle)
                if channel_id:
                    channel_ids.append(channel_id)
                else:
                    self.failed_handles.append(handle)

            except QuotaExceededError as exc:
                print(f"  {exc}")
                if not exc.keys_remaining:
                    break
                continue

            except Exception as e:
                print(f"Error resolving handle {handle}: {e}")
                self.failed_handles.append(handle)

        return channel_ids

    def get_channel_statistics(self, channel_id: str, key_format: str = "raw", output_format: str = "raw") -> Union[List[Dict], any]:
        """Fetch high-level statistics for a single channel, such as subscribers, total views, and total posts.
        Input is a YouTube channel ID."""
        if not self.check_quota():
            return []
        result = []
        request = self.youtube.channels().list(part="statistics,snippet", id=channel_id)
        response = self._execute(request)
        self.quota_used += 1

        if response["items"]:
            item = response["items"][0]
            channel_data = {
                "channelId": channel_id,
                "channelName": item["snippet"]["title"],
                "subscribers": int(item["statistics"].get("subscriberCount", 0)),
                "totalChannelViews": int(item["statistics"].get("viewCount", 0)),
                "totalPosts": int(item["statistics"].get("videoCount", 0)),
            }
            channel_data.update(current_commit_time("channelStats"))
            result.append(channel_data)
            if key_format != "raw":
                result = format_dict_keys(result, case=key_format)
            return convert_to_library(result, output_format=output_format)

        return [] if output_format == "raw" else convert_to_library([], output_format=output_format)

    def get_channel_statistics_for_channels(self, channel_ids: List[str], key_format: str = "raw", output_format: str = "raw") -> Union[List[Dict], any]:
        """Fetch statistics for multiple channels. Batches up to 50 IDs per API call (1 unit per 50 channels).
        Iterable version of get_channel_statistics."""
        results = []

        for i in range(0, len(channel_ids), 50):
            chunk = channel_ids[i:i + 50]
            if not self.check_quota():
                print("Quota exhausted.")
                break
            try:
                request = self.youtube.channels().list(part="statistics,snippet", id=",".join(chunk))
                response = self._execute(request)
                self.quota_used += 1
                for item in response.get("items", []):
                    channel_data = {
                        "channelId": item["id"],
                        "channelName": item["snippet"]["title"],
                        "subscribers": int(item["statistics"].get("subscriberCount", 0)),
                        "totalChannelViews": int(item["statistics"].get("viewCount", 0)),
                        "totalPosts": int(item["statistics"].get("videoCount", 0)),
                    }
                    channel_data.update(current_commit_time("channelStats"))
                    results.append(channel_data)

            except QuotaExceededError as exc:
                print(f"  {exc}")
                if not exc.keys_remaining:
                    break
                continue

            except Exception as e:
                print(f"Error retrieving stats for channel chunk: {e}")

        if key_format != "raw":
            results = format_dict_keys(results, case=key_format)
        return convert_to_library(results, output_format=output_format)

    def get_uploads_playlist_id(self, channel_id: str) -> Optional[str]:
        """Fetch the uploads playlist ID for a given channel.
        This is a secret playlist that can be used to obtain all
        public uploads on a channel. Used as a helper function in
        get_all_video_details method."""
        # Ensure quota hasn't been hit
        if not self.check_quota():
            return None
        request = self.youtube.channels().list(
            part="contentDetails",
            id=channel_id
        )
        response = self._execute(request)
        self.quota_used += 1
        return response['items'][0]['contentDetails']['relatedPlaylists']['uploads']

    def get_all_video_details_for_channel(self, channel_id: str, key_format: str = 'raw',
                                          output_format: str = "raw",
                                          published_after: Optional[str] = None,
                                          get_playlist_id_from_api: bool = False):
        """Function that takes in a channel ID, identifies the channels
        full playlist of uploads, and then extracts the metadata for all videos
        on the channel. Key format can be specified as 'upper', 'lower', or 'mixed'
        to make the dictionary keys more readable.

        Args:
            published_after: ISO 8601 timestamp (e.g. '2024-01-01T00:00:00Z'). When provided,
                pagination stops as soon as a video older than this date is encountered,
                avoiding a full scan for incremental collection runs.
            get_playlist_id_from_api: If False (default), the uploads playlist ID is derived
                directly from the channel ID by swapping the 'UC' prefix for 'UU', saving
                1 quota unit per channel. Set to True to fetch it via the API instead.
        """
        video_details = []
        if get_playlist_id_from_api:
            playlist_id = self.get_uploads_playlist_id(channel_id)
        else:
            playlist_id = "UU" + channel_id[2:]
        next_page_token = None
        stop_early = False

        while True:
            # Ensure quota hasn't been hit, break if it has and return what was collected
            if not self.check_quota():
                break
            request = self.youtube.playlistItems().list(
                part="snippet",
                playlistId=playlist_id,
                maxResults=50,
                pageToken=next_page_token
            )
            response = self._execute(request)
            self.quota_used += 1
            for item in response['items']:
                snippet = item['snippet']
                published_at = snippet["publishedAt"]
                # Videos are returned newest-first; stop once we pass the cutoff
                if published_after and published_at <= published_after:
                    stop_early = True
                    break
                video = {
                    "channelId": channel_id,
                    "videoId": snippet["resourceId"]["videoId"],
                    "publishedAt": published_at,
                    "title": snippet["title"],
                    "description": snippet["description"],
                    "channelTitle": snippet["channelTitle"],
                }
                video.update(current_commit_time('videoDetails'))
                video_details.append(video)

            next_page_token = response.get("nextPageToken")
            if not next_page_token or stop_early:
                break
        # Fix the key names if asked to
        if key_format != "raw":
            video_details = format_dict_keys(video_details, case=key_format)

        return convert_to_library(video_details, output_format)

    def get_all_video_details_for_channels(self, channel_ids: List[str], key_format: str = "raw",
                                           output_format: str = "raw", print_current_channel: bool = True,
                                           published_after: Optional[str] = None,
                                           get_playlist_id_from_api: bool = False) -> Union[List[Dict], any]:
        """Function that takes in a list of channel IDs, identifies the channels'
        full playlist of uploads, and then extracts the metadata for all videos
        on the channel. Key format can be specified as 'upper', 'lower', or 'mixed'
        to make the dictionary keys more readable.

        Args:
            published_after: ISO 8601 timestamp passed through to get_all_video_details_for_channel
                to short-circuit pagination for incremental runs.
            get_playlist_id_from_api: Passed through to get_all_video_details_for_channel.
                Defaults to False (derive playlist ID from channel ID without an API call).
        """
        all_videos = []
        self.failed_channel_ids = []
        for channel_id in channel_ids:
            if not self.check_quota():
                print("Quota limit reached. Stopping collection.")
                break

            if print_current_channel: print(f"Fetching videos for channel: {channel_id}")
            try:
                videos = self.get_all_video_details_for_channel(
                    channel_id, key_format=key_format, published_after=published_after,
                    get_playlist_id_from_api=get_playlist_id_from_api
                )
                all_videos.extend(videos)

            except QuotaExceededError as exc:
                print(f"  {exc}")
                if not exc.keys_remaining:
                    break
                continue

            except Exception as e:
                print(f"Error fetching videos for channel {channel_id}: {e}")
                self.failed_channel_ids.append(channel_id)

        return convert_to_library(all_videos, output_format)


    def get_video_stats(self, video_ids: List[str], key_format: str = 'raw', output_format: str = "raw") -> Union[List[Dict], any]:
        """Input a list of video IDs, and get descriptive statistics and metrics on the performance of the video.
        Returns views, engagement, metrics, duration, shorts classification and other metadata on the video."""
        all_video_data = []
        for i in range(0, len(video_ids), 50):
            # Ensure quota hasn't been hit, break if it has and return what was collected
            if not self.check_quota():
                break

            chunk = video_ids[i:i + 50]
            request = self.youtube.videos().list(
                part="snippet,statistics,contentDetails",
                id=",".join(chunk)
            )
            response = self._execute(request)
            self.quota_used += 1

            for item in response.get("items", []):
                duration = item["contentDetails"].get("duration", "PT0S")
                seconds = int(isodate.parse_duration(duration).total_seconds())
                video_stats = {
                    "videoId": item["id"],
                    "title": item["snippet"].get("title"),
                    "description": item["snippet"].get("description"),
                    "publishedAt": item["snippet"].get("publishedAt"),
                    "channelId": item["snippet"].get("channelId"),
                    "channelTitle": item["snippet"].get("channelTitle"),
                    "tags": item["snippet"].get("tags", []),
                    "categoryId": item["snippet"].get("categoryId"),
                    "viewCount": int(item["statistics"].get("viewCount", 0)),
                    "likeCount": int(item["statistics"].get("likeCount", 0)),
                    "commentCount": int(item["statistics"].get("commentCount", 0)),
                    "duration_seconds": seconds,
                    "definition": item["contentDetails"].get("definition"),
                    "isShort": seconds <= 60,
                }
                video_stats.update(current_commit_time('videoStats'))
                all_video_data.append(video_stats)
        # Fix the key names if asked to
        if key_format != "raw":
            all_video_data = format_dict_keys(all_video_data, case=key_format)

        return convert_to_library(all_video_data, output_format)

    def get_top_level_video_comments(self, video_id: str, key_format: str = 'raw', output_format: str = "raw") -> Union[List[Dict], any]:
        """Retrieve all top-level comments for a given video ID. Will not return nested comments."""
        comments = []
        request = self.youtube.commentThreads().list(
            part="snippet",
            videoId=video_id,
            textFormat="plainText",
            maxResults=100 # extract 100 comments per unit
        )

        while request:
            # Ensure quota hasn't been hit, break if it has and return what was collected
            if not self.check_quota():
                break

            response = self._execute(request)
            self.quota_used += 1
            for item in response.get('items', []):
                # Extract data on top level comments
                top_comment = item['snippet']['topLevelComment']
                snippet = item['snippet']['topLevelComment']['snippet']
                reply_count = item['snippet'].get('totalReplyCount', 0)
                comment = {
                    'videoId': video_id,
                    'commentId': top_comment['id'],
                    'author': snippet.get("authorDisplayName"),
                    'text': snippet.get("textDisplay"),
                    'publishedAt': snippet.get("publishedAt"),
                    'likeCount': snippet.get("likeCount", 0),
                    'replyCount': reply_count
                }
                comment.update(current_commit_time('videoTopLevelComments'))
                comments.append(comment)

            request = self.youtube.commentThreads().list_next(request, response)
        # Fix the key names if asked to
        if key_format != "raw":
            comments = format_dict_keys(comments, case=key_format)

        return convert_to_library(comments, output_format)

    def get_top_level_comments_for_video_ids(self, video_ids: List[str], key_format : str = 'raw',
                                              output_format: str = "raw", print_current_channel = True) -> Union[List[Dict], any]:
        all_comments = []
        self.failed_ids_for_comments = []

        for video_id in video_ids:
            if not self.check_quota():
                print("Quota limit reached. Stopping comment collection.")
                break

            if print_current_channel: print(f"Fetching comments for video ID: {video_id}")
            try:
                comments = self.get_top_level_video_comments(video_id)
                all_comments.extend(comments)

            except QuotaExceededError as exc:
                print(f"  {exc}")
                if not exc.keys_remaining:
                    break
                continue

            except HttpError as e:
                self.quota_used += 1
                print(f"[HttpError] Video {video_id}: {e}")
                self.failed_ids_for_comments.append(video_id)

            except Exception as e:
                print(f"[Exception] Video {video_id}: {e}")
                self.failed_ids_for_comments.append(video_id)

        if key_format != "raw":
            all_comments = format_dict_keys(all_comments, case=key_format)

        return convert_to_library(all_comments, output_format) # or return all_comments, failed_ids

    def get_replies_to_comment(self, parent_comment_id: str) -> List[Dict]:
        """Fetch all replies to a top-level comment using its comment ID. This is a helper function that is used
        in the get_all_video_comments method to gather comment replies and handle nested comments."""
        replies = []

        request = self.youtube.comments().list(
            part="snippet",
            parentId=parent_comment_id,
            textFormat="plainText",
            maxResults=100
        )

        while request:
            if not self.check_quota():
                break

            response = self._execute(request)
            self.quota_used += 1

            for item in response.get("items", []):
                snippet = item["snippet"]
                reply = {
                    "commentId": item["id"],
                    "parentId": parent_comment_id,
                    "author": snippet.get("authorDisplayName"),
                    "text": snippet.get("textDisplay"),
                    "publishedAt": snippet.get("publishedAt"),
                    "likeCount": snippet.get("likeCount", 0),
                    "videoId": snippet.get("videoId")
                }
                reply.update(current_commit_time("videoAllComments"))
                replies.append(reply)

            request = self.youtube.comments().list_next(request, response)

        return replies

    def get_all_video_comments(self, video_id: str, key_format: str = 'raw',
                                       output_format: str = "raw") -> Union[List[Dict], any]:
        """Fetch all comments (top-level and nested) for a video. Takes in a singular Video ID and returns
        all comments left on that video, including replies to other comments."""
        all_comments = []

        request = self.youtube.commentThreads().list(
            part="snippet",
            videoId=video_id,
            textFormat="plainText",
            maxResults=100
        )

        while request:
            if not self.check_quota():
                break

            response = self._execute(request)
            self.quota_used += 1

            for item in response.get("items", []):
                top_snippet = item['snippet']['topLevelComment']['snippet']
                top_id = item['snippet']['topLevelComment']['id']
                reply_count = item['snippet'].get('totalReplyCount', 0)

                # Top-level comment
                comment = {
                    'commentId': top_id,
                    'videoId': video_id,
                    'author': top_snippet.get("authorDisplayName"),
                    'text': top_snippet.get("textDisplay"),
                    'publishedAt': top_snippet.get("publishedAt"),
                    'likeCount': top_snippet.get("likeCount", 0),
                    'replyCount': reply_count,
                    'parentId': None
                }
                comment.update(current_commit_time("videoAllComments"))
                all_comments.append(comment)

                # For each comment, get any replies if they exist and append the data onto the comment output
                if reply_count > 0:
                    replies = self.get_replies_to_comment(top_id)
                    all_comments.extend(replies)

            request = self.youtube.commentThreads().list_next(request, response)
        # Format keys according to user specification
        if key_format != "raw":
            all_comments = format_dict_keys(all_comments, case=key_format)
        # Format output according to specified library structure, and return the output
        return convert_to_library(all_comments, output_format)

    def get_all_comments_for_video_ids(self, video_ids: List[str], key_format: str = 'raw',
                                    output_format: str = "raw", print_current_video: bool = True) -> Union[List[Dict], any]:
        """Fetches all comments (top-level and nested) for multiple videos IDs. Input is a list of video IDs. Output is all comments
        on the corresponding videos, including replies to other comments."""
        all_comments = []
        self.failed_ids_for_all_comments = []

        for video_id in video_ids:
            if not self.check_quota():
                print("Quota limit reached. Stopping comment collection.")
                break

            if print_current_video:
                print(f"Fetching all comments for video ID: {video_id}")

            try:
                comments = self.get_all_video_comments(video_id, key_format="raw", output_format="raw")
                all_comments.extend(comments)

            except QuotaExceededError as exc:
                print(f"  {exc}")
                if not exc.keys_remaining:
                    break
                continue

            except HttpError as e:
                self.quota_used += 1
                print(f"[HttpError] Video {video_id}: {e}")
                self.failed_ids_for_all_comments.append(video_id)

            except Exception as e:
                print(f"[Exception] Video {video_id}: {e}")
                self.failed_ids_for_all_comments.append(video_id)

        if key_format != "raw":
            all_comments = format_dict_keys(all_comments, case=key_format)

        return convert_to_library(all_comments, output_format)

    def get_quota_used(self) -> int:
        """Return quota used by the currently active API key."""
        return self.quota_used

    def get_all_quota_used(self) -> List[int]:
        """Return quota used by each API key as a list (index matches key order)."""
        return list(self._quota_per_key)

    def set_max_quota(self, limit: int):
        # Set the max quota that the client can hit in the session
        self.max_quota = limit
        print(f"Max quota set to {limit}.")

    def get_remaining_quota(self) -> int:
        """Return remaining quota for the currently active API key."""
        return self.max_quota - self.quota_used

    def reset_quota_used(self):
        """Reset quota counters for all API keys."""
        self._quota_per_key = [0] * len(self._api_keys)
        self._key_index = 0
        self.youtube = build("youtube", "v3", developerKey=self._api_keys[0])
