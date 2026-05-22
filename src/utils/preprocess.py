"""
데이터 전처리 모듈

텍스트 정제, 정규화, 특수 처리 기능을 제공합니다.
"""

import re
import unicodedata
from typing import Optional, Callable
from dataclasses import dataclass
from datetime import datetime

import pandas as pd
from loguru import logger


@dataclass
class PreprocessConfig:
    """전처리 설정"""
    lowercase: bool = True
    remove_urls: bool = True
    remove_mentions: bool = True
    remove_hashtags: bool = False  # 해시태그는 보존 옵션
    remove_emojis: bool = False
    remove_special_chars: bool = True
    remove_extra_spaces: bool = True
    remove_numbers: bool = False
    normalize_unicode: bool = True
    min_length: int = 2
    max_length: Optional[int] = None
    language: str = "auto"


class TextPreprocessor:
    """
    텍스트 전처리기
    
    소셜 미디어 텍스트를 정제하고 정규화합니다.
    """
    
    # 정규표현식 패턴
    URL_PATTERN = re.compile(
        r'https?://(?:[-\w.]|(?:%[\da-fA-F]{2}))+[^\s]*|'
        r'www\.(?:[-\w.]|(?:%[\da-fA-F]{2}))+[^\s]*'
    )
    
    MENTION_PATTERN = re.compile(r'@[\w]+')
    
    HASHTAG_PATTERN = re.compile(r'#[\w가-힣]+')
    
    EMAIL_PATTERN = re.compile(
        r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}'
    )
    
    # 이모지 패턴
    EMOJI_PATTERN = re.compile(
        "["
        "\U0001F600-\U0001F64F"  # 감정
        "\U0001F300-\U0001F5FF"  # 심볼 & 픽토그램
        "\U0001F680-\U0001F6FF"  # 교통 & 지도
        "\U0001F1E0-\U0001F1FF"  # 국기
        "\U00002702-\U000027B0"
        "\U000024C2-\U0001F251"
        "]+",
        flags=re.UNICODE
    )
    
    # 특수문자 패턴 (한글, 영문, 숫자 제외)
    SPECIAL_CHAR_PATTERN = re.compile(r'[^\w\s가-힣]')
    
    # 반복 문자 패턴
    REPEATED_CHAR_PATTERN = re.compile(r'(.)\1{3,}')
    
    # 한국어 자음/모음만 있는 패턴
    KOREAN_JAMO_PATTERN = re.compile(r'[ㄱ-ㅎㅏ-ㅣ]+')
    
    def __init__(self, config: Optional[PreprocessConfig] = None):
        """
        TextPreprocessor 초기화
        
        Args:
            config: 전처리 설정
        """
        self.config = config or PreprocessConfig()
        logger.info("TextPreprocessor initialized")
    
    def preprocess(self, text: str) -> str:
        """
        텍스트 전처리 수행
        
        Args:
            text: 원본 텍스트
        
        Returns:
            전처리된 텍스트
        """
        if not text or not isinstance(text, str):
            return ""
        
        # Unicode 정규화
        if self.config.normalize_unicode:
            text = unicodedata.normalize('NFC', text)
        
        # URL 제거
        if self.config.remove_urls:
            text = self.URL_PATTERN.sub(' ', text)
        
        # 멘션 제거
        if self.config.remove_mentions:
            text = self.MENTION_PATTERN.sub(' ', text)
        
        # 해시태그 제거
        if self.config.remove_hashtags:
            text = self.HASHTAG_PATTERN.sub(' ', text)
        
        # 이메일 제거
        text = self.EMAIL_PATTERN.sub(' ', text)
        
        # 이모지 제거
        if self.config.remove_emojis:
            text = self.EMOJI_PATTERN.sub(' ', text)
        
        # 특수문자 제거
        if self.config.remove_special_chars:
            # 기본 구두점 보존
            text = re.sub(r'[^\w\s가-힣.,!?\'"-]', ' ', text)
        
        # 숫자 제거
        if self.config.remove_numbers:
            text = re.sub(r'\d+', ' ', text)
        
        # 반복 문자 정규화 (ㅋㅋㅋㅋㅋ -> ㅋㅋㅋ)
        text = self.REPEATED_CHAR_PATTERN.sub(r'\1\1\1', text)
        
        # 연속 공백 제거
        if self.config.remove_extra_spaces:
            text = re.sub(r'\s+', ' ', text)
        
        # 소문자 변환
        if self.config.lowercase:
            text = text.lower()
        
        # 앞뒤 공백 제거
        text = text.strip()
        
        # 길이 필터링
        if len(text) < self.config.min_length:
            return ""
        
        if self.config.max_length and len(text) > self.config.max_length:
            text = text[:self.config.max_length]
        
        return text
    
    def preprocess_batch(
        self,
        texts: list[str],
        show_progress: bool = False
    ) -> list[str]:
        """
        배치 텍스트 전처리
        
        Args:
            texts: 텍스트 리스트
            show_progress: 진행률 표시
        
        Returns:
            전처리된 텍스트 리스트
        """
        if show_progress:
            from tqdm import tqdm
            texts = tqdm(texts, desc="Preprocessing")
        
        return [self.preprocess(text) for text in texts]
    
    def extract_urls(self, text: str) -> list[str]:
        """URL 추출"""
        return self.URL_PATTERN.findall(text)
    
    def extract_mentions(self, text: str) -> list[str]:
        """멘션 추출"""
        mentions = self.MENTION_PATTERN.findall(text)
        return [m.lstrip('@') for m in mentions]
    
    def extract_hashtags(self, text: str) -> list[str]:
        """해시태그 추출"""
        hashtags = self.HASHTAG_PATTERN.findall(text)
        return [h.lstrip('#') for h in hashtags]
    
    def extract_entities(self, text: str) -> dict:
        """
        텍스트에서 엔티티 추출
        
        Args:
            text: 텍스트
        
        Returns:
            엔티티 딕셔너리
        """
        return {
            "urls": self.extract_urls(text),
            "mentions": self.extract_mentions(text),
            "hashtags": self.extract_hashtags(text)
        }
    
    def detect_language(self, text: str) -> str:
        """
        언어 감지 (간단한 휴리스틱)
        
        Args:
            text: 텍스트
        
        Returns:
            언어 코드 ('ko', 'en', 'mixed', 'unknown')
        """
        # 전처리
        clean_text = self.MENTION_PATTERN.sub('', text)
        clean_text = self.URL_PATTERN.sub('', clean_text)
        clean_text = self.HASHTAG_PATTERN.sub('', clean_text)
        
        # 한글 비율 계산
        korean_chars = len(re.findall(r'[가-힣]', clean_text))
        english_chars = len(re.findall(r'[a-zA-Z]', clean_text))
        total_chars = korean_chars + english_chars
        
        if total_chars == 0:
            return "unknown"
        
        korean_ratio = korean_chars / total_chars
        
        if korean_ratio > 0.7:
            return "ko"
        elif korean_ratio < 0.3:
            return "en"
        else:
            return "mixed"
    
    def is_spam(self, text: str) -> bool:
        """
        스팸 텍스트 감지 (간단한 휴리스틱)
        
        Args:
            text: 텍스트
        
        Returns:
            스팸 여부
        """
        # URL이 너무 많음
        urls = self.extract_urls(text)
        if len(urls) > 3:
            return True
        
        # 반복 문자가 과도함
        if len(self.REPEATED_CHAR_PATTERN.findall(text)) > 5:
            return True
        
        # 특수문자 비율이 높음
        special_chars = len(re.findall(r'[^\w\s가-힣]', text))
        if len(text) > 0 and special_chars / len(text) > 0.3:
            return True
        
        # 대문자만 있음 (영어)
        if text.isupper() and len(text) > 10:
            return True
        
        return False
    
    def normalize_whitespace(self, text: str) -> str:
        """공백 정규화"""
        return ' '.join(text.split())
    
    def remove_control_chars(self, text: str) -> str:
        """제어 문자 제거"""
        return ''.join(
            char for char in text
            if unicodedata.category(char) != 'Cc'
        )


class DataCleaner:
    """
    데이터 정제기
    
    DataFrame 수준의 데이터 정제를 수행합니다.
    """
    
    def __init__(
        self,
        text_preprocessor: Optional[TextPreprocessor] = None
    ):
        """
        DataCleaner 초기화
        
        Args:
            text_preprocessor: TextPreprocessor 인스턴스
        """
        self.text_preprocessor = text_preprocessor or TextPreprocessor()
        logger.info("DataCleaner initialized")
    
    def clean_dataframe(
        self,
        df: pd.DataFrame,
        text_columns: list[str],
        drop_duplicates: bool = True,
        drop_empty: bool = True,
        inplace: bool = False
    ) -> pd.DataFrame:
        """
        DataFrame 정제
        
        Args:
            df: 입력 DataFrame
            text_columns: 텍스트 컬럼 리스트
            drop_duplicates: 중복 제거 여부
            drop_empty: 빈 행 제거 여부
            inplace: 원본 수정 여부
        
        Returns:
            정제된 DataFrame
        """
        if not inplace:
            df = df.copy()
        
        original_len = len(df)
        
        # 텍스트 컬럼 전처리
        for col in text_columns:
            if col in df.columns:
                df[col] = df[col].fillna("").astype(str)
                df[col] = df[col].apply(self.text_preprocessor.preprocess)
        
        # 빈 행 제거
        if drop_empty:
            for col in text_columns:
                if col in df.columns:
                    df = df[df[col].str.len() > 0]
        
        # 중복 제거
        if drop_duplicates and text_columns:
            df = df.drop_duplicates(subset=text_columns, keep='first')
        
        logger.info(f"Cleaned {original_len} -> {len(df)} rows")
        
        return df
    
    def remove_duplicates(
        self,
        df: pd.DataFrame,
        columns: list[str],
        keep: str = 'first'
    ) -> pd.DataFrame:
        """
        중복 제거
        
        Args:
            df: DataFrame
            columns: 중복 판단 컬럼
            keep: 유지할 행 ('first', 'last', False)
        
        Returns:
            중복 제거된 DataFrame
        """
        return df.drop_duplicates(subset=columns, keep=keep)
    
    def filter_by_date(
        self,
        df: pd.DataFrame,
        date_column: str,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> pd.DataFrame:
        """
        날짜 범위로 필터링
        
        Args:
            df: DataFrame
            date_column: 날짜 컬럼명
            start_date: 시작 날짜
            end_date: 종료 날짜
        
        Returns:
            필터링된 DataFrame
        """
        df = df.copy()
        
        # 날짜 변환
        df[date_column] = pd.to_datetime(df[date_column])
        
        if start_date:
            df = df[df[date_column] >= start_date]
        
        if end_date:
            df = df[df[date_column] <= end_date]
        
        return df
    
    def filter_by_language(
        self,
        df: pd.DataFrame,
        text_column: str,
        language: str = 'ko'
    ) -> pd.DataFrame:
        """
        언어로 필터링
        
        Args:
            df: DataFrame
            text_column: 텍스트 컬럼명
            language: 필터링할 언어 코드
        
        Returns:
            필터링된 DataFrame
        """
        df = df.copy()
        
        df['_detected_lang'] = df[text_column].apply(
            self.text_preprocessor.detect_language
        )
        
        df = df[df['_detected_lang'] == language]
        df = df.drop(columns=['_detected_lang'])
        
        return df
    
    def filter_spam(
        self,
        df: pd.DataFrame,
        text_column: str
    ) -> pd.DataFrame:
        """
        스팸 필터링
        
        Args:
            df: DataFrame
            text_column: 텍스트 컬럼명
        
        Returns:
            스팸 제거된 DataFrame
        """
        df = df.copy()
        
        df['_is_spam'] = df[text_column].apply(
            self.text_preprocessor.is_spam
        )
        
        df = df[~df['_is_spam']]
        df = df.drop(columns=['_is_spam'])
        
        return df
    
    def extract_features(
        self,
        df: pd.DataFrame,
        text_column: str
    ) -> pd.DataFrame:
        """
        텍스트 특성 추출
        
        Args:
            df: DataFrame
            text_column: 텍스트 컬럼명
        
        Returns:
            특성이 추가된 DataFrame
        """
        df = df.copy()
        
        # 텍스트 길이
        df['text_length'] = df[text_column].str.len()
        
        # 단어 수
        df['word_count'] = df[text_column].str.split().str.len()
        
        # URL 수
        df['url_count'] = df[text_column].apply(
            lambda x: len(self.text_preprocessor.extract_urls(x))
        )
        
        # 해시태그 수
        df['hashtag_count'] = df[text_column].apply(
            lambda x: len(self.text_preprocessor.extract_hashtags(x))
        )
        
        # 멘션 수
        df['mention_count'] = df[text_column].apply(
            lambda x: len(self.text_preprocessor.extract_mentions(x))
        )
        
        # 언어
        df['language'] = df[text_column].apply(
            self.text_preprocessor.detect_language
        )
        
        return df
    
    def deduplicate_near_duplicates(
        self,
        df: pd.DataFrame,
        text_column: str,
        threshold: float = 0.9,
        method: str = "minhash"
    ) -> pd.DataFrame:
        """
        유사 중복 제거
        
        Args:
            df: DataFrame
            text_column: 텍스트 컬럼명
            threshold: 유사도 임계값
            method: 방법 (minhash, cosine)
        
        Returns:
            유사 중복 제거된 DataFrame
        """
        # 간단한 구현: Jaccard 유사도 기반
        texts = df[text_column].tolist()
        n = len(texts)
        
        # 토큰화
        tokenized = [set(text.split()) for text in texts]
        
        # 유사 중복 찾기
        to_remove = set()
        
        for i in range(n):
            if i in to_remove:
                continue
            
            for j in range(i + 1, n):
                if j in to_remove:
                    continue
                
                # Jaccard 유사도
                intersection = len(tokenized[i] & tokenized[j])
                union = len(tokenized[i] | tokenized[j])
                
                if union > 0 and intersection / union >= threshold:
                    to_remove.add(j)
        
        df = df.drop(index=list(to_remove))
        
        logger.info(f"Removed {len(to_remove)} near-duplicates")
        
        return df


# 모듈 테스트용
if __name__ == "__main__":
    # TextPreprocessor 테스트
    preprocessor = TextPreprocessor()
    
    test_texts = [
        "안녕하세요! https://example.com 링크입니다 @user #테스트 ㅋㅋㅋㅋㅋㅋ",
        "This is a TEST message with URLS: bit.ly/abc123",
        "🎉 이모지 테스트 🚀🔥",
        "특수문자!@#$%^&*() 테스트",
    ]
    
    print("Text Preprocessing Test:")
    print("-" * 60)
    
    for text in test_texts:
        processed = preprocessor.preprocess(text)
        print(f"\nOriginal: {text}")
        print(f"Processed: {processed}")
        print(f"Entities: {preprocessor.extract_entities(text)}")
        print(f"Language: {preprocessor.detect_language(text)}")
    
    # DataCleaner 테스트
    print("\n" + "=" * 60)
    print("DataCleaner Test:")
    
    df = pd.DataFrame({
        "text": test_texts + [""],
        "date": ["2024-01-01"] * (len(test_texts) + 1)
    })
    
    cleaner = DataCleaner()
    cleaned_df = cleaner.clean_dataframe(df, ["text"])
    
    print(f"\nOriginal rows: {len(df)}")
    print(f"Cleaned rows: {len(cleaned_df)}")

