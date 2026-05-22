"""
Telegram 데이터 수집 모듈

Telethon 라이브러리를 사용하여 Telegram 채널, 그룹, 메시지를 수집합니다.
"""

import os
import json
import asyncio
from datetime import datetime, timedelta
from dataclasses import dataclass, field, asdict
from typing import Optional, AsyncGenerator, Union
from pathlib import Path

from telethon import TelegramClient
from telethon.tl.types import (
    Channel, Chat, User,
    Message, MessageMediaPhoto, MessageMediaDocument,
    PeerChannel, PeerChat, PeerUser
)
from telethon.tl.functions.channels import GetFullChannelRequest
from telethon.tl.functions.messages import GetHistoryRequest
from loguru import logger


@dataclass
class TelegramMessageData:
    """Telegram 메시지 데이터 구조"""
    message_id: int
    chat_id: int
    chat_title: str
    text: str
    date: datetime
    sender_id: Optional[int] = None
    sender_username: Optional[str] = None
    views: int = 0
    forwards: int = 0
    reply_to_msg_id: Optional[int] = None
    forward_from_chat_id: Optional[int] = None
    forward_from_msg_id: Optional[int] = None
    media_type: Optional[str] = None
    urls: list = field(default_factory=list)
    
    def to_dict(self) -> dict:
        """딕셔너리로 변환"""
        data = asdict(self)
        data['date'] = self.date.isoformat()
        return data


@dataclass  
class TelegramChannelData:
    """Telegram 채널/그룹 데이터 구조"""
    channel_id: int
    title: str
    username: Optional[str]
    date: datetime
    participants_count: int = 0
    description: Optional[str] = None
    is_channel: bool = True
    is_megagroup: bool = False
    linked_chat_id: Optional[int] = None
    
    def to_dict(self) -> dict:
        """딕셔너리로 변환"""
        data = asdict(self)
        data['date'] = self.date.isoformat()
        return data


@dataclass
class TelegramUserData:
    """Telegram 사용자 데이터 구조"""
    user_id: int
    username: Optional[str]
    first_name: str
    last_name: Optional[str] = None
    phone: Optional[str] = None
    is_bot: bool = False
    is_verified: bool = False
    
    def to_dict(self) -> dict:
        """딕셔너리로 변환"""
        return asdict(self)


class TelegramIngester:
    """
    Telegram 데이터 수집기
    
    Telethon을 사용하여 Telegram 채널, 그룹의 메시지와 메타데이터를 수집합니다.
    
    Attributes:
        client: TelegramClient 인스턴스
        output_dir: 수집 데이터 저장 경로
    """
    
    def __init__(
        self,
        api_id: Optional[str] = None,
        api_hash: Optional[str] = None,
        phone: Optional[str] = None,
        session_name: str = "k_fimi_session",
        output_dir: str = "data/raw/telegram"
    ):
        """
        Telegram 수집기 초기화
        
        Args:
            api_id: Telegram API ID
            api_hash: Telegram API Hash
            phone: 전화번호 (인증용)
            session_name: 세션 파일 이름
            output_dir: 수집 데이터 저장 경로
        """
        self.api_id = api_id or os.getenv("TELEGRAM_API_ID")
        self.api_hash = api_hash or os.getenv("TELEGRAM_API_HASH")
        self.phone = phone or os.getenv("TELEGRAM_PHONE")
        
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        self.session_name = session_name
        self._client: Optional[TelegramClient] = None
        
        logger.info(f"TelegramIngester initialized. Output: {self.output_dir}")
    
    @property
    def client(self) -> TelegramClient:
        """TelegramClient 인스턴스 반환"""
        if self._client is None:
            if not self.api_id or not self.api_hash:
                raise ValueError("Telegram API credentials are required")
            
            self._client = TelegramClient(
                str(self.output_dir / self.session_name),
                int(self.api_id),
                self.api_hash
            )
        return self._client
    
    async def connect(self):
        """클라이언트 연결 및 인증"""
        await self.client.start(phone=self.phone)
        logger.info("Telegram client connected")
    
    async def disconnect(self):
        """클라이언트 연결 해제"""
        if self._client:
            await self._client.disconnect()
            logger.info("Telegram client disconnected")
    
    async def get_channel_info(
        self,
        channel_identifier: Union[str, int]
    ) -> Optional[TelegramChannelData]:
        """
        채널/그룹 정보 조회
        
        Args:
            channel_identifier: 채널 username (@channel) 또는 ID
        
        Returns:
            TelegramChannelData 또는 None
        """
        try:
            entity = await self.client.get_entity(channel_identifier)
            
            if isinstance(entity, Channel):
                full_channel = await self.client(GetFullChannelRequest(entity))
                full_info = full_channel.full_chat
                
                channel_data = TelegramChannelData(
                    channel_id=entity.id,
                    title=entity.title,
                    username=entity.username,
                    date=entity.date,
                    participants_count=full_info.participants_count or 0,
                    description=full_info.about,
                    is_channel=not entity.megagroup,
                    is_megagroup=entity.megagroup,
                    linked_chat_id=full_info.linked_chat_id
                )
                
                logger.info(f"Fetched channel info: {entity.title}")
                return channel_data
            
            elif isinstance(entity, Chat):
                channel_data = TelegramChannelData(
                    channel_id=entity.id,
                    title=entity.title,
                    username=None,
                    date=entity.date,
                    participants_count=entity.participants_count or 0,
                    is_channel=False,
                    is_megagroup=False
                )
                return channel_data
                
        except Exception as e:
            logger.error(f"Error fetching channel info: {e}")
            return None
    
    async def get_messages(
        self,
        channel_identifier: Union[str, int],
        limit: int = 100,
        offset_date: Optional[datetime] = None,
        min_id: int = 0,
        max_id: int = 0
    ) -> list[TelegramMessageData]:
        """
        채널/그룹 메시지 조회
        
        Args:
            channel_identifier: 채널 username 또는 ID
            limit: 최대 메시지 수
            offset_date: 이 날짜 이전의 메시지만 조회
            min_id: 최소 메시지 ID
            max_id: 최대 메시지 ID
        
        Returns:
            TelegramMessageData 리스트
        """
        messages = []
        
        try:
            entity = await self.client.get_entity(channel_identifier)
            chat_title = getattr(entity, "title", str(channel_identifier))
            
            async for message in self.client.iter_messages(
                entity,
                limit=limit,
                offset_date=offset_date,
                min_id=min_id,
                max_id=max_id
            ):
                if message.text or message.media:
                    msg_data = await self._parse_message(message, entity.id, chat_title)
                    if msg_data:
                        messages.append(msg_data)
            
            logger.info(f"Fetched {len(messages)} messages from {chat_title}")
            
        except Exception as e:
            logger.error(f"Error fetching messages: {e}")
        
        return messages
    
    async def get_messages_by_date_range(
        self,
        channel_identifier: Union[str, int],
        start_date: datetime,
        end_date: datetime,
        limit: int = 10000
    ) -> list[TelegramMessageData]:
        """
        날짜 범위로 메시지 조회
        
        Args:
            channel_identifier: 채널 username 또는 ID
            start_date: 시작 날짜
            end_date: 종료 날짜
            limit: 최대 메시지 수
        
        Returns:
            TelegramMessageData 리스트
        """
        messages = []
        
        try:
            entity = await self.client.get_entity(channel_identifier)
            chat_title = getattr(entity, "title", str(channel_identifier))
            
            async for message in self.client.iter_messages(
                entity,
                limit=limit,
                offset_date=end_date
            ):
                if message.date < start_date:
                    break
                    
                if message.text or message.media:
                    msg_data = await self._parse_message(message, entity.id, chat_title)
                    if msg_data:
                        messages.append(msg_data)
            
            logger.info(f"Fetched {len(messages)} messages from {chat_title} ({start_date} - {end_date})")
            
        except Exception as e:
            logger.error(f"Error fetching messages by date: {e}")
        
        return messages
    
    async def search_messages(
        self,
        channel_identifier: Union[str, int],
        query: str,
        limit: int = 100
    ) -> list[TelegramMessageData]:
        """
        채널 내 메시지 검색
        
        Args:
            channel_identifier: 채널 username 또는 ID
            query: 검색 쿼리
            limit: 최대 결과 수
        
        Returns:
            TelegramMessageData 리스트
        """
        messages = []
        
        try:
            entity = await self.client.get_entity(channel_identifier)
            chat_title = getattr(entity, "title", str(channel_identifier))
            
            async for message in self.client.iter_messages(
                entity,
                limit=limit,
                search=query
            ):
                if message.text or message.media:
                    msg_data = await self._parse_message(message, entity.id, chat_title)
                    if msg_data:
                        messages.append(msg_data)
            
            logger.info(f"Found {len(messages)} messages for query '{query}' in {chat_title}")
            
        except Exception as e:
            logger.error(f"Error searching messages: {e}")
        
        return messages
    
    async def get_channel_participants(
        self,
        channel_identifier: Union[str, int],
        limit: int = 1000
    ) -> list[TelegramUserData]:
        """
        채널/그룹 참가자 목록 조회
        
        Args:
            channel_identifier: 채널 username 또는 ID
            limit: 최대 참가자 수
        
        Returns:
            TelegramUserData 리스트
        """
        users = []
        
        try:
            entity = await self.client.get_entity(channel_identifier)
            
            async for user in self.client.iter_participants(entity, limit=limit):
                user_data = TelegramUserData(
                    user_id=user.id,
                    username=user.username,
                    first_name=user.first_name or "",
                    last_name=user.last_name,
                    phone=user.phone,
                    is_bot=user.bot,
                    is_verified=user.verified
                )
                users.append(user_data)
            
            logger.info(f"Fetched {len(users)} participants")
            
        except Exception as e:
            logger.error(f"Error fetching participants: {e}")
        
        return users
    
    async def get_forwarded_sources(
        self,
        messages: list[TelegramMessageData]
    ) -> dict[int, TelegramChannelData]:
        """
        메시지의 포워딩 출처 채널 정보 조회
        
        Args:
            messages: TelegramMessageData 리스트
        
        Returns:
            {chat_id: TelegramChannelData} 딕셔너리
        """
        source_ids = set()
        
        for msg in messages:
            if msg.forward_from_chat_id:
                source_ids.add(msg.forward_from_chat_id)
        
        sources = {}
        for chat_id in source_ids:
            try:
                channel_info = await self.get_channel_info(chat_id)
                if channel_info:
                    sources[chat_id] = channel_info
            except Exception as e:
                logger.warning(f"Could not fetch source channel {chat_id}: {e}")
        
        return sources
    
    async def _parse_message(
        self,
        message: Message,
        chat_id: int,
        chat_title: str
    ) -> Optional[TelegramMessageData]:
        """메시지 객체 파싱"""
        try:
            # URL 추출
            urls = []
            if message.entities:
                for entity in message.entities:
                    if hasattr(entity, "url"):
                        urls.append(entity.url)
            
            # 미디어 타입
            media_type = None
            if message.media:
                if isinstance(message.media, MessageMediaPhoto):
                    media_type = "photo"
                elif isinstance(message.media, MessageMediaDocument):
                    media_type = "document"
                else:
                    media_type = type(message.media).__name__
            
            # 발신자 정보
            sender_id = None
            sender_username = None
            if message.sender:
                sender_id = message.sender.id
                sender_username = getattr(message.sender, "username", None)
            
            # 포워딩 정보
            forward_from_chat_id = None
            forward_from_msg_id = None
            if message.forward:
                if message.forward.chat_id:
                    forward_from_chat_id = message.forward.chat_id
                if message.forward.channel_post:
                    forward_from_msg_id = message.forward.channel_post
            
            return TelegramMessageData(
                message_id=message.id,
                chat_id=chat_id,
                chat_title=chat_title,
                text=message.text or "",
                date=message.date,
                sender_id=sender_id,
                sender_username=sender_username,
                views=message.views or 0,
                forwards=message.forwards or 0,
                reply_to_msg_id=message.reply_to_msg_id if message.reply_to else None,
                forward_from_chat_id=forward_from_chat_id,
                forward_from_msg_id=forward_from_msg_id,
                media_type=media_type,
                urls=urls
            )
            
        except Exception as e:
            logger.warning(f"Error parsing message {message.id}: {e}")
            return None
    
    def save_messages(self, messages: list[TelegramMessageData], filename: str) -> Path:
        """
        메시지 데이터를 파일로 저장
        
        Args:
            messages: TelegramMessageData 리스트
            filename: 저장할 파일명 (확장자 제외)
        
        Returns:
            저장된 파일 경로
        """
        filepath = self.output_dir / f"{filename}.json"
        
        data = [msg.to_dict() for msg in messages]
        
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        
        logger.info(f"Saved {len(messages)} messages to {filepath}")
        return filepath
    
    def save_channels(self, channels: list[TelegramChannelData], filename: str) -> Path:
        """
        채널 데이터를 파일로 저장
        
        Args:
            channels: TelegramChannelData 리스트
            filename: 저장할 파일명 (확장자 제외)
        
        Returns:
            저장된 파일 경로
        """
        filepath = self.output_dir / f"{filename}.json"
        
        data = [ch.to_dict() for ch in channels]
        
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        
        logger.info(f"Saved {len(channels)} channels to {filepath}")
        return filepath
    
    def load_messages(self, filename: str) -> list[TelegramMessageData]:
        """저장된 메시지 데이터 로드"""
        filepath = self.output_dir / f"{filename}.json"
        
        if not filepath.exists():
            logger.warning(f"File not found: {filepath}")
            return []
        
        with open(filepath, "r", encoding="utf-8") as f:
            data = json.load(f)
        
        messages = []
        for item in data:
            item["date"] = datetime.fromisoformat(item["date"])
            messages.append(TelegramMessageData(**item))
        
        return messages


# 비동기 실행 헬퍼
def run_async(coro):
    """비동기 코루틴 실행 헬퍼"""
    loop = asyncio.get_event_loop()
    return loop.run_until_complete(coro)


# 모듈 테스트용
if __name__ == "__main__":
    from dotenv import load_dotenv
    load_dotenv()
    
    async def main():
        ingester = TelegramIngester()
        await ingester.connect()
        
        try:
            # 테스트: 공개 채널에서 메시지 수집
            # channel = "@example_channel"
            # messages = await ingester.get_messages(channel, limit=10)
            # for msg in messages:
            #     print(f"[{msg.date}] {msg.text[:50]}...")
            pass
            
        finally:
            await ingester.disconnect()
    
    asyncio.run(main())

