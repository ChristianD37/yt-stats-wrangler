# Main client interface for interacting with Google's Youtube API V3
from googleapiclient.discovery import build
import isodate
import datetime
import pandas as pd

class YouTubeDataClient:
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.youtube = build("youtube", 'v3',developerKey =api_key)

    def get_uploads_playlist_id(self, channel_id:str) -> str:
        """Fetch the uploads playlist ID for a given channel.
        This is a secret playlist that can be used to obtain all
        public uploads on a channel. Used as a helper function in
        get_all_video_details method."""
        response = self.youtube.channels().list(
            part="contentDetails",
            id=channel_id
        ).execute()

        return response['items'][0]['contentDetails']['relatedPlaylists']['uploads']

    def get_all_video_details(self, channel_id: str) -> list:
        """Function that takes in a channel ID, identifies the channels
        full playlist of uploads, and then extracts the metadata for all videos
        on the channel. """
        video_details = []
        playlist_id = self.get_uploads_playlist_id(channel_id)
        next_page_token = None

        while True:
            response = self.youtube.playlistItems().list(
                part="snippet",
                playlistId=playlist_id,
                maxResults=50,
                pageToken=next_page_token
            ).execute()

            for item in response['items']:
                snippet = item['snippet']
                video_details.append({
                    "channelId": channel_id,
                    "videoId": snippet["resourceId"]["videoId"],
                    "publishedAt": snippet["publishedAt"],
                    "title": snippet["title"],
                    "description": snippet["description"],
                    "channelTitle": snippet["channelTitle"]
                })

            next_page_token = response.get("nextPageToken")
            if not next_page_token:
                break

        return video_details

    def get_video_stats(self, video_ids: list) -> pd.DataFrame:
        """Input a list of video IDs, and get a descriptiveb statistics and metrics on the performance of the video.
        Returns views, engagement, metrics, duration, shorts classification and other metadata on the video."""
        all_video_data = []
        for i in range(0, len(video_ids), 50):
            chunk = video_ids[i:i + 50]
            response = self.youtube.videos().list(
                part="snippet,statistics,contentDetails",
                id=",".join(chunk)
            ).execute()

            for item in response.get("items", []):
                duration = item["contentDetails"].get("duration", "PT0S")
                seconds = int(isodate.parse_duration(duration).total_seconds())

                all_video_data.append({
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
                    "commitTime": str(datetime.datetime.now())
                })

        return all_video_data   