"""
내러티브 자동 추출 모듈

텍스트에서 "동맹 파기", "선거 부정" 같은 구체적 내러티브를 자동으로 추출합니다.
"""

import re
from typing import List, Dict, Optional, Set
from dataclasses import dataclass, field
from collections import Counter
from datetime import datetime

from loguru import logger

try:
    from sentence_transformers import SentenceTransformer
    import numpy as np
    SENTENCE_TRANSFORMERS_AVAILABLE = True
except ImportError:
    SENTENCE_TRANSFORMERS_AVAILABLE = False
    logger.warning("sentence-transformers not available. Using basic extraction.")


@dataclass
class Narrative:
    """내러티브 데이터"""
    narrative_id: str
    narrative_text: str
    keywords: List[str] = field(default_factory=list)
    related_keywords: List[str] = field(default_factory=list)
    first_seen: Optional[datetime] = None
    prevalence: int = 0  # 출현 빈도
    confidence: float = 0.0  # 신뢰도
    category: Optional[str] = None  # 'security', 'election', 'diplomacy', etc.
    
    def to_dict(self) -> dict:
        return {
            "narrative_id": self.narrative_id,
            "narrative_text": self.narrative_text,
            "keywords": self.keywords,
            "related_keywords": self.related_keywords,
            "first_seen": self.first_seen.isoformat() if self.first_seen else None,
            "prevalence": self.prevalence,
            "confidence": self.confidence,
            "category": self.category
        }


class NarrativeExtractor:
    """
    내러티브 자동 추출기
    
    텍스트에서 반복되는 내러티브 패턴을 추출합니다.
    """
    
    # 알려진 내러티브 패턴
    KNOWN_NARRATIVES = [
        {
            "narrative_id": "alliance_breakdown",
            "narrative_text": "동맹 파기",
            "patterns": [
                r"동맹.*파기",
                r"동맹.*해체",
                r"동맹.*종료",
                r"한미동맹.*흔들",
                r"동맹.*위기"
            ],
            "keywords": ["동맹", "파기", "해체", "종료"],
            "category": "security"
        },
        {
            "narrative_id": "election_fraud",
            "narrative_text": "선거 부정",
            "patterns": [
                r"선거.*부정",
                r"선거.*조작",
                r"개표.*조작",
                r"투표.*조작",
                r"선거.*개입"
            ],
            "keywords": ["선거", "부정", "조작", "개표"],
            "category": "election"
        },
        {
            "narrative_id": "government_corruption",
            "narrative_text": "정부 부패",
            "patterns": [
                r"정부.*부패",
                r"정부.*비리",
                r"정부.*은폐",
                r"정부.*조작"
            ],
            "keywords": ["정부", "부패", "비리"],
            "category": "security"
        },
        {
            "narrative_id": "economic_crisis",
            "narrative_text": "경제 위기",
            "patterns": [
                r"경제.*위기",
                r"경제.*파탄",
                r"은행.*파산",
                r"금융.*위기",
                r"경제.*마비"
            ],
            "keywords": ["경제", "위기", "파산", "은행"],
            "category": "economy"
        },
        {
            "narrative_id": "document_leak",
            "narrative_text": "문서 유출",
            "patterns": [
                r"문서.*유출",
                r"내부.*문서",
                r"기밀.*유출",
                r"문서.*누출"
            ],
            "keywords": ["문서", "유출", "기밀"],
            "category": "disinformation"
        },
        {
            "narrative_id": "military_withdrawal",
            "narrative_text": "미군 철수",
            "patterns": [
                r"미군.*철수",
                r"주한미군.*철수",
                r"미군.*이탈",
                r"미군.*철수설"
            ],
            "keywords": ["미군", "철수", "주한미군"],
            "category": "security"
        }
    ]
    
    def __init__(
        self,
        use_embedding: bool = True,
        similarity_threshold: float = 0.7
    ):
        """
        NarrativeExtractor 초기화
        
        Args:
            use_embedding: 임베딩 기반 유사도 계산 사용 여부
            similarity_threshold: 유사도 임계값
        """
        self.use_embedding = use_embedding and SENTENCE_TRANSFORMERS_AVAILABLE
        self.similarity_threshold = similarity_threshold
        
        # 패턴 컴파일
        self.compiled_patterns = {}
        for narrative in self.KNOWN_NARRATIVES:
            self.compiled_patterns[narrative["narrative_id"]] = [
                re.compile(pattern, re.IGNORECASE) for pattern in narrative["patterns"]
            ]
        
        # 임베딩 모델 로드
        if self.use_embedding:
            try:
                self.embedding_model = SentenceTransformer(
                    'paraphrase-multilingual-MiniLM-L12-v2'
                )
                logger.info("Embedding model loaded for narrative extraction")
            except Exception as e:
                logger.warning(f"Failed to load embedding model: {e}")
                self.use_embedding = False
        
        logger.info("NarrativeExtractor initialized")
    
    def extract_from_text(self, text: str) -> List[Narrative]:
        """
        텍스트에서 내러티브 추출
        
        Args:
            text: 분석할 텍스트
        
        Returns:
            추출된 내러티브 리스트
        """
        narratives = []
        
        # 알려진 패턴 매칭
        for narrative_def in self.KNOWN_NARRATIVES:
            narrative_id = narrative_def["narrative_id"]
            patterns = self.compiled_patterns.get(narrative_id, [])
            
            for pattern in patterns:
                if pattern.search(text):
                    narrative = Narrative(
                        narrative_id=narrative_id,
                        narrative_text=narrative_def["narrative_text"],
                        keywords=narrative_def["keywords"],
                        first_seen=datetime.now(),
                        prevalence=1,
                        confidence=0.8,  # 패턴 매칭 기반 신뢰도
                        category=narrative_def["category"]
                    )
                    narratives.append(narrative)
                    break  # 하나의 패턴만 매칭되면 충분
        
        return narratives
    
    def extract_from_texts(
        self,
        texts: List[str],
        min_prevalence: int = 2
    ) -> Dict[str, Narrative]:
        """
        여러 텍스트에서 내러티브 추출 및 집계
        
        Args:
            texts: 텍스트 리스트
            min_prevalence: 최소 출현 빈도
        
        Returns:
            {narrative_id: Narrative} 딕셔너리
        """
        narrative_counts: Dict[str, int] = Counter()
        narrative_instances: Dict[str, List[Narrative]] = {}
        
        # 각 텍스트에서 내러티브 추출
        for text in texts:
            narratives = self.extract_from_text(text)
            for narrative in narratives:
                narrative_id = narrative.narrative_id
                narrative_counts[narrative_id] += 1
                
                if narrative_id not in narrative_instances:
                    narrative_instances[narrative_id] = []
                narrative_instances[narrative_id].append(narrative)
        
        # 최소 빈도 이상인 내러티브만 반환
        result = {}
        for narrative_id, count in narrative_counts.items():
            if count >= min_prevalence:
                instances = narrative_instances[narrative_id]
                first_instance = instances[0]
                
                # 집계된 내러티브 생성
                aggregated = Narrative(
                    narrative_id=narrative_id,
                    narrative_text=first_instance.narrative_text,
                    keywords=first_instance.keywords,
                    first_seen=min([n.first_seen for n in instances if n.first_seen]),
                    prevalence=count,
                    confidence=min(1.0, count / 10.0),  # 빈도 기반 신뢰도
                    category=first_instance.category
                )
                result[narrative_id] = aggregated
        
        return result
    
    def find_similar_narratives(
        self,
        text: str,
        existing_narratives: List[Narrative]
    ) -> List[tuple[Narrative, float]]:
        """
        임베딩 기반 유사 내러티브 찾기
        
        Args:
            text: 검색할 텍스트
            existing_narratives: 기존 내러티브 리스트
        
        Returns:
            [(Narrative, similarity_score)] 리스트
        """
        if not self.use_embedding or not existing_narratives:
            return []
        
        # 텍스트 임베딩
        text_embedding = self.embedding_model.encode([text])[0]
        
        # 기존 내러티브와 유사도 계산
        similar = []
        for narrative in existing_narratives:
            narrative_text = narrative.narrative_text
            narrative_embedding = self.embedding_model.encode([narrative_text])[0]
            
            # 코사인 유사도
            similarity = np.dot(text_embedding, narrative_embedding) / (
                np.linalg.norm(text_embedding) * np.linalg.norm(narrative_embedding)
            )
            
            if similarity >= self.similarity_threshold:
                similar.append((narrative, float(similarity)))
        
        # 유사도 순 정렬
        similar.sort(key=lambda x: x[1], reverse=True)
        
        return similar
    
    def extract_narratives_with_clustering(
        self,
        texts: List[str],
        min_cluster_size: int = 3
    ) -> Dict[str, Narrative]:
        """
        클러스터링 기반 내러티브 추출
        
        Args:
            texts: 텍스트 리스트
            min_cluster_size: 최소 클러스터 크기
        
        Returns:
            {narrative_id: Narrative} 딕셔너리
        """
        if not self.use_embedding:
            # 임베딩 없으면 기본 추출만 수행
            return self.extract_from_texts(texts, min_prevalence=min_cluster_size)
        
        try:
            from sklearn.cluster import DBSCAN
            from sklearn.metrics.pairwise import cosine_similarity
            
            # 텍스트 임베딩
            embeddings = self.embedding_model.encode(texts)
            
            # DBSCAN 클러스터링
            clustering = DBSCAN(
                eps=0.3,
                min_samples=min_cluster_size,
                metric='cosine'
            )
            cluster_labels = clustering.fit_predict(embeddings)
            
            # 클러스터별 내러티브 생성
            narratives = {}
            unique_labels = set(cluster_labels)
            
            for label in unique_labels:
                if label == -1:  # 노이즈
                    continue
                
                cluster_texts = [texts[i] for i in range(len(texts)) if cluster_labels[i] == label]
                
                if len(cluster_texts) < min_cluster_size:
                    continue
                
                # 클러스터 대표 텍스트 선택 (중앙값에 가까운 것)
                cluster_embeddings = embeddings[cluster_labels == label]
                centroid = cluster_embeddings.mean(axis=0)
                similarities = cosine_similarity([centroid], cluster_embeddings)[0]
                representative_idx = similarities.argmax()
                representative_text = cluster_texts[representative_idx]
                
                # 내러티브 생성
                narrative_id = f"narrative_cluster_{label}"
                narrative = Narrative(
                    narrative_id=narrative_id,
                    narrative_text=representative_text[:100],  # 처음 100자
                    first_seen=datetime.now(),
                    prevalence=len(cluster_texts),
                    confidence=min(1.0, len(cluster_texts) / 20.0),
                    category=None  # 자동 분류 필요
                )
                narratives[narrative_id] = narrative
            
            return narratives
            
        except ImportError:
            logger.warning("sklearn not available. Using basic extraction.")
            return self.extract_from_texts(texts, min_prevalence=min_cluster_size)


# 모듈 테스트용
if __name__ == "__main__":
    extractor = NarrativeExtractor()
    
    test_texts = [
        "한미동맹이 흔들리고 있다. 정부는 대책을 마련해야 한다.",
        "동맹 파기설이 돌고 있다. 확인되지 않은 정보에 주의하세요.",
        "선거 부정이 의심된다. 개표 과정을 재검토해야 한다.",
        "선거 조작이 있었다는 주장이 제기되고 있다.",
        "경제 위기가 다가오고 있다. 은행 시스템이 마비될 수 있다.",
    ]
    
    print("Narrative Extraction Test:")
    print("=" * 60)
    
    # 기본 추출
    narratives = extractor.extract_from_texts(test_texts, min_prevalence=1)
    for narrative_id, narrative in narratives.items():
        print(f"\nNarrative: {narrative.narrative_text}")
        print(f"  ID: {narrative_id}")
        print(f"  Category: {narrative.category}")
        print(f"  Prevalence: {narrative.prevalence}")
        print(f"  Confidence: {narrative.confidence:.2f}")
