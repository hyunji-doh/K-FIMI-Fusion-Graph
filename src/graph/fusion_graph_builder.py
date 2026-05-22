"""
Fusion Graph 빌더

다양한 데이터 소스로부터 Heterogeneous Fusion Graph를 구축합니다.
"""

import json
from datetime import datetime
from dataclasses import dataclass
from typing import Optional, Union, Any
from pathlib import Path
from urllib.parse import urlparse
import hashlib

import networkx as nx
import pandas as pd
import numpy as np
from loguru import logger

# PyTorch & PyG (선택적 import)
try:
    import torch
    from torch_geometric.data import HeteroData
    TORCH_AVAILABLE = True
except ImportError:
    torch = None
    HeteroData = None
    TORCH_AVAILABLE = False
    logger.warning("PyTorch/PyG not available. Some features disabled.")

from .hetero_graph_schema import (
    HeteroGraphSchema, NodeType, EdgeType, DEFAULT_SCHEMA
)


@dataclass
class GraphNode:
    """그래프 노드 데이터"""
    node_id: str
    node_type: NodeType
    attrs: dict
    embedding: Optional[np.ndarray] = None


@dataclass
class GraphEdge:
    """그래프 엣지 데이터"""
    source_id: str
    target_id: str
    edge_type: EdgeType
    attrs: dict = None
    weight: float = 1.0
    timestamp: Optional[datetime] = None


class FusionGraphBuilder:
    """
    Fusion Graph 빌더
    
    다양한 플랫폼의 데이터를 통합하여 Heterogeneous Graph를 구축합니다.
    
    Attributes:
        schema: 그래프 스키마
        nodes: 노드 저장소
        edges: 엣지 저장소
    """
    
    def __init__(
        self,
        schema: Optional[HeteroGraphSchema] = None,
        output_dir: str = "data/graphs"
    ):
        """
        FusionGraphBuilder 초기화
        
        Args:
            schema: 그래프 스키마 (None이면 기본 스키마 사용)
            output_dir: 그래프 저장 경로
        """
        self.schema = schema or DEFAULT_SCHEMA
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        # 노드/엣지 저장소
        self.nodes: dict[str, GraphNode] = {}
        self.edges: list[GraphEdge] = []
        
        # 노드 타입별 인덱스
        self.node_type_index: dict[NodeType, list[str]] = {
            nt: [] for nt in NodeType
        }
        
        # ID 매핑 (플랫폼별 ID → 통합 ID)
        self.id_mapping: dict[str, str] = {}
        
        logger.info(f"FusionGraphBuilder initialized. Output: {self.output_dir}")
    
    def _generate_node_id(
        self,
        node_type: NodeType,
        platform: str,
        original_id: str
    ) -> str:
        """통합 노드 ID 생성"""
        raw_id = f"{node_type.value}:{platform}:{original_id}"
        return hashlib.md5(raw_id.encode()).hexdigest()[:16]
    
    def add_node(
        self,
        node_type: NodeType,
        attrs: dict,
        embedding: Optional[np.ndarray] = None
    ) -> str:
        """
        노드 추가
        
        Args:
            node_type: 노드 타입
            attrs: 노드 속성
            embedding: 노드 임베딩 벡터
        
        Returns:
            생성된 노드 ID
        """
        # 스키마 검증
        node_schema = self.schema.get_node_schema(node_type)
        if node_schema and not node_schema.validate(attrs):
            logger.warning(f"Node validation failed for type {node_type}")
        
        # 노드 ID 생성
        platform = attrs.get("platform", "unknown")
        original_id = str(attrs.get("user_id") or attrs.get("content_id") or attrs.get("url") or attrs.get("tag") or attrs.get("domain"))
        node_id = self._generate_node_id(node_type, platform, original_id)
        
        # 중복 체크
        if node_id in self.nodes:
            # 기존 노드 업데이트
            existing = self.nodes[node_id]
            existing.attrs.update(attrs)
            if embedding is not None:
                existing.embedding = embedding
            return node_id
        
        # 새 노드 추가
        node = GraphNode(
            node_id=node_id,
            node_type=node_type,
            attrs=attrs,
            embedding=embedding
        )
        
        self.nodes[node_id] = node
        self.node_type_index[node_type].append(node_id)
        
        # ID 매핑 저장
        mapping_key = f"{platform}:{original_id}"
        self.id_mapping[mapping_key] = node_id
        
        return node_id
    
    def add_edge(
        self,
        source_id: str,
        target_id: str,
        edge_type: EdgeType,
        attrs: Optional[dict] = None,
        weight: float = 1.0,
        timestamp: Optional[datetime] = None
    ) -> bool:
        """
        엣지 추가
        
        Args:
            source_id: 소스 노드 ID
            target_id: 타겟 노드 ID
            edge_type: 엣지 타입
            attrs: 엣지 속성
            weight: 엣지 가중치
            timestamp: 타임스탬프
        
        Returns:
            성공 여부
        """
        # 노드 존재 확인
        if source_id not in self.nodes or target_id not in self.nodes:
            logger.warning(f"Edge creation failed: nodes not found ({source_id} -> {target_id})")
            return False
        
        # 스키마 검증
        edge_schema = self.schema.get_edge_schema(edge_type)
        if edge_schema:
            source_node = self.nodes[source_id]
            target_node = self.nodes[target_id]
            
            if source_node.node_type != edge_schema.source_type:
                logger.warning(f"Source node type mismatch: {source_node.node_type} != {edge_schema.source_type}")
            if target_node.node_type != edge_schema.target_type:
                logger.warning(f"Target node type mismatch: {target_node.node_type} != {edge_schema.target_type}")
        
        edge = GraphEdge(
            source_id=source_id,
            target_id=target_id,
            edge_type=edge_type,
            attrs=attrs or {},
            weight=weight,
            timestamp=timestamp
        )
        
        self.edges.append(edge)
        return True
    
    def add_user(
        self,
        platform: str,
        user_id: str,
        username: Optional[str] = None,
        display_name: Optional[str] = None,
        followers_count: int = 0,
        following_count: int = 0,
        created_at: Optional[datetime] = None,
        verified: bool = False,
        description: Optional[str] = None,
        embedding: Optional[np.ndarray] = None,
        **kwargs
    ) -> str:
        """
        사용자 노드 추가
        
        Args:
            platform: 플랫폼 (twitter, youtube, telegram 등)
            user_id: 플랫폼 내 사용자 ID
            username: 사용자명
            display_name: 표시 이름
            followers_count: 팔로워 수
            following_count: 팔로잉 수
            created_at: 계정 생성일
            verified: 인증 여부
            description: 프로필 설명
            embedding: 사용자 임베딩
        
        Returns:
            생성된 노드 ID
        """
        attrs = {
            "user_id": user_id,
            "platform": platform,
            "username": username,
            "display_name": display_name,
            "followers_count": followers_count,
            "following_count": following_count,
            "created_at": created_at.isoformat() if created_at else None,
            "verified": verified,
            "description": description,
            **kwargs
        }
        
        return self.add_node(NodeType.USER, attrs, embedding)
    
    def add_content(
        self,
        platform: str,
        content_id: str,
        text: str,
        author_id: str,
        created_at: Optional[datetime] = None,
        engagement_score: float = 0.0,
        view_count: int = 0,
        like_count: int = 0,
        share_count: int = 0,
        language: Optional[str] = None,
        embedding: Optional[np.ndarray] = None,
        **kwargs
    ) -> str:
        """
        콘텐츠 노드 추가
        
        Args:
            platform: 플랫폼
            content_id: 콘텐츠 ID
            text: 텍스트 내용
            author_id: 작성자 노드 ID
            created_at: 생성일
            engagement_score: 참여도 점수
            view_count: 조회수
            like_count: 좋아요 수
            share_count: 공유 수
            language: 언어
            embedding: 텍스트 임베딩
        
        Returns:
            생성된 노드 ID
        """
        attrs = {
            "content_id": content_id,
            "platform": platform,
            "text": text,
            "author_id": author_id,
            "created_at": created_at.isoformat() if created_at else None,
            "engagement_score": engagement_score,
            "view_count": view_count,
            "like_count": like_count,
            "share_count": share_count,
            "language": language,
            **kwargs
        }
        
        content_node_id = self.add_node(NodeType.CONTENT, attrs, embedding)
        
        # 작성자-콘텐츠 엣지 추가
        if author_id in self.nodes:
            self.add_edge(
                author_id,
                content_node_id,
                EdgeType.POSTS,
                timestamp=created_at
            )
        
        return content_node_id
    
    def add_url(
        self,
        url: str,
        first_seen: Optional[datetime] = None,
        title: Optional[str] = None
    ) -> str:
        """
        URL 노드 추가
        
        Args:
            url: URL 문자열
            first_seen: 최초 발견 시간
            title: 페이지 제목
        
        Returns:
            생성된 노드 ID
        """
        parsed = urlparse(url)
        domain = parsed.netloc
        
        attrs = {
            "url": url,
            "domain": domain,
            "first_seen": first_seen.isoformat() if first_seen else None,
            "title": title,
            "platform": "web"
        }
        
        url_node_id = self.add_node(NodeType.URL, attrs)
        
        # 도메인 노드 추가 및 연결
        domain_node_id = self.add_domain(domain)
        self.add_edge(url_node_id, domain_node_id, EdgeType.URL_BELONGS_TO)
        
        return url_node_id
    
    def add_domain(
        self,
        domain: str,
        credibility_score: Optional[float] = None,
        category: Optional[str] = None,
        country: Optional[str] = None
    ) -> str:
        """
        도메인 노드 추가
        
        Args:
            domain: 도메인 문자열
            credibility_score: 신뢰도 점수
            category: 카테고리
            country: 국가
        
        Returns:
            생성된 노드 ID
        """
        attrs = {
            "domain": domain,
            "credibility_score": credibility_score,
            "category": category,
            "country": country,
            "platform": "web"
        }
        
        return self.add_node(NodeType.DOMAIN, attrs)
    
    def add_hashtag(
        self,
        tag: str,
        usage_count: int = 1,
        first_seen: Optional[datetime] = None
    ) -> str:
        """
        해시태그 노드 추가
        
        Args:
            tag: 해시태그 (# 제외)
            usage_count: 사용 횟수
            first_seen: 최초 발견 시간
        
        Returns:
            생성된 노드 ID
        """
        tag = tag.lstrip("#").lower()
        
        attrs = {
            "tag": tag,
            "usage_count": usage_count,
            "first_seen": first_seen.isoformat() if first_seen else None,
            "platform": "hashtag"
        }
        
        return self.add_node(NodeType.HASHTAG, attrs)
    
    def add_time_bucket(
        self,
        time_bucket_id: str,
        timestamp: datetime,
        bucket_type: str = "1h",
        event_type: Optional[str] = None,
        post_count: int = 0,
        account_count: int = 0,
        intensity_score: float = 0.0
    ) -> str:
        """
        시간대 노드 추가
        
        Args:
            time_bucket_id: 시간대 ID (예: "2025-12-01T08:00:00Z_bucket_1h")
            timestamp: 타임스탬프
            bucket_type: 버킷 타입 ("10m", "1h", "1d" 등)
            event_type: 이벤트 타입 ("election", "security_incident" 등)
            post_count: 해당 시간대 게시물 수
            account_count: 해당 시간대 활동 계정 수
            intensity_score: 활동 집중도 점수
        
        Returns:
            생성된 노드 ID
        """
        attrs = {
            "time_bucket_id": time_bucket_id,
            "timestamp": timestamp.isoformat(),
            "bucket_type": bucket_type,
            "event_type": event_type,
            "post_count": post_count,
            "account_count": account_count,
            "intensity_score": intensity_score
        }
        
        return self.add_node(NodeType.TIME_BUCKET, attrs)
    
    def link_user_to_time_bucket(
        self,
        user_id: str,
        time_bucket_id: str,
        activity_count: int = 1,
        first_activity: Optional[datetime] = None,
        last_activity: Optional[datetime] = None
    ):
        """
        사용자-시간대 엣지 추가
        
        Args:
            user_id: 사용자 노드 ID
            time_bucket_id: 시간대 노드 ID
            activity_count: 활동 횟수
            first_activity: 최초 활동 시간
            last_activity: 마지막 활동 시간
        """
        attrs = {
            "activity_count": activity_count,
            "first_activity": first_activity.isoformat() if first_activity else None,
            "last_activity": last_activity.isoformat() if last_activity else None
        }
        
        self.add_edge(
            user_id,
            time_bucket_id,
            EdgeType.ACTIVE_IN_TIME_BUCKET,
            attrs=attrs,
            weight=float(activity_count)
        )
    
    def link_content_to_time_bucket(
        self,
        content_id: str,
        time_bucket_id: str,
        timestamp: Optional[datetime] = None
    ):
        """
        콘텐츠-시간대 엣지 추가
        
        Args:
            content_id: 콘텐츠 노드 ID
            time_bucket_id: 시간대 노드 ID
            timestamp: 게시 시간
        """
        self.add_edge(
            content_id,
            time_bucket_id,
            EdgeType.ACTIVE_IN_TIME_BUCKET,
            timestamp=timestamp
        )
    
    def link_content_to_url(self, content_node_id: str, url_node_id: str):
        """콘텐츠-URL 엣지 추가"""
        self.add_edge(content_node_id, url_node_id, EdgeType.CONTAINS_URL)
    
    def link_content_to_hashtag(self, content_node_id: str, hashtag_node_id: str):
        """콘텐츠-해시태그 엣지 추가"""
        self.add_edge(content_node_id, hashtag_node_id, EdgeType.CONTAINS_HASHTAG)
    
    def add_similarity_edge(
        self,
        node_id_1: str,
        node_id_2: str,
        similarity_score: float,
        similarity_type: str = "text"
    ):
        """
        유사도 엣지 추가
        
        Args:
            node_id_1: 첫 번째 노드 ID
            node_id_2: 두 번째 노드 ID
            similarity_score: 유사도 점수 (0-1)
            similarity_type: 유사도 타입 (text, media)
        """
        edge_type = EdgeType.SIMILAR_TEXT if similarity_type == "text" else EdgeType.SIMILAR_MEDIA
        
        self.add_edge(
            node_id_1,
            node_id_2,
            edge_type,
            attrs={"similarity_score": similarity_score},
            weight=similarity_score
        )
    
    def add_follow_edge(
        self,
        follower_id: str,
        followee_id: str
    ):
        """팔로우 엣지 추가"""
        self.add_edge(follower_id, followee_id, EdgeType.FOLLOWS)
    
    def add_retweet_edge(
        self,
        user_id: str,
        content_id: str,
        timestamp: Optional[datetime] = None
    ):
        """리트윗 엣지 추가"""
        self.add_edge(
            user_id,
            content_id,
            EdgeType.RETWEETS,
            timestamp=timestamp
        )
    
    def to_networkx(self) -> nx.MultiDiGraph:
        """
        NetworkX MultiDiGraph로 변환
        
        Returns:
            NetworkX 그래프
        """
        G = nx.MultiDiGraph()
        
        # 노드 추가
        for node_id, node in self.nodes.items():
            G.add_node(
                node_id,
                node_type=node.node_type.value,
                **node.attrs
            )
        
        # 엣지 추가
        for edge in self.edges:
            G.add_edge(
                edge.source_id,
                edge.target_id,
                edge_type=edge.edge_type.value,
                weight=edge.weight,
                timestamp=edge.timestamp.isoformat() if edge.timestamp else None,
                **(edge.attrs or {})
            )
        
        logger.info(f"NetworkX graph created: {G.number_of_nodes()} nodes, {G.number_of_edges()} edges")
        return G
    
    def to_hetero_data(self):
        """
        PyTorch Geometric HeteroData로 변환
        
        Returns:
            HeteroData 객체 또는 None (PyG 미설치 시)
        """
        if not TORCH_AVAILABLE:
            logger.warning("PyTorch/PyG not available. Cannot create HeteroData.")
            return None
        
        data = HeteroData()
        
        # 노드 타입별 인덱스 매핑
        node_idx_map: dict[str, int] = {}
        
        for node_type in NodeType:
            node_ids = self.node_type_index[node_type]
            if not node_ids:
                continue
            
            # 노드 인덱스 매핑
            for idx, node_id in enumerate(node_ids):
                node_idx_map[node_id] = idx
            
            # 노드 특성 수집
            embeddings = []
            for node_id in node_ids:
                node = self.nodes[node_id]
                if node.embedding is not None:
                    embeddings.append(node.embedding)
                else:
                    # 기본 임베딩 (스키마에서 차원 가져옴)
                    schema = self.schema.get_node_schema(node_type)
                    dim = schema.embedding_dim if schema else 768
                    embeddings.append(np.zeros(dim))
            
            if embeddings:
                data[node_type.value].x = torch.tensor(
                    np.array(embeddings),
                    dtype=torch.float32
                )
                data[node_type.value].num_nodes = len(node_ids)
        
        # 엣지 타입별 엣지 인덱스 구축
        edge_dict: dict[tuple, list] = {}
        edge_attrs: dict[tuple, list] = {}
        
        for edge in self.edges:
            source_node = self.nodes.get(edge.source_id)
            target_node = self.nodes.get(edge.target_id)
            
            if not source_node or not target_node:
                continue
            
            edge_key = (
                source_node.node_type.value,
                edge.edge_type.value,
                target_node.node_type.value
            )
            
            if edge_key not in edge_dict:
                edge_dict[edge_key] = [[], []]
                edge_attrs[edge_key] = []
            
            # 노드 타입 내 인덱스 계산
            source_idx = self.node_type_index[source_node.node_type].index(edge.source_id)
            target_idx = self.node_type_index[target_node.node_type].index(edge.target_id)
            
            edge_dict[edge_key][0].append(source_idx)
            edge_dict[edge_key][1].append(target_idx)
            edge_attrs[edge_key].append(edge.weight)
        
        # HeteroData에 엣지 추가
        for edge_key, (sources, targets) in edge_dict.items():
            data[edge_key].edge_index = torch.tensor(
                [sources, targets],
                dtype=torch.long
            )
            data[edge_key].edge_attr = torch.tensor(
                edge_attrs[edge_key],
                dtype=torch.float32
            ).unsqueeze(1)
        
        logger.info(f"HeteroData created: {data}")
        return data
    
    def save(self, filename: str):
        """
        그래프를 파일로 저장
        
        Args:
            filename: 파일명 (확장자 제외)
        """
        # NetworkX 형식으로 저장
        G = self.to_networkx()
        
        # JSON 저장
        json_path = self.output_dir / f"{filename}.json"
        
        graph_data = {
            "nodes": [
                {
                    "id": node_id,
                    "type": node.node_type.value,
                    "attrs": node.attrs
                }
                for node_id, node in self.nodes.items()
            ],
            "edges": [
                {
                    "source": edge.source_id,
                    "target": edge.target_id,
                    "type": edge.edge_type.value,
                    "weight": edge.weight,
                    "attrs": edge.attrs
                }
                for edge in self.edges
            ],
            "metadata": {
                "num_nodes": len(self.nodes),
                "num_edges": len(self.edges),
                "created_at": datetime.now().isoformat()
            }
        }
        
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(graph_data, f, ensure_ascii=False, indent=2)
        
        logger.info(f"Graph saved to {json_path}")
        
        # GraphML 저장 (선택적 - None 값 문제 시 스킵)
        try:
            graphml_path = self.output_dir / f"{filename}.graphml"
            # None 값을 빈 문자열로 변환
            G_clean = G.copy()
            for node in G_clean.nodes():
                for key, val in list(G_clean.nodes[node].items()):
                    if val is None:
                        G_clean.nodes[node][key] = ""
            for u, v, key in G_clean.edges(keys=True):
                for attr, val in list(G_clean.edges[u, v, key].items()):
                    if val is None:
                        G_clean.edges[u, v, key][attr] = ""
            nx.write_graphml(G_clean, graphml_path)
            logger.info(f"GraphML saved to {graphml_path}")
        except Exception as e:
            logger.warning(f"GraphML save skipped: {e}")
    
    def load(self, filename: str):
        """
        파일에서 그래프 로드
        
        Args:
            filename: 파일명 (확장자 제외)
        """
        json_path = self.output_dir / f"{filename}.json"
        
        if not json_path.exists():
            raise FileNotFoundError(f"Graph file not found: {json_path}")
        
        with open(json_path, "r", encoding="utf-8") as f:
            graph_data = json.load(f)
        
        # 노드 복원
        self.nodes.clear()
        for node_data in graph_data["nodes"]:
            node_type = NodeType(node_data["type"])
            node = GraphNode(
                node_id=node_data["id"],
                node_type=node_type,
                attrs=node_data["attrs"]
            )
            self.nodes[node.node_id] = node
            self.node_type_index[node_type].append(node.node_id)
        
        # 엣지 복원
        self.edges.clear()
        for edge_data in graph_data["edges"]:
            edge = GraphEdge(
                source_id=edge_data["source"],
                target_id=edge_data["target"],
                edge_type=EdgeType(edge_data["type"]),
                weight=edge_data.get("weight", 1.0),
                attrs=edge_data.get("attrs", {})
            )
            self.edges.append(edge)
        
        logger.info(f"Graph loaded: {len(self.nodes)} nodes, {len(self.edges)} edges")
    
    def get_statistics(self) -> dict:
        """그래프 통계 반환"""
        node_counts = {
            nt.value: len(ids) for nt, ids in self.node_type_index.items() if ids
        }
        
        edge_counts = {}
        for edge in self.edges:
            et = edge.edge_type.value
            edge_counts[et] = edge_counts.get(et, 0) + 1
        
        return {
            "total_nodes": len(self.nodes),
            "total_edges": len(self.edges),
            "node_counts": node_counts,
            "edge_counts": edge_counts
        }
    
    def __repr__(self) -> str:
        stats = self.get_statistics()
        return f"FusionGraph(nodes={stats['total_nodes']}, edges={stats['total_edges']})"


# 모듈 테스트용
if __name__ == "__main__":
    builder = FusionGraphBuilder()
    
    # 테스트 데이터 추가
    user1 = builder.add_user(
        platform="twitter",
        user_id="123",
        username="test_user",
        followers_count=1000
    )
    
    content1 = builder.add_content(
        platform="twitter",
        content_id="tweet_456",
        text="테스트 트윗입니다 #테스트",
        author_id=user1,
        created_at=datetime.now()
    )
    
    hashtag1 = builder.add_hashtag("테스트")
    builder.link_content_to_hashtag(content1, hashtag1)
    
    print(builder)
    print(builder.get_statistics())

