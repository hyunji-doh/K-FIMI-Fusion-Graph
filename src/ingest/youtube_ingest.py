"""
YouTube 데이터 수집 모듈

YouTube Data API v3를 사용하여 동영상, 댓글, 채널 데이터를 수집합니다.
"""

import os
import json
from datetime import datetime
from dataclasses import dataclass, field, asdict
from typing import Optional, Generator
from pathlib import Path

from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
import pandas as pd
from loguru import logger


@dataclass
class VideoData:
    """YouTube 동영상 데이터 구조"""
    video_id: str
    title: str
    description: str
    channel_id: str
    channel_title: str
    published_at: datetime
    view_count: int = 0
    like_count: int = 0
    comment_count: int = 0
    duration: Optional[str] = None
    tags: list = field(default_factory=list)
    category_id: Optional[str] = None
    default_language: Optional[str] = None
    thumbnail_url: Optional[str] = None
    
    def to_dict(self) -> dict:
        """딕셔너리로 변환"""
        data = asdict(self)
        data['published_at'] = self.published_at.isoformat()
        return data


@dataclass
class CommentData:
    """YouTube 댓글 데이터 구조"""
    comment_id: str
    video_id: str
    text: str
    author_channel_id: Optional[str]
    author_display_name: str
    published_at: datetime
    like_count: int = 0
    reply_count: int = 0
    parent_id: Optional[str] = None  # 답글인 경우 상위 댓글 ID
    
    def to_dict(self) -> dict:
        """딕셔너리로 변환"""
        data = asdict(self)
        data['published_at'] = self.published_at.isoformat()
        return data


@dataclass
class ChannelData:
    """YouTube 채널 데이터 구조"""
    channel_id: str
    title: str
    description: str
    published_at: datetime
    subscriber_count: int = 0
    video_count: int = 0
    view_count: int = 0
    country: Optional[str] = None
    custom_url: Optional[str] = None
    thumbnail_url: Optional[str] = None
    
    def to_dict(self) -> dict:
        """딕셔너리로 변환"""
        data = asdict(self)
        data['published_at'] = self.published_at.isoformat()
        return data


class YouTubeIngester:
    """
    YouTube 데이터 수집기
    
    YouTube Data API v3를 사용하여 동영상, 댓글, 채널 데이터를 수집합니다.
    
    Attributes:
        youtube: YouTube API 클라이언트
        output_dir: 수집 데이터 저장 경로
    """
    
    def __init__(
        self,
        api_key: Optional[str] = None,
        output_dir: str = "data/raw/youtube"
    ):
        """
        YouTube 수집기 초기화
        
        Args:
            api_key: YouTube Data API 키
            output_dir: 수집 데이터 저장 경로
        """
        self.api_key = api_key or os.getenv("YOUTUBE_API_KEY")
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        self._youtube = None
        
        logger.info(f"YouTubeIngester initialized. Output: {self.output_dir}")
    
    @property
    def youtube(self):
        """YouTube API 클라이언트 반환 (지연 초기화)"""
        if self._youtube is None:
            if not self.api_key:
                raise ValueError("YouTube API key is required")
            self._youtube = build("youtube", "v3", developerKey=self.api_key)
        return self._youtube
    
    def search_videos(
        self,
        query: str,
        max_results: int = 50,
        published_after: Optional[datetime] = None,
        published_before: Optional[datetime] = None,
        region_code: str = "KR",
        relevance_language: str = "ko",
        order: str = "relevance"
    ) -> list[VideoData]:
        """
        동영상 검색
        
        Args:
            query: 검색 쿼리
            max_results: 최대 결과 수 (최대 50)
            published_after: 게시 시작 날짜
            published_before: 게시 종료 날짜
            region_code: 지역 코드
            relevance_language: 관련성 언어
            order: 정렬 기준 (relevance, date, viewCount, rating)
        
        Returns:
            VideoData 리스트
        """
        videos = []
        
        try:
            search_params = {
                "part": "snippet",
                "q": query,
                "type": "video",
                "maxResults": min(max_results, 50),
                "regionCode": region_code,
                "relevanceLanguage": relevance_language,
                "order": order
            }
            
            if published_after:
                search_params["publishedAfter"] = published_after.isoformat() + "Z"
            if published_before:
                search_params["publishedBefore"] = published_before.isoformat() + "Z"
            
            response = self.youtube.search().list(**search_params).execute()
            
            video_ids = [item["id"]["videoId"] for item in response.get("items", [])]
            
            if video_ids:
                videos = self.get_video_details(video_ids)
            
            logger.info(f"Found {len(videos)} videos for query: {query}")
            return videos
            
        except HttpError as e:
            logger.error(f"YouTube API error: {e}")
            return []
    
    def get_video_details(self, video_ids: list[str]) -> list[VideoData]:
        """
        동영상 상세 정보 조회
        
        Args:
            video_ids: 동영상 ID 리스트
        
        Returns:
            VideoData 리스트
        """
        videos = []
        
        # 50개씩 배치 처리
        for i in range(0, len(video_ids), 50):
            batch_ids = video_ids[i:i+50]
            
            try:
                response = self.youtube.videos().list(
                    part="snippet,statistics,contentDetails",
                    id=",".join(batch_ids)
                ).execute()
                
                for item in response.get("items", []):
                    snippet = item["snippet"]
                    statistics = item.get("statistics", {})
                    content_details = item.get("contentDetails", {})
                    
                    # 썸네일 URL 추출
                    thumbnails = snippet.get("thumbnails", {})
                    thumbnail_url = None
                    for quality in ["maxres", "high", "medium", "default"]:
                        if quality in thumbnails:
                            thumbnail_url = thumbnails[quality].get("url")
                            break
                    
                    video = VideoData(
                        video_id=item["id"],
                        title=snippet["title"],
                        description=snippet.get("description", ""),
                        channel_id=snippet["channelId"],
                        channel_title=snippet["channelTitle"],
                        published_at=datetime.fromisoformat(
                            snippet["publishedAt"].replace("Z", "+00:00")
                        ),
                        view_count=int(statistics.get("viewCount", 0)),
                        like_count=int(statistics.get("likeCount", 0)),
                        comment_count=int(statistics.get("commentCount", 0)),
                        duration=content_details.get("duration"),
                        tags=snippet.get("tags", []),
                        category_id=snippet.get("categoryId"),
                        default_language=snippet.get("defaultLanguage"),
                        thumbnail_url=thumbnail_url
                    )
                    videos.append(video)
                    
            except HttpError as e:
                logger.error(f"Error fetching video details: {e}")
        
        return videos
    
    def get_video_comments(
        self,
        video_id: str,
        max_results: int = 100,
        include_replies: bool = True
    ) -> list[CommentData]:
        """
        동영상 댓글 조회
        
        Args:
            video_id: 동영상 ID
            max_results: 최대 결과 수
            include_replies: 답글 포함 여부
        
        Returns:
            CommentData 리스트
        """
        comments = []
        page_token = None
        
        try:
            while len(comments) < max_results:
                response = self.youtube.commentThreads().list(
                    part="snippet,replies",
                    videoId=video_id,
                    maxResults=min(100, max_results - len(comments)),
                    pageToken=page_token,
                    textFormat="plainText"
                ).execute()
                
                for item in response.get("items", []):
                    # 최상위 댓글
                    top_comment = item["snippet"]["topLevelComment"]["snippet"]
                    
                    comment = CommentData(
                        comment_id=item["snippet"]["topLevelComment"]["id"],
                        video_id=video_id,
                        text=top_comment["textDisplay"],
                        author_channel_id=top_comment.get("authorChannelId", {}).get("value"),
                        author_display_name=top_comment["authorDisplayName"],
                        published_at=datetime.fromisoformat(
                            top_comment["publishedAt"].replace("Z", "+00:00")
                        ),
                        like_count=top_comment.get("likeCount", 0),
                        reply_count=item["snippet"].get("totalReplyCount", 0)
                    )
                    comments.append(comment)
                    
                    # 답글 처리
                    if include_replies and "replies" in item:
                        for reply_item in item["replies"]["comments"]:
                            reply_snippet = reply_item["snippet"]
                            
                            reply = CommentData(
                                comment_id=reply_item["id"],
                                video_id=video_id,
                                text=reply_snippet["textDisplay"],
                                author_channel_id=reply_snippet.get("authorChannelId", {}).get("value"),
                                author_display_name=reply_snippet["authorDisplayName"],
                                published_at=datetime.fromisoformat(
                                    reply_snippet["publishedAt"].replace("Z", "+00:00")
                                ),
                                like_count=reply_snippet.get("likeCount", 0),
                                parent_id=reply_snippet.get("parentId")
                            )
                            comments.append(reply)
                
                page_token = response.get("nextPageToken")
                if not page_token:
                    break
                    
        except HttpError as e:
            # 댓글이 비활성화된 경우 등
            if "commentsDisabled" in str(e):
                logger.warning(f"Comments disabled for video: {video_id}")
            else:
                logger.error(f"Error fetching comments: {e}")
        
        logger.info(f"Fetched {len(comments)} comments for video: {video_id}")
        return comments
    
    def get_channel_info(self, channel_ids: list[str]) -> list[ChannelData]:
        """
        채널 정보 조회
        
        Args:
            channel_ids: 채널 ID 리스트
        
        Returns:
            ChannelData 리스트
        """
        channels = []
        
        # 50개씩 배치 처리
        for i in range(0, len(channel_ids), 50):
            batch_ids = channel_ids[i:i+50]
            
            try:
                response = self.youtube.channels().list(
                    part="snippet,statistics",
                    id=",".join(batch_ids)
                ).execute()
                
                for item in response.get("items", []):
                    snippet = item["snippet"]
                    statistics = item.get("statistics", {})
                    
                    # 썸네일 URL
                    thumbnails = snippet.get("thumbnails", {})
                    thumbnail_url = thumbnails.get("default", {}).get("url")
                    
                    channel = ChannelData(
                        channel_id=item["id"],
                        title=snippet["title"],
                        description=snippet.get("description", ""),
                        published_at=datetime.fromisoformat(
                            snippet["publishedAt"].replace("Z", "+00:00")
                        ),
                        subscriber_count=int(statistics.get("subscriberCount", 0)),
                        video_count=int(statistics.get("videoCount", 0)),
                        view_count=int(statistics.get("viewCount", 0)),
                        country=snippet.get("country"),
                        custom_url=snippet.get("customUrl"),
                        thumbnail_url=thumbnail_url
                    )
                    channels.append(channel)
                    
            except HttpError as e:
                logger.error(f"Error fetching channel info: {e}")
        
        logger.info(f"Fetched {len(channels)} channel profiles")
        return channels
    
    def get_channel_videos(
        self,
        channel_id: str,
        max_results: int = 50,
        order: str = "date"
    ) -> list[VideoData]:
        """
        채널의 동영상 목록 조회
        
        Args:
            channel_id: 채널 ID
            max_results: 최대 결과 수
            order: 정렬 기준 (date, viewCount)
        
        Returns:
            VideoData 리스트
        """
        try:
            # 채널의 업로드 플레이리스트 ID 조회
            channel_response = self.youtube.channels().list(
                part="contentDetails",
                id=channel_id
            ).execute()
            
            if not channel_response.get("items"):
                return []
            
            uploads_playlist_id = channel_response["items"][0]["contentDetails"]["relatedPlaylists"]["uploads"]
            
            # 플레이리스트 아이템 조회
            video_ids = []
            page_token = None
            
            while len(video_ids) < max_results:
                playlist_response = self.youtube.playlistItems().list(
                    part="contentDetails",
                    playlistId=uploads_playlist_id,
                    maxResults=min(50, max_results - len(video_ids)),
                    pageToken=page_token
                ).execute()
                
                for item in playlist_response.get("items", []):
                    video_ids.append(item["contentDetails"]["videoId"])
                
                page_token = playlist_response.get("nextPageToken")
                if not page_token:
                    break
            
            # 동영상 상세 정보 조회
            return self.get_video_details(video_ids)
            
        except HttpError as e:
            logger.error(f"Error fetching channel videos: {e}")
            return []
    
    def get_related_videos(
        self,
        video_id: str,
        max_results: int = 25
    ) -> list[VideoData]:
        """
        관련 동영상 조회
        
        Args:
            video_id: 기준 동영상 ID
            max_results: 최대 결과 수
        
        Returns:
            VideoData 리스트
        """
        try:
            response = self.youtube.search().list(
                part="snippet",
                relatedToVideoId=video_id,
                type="video",
                maxResults=min(max_results, 50)
            ).execute()
            
            video_ids = [item["id"]["videoId"] for item in response.get("items", [])]
            
            if video_ids:
                return self.get_video_details(video_ids)
            return []
            
        except HttpError as e:
            logger.error(f"Error fetching related videos: {e}")
            return []
    
    def save_videos(self, videos: list[VideoData], filename: str) -> Path:
        """
        동영상 데이터를 파일로 저장
        
        Args:
            videos: VideoData 리스트
            filename: 저장할 파일명 (확장자 제외)
        
        Returns:
            저장된 파일 경로
        """
        filepath = self.output_dir / f"{filename}.json"
        
        data = [video.to_dict() for video in videos]
        
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        
        logger.info(f"Saved {len(videos)} videos to {filepath}")
        return filepath
    
    def save_comments(self, comments: list[CommentData], filename: str) -> Path:
        """
        댓글 데이터를 파일로 저장
        
        Args:
            comments: CommentData 리스트
            filename: 저장할 파일명 (확장자 제외)
        
        Returns:
            저장된 파일 경로
        """
        filepath = self.output_dir / f"{filename}.json"
        
        data = [comment.to_dict() for comment in comments]
        
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        
        logger.info(f"Saved {len(comments)} comments to {filepath}")
        return filepath
    
    def save_channels(self, channels: list[ChannelData], filename: str) -> Path:
        """
        채널 데이터를 파일로 저장
        
        Args:
            channels: ChannelData 리스트
            filename: 저장할 파일명 (확장자 제외)
        
        Returns:
            저장된 파일 경로
        """
        filepath = self.output_dir / f"{filename}.json"
        
        data = [channel.to_dict() for channel in channels]
        
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        
        logger.info(f"Saved {len(channels)} channels to {filepath}")
        return filepath
    
    def load_videos(self, filename: str) -> list[VideoData]:
        """저장된 동영상 데이터 로드"""
        filepath = self.output_dir / f"{filename}.json"
        
        if not filepath.exists():
            logger.warning(f"File not found: {filepath}")
            return []
        
        with open(filepath, "r", encoding="utf-8") as f:
            data = json.load(f)
        
        videos = []
        for item in data:
            item["published_at"] = datetime.fromisoformat(item["published_at"])
            videos.append(VideoData(**item))
        
        return videos


# 모듈 테스트용
if __name__ == "__main__":
    from dotenv import load_dotenv
    load_dotenv()
    
    ingester = YouTubeIngester()
    
    # 테스트 검색
    videos = ingester.search_videos(
        query="허위정보 팩트체크",
        max_results=5
    )
    
    for video in videos:
        print(f"[{video.published_at}] {video.title}")
        print(f"  Views: {video.view_count}, Likes: {video.like_count}")

