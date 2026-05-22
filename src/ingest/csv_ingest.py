"""
CSV 데이터 수집 모듈

PoC용 CSV 파일에서 소셜 미디어 게시물 데이터를 로드하고 처리합니다.
"""

import ast
import json
from datetime import datetime
from dataclasses import dataclass, field, asdict
from typing import Optional, Union, Generator
from pathlib import Path

import pandas as pd
import numpy as np
from loguru import logger


@dataclass
class PostData:
    """통합 게시물 데이터 구조"""
    post_id: str
    platform: str
    account_hash: str
    text: str
    created_at: datetime
    
    # 계정 정보
    account_created_days: int = 0
    followers: int = 0
    following: int = 0
    is_verified: bool = False
    
    # 메타데이터
    language: Optional[str] = None
    country_inferred: Optional[str] = None
    time_bucket: Optional[str] = None
    text_template_id: Optional[str] = None
    
    # 임베딩
    embedding: Optional[list[float]] = None
    
    # 연결 정보
    urls: list[str] = field(default_factory=list)
    media_hash: Optional[str] = None
    reply_to_post: Optional[str] = None
    retweet_of: Optional[str] = None
    
    # 태그
    topic_tags: list[str] = field(default_factory=list)
    privacy_flag: str = "pseudonymized"
    
    def to_dict(self) -> dict:
        """딕셔너리로 변환"""
        data = asdict(self)
        data['created_at'] = self.created_at.isoformat()
        return data
    
    @property
    def is_retweet(self) -> bool:
        """리트윗 여부"""
        return self.retweet_of is not None and self.retweet_of != ""
    
    @property
    def is_reply(self) -> bool:
        """답글 여부"""
        return self.reply_to_post is not None and self.reply_to_post != ""
    
    @property
    def has_urls(self) -> bool:
        """URL 포함 여부"""
        return len(self.urls) > 0
    
    @property
    def account_age_category(self) -> str:
        """계정 나이 카테고리"""
        if self.account_created_days < 30:
            return "very_new"
        elif self.account_created_days < 90:
            return "new"
        elif self.account_created_days < 365:
            return "established"
        else:
            return "veteran"
    
    @property
    def follower_following_ratio(self) -> float:
        """팔로워/팔로잉 비율"""
        if self.following == 0:
            return float(self.followers)
        return self.followers / self.following


@dataclass
class AccountData:
    """계정 데이터 구조 (CSV에서 추출)"""
    account_hash: str
    platform: str
    account_created_days: int = 0
    followers: int = 0
    following: int = 0
    is_verified: bool = False
    country_inferred: Optional[str] = None
    post_count: int = 0
    languages: list[str] = field(default_factory=list)
    
    def to_dict(self) -> dict:
        return asdict(self)


class CSVIngester:
    """
    CSV 데이터 수집기
    
    PoC용 CSV 파일에서 소셜 미디어 데이터를 로드하고 처리합니다.
    
    Attributes:
        output_dir: 처리된 데이터 저장 경로
    """
    
    # 플랫폼 매핑
    PLATFORM_MAPPING = {
        "X": "twitter",
        "x": "twitter",
        "Twitter": "twitter",
        "twitter": "twitter",
        "YouTube": "youtube",
        "youtube": "youtube",
        "yt": "youtube",
        "Telegram": "telegram",
        "telegram": "telegram",
        "tg": "telegram",
    }
    
    def __init__(
        self,
        output_dir: str = "data/processed"
    ):
        """
        CSVIngester 초기화
        
        Args:
            output_dir: 처리된 데이터 저장 경로
        """
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        self.posts: list[PostData] = []
        self.accounts: dict[str, AccountData] = {}
        
        logger.info(f"CSVIngester initialized. Output: {self.output_dir}")
    
    def load_csv(
        self,
        filepath: Union[str, Path],
        encoding: str = "utf-8"
    ) -> pd.DataFrame:
        """
        CSV 파일 로드
        
        Args:
            filepath: CSV 파일 경로
            encoding: 파일 인코딩
        
        Returns:
            pandas DataFrame
        """
        filepath = Path(filepath)
        
        if not filepath.exists():
            raise FileNotFoundError(f"CSV file not found: {filepath}")
        
        df = pd.read_csv(filepath, encoding=encoding)
        
        logger.info(f"Loaded {len(df)} rows from {filepath}")
        logger.info(f"Columns: {list(df.columns)}")
        
        return df
    
    def parse_posts(
        self,
        df: pd.DataFrame
    ) -> list[PostData]:
        """
        DataFrame을 PostData 객체로 파싱
        
        Args:
            df: 입력 DataFrame
        
        Returns:
            PostData 리스트
        """
        posts = []
        
        for idx, row in df.iterrows():
            try:
                post = self._parse_row(row)
                if post:
                    posts.append(post)
            except Exception as e:
                logger.warning(f"Error parsing row {idx}: {e}")
        
        self.posts.extend(posts)
        logger.info(f"Parsed {len(posts)} posts")
        
        return posts
    
    def _parse_row(self, row: pd.Series) -> Optional[PostData]:
        """단일 행 파싱"""
        # 필수 필드 확인
        if pd.isna(row.get("post_id")) or pd.isna(row.get("text")):
            return None
        
        # 플랫폼 정규화
        platform = self.PLATFORM_MAPPING.get(
            row.get("platform", "unknown"),
            row.get("platform", "unknown").lower()
        )
        
        # 날짜 파싱
        created_at = self._parse_datetime(row.get("created_at_utc"))
        
        # 임베딩 파싱
        embedding = self._parse_embedding(row.get("sbert_emb_vec"))
        
        # URL 파싱
        urls = self._parse_urls(row.get("urls"))
        
        # 태그 파싱
        topic_tags = self._parse_tags(row.get("topic_tags"))
        
        # Boolean 파싱
        is_verified = self._parse_bool(row.get("is_verified"))
        
        return PostData(
            post_id=str(row["post_id"]),
            platform=platform,
            account_hash=str(row.get("account_hash", "")),
            text=str(row["text"]),
            created_at=created_at,
            account_created_days=int(row.get("account_created_days", 0) or 0),
            followers=int(row.get("followers", 0) or 0),
            following=int(row.get("following", 0) or 0),
            is_verified=is_verified,
            language=row.get("language"),
            country_inferred=row.get("country_inferred"),
            time_bucket=row.get("time_bucket"),
            text_template_id=row.get("text_template_id"),
            embedding=embedding,
            urls=urls,
            media_hash=row.get("media_hash") if pd.notna(row.get("media_hash")) else None,
            reply_to_post=row.get("reply_to_post") if pd.notna(row.get("reply_to_post")) else None,
            retweet_of=row.get("retweet_of") if pd.notna(row.get("retweet_of")) else None,
            topic_tags=topic_tags,
            privacy_flag=row.get("privacy_flag", "pseudonymized")
        )
    
    def _parse_datetime(self, value) -> datetime:
        """날짜/시간 파싱"""
        if pd.isna(value):
            return datetime.now()
        
        if isinstance(value, datetime):
            return value
        
        try:
            # ISO 형식
            return datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        except ValueError:
            try:
                # 다른 형식 시도
                return pd.to_datetime(value).to_pydatetime()
            except Exception:
                return datetime.now()
    
    def _parse_embedding(self, value) -> Optional[list[float]]:
        """임베딩 벡터 파싱"""
        if pd.isna(value) or value == "":
            return None
        
        try:
            if isinstance(value, str):
                # "[0.12,-0.03,...]" 형식 파싱
                value = value.strip()
                if value.startswith("[") and value.endswith("]"):
                    return ast.literal_eval(value)
                # 쉼표로 구분된 숫자
                return [float(x.strip()) for x in value.split(",") if x.strip()]
            elif isinstance(value, (list, np.ndarray)):
                return list(value)
        except Exception as e:
            logger.debug(f"Failed to parse embedding: {e}")
        
        return None
    
    def _parse_urls(self, value) -> list[str]:
        """URL 파싱"""
        if pd.isna(value) or value == "":
            return []
        
        if isinstance(value, str):
            # 세미콜론 또는 쉼표로 구분
            urls = []
            for sep in [";", ","]:
                if sep in value:
                    urls = [u.strip() for u in value.split(sep) if u.strip()]
                    break
            else:
                urls = [value.strip()] if value.strip() else []
            return urls
        elif isinstance(value, list):
            return value
        
        return []
    
    def _parse_tags(self, value) -> list[str]:
        """태그 파싱"""
        if pd.isna(value) or value == "":
            return []
        
        if isinstance(value, str):
            return [t.strip() for t in value.split(";") if t.strip()]
        elif isinstance(value, list):
            return value
        
        return []
    
    def _parse_bool(self, value) -> bool:
        """Boolean 파싱"""
        if pd.isna(value):
            return False
        
        if isinstance(value, bool):
            return value
        
        if isinstance(value, str):
            return value.lower() in ("true", "1", "yes", "t")
        
        return bool(value)
    
    def extract_accounts(self) -> dict[str, AccountData]:
        """
        게시물에서 계정 정보 추출
        
        Returns:
            {account_hash: AccountData} 딕셔너리
        """
        accounts: dict[str, AccountData] = {}
        
        for post in self.posts:
            key = f"{post.platform}:{post.account_hash}"
            
            if key not in accounts:
                accounts[key] = AccountData(
                    account_hash=post.account_hash,
                    platform=post.platform,
                    account_created_days=post.account_created_days,
                    followers=post.followers,
                    following=post.following,
                    is_verified=post.is_verified,
                    country_inferred=post.country_inferred,
                    post_count=0,
                    languages=[]
                )
            
            account = accounts[key]
            account.post_count += 1
            
            if post.language and post.language not in account.languages:
                account.languages.append(post.language)
            
            # 최신 정보로 업데이트
            if post.followers > account.followers:
                account.followers = post.followers
                account.following = post.following
        
        self.accounts = accounts
        logger.info(f"Extracted {len(accounts)} unique accounts")
        
        return accounts
    
    def get_posts_by_platform(self, platform: str) -> list[PostData]:
        """
        플랫폼별 게시물 필터링
        
        Args:
            platform: 플랫폼 이름 (twitter, youtube, telegram)
        
        Returns:
            PostData 리스트
        """
        platform = self.PLATFORM_MAPPING.get(platform, platform.lower())
        return [p for p in self.posts if p.platform == platform]
    
    def get_posts_by_account(self, account_hash: str) -> list[PostData]:
        """계정별 게시물 필터링"""
        return [p for p in self.posts if p.account_hash == account_hash]
    
    def get_posts_by_tag(self, tag: str) -> list[PostData]:
        """태그별 게시물 필터링"""
        return [p for p in self.posts if tag in p.topic_tags]
    
    def get_posts_by_language(self, language: str) -> list[PostData]:
        """언어별 게시물 필터링"""
        return [p for p in self.posts if p.language == language]
    
    def get_posts_in_time_range(
        self,
        start: datetime,
        end: datetime
    ) -> list[PostData]:
        """시간 범위별 게시물 필터링"""
        return [
            p for p in self.posts
            if start <= p.created_at <= end
        ]
    
    def find_duplicate_texts(self) -> dict[str, list[PostData]]:
        """
        동일 텍스트 게시물 찾기
        
        Returns:
            {text: [posts]} 딕셔너리
        """
        text_groups: dict[str, list[PostData]] = {}
        
        for post in self.posts:
            # 텍스트 정규화 (공백 제거)
            normalized = " ".join(post.text.split())
            
            if normalized not in text_groups:
                text_groups[normalized] = []
            text_groups[normalized].append(post)
        
        # 2개 이상인 그룹만 반환
        duplicates = {
            text: posts for text, posts in text_groups.items()
            if len(posts) > 1
        }
        
        logger.info(f"Found {len(duplicates)} duplicate text groups")
        return duplicates
    
    def find_coordinated_accounts(
        self,
        time_window_seconds: int = 300,
        min_shared_urls: int = 1
    ) -> list[tuple[str, str, dict]]:
        """
        협응 행위 의심 계정 쌍 찾기
        
        Args:
            time_window_seconds: 시간 윈도우 (초)
            min_shared_urls: 최소 공유 URL 수
        
        Returns:
            [(account1, account2, evidence)] 리스트
        """
        from collections import defaultdict
        
        # URL별 게시물 그룹화
        url_posts: dict[str, list[PostData]] = defaultdict(list)
        
        for post in self.posts:
            for url in post.urls:
                url_posts[url].append(post)
        
        # 계정 쌍별 공유 URL 카운트
        account_pairs: dict[tuple, dict] = defaultdict(lambda: {
            "shared_urls": [],
            "time_diffs": []
        })
        
        for url, posts in url_posts.items():
            if len(posts) < 2:
                continue
            
            # 시간순 정렬
            sorted_posts = sorted(posts, key=lambda p: p.created_at)
            
            for i, post1 in enumerate(sorted_posts):
                for post2 in sorted_posts[i+1:]:
                    if post1.account_hash == post2.account_hash:
                        continue
                    
                    time_diff = (post2.created_at - post1.created_at).total_seconds()
                    
                    if time_diff <= time_window_seconds:
                        pair_key = tuple(sorted([
                            f"{post1.platform}:{post1.account_hash}",
                            f"{post2.platform}:{post2.account_hash}"
                        ]))
                        
                        account_pairs[pair_key]["shared_urls"].append(url)
                        account_pairs[pair_key]["time_diffs"].append(time_diff)
        
        # 의심 쌍 필터링
        suspicious_pairs = []
        for (acc1, acc2), evidence in account_pairs.items():
            if len(evidence["shared_urls"]) >= min_shared_urls:
                suspicious_pairs.append((
                    acc1, acc2, {
                        "shared_urls": list(set(evidence["shared_urls"])),
                        "avg_time_diff": sum(evidence["time_diffs"]) / len(evidence["time_diffs"]),
                        "count": len(evidence["shared_urls"])
                    }
                ))
        
        logger.info(f"Found {len(suspicious_pairs)} suspicious account pairs")
        return suspicious_pairs
    
    def get_statistics(self) -> dict:
        """데이터 통계 반환"""
        if not self.posts:
            return {"total_posts": 0}
        
        platform_counts = {}
        language_counts = {}
        country_counts = {}
        tag_counts = {}
        
        for post in self.posts:
            # 플랫폼
            platform_counts[post.platform] = platform_counts.get(post.platform, 0) + 1
            
            # 언어
            if post.language:
                language_counts[post.language] = language_counts.get(post.language, 0) + 1
            
            # 국가
            if post.country_inferred:
                country_counts[post.country_inferred] = country_counts.get(post.country_inferred, 0) + 1
            
            # 태그
            for tag in post.topic_tags:
                tag_counts[tag] = tag_counts.get(tag, 0) + 1
        
        # 시간 범위
        dates = [p.created_at for p in self.posts]
        
        return {
            "total_posts": len(self.posts),
            "total_accounts": len(self.accounts) if self.accounts else len(set(p.account_hash for p in self.posts)),
            "platform_counts": platform_counts,
            "language_counts": language_counts,
            "country_counts": country_counts,
            "top_tags": dict(sorted(tag_counts.items(), key=lambda x: x[1], reverse=True)[:10]),
            "date_range": {
                "start": min(dates).isoformat(),
                "end": max(dates).isoformat()
            },
            "posts_with_urls": sum(1 for p in self.posts if p.has_urls),
            "replies": sum(1 for p in self.posts if p.is_reply),
            "retweets": sum(1 for p in self.posts if p.is_retweet)
        }
    
    def save_posts(self, filename: str) -> Path:
        """
        게시물 데이터를 JSON으로 저장
        
        Args:
            filename: 파일명 (확장자 제외)
        
        Returns:
            저장된 파일 경로
        """
        filepath = self.output_dir / f"{filename}.json"
        
        data = [post.to_dict() for post in self.posts]
        
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        
        logger.info(f"Saved {len(self.posts)} posts to {filepath}")
        return filepath
    
    def save_accounts(self, filename: str) -> Path:
        """
        계정 데이터를 JSON으로 저장
        
        Args:
            filename: 파일명 (확장자 제외)
        
        Returns:
            저장된 파일 경로
        """
        if not self.accounts:
            self.extract_accounts()
        
        filepath = self.output_dir / f"{filename}.json"
        
        data = {k: v.to_dict() for k, v in self.accounts.items()}
        
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        
        logger.info(f"Saved {len(self.accounts)} accounts to {filepath}")
        return filepath
    
    def to_dataframe(self) -> pd.DataFrame:
        """게시물을 DataFrame으로 변환"""
        return pd.DataFrame([post.to_dict() for post in self.posts])
    
    def clear(self):
        """데이터 초기화"""
        self.posts.clear()
        self.accounts.clear()


def load_sample_data(
    filepath: str = "data/raw/sample_posts.csv"
) -> tuple[list[PostData], dict]:
    """
    샘플 데이터 로드 헬퍼 함수
    
    Args:
        filepath: CSV 파일 경로
    
    Returns:
        (posts, statistics) 튜플
    """
    ingester = CSVIngester()
    df = ingester.load_csv(filepath)
    posts = ingester.parse_posts(df)
    ingester.extract_accounts()
    stats = ingester.get_statistics()
    
    return posts, stats


# 모듈 테스트용
if __name__ == "__main__":
    import sys
    
    # 프로젝트 루트 찾기
    project_root = Path(__file__).parent.parent.parent
    csv_path = project_root / "data" / "raw" / "sample_posts.csv"
    
    print(f"Loading sample data from: {csv_path}")
    print("=" * 60)
    
    ingester = CSVIngester(output_dir=str(project_root / "data" / "processed"))
    
    # CSV 로드 및 파싱
    df = ingester.load_csv(csv_path)
    posts = ingester.parse_posts(df)
    accounts = ingester.extract_accounts()
    
    # 통계 출력
    stats = ingester.get_statistics()
    print("\n 데이터 통계:")
    print(f"  총 게시물: {stats['total_posts']}")
    print(f"  총 계정: {stats['total_accounts']}")
    print(f"  플랫폼별: {stats['platform_counts']}")
    print(f"  언어별: {stats['language_counts']}")
    print(f"  국가별: {stats['country_counts']}")
    print(f"  상위 태그: {stats['top_tags']}")
    print(f"  URL 포함: {stats['posts_with_urls']}")
    
    # 중복 텍스트 찾기
    duplicates = ingester.find_duplicate_texts()
    print(f"\n 중복 텍스트 그룹: {len(duplicates)}")
    for text, dup_posts in list(duplicates.items())[:3]:
        print(f"  - '{text[:50]}...' ({len(dup_posts)}개)")
    
    # 협응 행위 의심 계정
    suspicious = ingester.find_coordinated_accounts()
    print(f"\n 협응 행위 의심 계정 쌍: {len(suspicious)}")
    for acc1, acc2, evidence in suspicious[:3]:
        print(f"  - {acc1} <-> {acc2}")
        print(f"    공유 URL: {evidence['count']}개, 평균 시간차: {evidence['avg_time_diff']:.1f}초")
    
    # 플랫폼별 출력
    print("\n 플랫폼별 게시물:")
    for platform in ["twitter", "youtube", "telegram"]:
        platform_posts = ingester.get_posts_by_platform(platform)
        print(f"  {platform}: {len(platform_posts)}개")
    
    # 샘플 게시물 출력
    print("\n 샘플 게시물:")
    for post in posts[:3]:
        print(f"  [{post.platform}] {post.post_id}")
        print(f"    Text: {post.text[:60]}...")
        print(f"    Account: {post.account_hash[:12]}... (팔로워: {post.followers})")
        print(f"    Tags: {post.topic_tags}")
        print()
    
    # JSON으로 저장
    ingester.save_posts("parsed_posts")
    ingester.save_accounts("parsed_accounts")
    
    print(" 처리 완료!")

