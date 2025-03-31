# Main client interface for interacting with Google's Youtube API V3
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
import isodate
import datetime

# Import helper functions within the package
from yt_stats_wrangler.utils.helpers import current_commit_time, format_dict_keys, convert_to_library

class YouTubeDataClient:
    def __init__(self, api_key: str, max_quota : int = -1):
        self.api_key = api_key
        self.youtube = build("youtube", 'v3',developerKey =api_key)
        self.quota_used = 0 # track quota usage across calls
        self.max_quota = max_quota # -1 defaults to no API call limit

    def check_quota(self, units: int = 1) -> bool:
        """Check if calling the next API would exceed the quota."""
        # Negative one assumes the user wants no limit
        if self.max_quota == -1:
            return True
        # Otherwise, check if the quota is exceeded
        if self.quota_used + units > self.max_quota:
            print(f"Quota limit reached: {self.quota_used + units} would exceed max of {self.max_quota}.")
            return False
        return True

    def get_uploads_playlist_id(self, channel_id:str) -> str:
        """Fetch the uploads playlist ID for a given channel.
        This is a secret playlist that can be used to obtain all
        public uploads on a channel. Used as a helper function in
        get_all_video_details method."""
        # Ensure quota hasn't been hit
        if not self.check_quota():
            return None
        response = self.youtube.channels().list(
            part="contentDetails",
            id=channel_id
        ).execute()
        self.quota_used += 1
        return response['items'][0]['contentDetails']['relatedPlaylists']['uploads']

    def get_all_video_details_for_channel(self, channel_id: str, key_format : str = 'raw', output_format: str = "raw") -> list:
        """Function that takes in a channel ID, identifies the channels
        full playlist of uploads, and then extracts the metadata for all videos
        on the channel. Key format can be specified as 'upper', 'lower', or 'mixed'
        to make the dictionary keys more readable."""
        video_details = []
        playlist_id = self.get_uploads_playlist_id(channel_id)
        next_page_token = None

        while True:
            # Ensure quota hasn't been hit, break if it has and return what was collected
            if not self.check_quota():
                break
            response = self.youtube.playlistItems().list(
                part="snippet",
                playlistId=playlist_id,
                maxResults=50,
                pageToken=next_page_token
            ).execute()
            self.quota_used += 1
            for item in response['items']:
                snippet = item['snippet']
                video = {
                    "channelId": channel_id,
                    "videoId": snippet["resourceId"]["videoId"],
                    "publishedAt": snippet["publishedAt"],
                    "title": snippet["title"],
                    "description": snippet["description"],
                    "channelTitle": snippet["channelTitle"],
                    
                }
                video.update(current_commit_time('videoDetails'))
                video_details.append(video)
                

            next_page_token = response.get("nextPageToken")
            if not next_page_token:
                break
        # Fix the key names if asked to
        if key_format != "raw":
            video_details = format_dict_keys(video_details, case=key_format)

        return convert_to_library(video_details, output_format)
    
    def get_all_video_details_for_channels(self, channel_ids: list, key_format: str = "raw", output_format: str = "raw") -> list:
        """Function that takes in a list of channel IDs, identifies the channels'
        full playlist of uploads, and then extracts the metadata for all videos
        on the channel. Key format can be specified as 'upper', 'lower', or 'mixed'
        to make the dictionary keys more readable."""
        all_videos = []
        self.failed_channel_ids =[]
        for channel_id in channel_ids:
            if not self.check_quota():
                print("Quota limit reached. Stopping collection.")
                break

            print(f"Fetching videos for channel: {channel_id}")
            try:
                videos = self.get_all_video_details_for_channel(channel_id, key_format=key_format)
                all_videos.extend(videos)
            except Exception as e:
                print(f"Error fetching videos for channel {channel_id}: {e}")
                self.failed_channel_ids.append(channel_id)

        return convert_to_library(all_videos, output_format)


    def get_video_stats(self, video_ids: list, key_format : str = 'raw', output_format: str = "raw") -> list:
        """Input a list of video IDs, and get a descriptiveb statistics and metrics on the performance of the video.
        Returns views, engagement, metrics, duration, shorts classification and other metadata on the video."""
        all_video_data = []
        for i in range(0, len(video_ids), 50):
            # Ensure quota hasn't been hit, break if it has and return what was collected
            if not self.check_quota():
                break

            chunk = video_ids[i:i + 50]
            response = self.youtube.videos().list(
                part="snippet,statistics,contentDetails",
                id=",".join(chunk)
            ).execute()
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
    
    def get_top_level_video_comments(self, video_id: str, key_format : str = 'raw', output_format: str = "raw") -> list:
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

            response = request.execute()
            self.quota_used += 1
            for item in response.get('items', []):
                # Extract data on top level comments
                snippet = item['snippet']['topLevelComment']['snippet']
                reply_count = item['snippet'].get('totalReplyCount', 0)
                comment = {
                    'videoId': video_id,
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
    
    def get_top_level_comments_for_video_ids(self, video_ids: list, key_format : str = 'raw', output_format: str = "raw") -> list:
        all_comments = []
        self.failed_ids_for_comments = []

        for video_id in video_ids:
            if not self.check_quota():
                print("Quota limit reached. Stopping comment collection.")
                break

            print(f"Fetching comments for video ID: {video_id}")
            try:
                comments = self.get_top_level_video_comments(video_id)
                all_comments.extend(comments)

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
    
    def get_quota_used(self):
        # get the current max quota
        return self.quota_used
    
    def set_max_quota(self, limit: int):
        # Set the max quota thjat the client can hit in the session
        self.max_quota = limit
        print(f"Max quota set to {limit}.")

    def reset_quota_used(self):
        # Reset the quota
        self.quota_used = 0