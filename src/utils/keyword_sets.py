"""
키워드 세트 정의 모듈

안보·선거·외교 관련 키워드 세트를 체계적으로 관리합니다.
"""

import json
from typing import Optional, Set, Dict, List
from pathlib import Path
from dataclasses import dataclass, field, asdict
from enum import Enum

from loguru import logger


class KeywordCategory(str, Enum):
    """키워드 카테고리"""
    SECURITY = "security"      # 안보
    ELECTION = "election"      # 선거
    DIPLOMACY = "diplomacy"    # 외교
    ECONOMY = "economy"        # 경제
    DISINFORMATION = "disinformation"  # 허위정보


@dataclass
class Keyword:
    """키워드 데이터"""
    keyword: str
    category: KeywordCategory
    weight: float = 1.0  # 중요도 가중치
    aliases: List[str] = field(default_factory=list)  # 동의어/유사어
    description: Optional[str] = None
    related_keywords: List[str] = field(default_factory=list)
    
    def to_dict(self) -> dict:
        return asdict(self)


class KeywordSetManager:
    """
    키워드 세트 관리자
    
    안보·선거·외교 관련 키워드를 체계적으로 관리합니다.
    """
    
    # 안보 관련 키워드
    SECURITY_KEYWORDS = [
        Keyword("동맹", KeywordCategory.SECURITY, 1.0, 
                aliases=["한미동맹", "미한동맹", "동맹관계"],
                description="한미동맹 관련 키워드",
                related_keywords=["주한미군", "방위비", "사드"]),
        Keyword("주한미군", KeywordCategory.SECURITY, 1.0,
                aliases=["미군", "주한미국군", "미군기지"],
                description="주한미군 관련 키워드"),
        Keyword("제재", KeywordCategory.SECURITY, 0.9,
                aliases=["제재조치", "경제제재", "국제제재"],
                description="제재 관련 키워드"),
        Keyword("핵실험", KeywordCategory.SECURITY, 1.0,
                aliases=["핵시험", "핵무기실험", "핵개발"],
                description="핵실험 관련 키워드"),
        Keyword("방위비", KeywordCategory.SECURITY, 0.9,
                aliases=["방위비분담금", "SMFA", "방위비협정"],
                description="방위비 분담 관련 키워드"),
        Keyword("사드", KeywordCategory.SECURITY, 0.9,
                aliases=["THAAD", "사드배치", "미사일방어"],
                description="사드 배치 관련 키워드"),
        Keyword("안보", KeywordCategory.SECURITY, 0.8,
                aliases=["국가안보", "안보위기", "안보협력"],
                description="안보 일반 키워드"),
        Keyword("군사", KeywordCategory.SECURITY, 0.7,
                aliases=["군사력", "군사협력", "군사동맹"]),
        Keyword("북한", KeywordCategory.SECURITY, 0.9,
                aliases=["북", "조선", "DPRK"]),
        Keyword("미사일", KeywordCategory.SECURITY, 0.8,
                aliases=["탄도미사일", "미사일발사", "ICBM"]),
    ]
    
    # 선거 관련 키워드
    ELECTION_KEYWORDS = [
        Keyword("선거", KeywordCategory.ELECTION, 1.0,
                aliases=["선거일", "선거운동", "선거법"],
                description="선거 일반 키워드",
                related_keywords=["투표", "후보", "정당"]),
        Keyword("투표", KeywordCategory.ELECTION, 1.0,
                aliases=["투표소", "사전투표", "부재자투표"],
                description="투표 관련 키워드"),
        Keyword("후보", KeywordCategory.ELECTION, 0.9,
                aliases=["후보자", "대선후보", "후보등록"],
                description="후보 관련 키워드"),
        Keyword("정당", KeywordCategory.ELECTION, 0.8,
                aliases=["정당정치", "여당", "야당"],
                description="정당 관련 키워드"),
        Keyword("개표", KeywordCategory.ELECTION, 0.9,
                aliases=["개표소", "개표작업", "개표결과"],
                description="개표 관련 키워드"),
        Keyword("선거부정", KeywordCategory.ELECTION, 1.0,
                aliases=["선거조작", "부정선거", "선거개입"],
                description="선거 부정 관련 키워드"),
        Keyword("여론조사", KeywordCategory.ELECTION, 0.7,
                aliases=["여론조사결과", "지지율", "출구조사"]),
        Keyword("공천", KeywordCategory.ELECTION, 0.7,
                aliases=["공천과정", "공천자", "공천논란"]),
    ]
    
    # 외교 관련 키워드
    DIPLOMACY_KEYWORDS = [
        Keyword("외교", KeywordCategory.DIPLOMACY, 0.9,
                aliases=["외교관계", "외교정책", "외교부"],
                description="외교 일반 키워드",
                related_keywords=["국교", "협정", "정상회담"]),
        Keyword("국교", KeywordCategory.DIPLOMACY, 0.9,
                aliases=["국교수립", "국교정상화", "외교관계"],
                description="국교 관련 키워드"),
        Keyword("협정", KeywordCategory.DIPLOMACY, 0.8,
                aliases=["FTA", "자유무역협정", "경제협정"],
                description="협정 관련 키워드"),
        Keyword("정상회담", KeywordCategory.DIPLOMACY, 1.0,
                aliases=["정상회의", "정상회의", "정상회의"],
                description="정상회담 관련 키워드"),
        Keyword("외교관", KeywordCategory.DIPLOMACY, 0.7,
                aliases=["대사", "공사", "영사"]),
        Keyword("국제관계", KeywordCategory.DIPLOMACY, 0.8,
                aliases=["국제협력", "국제질서", "국제사회"]),
        Keyword("외교부", KeywordCategory.DIPLOMACY, 0.7,
                aliases=["MOFA", "외무부"]),
    ]
    
    # 경제 관련 키워드 (경제 허위정보 탐지용)
    ECONOMY_KEYWORDS = [
        Keyword("경제위기", KeywordCategory.ECONOMY, 0.9,
                aliases=["경제불안", "경제침체", "경제파탄"],
                description="경제 위기 관련 키워드"),
        Keyword("은행", KeywordCategory.ECONOMY, 0.8,
                aliases=["금융기관", "은행파산", "은행마비"]),
        Keyword("환율", KeywordCategory.ECONOMY, 0.7,
                aliases=["환율폭등", "환율폭락", "원화가치"]),
        Keyword("주식", KeywordCategory.ECONOMY, 0.7,
                aliases=["주식시장", "코스피", "코스닥"]),
    ]
    
    # 허위정보 관련 키워드
    DISINFORMATION_KEYWORDS = [
        Keyword("유출", KeywordCategory.DISINFORMATION, 0.9,
                aliases=["내부문서", "기밀유출", "문서유출"],
                description="문서 유출 관련 키워드"),
        Keyword("음모", KeywordCategory.DISINFORMATION, 0.8,
                aliases=["음모론", "음모설", "음모"]),
        Keyword("조작", KeywordCategory.DISINFORMATION, 0.9,
                aliases=["정보조작", "뉴스조작", "조작설"]),
    ]
    
    def __init__(self, custom_keywords_file: Optional[str] = None):
        """
        KeywordSetManager 초기화
        
        Args:
            custom_keywords_file: 커스텀 키워드 파일 경로 (JSON)
        """
        self.keywords: Dict[str, Keyword] = {}
        self.keyword_index: Dict[str, List[str]] = {}  # 키워드 -> 매칭 가능한 모든 형태
        
        # 기본 키워드 로드
        self._load_default_keywords()
        
        # 커스텀 키워드 로드
        if custom_keywords_file:
            self.load_custom_keywords(custom_keywords_file)
        
        # 인덱스 구축
        self._build_index()
        
        logger.info(f"KeywordSetManager initialized: {len(self.keywords)} keywords")
    
    def _load_default_keywords(self):
        """기본 키워드 로드"""
        all_keywords = (
            self.SECURITY_KEYWORDS +
            self.ELECTION_KEYWORDS +
            self.DIPLOMACY_KEYWORDS +
            self.ECONOMY_KEYWORDS +
            self.DISINFORMATION_KEYWORDS
        )
        
        for kw in all_keywords:
            self.keywords[kw.keyword] = kw
    
    def _build_index(self):
        """키워드 인덱스 구축"""
        for keyword, kw_obj in self.keywords.items():
            # 기본 키워드
            if keyword not in self.keyword_index:
                self.keyword_index[keyword] = []
            self.keyword_index[keyword].append(keyword)
            
            # 동의어
            for alias in kw_obj.aliases:
                if alias not in self.keyword_index:
                    self.keyword_index[alias] = []
                self.keyword_index[alias].append(keyword)
    
    def load_custom_keywords(self, filepath: str):
        """
        커스텀 키워드 로드
        
        Args:
            filepath: JSON 파일 경로
        """
        with open(filepath, "r", encoding="utf-8") as f:
            data = json.load(f)
        
        for item in data:
            kw = Keyword(
                keyword=item["keyword"],
                category=KeywordCategory(item["category"]),
                weight=item.get("weight", 1.0),
                aliases=item.get("aliases", []),
                description=item.get("description"),
                related_keywords=item.get("related_keywords", [])
            )
            self.keywords[kw.keyword] = kw
        
        # 인덱스 재구축
        self._build_index()
        logger.info(f"Loaded {len(data)} custom keywords")
    
    def save_keywords(self, filepath: str):
        """키워드 저장"""
        data = [kw.to_dict() for kw in self.keywords.values()]
        
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        
        logger.info(f"Saved {len(data)} keywords to {filepath}")
    
    def match_keywords(self, text: str, case_sensitive: bool = False) -> Dict[str, List[str]]:
        """
        텍스트에서 키워드 매칭
        
        Args:
            text: 검색할 텍스트
            case_sensitive: 대소문자 구분 여부
        
        Returns:
            {카테고리: [매칭된 키워드 리스트]} 딕셔너리
        """
        if not case_sensitive:
            text = text.lower()
        
        matches: Dict[str, List[str]] = {
            cat.value: [] for cat in KeywordCategory
        }
        
        for keyword, kw_obj in self.keywords.items():
            # 기본 키워드 매칭
            search_keyword = keyword if case_sensitive else keyword.lower()
            if search_keyword in text:
                matches[kw_obj.category.value].append(keyword)
                continue
            
            # 동의어 매칭
            for alias in kw_obj.aliases:
                search_alias = alias if case_sensitive else alias.lower()
                if search_alias in text:
                    matches[kw_obj.category.value].append(keyword)
                    break
        
        # 중복 제거
        for cat in matches:
            matches[cat] = list(set(matches[cat]))
        
        return matches
    
    def get_keywords_by_category(self, category: KeywordCategory) -> List[Keyword]:
        """카테고리별 키워드 조회"""
        return [kw for kw in self.keywords.values() if kw.category == category]
    
    def get_keyword(self, keyword: str) -> Optional[Keyword]:
        """키워드 조회"""
        return self.keywords.get(keyword)
    
    def add_keyword(self, keyword: Keyword):
        """키워드 추가"""
        self.keywords[keyword.keyword] = keyword
        self._build_index()
    
    def get_keyword_score(self, text: str) -> float:
        """
        텍스트의 키워드 기반 점수 계산
        
        Args:
            text: 텍스트
        
        Returns:
            키워드 점수 (0-1)
        """
        matches = self.match_keywords(text)
        
        total_score = 0.0
        total_weight = 0.0
        
        for cat, matched_keywords in matches.items():
            for kw_str in matched_keywords:
                kw_obj = self.keywords.get(kw_str)
                if kw_obj:
                    total_score += kw_obj.weight
                    total_weight += 1.0
        
        # 정규화 (최대 점수로 나눔)
        if total_weight > 0:
            max_possible_score = len(self.keywords) * 1.0  # 모든 키워드가 매칭된 경우
            return min(1.0, total_score / max_possible_score)
        
        return 0.0
    
    def get_statistics(self) -> dict:
        """통계 반환"""
        stats = {
            cat.value: len(self.get_keywords_by_category(cat))
            for cat in KeywordCategory
        }
        stats["total"] = len(self.keywords)
        return stats


# 전역 인스턴스
_default_manager: Optional[KeywordSetManager] = None


def get_keyword_manager() -> KeywordSetManager:
    """전역 키워드 매니저 인스턴스 반환"""
    global _default_manager
    if _default_manager is None:
        _default_manager = KeywordSetManager()
    return _default_manager


# 모듈 테스트용
if __name__ == "__main__":
    manager = KeywordSetManager()
    
    test_texts = [
        "한미동맹이 흔들리고 있다. 정부는 대책을 마련해야 한다.",
        "선거 부정이 의심된다. 개표 과정을 재검토해야 한다.",
        "외교부가 정상회담을 발표했다.",
        "경제위기가 다가오고 있다. 은행 시스템이 마비될 수 있다.",
    ]
    
    print("Keyword Set Manager Test:")
    print("=" * 60)
    print(f"Total keywords: {manager.get_statistics()}")
    print()
    
    for text in test_texts:
        matches = manager.match_keywords(text)
        score = manager.get_keyword_score(text)
        
        print(f"Text: {text}")
        print(f"  Matches: {matches}")
        print(f"  Score: {score:.3f}")
        print()
