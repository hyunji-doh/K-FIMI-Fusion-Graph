"""
Twitter/X 데이터 수집 모듈

X/Twitter API v2를 사용하여 트윗, 사용자, 관계 데이터를 수집합니다.
"""

import os
import json
import asyncio
from datetime import datetime, timedelta
from dataclasses import dataclass, field, asdict
from typing import Optional, AsyncGenerator
from pathlib import Path

import tweepy
from tweepy import StreamingClient, StreamRule
import pandas as pd
from loguru import logger


@dataclass
class TweetData:
    """트윗 데이터 구조"""
    tweet_id: str
    text: str
    author_id: str
    created_at: datetime
    retweet_count: int = 0
    like_count: int = 0
    reply_count: int = 0
    quote_count: int = 0
    language: Optional[str] = None
    source: Optional[str] = None
    conversation_id: Optional[str] = None
    in_reply_to_user_id: Optional[str] = None
    referenced_tweets: list = field(default_factory=list)
    urls: list = field(default_factory=list)
    hashtags: list = field(default_factory=list)
    mentions: list = field(default_factory=list)
    media: list = field(default_factory=list)
    
    def to_dict(self) -> dict:
        """딕셔너리로 변환"""
        data = asdict(self)
        data['created_at'] = self.created_at.isoformat()
        return data


@dataclass
class TwitterUserData:
    """트위터 사용자 데이터 구조"""
    user_id: str
    username: str
    name: str
    created_at: datetime
    followers_count: int = 0
    following_count: int = 0
    tweet_count: int = 0
    verified: bool = False
    description: Optional[str] = None
    location: Optional[str] = None
    profile_image_url: Optional[str] = None
    
    def to_dict(self) -> dict:
        """딕셔너리로 변환"""
        data = asdict(self)
        data['created_at'] = self.created_at.isoformat()
        return data


class TwitterIngester:
    """
    Twitter/X 데이터 수집기
    
    API v2를 사용하여 트윗, 사용자 정보, 관계 데이터를 수집합니다.
    
    Attributes:
        client: Tweepy Client 인스턴스
        output_dir: 수집 데이터 저장 경로
    """
    
    def __init__(
        self,
        bearer_token: Optional[str] = None,
        api_key: Optional[str] = None,
        api_secret: Optional[str] = None,
        access_token: Optional[str] = None,
        access_secret: Optional[str] = None,
        output_dir: str = "data/raw/twitter"
    ):
        """
        Twitter 수집기 초기화
        
        Args:
            bearer_token: Twitter API Bearer Token
            api_key: API Key (OAuth 1.0a)
            api_secret: API Secret
            access_token: Access Token
            access_secret: Access Token Secret
            output_dir: 수집 데이터 저장 경로
        """
        self.bearer_token = bearer_token or os.getenv("TWITTER_BEARER_TOKEN")
        self.api_key = api_key or os.getenv("TWITTER_API_KEY")
        self.api_secret = api_secret or os.getenv("TWITTER_API_SECRET")
        self.access_token = access_token or os.getenv("TWITTER_ACCESS_TOKEN")
        self.access_secret = access_secret or os.getenv("TWITTER_ACCESS_SECRET")
        
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        self._client: Optional[tweepy.Client] = None
        self._stream_client: Optional[StreamingClient] = None
        
        logger.info(f"TwitterIngester initialized. Output: {self.output_dir}")
    
    @property
    def client(self) -> tweepy.Client:
        """Tweepy Client 인스턴스 반환 (지연 초기화)"""
        if self._client is None:
            self._client = tweepy.Client(
                bearer_token=self.bearer_token,
                consumer_key=self.api_key,
                consumer_secret=self.api_secret,
                access_token=self.access_token,
                access_token_secret=self.access_secret,
                wait_on_rate_limit=True
            )
        return self._client
    
    def search_tweets(
        self,
        query: str,
        max_results: int = 100,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        language: Optional[str] = None
    ) -> list[TweetData]:
        """
        트윗 검색
        
        Args:
            query: 검색 쿼리 (Twitter 검색 문법 지원)
            max_results: 최대 결과 수 (10-100)
            start_time: 검색 시작 시간
            end_time: 검색 종료 시간
            language: 언어 필터 (예: 'ko', 'en')
        
        Returns:
            TweetData 리스트
        """
        if language:
            query = f"{query} lang:{language}"
        
        tweet_fields = [
            "id", "text", "author_id", "created_at",
            "public_metrics", "lang", "source",
            "conversation_id", "in_reply_to_user_id",
            "referenced_tweets", "entities"
        ]
        
        expansions = ["author_id", "referenced_tweets.id"]
        
        try:
            response = self.client.search_recent_tweets(
                query=query,
                max_results=min(max_results, 100),
                start_time=start_time,
                end_time=end_time,
                tweet_fields=tweet_fields,
                expansions=expansions
            )
            
            tweets = self._parse_tweets(response)
            logger.info(f"Fetched {len(tweets)} tweets for query: {query}")
            return tweets
            
        except tweepy.TweepyException as e:
            logger.error(f"Twitter API error: {e}")
            return []
    
    def get_user_tweets(
        self,
        user_id: str,
        max_results: int = 100,
        exclude_retweets: bool = False
    ) -> list[TweetData]:
        """
        특정 사용자의 트윗 조회
        
        Args:
            user_id: 사용자 ID
            max_results: 최대 결과 수
            exclude_retweets: 리트윗 제외 여부
        
        Returns:
            TweetData 리스트
        """
        tweet_fields = [
            "id", "text", "author_id", "created_at",
            "public_metrics", "lang", "source",
            "conversation_id", "referenced_tweets", "entities"
        ]
        
        exclude = ["retweets"] if exclude_retweets else None
        
        try:
            response = self.client.get_users_tweets(
                id=user_id,
                max_results=min(max_results, 100),
                tweet_fields=tweet_fields,
                exclude=exclude
            )
            
            return self._parse_tweets(response)
            
        except tweepy.TweepyException as e:
            logger.error(f"Error fetching user tweets: {e}")
            return []
    
    def get_user_info(self, user_ids: list[str]) -> list[TwitterUserData]:
        """
        사용자 정보 조회
        
        Args:
            user_ids: 사용자 ID 리스트
        
        Returns:
            TwitterUserData 리스트
        """
        user_fields = [
            "id", "username", "name", "created_at",
            "public_metrics", "verified", "description",
            "location", "profile_image_url"
        ]
        
        users = []
        
        # 100개씩 배치 처리
        for i in range(0, len(user_ids), 100):
            batch = user_ids[i:i+100]
            
            try:
                response = self.client.get_users(
                    ids=batch,
                    user_fields=user_fields
                )
                
                if response.data:
                    for user in response.data:
                        user_data = TwitterUserData(
                            user_id=user.id,
                            username=user.username,
                            name=user.name,
                            created_at=user.created_at,
                            followers_count=user.public_metrics.get("followers_count", 0),
                            following_count=user.public_metrics.get("following_count", 0),
                            tweet_count=user.public_metrics.get("tweet_count", 0),
                            verified=getattr(user, "verified", False),
                            description=getattr(user, "description", None),
                            location=getattr(user, "location", None),
                            profile_image_url=getattr(user, "profile_image_url", None)
                        )
                        users.append(user_data)
                        
            except tweepy.TweepyException as e:
                logger.error(f"Error fetching user info: {e}")
        
        logger.info(f"Fetched {len(users)} user profiles")
        return users
    
    def get_followers(
        self,
        user_id: str,
        max_results: int = 1000
    ) -> list[str]:
        """
        사용자의 팔로워 ID 목록 조회
        
        Args:
            user_id: 대상 사용자 ID
            max_results: 최대 결과 수
        
        Returns:
            팔로워 사용자 ID 리스트
        """
        follower_ids = []
        
        try:
            paginator = tweepy.Paginator(
                self.client.get_users_followers,
                id=user_id,
                max_results=min(max_results, 1000)
            )
            
            for response in paginator:
                if response.data:
                    follower_ids.extend([user.id for user in response.data])
                    
                if len(follower_ids) >= max_results:
                    break
                    
        except tweepy.TweepyException as e:
            logger.error(f"Error fetching followers: {e}")
        
        return follower_ids[:max_results]
    
    def get_following(
        self,
        user_id: str,
        max_results: int = 1000
    ) -> list[str]:
        """
        사용자가 팔로우하는 계정 ID 목록 조회
        
        Args:
            user_id: 대상 사용자 ID
            max_results: 최대 결과 수
        
        Returns:
            팔로잉 사용자 ID 리스트
        """
        following_ids = []
        
        try:
            paginator = tweepy.Paginator(
                self.client.get_users_following,
                id=user_id,
                max_results=min(max_results, 1000)
            )
            
            for response in paginator:
                if response.data:
                    following_ids.extend([user.id for user in response.data])
                    
                if len(following_ids) >= max_results:
                    break
                    
        except tweepy.TweepyException as e:
            logger.error(f"Error fetching following: {e}")
        
        return following_ids[:max_results]
    
    def get_retweeters(self, tweet_id: str) -> list[str]:
        """
        트윗을 리트윗한 사용자 ID 목록 조회
        
        Args:
            tweet_id: 트윗 ID
        
        Returns:
            리트위터 사용자 ID 리스트
        """
        try:
            response = self.client.get_retweeters(id=tweet_id)
            
            if response.data:
                return [user.id for user in response.data]
            return []
            
        except tweepy.TweepyException as e:
            logger.error(f"Error fetching retweeters: {e}")
            return []
    
    def _parse_tweets(self, response) -> list[TweetData]:
        """API 응답을 TweetData 객체로 파싱"""
        tweets = []
        
        if not response.data:
            return tweets
        
        for tweet in response.data:
            # 엔티티 파싱
            urls = []
            hashtags = []
            mentions = []
            
            if hasattr(tweet, "entities") and tweet.entities:
                entities = tweet.entities
                
                if "urls" in entities:
                    urls = [u.get("expanded_url", u.get("url")) for u in entities["urls"]]
                
                if "hashtags" in entities:
                    hashtags = [h.get("tag") for h in entities["hashtags"]]
                
                if "mentions" in entities:
                    mentions = [m.get("username") for m in entities["mentions"]]
            
            # 참조 트윗 파싱
            referenced = []
            if hasattr(tweet, "referenced_tweets") and tweet.referenced_tweets:
                referenced = [
                    {"type": ref.type, "id": ref.id}
                    for ref in tweet.referenced_tweets
                ]
            
            # 메트릭스
            metrics = getattr(tweet, "public_metrics", {}) or {}
            
            tweet_data = TweetData(
                tweet_id=tweet.id,
                text=tweet.text,
                author_id=tweet.author_id,
                created_at=tweet.created_at,
                retweet_count=metrics.get("retweet_count", 0),
                like_count=metrics.get("like_count", 0),
                reply_count=metrics.get("reply_count", 0),
                quote_count=metrics.get("quote_count", 0),
                language=getattr(tweet, "lang", None),
                source=getattr(tweet, "source", None),
                conversation_id=getattr(tweet, "conversation_id", None),
                in_reply_to_user_id=getattr(tweet, "in_reply_to_user_id", None),
                referenced_tweets=referenced,
                urls=urls,
                hashtags=hashtags,
                mentions=mentions
            )
            tweets.append(tweet_data)
        
        return tweets
    
    def save_tweets(self, tweets: list[TweetData], filename: str) -> Path:
        """
        트윗 데이터를 파일로 저장
        
        Args:
            tweets: TweetData 리스트
            filename: 저장할 파일명 (확장자 제외)
        
        Returns:
            저장된 파일 경로
        """
        filepath = self.output_dir / f"{filename}.json"
        
        data = [tweet.to_dict() for tweet in tweets]
        
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        
        logger.info(f"Saved {len(tweets)} tweets to {filepath}")
        return filepath
    
    def save_users(self, users: list[TwitterUserData], filename: str) -> Path:
        """
        사용자 데이터를 파일로 저장
        
        Args:
            users: TwitterUserData 리스트
            filename: 저장할 파일명 (확장자 제외)
        
        Returns:
            저장된 파일 경로
        """
        filepath = self.output_dir / f"{filename}.json"
        
        data = [user.to_dict() for user in users]
        
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        
        logger.info(f"Saved {len(users)} users to {filepath}")
        return filepath
    
    def load_tweets(self, filename: str) -> list[TweetData]:
        """저장된 트윗 데이터 로드"""
        filepath = self.output_dir / f"{filename}.json"
        
        if not filepath.exists():
            logger.warning(f"File not found: {filepath}")
            return []
        
        with open(filepath, "r", encoding="utf-8") as f:
            data = json.load(f)
        
        tweets = []
        for item in data:
            item["created_at"] = datetime.fromisoformat(item["created_at"])
            tweets.append(TweetData(**item))
        
        return tweets


class TwitterStreamListener(StreamingClient):
    """
    Twitter 스트리밍 클라이언트
    
    실시간 트윗 수집을 위한 스트리밍 API 클라이언트입니다.
    """
    
    def __init__(
        self,
        bearer_token: str,
        output_dir: str = "data/raw/twitter/stream",
        max_tweets: int = 10000
    ):
        super().__init__(bearer_token, wait_on_rate_limit=True)
        
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        self.max_tweets = max_tweets
        self.tweet_count = 0
        self.tweets_buffer: list[dict] = []
        self.buffer_size = 100
    
    def on_tweet(self, tweet):
        """트윗 수신 시 호출"""
        self.tweet_count += 1
        
        tweet_data = {
            "id": tweet.id,
            "text": tweet.text,
            "created_at": datetime.now().isoformat()
        }
        self.tweets_buffer.append(tweet_data)
        
        if len(self.tweets_buffer) >= self.buffer_size:
            self._flush_buffer()
        
        if self.tweet_count >= self.max_tweets:
            logger.info(f"Reached max tweets ({self.max_tweets}). Stopping stream.")
            self.disconnect()
    
    def on_error(self, status_code):
        """에러 발생 시 호출"""
        logger.error(f"Stream error: {status_code}")
        if status_code == 420:  # Rate limit
            return False
        return True
    
    def _flush_buffer(self):
        """버퍼를 파일로 저장"""
        if not self.tweets_buffer:
            return
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filepath = self.output_dir / f"stream_{timestamp}.json"
        
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(self.tweets_buffer, f, ensure_ascii=False, indent=2)
        
        logger.info(f"Flushed {len(self.tweets_buffer)} tweets to {filepath}")
        self.tweets_buffer = []
    
    def add_rules_for_keywords(self, keywords: list[str]):
        """키워드 기반 필터 규칙 추가"""
        rules = [StreamRule(value=kw) for kw in keywords]
        self.add_rules(rules)
        logger.info(f"Added {len(rules)} stream rules")
    
    def start_streaming(self):
        """스트리밍 시작"""
        logger.info("Starting Twitter stream...")
        self.filter(
            tweet_fields=["id", "text", "author_id", "created_at"],
            threaded=True
        )


# 모듈 테스트용
if __name__ == "__main__":
    # 환경변수에서 토큰 로드
    from dotenv import load_dotenv
    load_dotenv()
    
    ingester = TwitterIngester()
    
    # 테스트 검색
    tweets = ingester.search_tweets(
        query="허위정보 OR 가짜뉴스",
        max_results=10,
        language="ko"
    )
    
    for tweet in tweets:
        print(f"[{tweet.created_at}] {tweet.text[:50]}...")

