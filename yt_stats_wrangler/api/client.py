# Main client interface for interacting with Google's Youtube API V3
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
import isodate
import datetime
from typing import List, Dict, Optional, Union

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
    
    def get_channel_statistics(self, channel_id: str, key_format: str = "raw", output_format: str = "raw") -> Union[List[Dict], any]:
        """Fetch high-level statistics for a single channel, such as subscribers, total views, and total posts.
        Input is a YouTube channel ID."""
        if not self.check_quota():
            return []
        result = []
        response = self.youtube.channels().list(part="statistics,snippet", id=channel_id).execute()
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
        """Fetch statistics for multiple channels at once. Input is a list of YouTube Channel IDs. 
        Iterable version of get_channel_statistics_for_channel."""
        results = []

        for channel_id in channel_ids:
            if not self.check_quota():
                print("Quota exhausted.")
                break
            try:
                single = self.get_channel_statistics(channel_id, key_format=key_format, output_format="raw")
                results.extend(single)
            except Exception as e:
                print(f"Error retrieving stats for {channel_id}: {e}")
                continue

        return convert_to_library(results, output_format=output_format)

    def get_uploads_playlist_id(self, channel_id: str) -> Optional[str]:
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

    def get_all_video_details_for_channel(self, channel_id: str, key_format : str = 'raw', output_format: str = "raw"):
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
    
    def get_all_video_details_for_channels(self, channel_ids: List[str], key_format: str = "raw", 
                                           output_format: str = "raw", print_current_channel = True) -> Union[List[Dict], any]:
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

            if print_current_channel: print(f"Fetching videos for channel: {channel_id}")
            try:
                videos = self.get_all_video_details_for_channel(channel_id, key_format=key_format)
                all_videos.extend(videos)
            except Exception as e:
                print(f"Error fetching videos for channel {channel_id}: {e}")
                self.failed_channel_ids.append(channel_id)

        return convert_to_library(all_videos, output_format)


    def get_video_stats(self, video_ids: List[str], key_format: str = 'raw', output_format: str = "raw") -> Union[List[Dict], any]:
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

            response = request.execute()
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
    
    def get_channel_id_from_handle(self, handle: str) -> Optional[str]:
        """
        Retrieve the channel ID associated with a given YouTube handle (e.g., '@cdcodes').

        Note: This method uses the search endpoint, which consumes **100 quota units** per call.
        """
        if not self.check_quota(units=100):
            print("Quota exhausted. Cannot perform search.")
            return None

        try:
            response = self.youtube.search().list(
                part="snippet",
                q=handle,
                type="channel",
                maxResults=1
            ).execute()

            self.quota_used += 100

            if response.get("items"):
                return response["items"][0]["id"]["channelId"]

        except Exception as e:
            print(f"Error retrieving channel ID for handle {handle}: {e}")

        return None
    
    def get_channel_ids_from_handles(self, handles: List[str], print_current_handle = True) -> List[str]:
        """Takes a list of YouTube handles and returns the corresponding list of channel IDs."""
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

            except Exception as e:
                print(f"Error resolving handle {handle}: {e}")
                self.failed_handles.append(handle)

        return channel_ids
    
    def get_quota_used(self):
        # get the current max quota
        return self.quota_used
    
    def set_max_quota(self, limit: int):
        # Set the max quota thjat the client can hit in the session
        self.max_quota = limit
        print(f"Max quota set to {limit}.")

    def get_remaining_quota(self):
        return self.max_quota - self.quota_used

    def reset_quota_used(self):
        # Reset the quota
        self.quota_used = 0