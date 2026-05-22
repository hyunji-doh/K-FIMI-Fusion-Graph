# Data Ingestion Module
"""
데이터 수집 모듈: 다양한 소셜 미디어 플랫폼에서 데이터를 수집합니다.
"""

# CSV Ingester (의존성 없음)
from .csv_ingest import CSVIngester, PostData, AccountData, load_sample_data

# 선택적 import (API 라이브러리 필요)
try:
    from .twitter_ingest import TwitterIngester
except ImportError:
    TwitterIngester = None

try:
    from .youtube_ingest import YouTubeIngester
except ImportError:
    YouTubeIngester = None

try:
    from .telegram_ingest import TelegramIngester
except ImportError:
    TelegramIngester = None

__all__ = [
    "CSVIngester",
    "PostData",
    "AccountData",
    "load_sample_data",
    "TwitterIngester",
    "YouTubeIngester", 
    "TelegramIngester",
]

