"""
그래프 클러스터링 모듈

Louvain, Leiden, Spectral Clustering, BERTopic 등을 사용하여
캠페인 단위 클러스터링을 수행합니다.
"""

from typing import Optional, Union
from dataclasses import dataclass, field
from enum import Enum

import numpy as np
import networkx as nx
import pandas as pd
from sklearn.cluster import SpectralClustering, KMeans, DBSCAN
from sklearn.metrics import silhouette_score
from loguru import logger

# Community detection libraries
try:
    import community as community_louvain  # python-louvain
    LOUVAIN_AVAILABLE = True
except ImportError:
    LOUVAIN_AVAILABLE = False
    logger.warning("python-louvain not installed. Louvain clustering unavailable.")

try:
    import leidenalg
    import igraph as ig
    LEIDEN_AVAILABLE = True
except ImportError:
    LEIDEN_AVAILABLE = False
    logger.warning("leidenalg not installed. Leiden clustering unavailable.")

try:
    from bertopic import BERTopic
    BERTOPIC_AVAILABLE = True
except ImportError:
    BERTOPIC_AVAILABLE = False
    logger.warning("bertopic not installed. Topic clustering unavailable.")


class ClusteringMethod(str, Enum):
    """클러스터링 방법"""
    LOUVAIN = "louvain"
    LEIDEN = "leiden"
    SPECTRAL = "spectral"
    KMEANS = "kmeans"
    DBSCAN = "dbscan"
    BERTOPIC = "bertopic"


@dataclass
class ClusterResult:
    """클러스터링 결과"""
    method: ClusteringMethod
    num_clusters: int
    labels: np.ndarray
    node_ids: list[str]
    modularity: Optional[float] = None
    silhouette: Optional[float] = None
    cluster_sizes: dict = field(default_factory=dict)
    cluster_metadata: dict = field(default_factory=dict)
    
    def get_cluster_members(self, cluster_id: int) -> list[str]:
        """특정 클러스터의 멤버 노드 반환"""
        return [
            self.node_ids[i] for i, label in enumerate(self.labels)
            if label == cluster_id
        ]
    
    def to_dict(self) -> dict:
        """딕셔너리 변환"""
        return {
            "method": self.method.value,
            "num_clusters": self.num_clusters,
            "modularity": self.modularity,
            "silhouette": self.silhouette,
            "cluster_sizes": self.cluster_sizes,
            "clusters": {
                cluster_id: self.get_cluster_members(cluster_id)
                for cluster_id in range(self.num_clusters)
            }
        }


class GraphClusterer:
    """
    그래프 클러스터링 클래스
    
    다양한 클러스터링 알고리즘을 사용하여 그래프 커뮤니티를 탐지합니다.
    """
    
    def __init__(self, random_state: int = 42):
        """
        GraphClusterer 초기화
        
        Args:
            random_state: 랜덤 시드
        """
        self.random_state = random_state
        logger.info("GraphClusterer initialized")
    
    def cluster(
        self,
        G: nx.Graph,
        method: ClusteringMethod = ClusteringMethod.LOUVAIN,
        n_clusters: Optional[int] = None,
        resolution: float = 1.0,
        **kwargs
    ) -> ClusterResult:
        """
        그래프 클러스터링 수행
        
        Args:
            G: NetworkX 그래프
            method: 클러스터링 방법
            n_clusters: 클러스터 수 (일부 알고리즘에서 사용)
            resolution: 해상도 파라미터 (Louvain, Leiden)
            **kwargs: 추가 파라미터
        
        Returns:
            ClusterResult 객체
        """
        if method == ClusteringMethod.LOUVAIN:
            return self._louvain_clustering(G, resolution)
        elif method == ClusteringMethod.LEIDEN:
            return self._leiden_clustering(G, resolution)
        elif method == ClusteringMethod.SPECTRAL:
            return self._spectral_clustering(G, n_clusters or 10, **kwargs)
        elif method == ClusteringMethod.KMEANS:
            return self._kmeans_clustering(G, n_clusters or 10, **kwargs)
        elif method == ClusteringMethod.DBSCAN:
            return self._dbscan_clustering(G, **kwargs)
        else:
            raise ValueError(f"Unknown clustering method: {method}")
    
    def _louvain_clustering(
        self,
        G: nx.Graph,
        resolution: float = 1.0
    ) -> ClusterResult:
        """
        Louvain 커뮤니티 탐지
        
        Args:
            G: NetworkX 그래프 (무방향)
            resolution: 해상도 파라미터
        
        Returns:
            ClusterResult
        """
        if not LOUVAIN_AVAILABLE:
            raise ImportError("python-louvain is required for Louvain clustering")
        
        # 무방향 그래프로 변환
        if G.is_directed():
            G = G.to_undirected()
        
        # Louvain 클러스터링
        partition = community_louvain.best_partition(
            G,
            resolution=resolution,
            random_state=self.random_state
        )
        
        # 결과 정리
        node_ids = list(partition.keys())
        labels = np.array([partition[node] for node in node_ids])
        num_clusters = len(set(labels))
        
        # 모듈러리티 계산
        modularity = community_louvain.modularity(partition, G)
        
        # 클러스터 크기
        cluster_sizes = {}
        for label in set(labels):
            cluster_sizes[label] = np.sum(labels == label)
        
        logger.info(f"Louvain clustering: {num_clusters} clusters, modularity={modularity:.4f}")
        
        return ClusterResult(
            method=ClusteringMethod.LOUVAIN,
            num_clusters=num_clusters,
            labels=labels,
            node_ids=node_ids,
            modularity=modularity,
            cluster_sizes=cluster_sizes
        )
    
    def _leiden_clustering(
        self,
        G: nx.Graph,
        resolution: float = 1.0
    ) -> ClusterResult:
        """
        Leiden 커뮤니티 탐지
        
        Args:
            G: NetworkX 그래프
            resolution: 해상도 파라미터
        
        Returns:
            ClusterResult
        """
        if not LEIDEN_AVAILABLE:
            raise ImportError("leidenalg is required for Leiden clustering")
        
        # NetworkX -> igraph 변환
        if G.is_directed():
            G = G.to_undirected()
        
        # igraph 그래프 생성
        node_ids = list(G.nodes())
        node_idx = {node: i for i, node in enumerate(node_ids)}
        
        edges = [(node_idx[u], node_idx[v]) for u, v in G.edges()]
        ig_graph = ig.Graph(n=len(node_ids), edges=edges)
        
        # 가중치 설정
        if nx.is_weighted(G):
            weights = [G[u][v].get("weight", 1.0) for u, v in G.edges()]
            ig_graph.es["weight"] = weights
        
        # Leiden 클러스터링
        partition = leidenalg.find_partition(
            ig_graph,
            leidenalg.RBConfigurationVertexPartition,
            resolution_parameter=resolution,
            seed=self.random_state
        )
        
        # 결과 정리
        labels = np.array(partition.membership)
        num_clusters = len(set(labels))
        
        # 모듈러리티
        modularity = partition.modularity
        
        # 클러스터 크기
        cluster_sizes = {i: len(c) for i, c in enumerate(partition)}
        
        logger.info(f"Leiden clustering: {num_clusters} clusters, modularity={modularity:.4f}")
        
        return ClusterResult(
            method=ClusteringMethod.LEIDEN,
            num_clusters=num_clusters,
            labels=labels,
            node_ids=node_ids,
            modularity=modularity,
            cluster_sizes=cluster_sizes
        )
    
    def _spectral_clustering(
        self,
        G: nx.Graph,
        n_clusters: int = 10,
        **kwargs
    ) -> ClusterResult:
        """
        Spectral Clustering
        
        Args:
            G: NetworkX 그래프
            n_clusters: 클러스터 수
        
        Returns:
            ClusterResult
        """
        # 인접 행렬 추출
        node_ids = list(G.nodes())
        adj_matrix = nx.to_numpy_array(G)
        
        # Spectral Clustering
        spectral = SpectralClustering(
            n_clusters=n_clusters,
            affinity="precomputed",
            random_state=self.random_state,
            assign_labels="kmeans"
        )
        
        # 인접 행렬을 유사도로 사용 (자기 자신과의 연결 추가)
        np.fill_diagonal(adj_matrix, 1)
        labels = spectral.fit_predict(adj_matrix)
        
        # Silhouette score 계산
        silhouette = None
        if n_clusters > 1 and n_clusters < len(node_ids):
            try:
                silhouette = silhouette_score(adj_matrix, labels, metric="precomputed")
            except Exception:
                pass
        
        # 클러스터 크기
        cluster_sizes = {}
        for label in set(labels):
            cluster_sizes[label] = np.sum(labels == label)
        
        logger.info(f"Spectral clustering: {n_clusters} clusters")
        
        return ClusterResult(
            method=ClusteringMethod.SPECTRAL,
            num_clusters=n_clusters,
            labels=labels,
            node_ids=node_ids,
            silhouette=silhouette,
            cluster_sizes=cluster_sizes
        )
    
    def _kmeans_clustering(
        self,
        G: nx.Graph,
        n_clusters: int = 10,
        use_embeddings: bool = True,
        **kwargs
    ) -> ClusterResult:
        """
        K-Means 클러스터링 (노드 임베딩 기반)
        
        Args:
            G: NetworkX 그래프
            n_clusters: 클러스터 수
            use_embeddings: 노드 임베딩 사용 여부
        
        Returns:
            ClusterResult
        """
        node_ids = list(G.nodes())
        
        # 노드 특성 추출
        if use_embeddings and "embedding" in G.nodes[node_ids[0]]:
            features = np.array([G.nodes[n].get("embedding") for n in node_ids])
        else:
            # 인접 행렬 기반 특성
            features = nx.to_numpy_array(G)
        
        # K-Means
        kmeans = KMeans(
            n_clusters=n_clusters,
            random_state=self.random_state,
            n_init=10
        )
        labels = kmeans.fit_predict(features)
        
        # Silhouette score
        silhouette = None
        if n_clusters > 1:
            try:
                silhouette = silhouette_score(features, labels)
            except Exception:
                pass
        
        # 클러스터 크기
        cluster_sizes = {}
        for label in set(labels):
            cluster_sizes[label] = np.sum(labels == label)
        
        logger.info(f"K-Means clustering: {n_clusters} clusters")
        
        return ClusterResult(
            method=ClusteringMethod.KMEANS,
            num_clusters=n_clusters,
            labels=labels,
            node_ids=node_ids,
            silhouette=silhouette,
            cluster_sizes=cluster_sizes
        )
    
    def _dbscan_clustering(
        self,
        G: nx.Graph,
        eps: float = 0.5,
        min_samples: int = 5,
        **kwargs
    ) -> ClusterResult:
        """
        DBSCAN 클러스터링
        
        Args:
            G: NetworkX 그래프
            eps: 이웃 반경
            min_samples: 최소 샘플 수
        
        Returns:
            ClusterResult
        """
        node_ids = list(G.nodes())
        
        # 그래프 거리 행렬 계산
        try:
            dist_matrix = np.zeros((len(node_ids), len(node_ids)))
            path_lengths = dict(nx.all_pairs_shortest_path_length(G))
            
            for i, n1 in enumerate(node_ids):
                for j, n2 in enumerate(node_ids):
                    if n2 in path_lengths.get(n1, {}):
                        dist_matrix[i, j] = path_lengths[n1][n2]
                    else:
                        dist_matrix[i, j] = float('inf')
            
            # 무한대를 큰 값으로 대체
            max_dist = np.max(dist_matrix[dist_matrix != float('inf')])
            dist_matrix[dist_matrix == float('inf')] = max_dist + 1
            
        except Exception:
            # fallback: 인접 행렬 사용
            adj_matrix = nx.to_numpy_array(G)
            dist_matrix = 1 - adj_matrix  # 유사도를 거리로 변환
        
        # DBSCAN
        dbscan = DBSCAN(
            eps=eps,
            min_samples=min_samples,
            metric="precomputed"
        )
        labels = dbscan.fit_predict(dist_matrix)
        
        # 노이즈 포인트(-1)를 별도 클러스터로
        num_clusters = len(set(labels)) - (1 if -1 in labels else 0)
        
        # 클러스터 크기
        cluster_sizes = {}
        for label in set(labels):
            cluster_sizes[label] = np.sum(labels == label)
        
        logger.info(f"DBSCAN clustering: {num_clusters} clusters (+{cluster_sizes.get(-1, 0)} noise)")
        
        return ClusterResult(
            method=ClusteringMethod.DBSCAN,
            num_clusters=num_clusters,
            labels=labels,
            node_ids=node_ids,
            cluster_sizes=cluster_sizes
        )
    
    def topic_clustering(
        self,
        texts: list[str],
        node_ids: list[str],
        n_topics: Optional[int] = None,
        min_topic_size: int = 10,
        language: str = "korean"
    ) -> ClusterResult:
        """
        BERTopic 기반 토픽 클러스터링
        
        Args:
            texts: 텍스트 리스트
            node_ids: 노드 ID 리스트
            n_topics: 토픽 수 (None이면 자동 결정)
            min_topic_size: 최소 토픽 크기
            language: 언어
        
        Returns:
            ClusterResult
        """
        if not BERTOPIC_AVAILABLE:
            raise ImportError("bertopic is required for topic clustering")
        
        # BERTopic 모델 생성
        topic_model = BERTopic(
            language=language,
            min_topic_size=min_topic_size,
            nr_topics=n_topics,
            verbose=False
        )
        
        # 토픽 추출
        topics, probs = topic_model.fit_transform(texts)
        
        labels = np.array(topics)
        num_clusters = len(set(topics)) - (1 if -1 in topics else 0)
        
        # 토픽 메타데이터
        topic_info = topic_model.get_topic_info()
        cluster_metadata = {
            row["Topic"]: {
                "name": row.get("Name", f"Topic_{row['Topic']}"),
                "count": row["Count"],
                "representative_docs": topic_model.get_representative_docs(row["Topic"])[:3]
                if row["Topic"] != -1 else []
            }
            for _, row in topic_info.iterrows()
        }
        
        # 클러스터 크기
        cluster_sizes = dict(topic_info[["Topic", "Count"]].values)
        
        logger.info(f"BERTopic clustering: {num_clusters} topics")
        
        return ClusterResult(
            method=ClusteringMethod.BERTOPIC,
            num_clusters=num_clusters,
            labels=labels,
            node_ids=node_ids,
            cluster_sizes=cluster_sizes,
            cluster_metadata=cluster_metadata
        )
    
    def hierarchical_clustering(
        self,
        G: nx.Graph,
        levels: int = 3,
        base_resolution: float = 1.0
    ) -> list[ClusterResult]:
        """
        계층적 클러스터링
        
        다양한 해상도에서 클러스터링을 수행하여 계층 구조를 추출합니다.
        
        Args:
            G: NetworkX 그래프
            levels: 계층 수
            base_resolution: 기본 해상도
        
        Returns:
            각 레벨의 ClusterResult 리스트
        """
        results = []
        
        resolutions = [base_resolution * (0.5 ** i) for i in range(levels)]
        
        for i, resolution in enumerate(resolutions):
            if LEIDEN_AVAILABLE:
                result = self._leiden_clustering(G, resolution)
            elif LOUVAIN_AVAILABLE:
                result = self._louvain_clustering(G, resolution)
            else:
                logger.warning("Neither Leiden nor Louvain available. Skipping hierarchical clustering.")
                break
            
            result.cluster_metadata["level"] = i
            result.cluster_metadata["resolution"] = resolution
            results.append(result)
            
            logger.info(f"Level {i}: resolution={resolution:.4f}, clusters={result.num_clusters}")
        
        return results
    
    def ensemble_clustering(
        self,
        G: nx.Graph,
        methods: list[ClusteringMethod] = None,
        n_clusters: int = 10
    ) -> ClusterResult:
        """
        앙상블 클러스터링
        
        여러 클러스터링 방법의 결과를 결합합니다.
        
        Args:
            G: NetworkX 그래프
            methods: 사용할 클러스터링 방법들
            n_clusters: 최종 클러스터 수
        
        Returns:
            앙상블 ClusterResult
        """
        if methods is None:
            methods = []
            if LOUVAIN_AVAILABLE:
                methods.append(ClusteringMethod.LOUVAIN)
            if LEIDEN_AVAILABLE:
                methods.append(ClusteringMethod.LEIDEN)
            methods.append(ClusteringMethod.SPECTRAL)
        
        if len(methods) == 0:
            raise ValueError("No clustering methods available")
        
        # 각 방법으로 클러스터링
        results = []
        for method in methods:
            try:
                result = self.cluster(G, method, n_clusters=n_clusters)
                results.append(result)
            except Exception as e:
                logger.warning(f"Failed to run {method}: {e}")
        
        if len(results) == 0:
            raise RuntimeError("All clustering methods failed")
        
        # Co-association 행렬 구축
        node_ids = results[0].node_ids
        n_nodes = len(node_ids)
        co_assoc = np.zeros((n_nodes, n_nodes))
        
        for result in results:
            for i in range(n_nodes):
                for j in range(i + 1, n_nodes):
                    if result.labels[i] == result.labels[j]:
                        co_assoc[i, j] += 1
                        co_assoc[j, i] += 1
        
        co_assoc /= len(results)
        np.fill_diagonal(co_assoc, 1)
        
        # 최종 클러스터링 (Spectral)
        spectral = SpectralClustering(
            n_clusters=n_clusters,
            affinity="precomputed",
            random_state=self.random_state
        )
        labels = spectral.fit_predict(co_assoc)
        
        # 클러스터 크기
        cluster_sizes = {}
        for label in set(labels):
            cluster_sizes[int(label)] = int(np.sum(labels == label))
        
        logger.info(f"Ensemble clustering: {n_clusters} clusters from {len(results)} methods")
        
        return ClusterResult(
            method=ClusteringMethod.SPECTRAL,  # Final method
            num_clusters=n_clusters,
            labels=labels,
            node_ids=node_ids,
            cluster_sizes=cluster_sizes,
            cluster_metadata={"ensemble_methods": [m.value for m in methods]}
        )


# 모듈 테스트용
if __name__ == "__main__":
    # 테스트 그래프 생성
    G = nx.karate_club_graph()
    
    clusterer = GraphClusterer()
    
    # Louvain 클러스터링
    if LOUVAIN_AVAILABLE:
        result = clusterer.cluster(G, ClusteringMethod.LOUVAIN)
        print(f"\nLouvain: {result.num_clusters} clusters")
        print(f"Modularity: {result.modularity:.4f}")
    
    # Spectral 클러스터링
    result = clusterer.cluster(G, ClusteringMethod.SPECTRAL, n_clusters=4)
    print(f"\nSpectral: {result.num_clusters} clusters")

