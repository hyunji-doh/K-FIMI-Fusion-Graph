"""
텍스트 임베딩 모듈

Sentence Transformers를 사용하여 텍스트를 벡터로 변환합니다.
"""

import os
from typing import Optional, Union
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import torch
from loguru import logger

try:
    from sentence_transformers import SentenceTransformer
    SENTENCE_TRANSFORMERS_AVAILABLE = True
except ImportError:
    SENTENCE_TRANSFORMERS_AVAILABLE = False
    logger.warning("sentence-transformers not installed")

try:
    from transformers import AutoTokenizer, AutoModel
    TRANSFORMERS_AVAILABLE = True
except ImportError:
    TRANSFORMERS_AVAILABLE = False


@dataclass
class EmbeddingConfig:
    """임베딩 설정"""
    model_name: str = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
    max_seq_length: int = 512
    batch_size: int = 32
    device: str = "auto"
    normalize: bool = True
    cache_dir: Optional[str] = None
    
    def get_device(self) -> str:
        if self.device == "auto":
            return "cuda" if torch.cuda.is_available() else "cpu"
        return self.device


class TextEmbedder:
    """
    텍스트 임베딩 생성기
    
    다국어 Sentence Transformer를 사용하여 텍스트를 임베딩합니다.
    """
    
    # 권장 다국어 모델들
    RECOMMENDED_MODELS = {
        "multilingual-mini": "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2",
        "multilingual-mpnet": "sentence-transformers/paraphrase-multilingual-mpnet-base-v2",
        "korean-roberta": "jhgan/ko-sroberta-multitask",
        "korean-electra": "snunlp/KR-SBERT-V40K-klueNLI-augSTS",
        "bge-m3": "BAAI/bge-m3",
    }
    
    def __init__(
        self,
        config: Optional[EmbeddingConfig] = None,
        model_name: Optional[str] = None
    ):
        """
        TextEmbedder 초기화
        
        Args:
            config: 임베딩 설정
            model_name: 모델 이름 (config보다 우선)
        """
        if not SENTENCE_TRANSFORMERS_AVAILABLE:
            raise ImportError("sentence-transformers is required")
        
        self.config = config or EmbeddingConfig()
        
        if model_name:
            self.config.model_name = model_name
        
        # 환경변수에서 모델명 확인
        env_model = os.getenv("EMBEDDING_MODEL")
        if env_model:
            self.config.model_name = env_model
        
        self.device = self.config.get_device()
        
        # 모델 로드
        self.model = SentenceTransformer(
            self.config.model_name,
            device=self.device,
            cache_folder=self.config.cache_dir
        )
        self.model.max_seq_length = self.config.max_seq_length
        
        self.embedding_dim = self.model.get_sentence_embedding_dimension()
        
        logger.info(
            f"TextEmbedder initialized: {self.config.model_name} "
            f"(dim={self.embedding_dim}, device={self.device})"
        )
    
    def encode(
        self,
        texts: Union[str, list[str]],
        batch_size: Optional[int] = None,
        show_progress: bool = False,
        convert_to_numpy: bool = True
    ) -> Union[np.ndarray, torch.Tensor]:
        """
        텍스트를 임베딩으로 변환
        
        Args:
            texts: 텍스트 또는 텍스트 리스트
            batch_size: 배치 크기
            show_progress: 진행률 표시
            convert_to_numpy: numpy 배열로 변환
        
        Returns:
            임베딩 벡터 (N, dim)
        """
        if isinstance(texts, str):
            texts = [texts]
        
        embeddings = self.model.encode(
            texts,
            batch_size=batch_size or self.config.batch_size,
            show_progress_bar=show_progress,
            convert_to_numpy=convert_to_numpy,
            normalize_embeddings=self.config.normalize
        )
        
        return embeddings
    
    def encode_with_cache(
        self,
        texts: list[str],
        cache_path: str,
        text_ids: Optional[list[str]] = None
    ) -> np.ndarray:
        """
        캐시를 활용한 인코딩
        
        Args:
            texts: 텍스트 리스트
            cache_path: 캐시 파일 경로
            text_ids: 텍스트 ID 리스트 (캐시 키로 사용)
        
        Returns:
            임베딩 배열
        """
        cache_file = Path(cache_path)
        
        if cache_file.exists():
            # 캐시 로드
            cache = np.load(cache_file, allow_pickle=True).item()
            
            # 캐시에 없는 텍스트만 인코딩
            if text_ids:
                missing_indices = [
                    i for i, tid in enumerate(text_ids)
                    if tid not in cache
                ]
            else:
                missing_indices = list(range(len(texts)))
            
            if missing_indices:
                missing_texts = [texts[i] for i in missing_indices]
                new_embeddings = self.encode(missing_texts)
                
                # 캐시 업데이트
                for i, idx in enumerate(missing_indices):
                    key = text_ids[idx] if text_ids else idx
                    cache[key] = new_embeddings[i]
                
                np.save(cache_file, cache)
            
            # 결과 조합
            if text_ids:
                embeddings = np.array([cache[tid] for tid in text_ids])
            else:
                embeddings = np.array([cache[i] for i in range(len(texts))])
        
        else:
            # 새로 인코딩
            embeddings = self.encode(texts, show_progress=True)
            
            # 캐시 저장
            if text_ids:
                cache = {tid: emb for tid, emb in zip(text_ids, embeddings)}
            else:
                cache = {i: emb for i, emb in enumerate(embeddings)}
            
            cache_file.parent.mkdir(parents=True, exist_ok=True)
            np.save(cache_file, cache)
        
        return embeddings
    
    def compute_similarity(
        self,
        texts1: Union[str, list[str]],
        texts2: Union[str, list[str]],
        metric: str = "cosine"
    ) -> np.ndarray:
        """
        텍스트 쌍의 유사도 계산
        
        Args:
            texts1: 첫 번째 텍스트(들)
            texts2: 두 번째 텍스트(들)
            metric: 유사도 메트릭 (cosine, dot, euclidean)
        
        Returns:
            유사도 점수 배열
        """
        emb1 = self.encode(texts1)
        emb2 = self.encode(texts2)
        
        if emb1.ndim == 1:
            emb1 = emb1.reshape(1, -1)
        if emb2.ndim == 1:
            emb2 = emb2.reshape(1, -1)
        
        if metric == "cosine":
            # 코사인 유사도
            sim = np.dot(emb1, emb2.T)
            if not self.config.normalize:
                norm1 = np.linalg.norm(emb1, axis=1, keepdims=True)
                norm2 = np.linalg.norm(emb2, axis=1, keepdims=True)
                sim = sim / (norm1 @ norm2.T + 1e-8)
        
        elif metric == "dot":
            # 내적
            sim = np.dot(emb1, emb2.T)
        
        elif metric == "euclidean":
            # 유클리드 거리 (거리를 유사도로 변환)
            from scipy.spatial.distance import cdist
            dist = cdist(emb1, emb2, metric='euclidean')
            sim = 1 / (1 + dist)
        
        else:
            raise ValueError(f"Unknown metric: {metric}")
        
        return sim.squeeze()
    
    def find_similar(
        self,
        query: str,
        corpus: list[str],
        top_k: int = 10,
        threshold: float = 0.0
    ) -> list[tuple[int, str, float]]:
        """
        유사 텍스트 검색
        
        Args:
            query: 쿼리 텍스트
            corpus: 검색 대상 텍스트 리스트
            top_k: 상위 k개 반환
            threshold: 최소 유사도 임계값
        
        Returns:
            (인덱스, 텍스트, 유사도) 튜플 리스트
        """
        query_emb = self.encode(query)
        corpus_emb = self.encode(corpus, show_progress=True)
        
        # 코사인 유사도
        similarities = np.dot(corpus_emb, query_emb)
        
        # 상위 k개 추출
        top_indices = np.argsort(similarities)[::-1][:top_k]
        
        results = []
        for idx in top_indices:
            sim = similarities[idx]
            if sim >= threshold:
                results.append((idx, corpus[idx], float(sim)))
        
        return results
    
    def cluster_texts(
        self,
        texts: list[str],
        n_clusters: int = 10,
        method: str = "kmeans"
    ) -> tuple[np.ndarray, np.ndarray]:
        """
        텍스트 클러스터링
        
        Args:
            texts: 텍스트 리스트
            n_clusters: 클러스터 수
            method: 클러스터링 방법 (kmeans, hdbscan)
        
        Returns:
            (레이블 배열, 임베딩 배열) 튜플
        """
        embeddings = self.encode(texts, show_progress=True)
        
        if method == "kmeans":
            from sklearn.cluster import KMeans
            kmeans = KMeans(n_clusters=n_clusters, random_state=42)
            labels = kmeans.fit_predict(embeddings)
        
        elif method == "hdbscan":
            try:
                import hdbscan
                clusterer = hdbscan.HDBSCAN(min_cluster_size=5)
                labels = clusterer.fit_predict(embeddings)
            except ImportError:
                logger.warning("hdbscan not installed, using kmeans")
                return self.cluster_texts(texts, n_clusters, "kmeans")
        
        else:
            raise ValueError(f"Unknown method: {method}")
        
        return labels, embeddings
    
    @classmethod
    def get_recommended_model(cls, language: str = "multilingual") -> str:
        """권장 모델 반환"""
        if language == "korean":
            return cls.RECOMMENDED_MODELS["korean-roberta"]
        elif language == "multilingual":
            return cls.RECOMMENDED_MODELS["multilingual-mini"]
        else:
            return cls.RECOMMENDED_MODELS["multilingual-mpnet"]


class HuggingFaceEmbedder:
    """
    HuggingFace Transformers 기반 임베딩 생성기
    
    커스텀 모델이나 LLM 임베딩을 위한 대안 클래스입니다.
    """
    
    def __init__(
        self,
        model_name: str = "klue/roberta-base",
        pooling: str = "mean",
        device: str = "auto"
    ):
        """
        HuggingFaceEmbedder 초기화
        
        Args:
            model_name: HuggingFace 모델 이름
            pooling: 풀링 전략 (mean, cls, max)
            device: 디바이스
        """
        if not TRANSFORMERS_AVAILABLE:
            raise ImportError("transformers is required")
        
        self.device = device if device != "auto" else (
            "cuda" if torch.cuda.is_available() else "cpu"
        )
        
        self.tokenizer = AutoTokenizer.from_pretrained(model_name)
        self.model = AutoModel.from_pretrained(model_name).to(self.device)
        self.model.eval()
        
        self.pooling = pooling
        self.embedding_dim = self.model.config.hidden_size
        
        logger.info(f"HuggingFaceEmbedder: {model_name} (dim={self.embedding_dim})")
    
    def encode(
        self,
        texts: Union[str, list[str]],
        batch_size: int = 32
    ) -> np.ndarray:
        """텍스트 인코딩"""
        if isinstance(texts, str):
            texts = [texts]
        
        all_embeddings = []
        
        for i in range(0, len(texts), batch_size):
            batch = texts[i:i + batch_size]
            
            # 토큰화
            inputs = self.tokenizer(
                batch,
                padding=True,
                truncation=True,
                max_length=512,
                return_tensors="pt"
            ).to(self.device)
            
            # 임베딩 추출
            with torch.no_grad():
                outputs = self.model(**inputs)
                
                if self.pooling == "mean":
                    # Mean pooling
                    attention_mask = inputs["attention_mask"]
                    token_embeddings = outputs.last_hidden_state
                    mask_expanded = attention_mask.unsqueeze(-1).expand(token_embeddings.size())
                    sum_embeddings = torch.sum(token_embeddings * mask_expanded, dim=1)
                    sum_mask = mask_expanded.sum(dim=1).clamp(min=1e-9)
                    embeddings = sum_embeddings / sum_mask
                
                elif self.pooling == "cls":
                    # CLS 토큰
                    embeddings = outputs.last_hidden_state[:, 0, :]
                
                elif self.pooling == "max":
                    # Max pooling
                    token_embeddings = outputs.last_hidden_state
                    embeddings = torch.max(token_embeddings, dim=1)[0]
                
                all_embeddings.append(embeddings.cpu().numpy())
        
        return np.vstack(all_embeddings)


# 모듈 테스트용
if __name__ == "__main__":
    # TextEmbedder 테스트
    embedder = TextEmbedder()
    
    texts = [
        "허위정보 탐지 시스템을 개발하고 있습니다.",
        "가짜뉴스 검출 기술 연구 중입니다.",
        "오늘 날씨가 좋습니다.",
        "맛있는 음식을 먹었습니다."
    ]
    
    embeddings = embedder.encode(texts)
    print(f"Embeddings shape: {embeddings.shape}")
    
    # 유사도 계산
    similarities = embedder.compute_similarity(texts[0], texts)
    print(f"Similarities to first text: {similarities}")
    
    # 유사 텍스트 검색
    results = embedder.find_similar(texts[0], texts, top_k=3)
    print("\nSimilar texts:")
    for idx, text, sim in results:
        print(f"  {sim:.4f}: {text}")

