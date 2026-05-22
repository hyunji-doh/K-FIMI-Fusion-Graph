"""
도메인 신뢰도 스코어링 모듈

URL 도메인의 신뢰도를 평가하고 점수를 매깁니다.
"""

import re
import json
from typing import Optional
from dataclasses import dataclass, field
from urllib.parse import urlparse
from pathlib import Path

import pandas as pd
from loguru import logger


@dataclass
class DomainInfo:
    """도메인 정보"""
    domain: str
    credibility_score: float = 0.5  # 0-1 범위
    category: Optional[str] = None
    country: Optional[str] = None
    language: Optional[str] = None
    is_news_outlet: bool = False
    is_government: bool = False
    is_social_media: bool = False
    is_known_disinformation: bool = False
    fact_check_rating: Optional[str] = None
    alexa_rank: Optional[int] = None
    first_seen: Optional[str] = None
    metadata: dict = field(default_factory=dict)
    
    def to_dict(self) -> dict:
        return {
            "domain": self.domain,
            "credibility_score": self.credibility_score,
            "category": self.category,
            "country": self.country,
            "language": self.language,
            "is_news_outlet": self.is_news_outlet,
            "is_government": self.is_government,
            "is_social_media": self.is_social_media,
            "is_known_disinformation": self.is_known_disinformation,
            "fact_check_rating": self.fact_check_rating,
            "metadata": self.metadata
        }


class DomainScorer:
    """
    도메인 신뢰도 스코어러
    
    URL 도메인의 신뢰도를 평가합니다.
    """
    
    # 알려진 신뢰할 수 있는 도메인 패턴
    TRUSTED_DOMAINS = {
        # 한국 주요 언론사
        "news.naver.com": {"score": 0.7, "category": "news_portal", "country": "KR"},
        "news.daum.net": {"score": 0.7, "category": "news_portal", "country": "KR"},
        "chosun.com": {"score": 0.7, "category": "news", "country": "KR"},
        "joongang.co.kr": {"score": 0.7, "category": "news", "country": "KR"},
        "donga.com": {"score": 0.7, "category": "news", "country": "KR"},
        "hani.co.kr": {"score": 0.7, "category": "news", "country": "KR"},
        "khan.co.kr": {"score": 0.7, "category": "news", "country": "KR"},
        "yna.co.kr": {"score": 0.85, "category": "news_agency", "country": "KR"},
        "yonhapnews.co.kr": {"score": 0.85, "category": "news_agency", "country": "KR"},
        "kbs.co.kr": {"score": 0.8, "category": "broadcast", "country": "KR"},
        "mbc.co.kr": {"score": 0.8, "category": "broadcast", "country": "KR"},
        "sbs.co.kr": {"score": 0.8, "category": "broadcast", "country": "KR"},
        
        # 한국 정부/공공기관
        "go.kr": {"score": 0.9, "category": "government", "country": "KR"},
        "or.kr": {"score": 0.75, "category": "organization", "country": "KR"},
        "ac.kr": {"score": 0.85, "category": "academic", "country": "KR"},
        
        # 국제 신뢰 도메인
        "bbc.com": {"score": 0.8, "category": "news", "country": "UK"},
        "bbc.co.uk": {"score": 0.8, "category": "news", "country": "UK"},
        "reuters.com": {"score": 0.85, "category": "news_agency", "country": "UK"},
        "ap.org": {"score": 0.85, "category": "news_agency", "country": "US"},
        "nytimes.com": {"score": 0.8, "category": "news", "country": "US"},
        "washingtonpost.com": {"score": 0.8, "category": "news", "country": "US"},
        "theguardian.com": {"score": 0.75, "category": "news", "country": "UK"},
        
        # 팩트체크 기관
        "snopes.com": {"score": 0.85, "category": "fact_check", "country": "US"},
        "factcheck.org": {"score": 0.85, "category": "fact_check", "country": "US"},
        "politifact.com": {"score": 0.85, "category": "fact_check", "country": "US"},
        "factchecker.or.kr": {"score": 0.85, "category": "fact_check", "country": "KR"},
        
        # 학술/연구
        "nature.com": {"score": 0.9, "category": "academic", "country": "INT"},
        "science.org": {"score": 0.9, "category": "academic", "country": "INT"},
        "arxiv.org": {"score": 0.8, "category": "academic", "country": "INT"},
    }
    
    # 허위정보 유포 의심 도메인 패턴
    SUSPICIOUS_PATTERNS = [
        r".*-news\d+\..*",  # fake-news123.com 패턴
        r".*breaking.*news.*",
        r".*\.tk$",  # .tk 도메인
        r".*\.xyz$",  # .xyz 도메인
        r".*\.top$",
        r".*\.cc$",
        r".*-today\..*",
        r".*daily-.*\..*",
    ]
    
    # 소셜 미디어 도메인
    SOCIAL_MEDIA = {
        "twitter.com", "x.com",
        "facebook.com", "fb.com",
        "instagram.com",
        "youtube.com", "youtu.be",
        "tiktok.com",
        "t.me", "telegram.org",
        "reddit.com",
        "linkedin.com",
    }
    
    # URL 단축 서비스
    URL_SHORTENERS = {
        "bit.ly", "tinyurl.com", "t.co", "goo.gl",
        "ow.ly", "is.gd", "buff.ly", "j.mp",
        "han.gl", "me2.do", "vo.la",
    }
    
    def __init__(
        self,
        custom_scores_file: Optional[str] = None,
        blocklist_file: Optional[str] = None
    ):
        """
        DomainScorer 초기화
        
        Args:
            custom_scores_file: 커스텀 도메인 점수 파일 (JSON)
            blocklist_file: 차단 도메인 리스트 파일
        """
        self.domain_scores: dict[str, DomainInfo] = {}
        self.blocklist: set[str] = set()
        
        # 기본 점수 로드
        self._init_default_scores()
        
        # 커스텀 점수 로드
        if custom_scores_file:
            self.load_custom_scores(custom_scores_file)
        
        # 차단 리스트 로드
        if blocklist_file:
            self.load_blocklist(blocklist_file)
        
        logger.info(f"DomainScorer initialized: {len(self.domain_scores)} domains")
    
    def _init_default_scores(self):
        """기본 도메인 점수 초기화"""
        for domain, info in self.TRUSTED_DOMAINS.items():
            self.domain_scores[domain] = DomainInfo(
                domain=domain,
                credibility_score=info["score"],
                category=info.get("category"),
                country=info.get("country"),
                is_news_outlet=info.get("category") in ["news", "news_agency", "broadcast"],
                is_government=info.get("category") == "government"
            )
    
    def load_custom_scores(self, filepath: str):
        """
        커스텀 도메인 점수 로드
        
        Args:
            filepath: JSON 파일 경로
        """
        with open(filepath, "r", encoding="utf-8") as f:
            data = json.load(f)
        
        for domain, info in data.items():
            if isinstance(info, dict):
                self.domain_scores[domain] = DomainInfo(
                    domain=domain,
                    **info
                )
            else:
                self.domain_scores[domain] = DomainInfo(
                    domain=domain,
                    credibility_score=float(info)
                )
        
        logger.info(f"Loaded {len(data)} custom domain scores")
    
    def load_blocklist(self, filepath: str):
        """
        차단 도메인 리스트 로드
        
        Args:
            filepath: 텍스트 파일 경로 (한 줄에 하나의 도메인)
        """
        with open(filepath, "r", encoding="utf-8") as f:
            for line in f:
                domain = line.strip()
                if domain and not domain.startswith("#"):
                    self.blocklist.add(domain)
        
        logger.info(f"Loaded {len(self.blocklist)} blocked domains")
    
    def extract_domain(self, url: str) -> str:
        """
        URL에서 도메인 추출
        
        Args:
            url: URL 문자열
        
        Returns:
            도메인 문자열
        """
        if not url:
            return ""
        
        # URL 파싱
        if not url.startswith(("http://", "https://")):
            url = "http://" + url
        
        try:
            parsed = urlparse(url)
            domain = parsed.netloc.lower()
            
            # www 제거
            if domain.startswith("www."):
                domain = domain[4:]
            
            return domain
        except Exception:
            return ""
    
    def get_domain_info(self, url_or_domain: str) -> DomainInfo:
        """
        도메인 정보 조회
        
        Args:
            url_or_domain: URL 또는 도메인
        
        Returns:
            DomainInfo 객체
        """
        # 도메인 추출
        if "/" in url_or_domain or ":" in url_or_domain:
            domain = self.extract_domain(url_or_domain)
        else:
            domain = url_or_domain.lower()
        
        # 캐시된 정보 확인
        if domain in self.domain_scores:
            return self.domain_scores[domain]
        
        # 상위 도메인 확인 (예: news.example.com -> example.com)
        parts = domain.split(".")
        for i in range(len(parts) - 1):
            parent_domain = ".".join(parts[i:])
            if parent_domain in self.domain_scores:
                return self.domain_scores[parent_domain]
        
        # TLD 기반 확인 (예: .go.kr)
        for tld in [".go.kr", ".or.kr", ".ac.kr", ".gov", ".edu"]:
            if domain.endswith(tld):
                return DomainInfo(
                    domain=domain,
                    credibility_score=0.8,
                    category="official",
                    is_government=tld in [".go.kr", ".gov"]
                )
        
        # 새 도메인 정보 생성
        info = self._analyze_domain(domain)
        self.domain_scores[domain] = info
        
        return info
    
    def _analyze_domain(self, domain: str) -> DomainInfo:
        """도메인 분석"""
        info = DomainInfo(domain=domain)
        
        # 차단 리스트 확인
        if domain in self.blocklist:
            info.credibility_score = 0.0
            info.is_known_disinformation = True
            return info
        
        # 소셜 미디어 확인
        if domain in self.SOCIAL_MEDIA:
            info.is_social_media = True
            info.credibility_score = 0.5  # 중립
            info.category = "social_media"
            return info
        
        # URL 단축 서비스 확인
        if domain in self.URL_SHORTENERS:
            info.credibility_score = 0.4
            info.category = "url_shortener"
            return info
        
        # 의심스러운 패턴 확인
        for pattern in self.SUSPICIOUS_PATTERNS:
            if re.match(pattern, domain):
                info.credibility_score = 0.2
                info.category = "suspicious"
                return info
        
        # 기본 휴리스틱
        score = 0.5
        
        # 도메인 길이 (너무 길면 의심)
        if len(domain) > 30:
            score -= 0.1
        
        # 숫자 포함 (의심)
        if re.search(r'\d', domain):
            score -= 0.05
        
        # 하이픈 다수 포함 (의심)
        if domain.count("-") > 2:
            score -= 0.1
        
        # TLD 확인
        known_tlds = [".com", ".org", ".net", ".kr", ".co.kr"]
        has_known_tld = any(domain.endswith(tld) for tld in known_tlds)
        if not has_known_tld:
            score -= 0.1
        
        info.credibility_score = max(0.1, min(0.9, score))
        return info
    
    def score_url(self, url: str) -> float:
        """
        URL 신뢰도 점수 반환
        
        Args:
            url: URL 문자열
        
        Returns:
            신뢰도 점수 (0-1)
        """
        info = self.get_domain_info(url)
        return info.credibility_score
    
    def score_urls(self, urls: list[str]) -> list[float]:
        """
        여러 URL의 신뢰도 점수 반환
        
        Args:
            urls: URL 리스트
        
        Returns:
            점수 리스트
        """
        return [self.score_url(url) for url in urls]
    
    def is_blocked(self, url: str) -> bool:
        """도메인이 차단 리스트에 있는지 확인"""
        domain = self.extract_domain(url)
        return domain in self.blocklist
    
    def is_social_media(self, url: str) -> bool:
        """소셜 미디어 URL인지 확인"""
        domain = self.extract_domain(url)
        return domain in self.SOCIAL_MEDIA
    
    def is_url_shortener(self, url: str) -> bool:
        """URL 단축 서비스인지 확인"""
        domain = self.extract_domain(url)
        return domain in self.URL_SHORTENERS
    
    def get_category(self, url: str) -> Optional[str]:
        """도메인 카테고리 반환"""
        info = self.get_domain_info(url)
        return info.category
    
    def add_domain_score(
        self,
        domain: str,
        score: float,
        category: Optional[str] = None,
        **kwargs
    ):
        """
        도메인 점수 추가/업데이트
        
        Args:
            domain: 도메인
            score: 신뢰도 점수
            category: 카테고리
            **kwargs: 추가 속성
        """
        self.domain_scores[domain] = DomainInfo(
            domain=domain,
            credibility_score=score,
            category=category,
            **kwargs
        )
    
    def add_to_blocklist(self, domain: str):
        """도메인을 차단 리스트에 추가"""
        self.blocklist.add(domain)
        
        if domain in self.domain_scores:
            self.domain_scores[domain].credibility_score = 0.0
            self.domain_scores[domain].is_known_disinformation = True
    
    def save_scores(self, filepath: str):
        """도메인 점수 저장"""
        data = {
            domain: info.to_dict()
            for domain, info in self.domain_scores.items()
        }
        
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        
        logger.info(f"Saved {len(data)} domain scores to {filepath}")
    
    def get_statistics(self) -> dict:
        """통계 반환"""
        scores = [info.credibility_score for info in self.domain_scores.values()]
        categories = {}
        
        for info in self.domain_scores.values():
            cat = info.category or "unknown"
            categories[cat] = categories.get(cat, 0) + 1
        
        return {
            "total_domains": len(self.domain_scores),
            "blocked_domains": len(self.blocklist),
            "avg_score": sum(scores) / len(scores) if scores else 0,
            "min_score": min(scores) if scores else 0,
            "max_score": max(scores) if scores else 0,
            "categories": categories
        }


# 모듈 테스트용
if __name__ == "__main__":
    scorer = DomainScorer()
    
    test_urls = [
        "https://www.yna.co.kr/view/AKR20231115123456789",
        "https://news.naver.com/main/article.nhn?id=123",
        "https://bit.ly/abc123",
        "https://suspicious-news123.xyz/fake-article",
        "https://twitter.com/user/status/123",
        "https://www.go.kr/portal/main",
    ]
    
    print("Domain Scoring Test:")
    print("-" * 60)
    
    for url in test_urls:
        info = scorer.get_domain_info(url)
        print(f"\nURL: {url}")
        print(f"  Domain: {info.domain}")
        print(f"  Score: {info.credibility_score:.2f}")
        print(f"  Category: {info.category}")
        print(f"  Social Media: {info.is_social_media}")
    
    print("\n" + "=" * 60)
    print("Statistics:", scorer.get_statistics())

