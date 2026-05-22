"""
N-gram 기반 템플릿 추출 모듈

유사 문장 템플릿을 N-gram 및 벡터 유사도 기반으로 추출합니다.
"""

import re
from typing import List, Dict, Tuple, Set
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from datetime import datetime

from loguru import logger

try:
    from sentence_transformers import SentenceTransformer
    import numpy as np
    from sklearn.metrics.pairwise import cosine_similarity
    SENTENCE_TRANSFORMERS_AVAILABLE = True
except ImportError:
    SENTENCE_TRANSFORMERS_AVAILABLE = False
    logger.warning("sentence-transformers/sklearn not available. Using basic N-gram extraction.")


@dataclass
class TextTemplate:
    """텍스트 템플릿"""
    template_id: str
    template_text: str
    ngram_pattern: Optional[str] = None
    frequency: int = 0
    similar_texts: List[str] = field(default_factory=list)
    first_seen: Optional[datetime] = None
    last_seen: Optional[datetime] = None
    
    def to_dict(self) -> dict:
        return {
            "template_id": self.template_id,
            "template_text": self.template_text,
            "ngram_pattern": self.ngram_pattern,
            "frequency": self.frequency,
            "similar_texts": self.similar_texts[:5],  # 상위 5개만
            "first_seen": self.first_seen.isoformat() if self.first_seen else None,
            "last_seen": self.last_seen.isoformat() if self.last_seen else None
        }


class TemplateExtractor:
    """
    템플릿 추출기
    
    N-gram 및 벡터 유사도 기반으로 유사 문장 템플릿을 추출합니다.
    """
    
    def __init__(
        self,
        ngram_size: int = 3,
        similarity_threshold: float = 0.8,
        min_frequency: int = 2,
        use_embedding: bool = True
    ):
        """
        TemplateExtractor 초기화
        
        Args:
            ngram_size: N-gram 크기
            similarity_threshold: 유사도 임계값
            min_frequency: 최소 출현 빈도
            use_embedding: 임베딩 기반 유사도 사용 여부
        """
        self.ngram_size = ngram_size
        self.similarity_threshold = similarity_threshold
        self.min_frequency = min_frequency
        self.use_embedding = use_embedding and SENTENCE_TRANSFORMERS_AVAILABLE
        
        if self.use_embedding:
            try:
                self.embedding_model = SentenceTransformer(
                    'paraphrase-multilingual-MiniLM-L12-v2'
                )
                logger.info("Embedding model loaded for template extraction")
            except Exception as e:
                logger.warning(f"Failed to load embedding model: {e}")
                self.use_embedding = False
        
        logger.info("TemplateExtractor initialized")
    
    def extract_ngrams(self, text: str) -> List[str]:
        """
        텍스트에서 N-gram 추출
        
        Args:
            text: 텍스트
        
        Returns:
            N-gram 리스트
        """
        # 단어 토큰화 (한글, 영문, 숫자)
        words = re.findall(r'\w+', text.lower())
        
        if len(words) < self.ngram_size:
            return []
        
        ngrams = []
        for i in range(len(words) - self.ngram_size + 1):
            ngram = ' '.join(words[i:i + self.ngram_size])
            ngrams.append(ngram)
        
        return ngrams
    
    def extract_templates_ngram(self, texts: List[str]) -> Dict[str, TextTemplate]:
        """
        N-gram 기반 템플릿 추출
        
        Args:
            texts: 텍스트 리스트
        
        Returns:
            {template_id: TextTemplate} 딕셔너리
        """
        # 모든 텍스트에서 N-gram 추출
        text_ngrams: Dict[int, List[str]] = {}  # {text_idx: [ngrams]}
        ngram_to_texts: Dict[str, List[int]] = defaultdict(list)  # {ngram: [text_indices]}
        
        for idx, text in enumerate(texts):
            ngrams = self.extract_ngrams(text)
            text_ngrams[idx] = ngrams
            
            for ngram in ngrams:
                ngram_to_texts[ngram].append(idx)
        
        # 공통 N-gram 찾기 (최소 빈도 이상)
        common_ngrams = {
            ngram: text_indices
            for ngram, text_indices in ngram_to_texts.items()
            if len(text_indices) >= self.min_frequency
        }
        
        # N-gram 기반 템플릿 그룹핑
        templates = {}
        template_counter = 0
        
        # N-gram을 공유하는 텍스트들을 그룹화
        ngram_groups: Dict[Tuple[str, ...], List[int]] = defaultdict(list)
        
        for ngram, text_indices in common_ngrams.items():
            # 공통 N-gram을 가진 텍스트들을 그룹화
            for text_idx in text_indices:
                # 해당 텍스트의 모든 N-gram
                text_ngram_set = set(text_ngrams[text_idx])
                # 공통 N-gram과 교집합이 있는 텍스트들을 같은 그룹으로
                key = tuple(sorted(text_ngram_set & set([ngram])))
                ngram_groups[key].append(text_idx)
        
        # 각 그룹에서 템플릿 생성
        for ngram_set, text_indices in ngram_groups.items():
            if len(text_indices) < self.min_frequency:
                continue
            
            # 대표 텍스트 선택 (가장 짧은 것)
            representative_text = min(
                [texts[idx] for idx in text_indices],
                key=len
            )
            
            template_id = f"tmpl_{template_counter:03d}"
            template = TextTemplate(
                template_id=template_id,
                template_text=representative_text,
                ngram_pattern=', '.join(ngram_set),
                frequency=len(text_indices),
                similar_texts=[texts[idx] for idx in text_indices[:10]],
                first_seen=datetime.now(),
                last_seen=datetime.now()
            )
            
            templates[template_id] = template
            template_counter += 1
        
        return templates
    
    def extract_templates_embedding(
        self,
        texts: List[str],
        min_cluster_size: int = 2
    ) -> Dict[str, TextTemplate]:
        """
        임베딩 기반 템플릿 추출
        
        Args:
            texts: 텍스트 리스트
            min_cluster_size: 최소 클러스터 크기
        
        Returns:
            {template_id: TextTemplate} 딕셔너리
        """
        if not self.use_embedding:
            return self.extract_templates_ngram(texts)
        
        try:
            from sklearn.cluster import DBSCAN
            
            # 텍스트 임베딩
            embeddings = self.embedding_model.encode(texts)
            
            # DBSCAN 클러스터링
            clustering = DBSCAN(
                eps=0.3,
                min_samples=min_cluster_size,
                metric='cosine'
            )
            cluster_labels = clustering.fit_predict(embeddings)
            
            templates = {}
            template_counter = 0
            
            unique_labels = set(cluster_labels)
            for label in unique_labels:
                if label == -1:  # 노이즈
                    continue
                
                cluster_texts = [
                    texts[i] for i in range(len(texts))
                    if cluster_labels[i] == label
                ]
                
                if len(cluster_texts) < min_cluster_size:
                    continue
                
                # 클러스터 중심에 가까운 텍스트를 대표 텍스트로 선택
                cluster_embeddings = embeddings[cluster_labels == label]
                centroid = cluster_embeddings.mean(axis=0)
                similarities = cosine_similarity([centroid], cluster_embeddings)[0]
                representative_idx = similarities.argmax()
                representative_text = cluster_texts[representative_idx]
                
                template_id = f"tmpl_{template_counter:03d}"
                template = TextTemplate(
                    template_id=template_id,
                    template_text=representative_text,
                    frequency=len(cluster_texts),
                    similar_texts=cluster_texts[:10],
                    first_seen=datetime.now(),
                    last_seen=datetime.now()
                )
                
                templates[template_id] = template
                template_counter += 1
            
            return templates
            
        except ImportError:
            logger.warning("sklearn not available. Using N-gram extraction.")
            return self.extract_templates_ngram(texts)
    
    def extract_templates(
        self,
        texts: List[str],
        method: str = "auto"
    ) -> Dict[str, TextTemplate]:
        """
        템플릿 추출 (통합 메서드)
        
        Args:
            texts: 텍스트 리스트
            method: 추출 방법 ('ngram', 'embedding', 'auto')
        
        Returns:
            {template_id: TextTemplate} 딕셔너리
        """
        if method == "ngram":
            return self.extract_templates_ngram(texts)
        elif method == "embedding":
            return self.extract_templates_embedding(texts)
        else:  # auto
            # 둘 다 시도하고 더 많은 템플릿을 찾은 방법 사용
            ngram_templates = self.extract_templates_ngram(texts)
            embedding_templates = self.extract_templates_embedding(texts)
            
            if len(embedding_templates) > len(ngram_templates):
                return embedding_templates
            else:
                return ngram_templates


# 모듈 테스트용
if __name__ == "__main__":
    extractor = TemplateExtractor(ngram_size=3, min_frequency=2)
    
    test_texts = [
        "한미동맹이 흔들리고 있다. 정부는 대책을 마련해야 한다.",
        "한미동맹이 흔들리고 있다. 정부는 대책을 마련해야 한다.",
        "동맹이 흔들리고 있다. 정부는 대책을 마련해야 한다.",
        "선거 부정이 의심된다. 개표 과정을 재검토해야 한다.",
        "선거 부정이 의심된다. 개표 과정을 재검토해야 한다.",
    ]
    
    print("Template Extraction Test:")
    print("=" * 60)
    
    templates = extractor.extract_templates(test_texts, method="auto")
    
    for template_id, template in templates.items():
        print(f"\nTemplate: {template_id}")
        print(f"  Text: {template.template_text}")
        print(f"  Frequency: {template.frequency}")
        print(f"  N-gram pattern: {template.ngram_pattern}")


