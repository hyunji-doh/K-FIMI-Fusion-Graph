"""
Heterogeneous Graph 스키마 정의

Fusion Graph의 노드 타입, 엣지 타입, 속성을 정의합니다.
"""

from enum import Enum
from dataclasses import dataclass, field
from typing import Optional, Any


class NodeType(str, Enum):
    """그래프 노드 타입 정의"""
    
    # 사용자/계정 관련
    USER = "user"                      # 소셜 미디어 사용자
    
    # 콘텐츠 관련
    CONTENT = "content"                # 게시물/트윗/영상/메시지
    
    # 메타데이터 관련
    URL = "url"                        # 공유된 URL/링크
    DOMAIN = "domain"                  # URL 도메인
    HASHTAG = "hashtag"                # 해시태그
    MEDIA = "media"                    # 이미지/비디오 미디어
    
    # 시간 관련
    TIME_BUCKET = "time_bucket"        # 시간대 노드 (특정 시점/이벤트)
    
    # 엔티티 관련
    NARRATIVE = "narrative"            # 내러티브/주제
    ENTITY = "entity"                  # 명명된 엔티티 (인물, 조직 등)
    
    # 캠페인 관련
    CAMPAIGN = "campaign"              # 탐지된 캠페인
    CLUSTER = "cluster"                # 클러스터


class EdgeType(str, Enum):
    """그래프 엣지 타입 정의"""
    
    # 사용자-콘텐츠 관계
    POSTS = "posts"                    # 사용자가 콘텐츠를 게시
    RETWEETS = "retweets"              # 리트윗/공유
    REPLIES = "replies"                # 답글
    QUOTES = "quotes"                  # 인용
    LIKES = "likes"                    # 좋아요
    COMMENTS = "comments"              # 댓글
    
    # 사용자-사용자 관계
    FOLLOWS = "follows"                # 팔로우
    MENTIONS = "mentions"              # 멘션
    
    # 콘텐츠-메타데이터 관계
    CONTAINS_URL = "contains_url"      # URL 포함
    CONTAINS_HASHTAG = "contains_hashtag"  # 해시태그 포함
    CONTAINS_MEDIA = "contains_media"  # 미디어 포함
    
    # URL 관계
    URL_BELONGS_TO = "url_belongs_to"  # URL이 도메인에 속함
    
    # 콘텐츠 유사도 관계
    SIMILAR_TEXT = "similar_text"      # 텍스트 유사도
    SIMILAR_MEDIA = "similar_media"    # 미디어 유사도
    CO_SHARED = "co_shared"            # 동시 공유
    
    # 시간적 관계
    TEMPORALLY_CLOSE = "temporally_close"  # 시간적으로 가까움
    FORWARDED_FROM = "forwarded_from"  # 포워딩 출처
    ACTIVE_IN_TIME_BUCKET = "active_in_time_bucket"  # 특정 시간대에 활동
    
    # 캠페인 관계
    BELONGS_TO_CAMPAIGN = "belongs_to_campaign"  # 캠페인에 속함
    BELONGS_TO_CLUSTER = "belongs_to_cluster"    # 클러스터에 속함
    
    # 내러티브 관계
    EXPRESSES_NARRATIVE = "expresses_narrative"  # 내러티브 표현
    MENTIONS_ENTITY = "mentions_entity"  # 엔티티 언급


@dataclass
class NodeSchema:
    """노드 스키마 정의"""
    node_type: NodeType
    required_attrs: list[str] = field(default_factory=list)
    optional_attrs: list[str] = field(default_factory=list)
    embedding_dim: int = 768
    has_features: bool = True
    
    def validate(self, attrs: dict) -> bool:
        """속성 유효성 검사"""
        for attr in self.required_attrs:
            if attr not in attrs:
                return False
        return True


@dataclass
class EdgeSchema:
    """엣지 스키마 정의"""
    edge_type: EdgeType
    source_type: NodeType
    target_type: NodeType
    is_directed: bool = True
    has_weight: bool = False
    has_timestamp: bool = False
    attrs: list[str] = field(default_factory=list)


class HeteroGraphSchema:
    """
    Heterogeneous Graph 스키마
    
    노드 타입, 엣지 타입, 속성을 정의하고 관리합니다.
    """
    
    def __init__(self):
        self.node_schemas: dict[NodeType, NodeSchema] = {}
        self.edge_schemas: dict[EdgeType, EdgeSchema] = {}
        
        # 기본 스키마 초기화
        self._init_default_schemas()
    
    def _init_default_schemas(self):
        """기본 스키마 정의"""
        
        # === 노드 스키마 ===
        
        # User 노드
        self.add_node_schema(NodeSchema(
            node_type=NodeType.USER,
            required_attrs=["user_id", "platform"],
            optional_attrs=[
                "username", "display_name", "followers_count",
                "following_count", "created_at", "verified",
                "description", "location"
            ],
            embedding_dim=768
        ))
        
        # Content 노드
        self.add_node_schema(NodeSchema(
            node_type=NodeType.CONTENT,
            required_attrs=["content_id", "platform", "text"],
            optional_attrs=[
                "created_at", "author_id", "engagement_score",
                "view_count", "like_count", "share_count",
                "language"
            ],
            embedding_dim=768
        ))
        
        # URL 노드
        self.add_node_schema(NodeSchema(
            node_type=NodeType.URL,
            required_attrs=["url"],
            optional_attrs=["domain", "first_seen", "share_count", "title"],
            embedding_dim=256,
            has_features=False
        ))
        
        # Domain 노드
        self.add_node_schema(NodeSchema(
            node_type=NodeType.DOMAIN,
            required_attrs=["domain"],
            optional_attrs=[
                "credibility_score", "category", "country",
                "first_seen", "total_shares"
            ],
            embedding_dim=128,
            has_features=False
        ))
        
        # Hashtag 노드
        self.add_node_schema(NodeSchema(
            node_type=NodeType.HASHTAG,
            required_attrs=["tag"],
            optional_attrs=["usage_count", "first_seen"],
            embedding_dim=128,
            has_features=False
        ))
        
        # Media 노드
        self.add_node_schema(NodeSchema(
            node_type=NodeType.MEDIA,
            required_attrs=["media_id", "media_type"],
            optional_attrs=["hash", "url", "similarity_cluster"],
            embedding_dim=512
        ))
        
        # Time Bucket 노드
        self.add_node_schema(NodeSchema(
            node_type=NodeType.TIME_BUCKET,
            required_attrs=["time_bucket_id", "start_time", "end_time"],
            optional_attrs=[
                "bucket_type",  # 'hour', 'day', 'event'
                "event_type",   # 'election', 'security_incident', etc.
                "activity_count",
                "unique_accounts",
                "intensity_score"  # 집중도 점수
                "intensity_score"  # 해당 시간대의 활동 집중도
            ],
            embedding_dim=64,
            has_features=False
        ))
        
        # Narrative 노드
        self.add_node_schema(NodeSchema(
            node_type=NodeType.NARRATIVE,
            required_attrs=["narrative_id", "description"],
            optional_attrs=["keywords", "first_seen", "prevalence"],
            embedding_dim=768
        ))
        
        # Campaign 노드
        self.add_node_schema(NodeSchema(
            node_type=NodeType.CAMPAIGN,
            required_attrs=["campaign_id"],
            optional_attrs=[
                "name", "detected_at", "confidence_score",
                "size", "start_date", "end_date"
            ],
            embedding_dim=256,
            has_features=False
        ))
        
        # === 엣지 스키마 ===
        
        # 사용자-콘텐츠 관계
        self.add_edge_schema(EdgeSchema(
            edge_type=EdgeType.POSTS,
            source_type=NodeType.USER,
            target_type=NodeType.CONTENT,
            is_directed=True,
            has_timestamp=True
        ))
        
        self.add_edge_schema(EdgeSchema(
            edge_type=EdgeType.RETWEETS,
            source_type=NodeType.USER,
            target_type=NodeType.CONTENT,
            is_directed=True,
            has_timestamp=True
        ))
        
        self.add_edge_schema(EdgeSchema(
            edge_type=EdgeType.REPLIES,
            source_type=NodeType.CONTENT,
            target_type=NodeType.CONTENT,
            is_directed=True,
            has_timestamp=True
        ))
        
        self.add_edge_schema(EdgeSchema(
            edge_type=EdgeType.COMMENTS,
            source_type=NodeType.USER,
            target_type=NodeType.CONTENT,
            is_directed=True,
            has_timestamp=True,
            attrs=["comment_text"]
        ))
        
        # 사용자-사용자 관계
        self.add_edge_schema(EdgeSchema(
            edge_type=EdgeType.FOLLOWS,
            source_type=NodeType.USER,
            target_type=NodeType.USER,
            is_directed=True
        ))
        
        self.add_edge_schema(EdgeSchema(
            edge_type=EdgeType.MENTIONS,
            source_type=NodeType.CONTENT,
            target_type=NodeType.USER,
            is_directed=True
        ))
        
        # 콘텐츠-메타데이터 관계
        self.add_edge_schema(EdgeSchema(
            edge_type=EdgeType.CONTAINS_URL,
            source_type=NodeType.CONTENT,
            target_type=NodeType.URL,
            is_directed=True
        ))
        
        self.add_edge_schema(EdgeSchema(
            edge_type=EdgeType.CONTAINS_HASHTAG,
            source_type=NodeType.CONTENT,
            target_type=NodeType.HASHTAG,
            is_directed=True
        ))
        
        self.add_edge_schema(EdgeSchema(
            edge_type=EdgeType.CONTAINS_MEDIA,
            source_type=NodeType.CONTENT,
            target_type=NodeType.MEDIA,
            is_directed=True
        ))
        
        # URL-도메인 관계
        self.add_edge_schema(EdgeSchema(
            edge_type=EdgeType.URL_BELONGS_TO,
            source_type=NodeType.URL,
            target_type=NodeType.DOMAIN,
            is_directed=True
        ))
        
        # 유사도 관계
        self.add_edge_schema(EdgeSchema(
            edge_type=EdgeType.SIMILAR_TEXT,
            source_type=NodeType.CONTENT,
            target_type=NodeType.CONTENT,
            is_directed=False,
            has_weight=True,
            attrs=["similarity_score"]
        ))
        
        self.add_edge_schema(EdgeSchema(
            edge_type=EdgeType.SIMILAR_MEDIA,
            source_type=NodeType.MEDIA,
            target_type=NodeType.MEDIA,
            is_directed=False,
            has_weight=True,
            attrs=["similarity_score"]
        ))
        
        self.add_edge_schema(EdgeSchema(
            edge_type=EdgeType.CO_SHARED,
            source_type=NodeType.USER,
            target_type=NodeType.USER,
            is_directed=False,
            has_weight=True,
            attrs=["shared_urls_count"]
        ))
        
        # 시간적 관계
        self.add_edge_schema(EdgeSchema(
            edge_type=EdgeType.TEMPORALLY_CLOSE,
            source_type=NodeType.CONTENT,
            target_type=NodeType.CONTENT,
            is_directed=False,
            has_weight=True,
            attrs=["time_diff_seconds"]
        ))
        
        self.add_edge_schema(EdgeSchema(
            edge_type=EdgeType.FORWARDED_FROM,
            source_type=NodeType.CONTENT,
            target_type=NodeType.CONTENT,
            is_directed=True,
            has_timestamp=True
        ))
        
        # 시간대 관계
        self.add_edge_schema(EdgeSchema(
            edge_type=EdgeType.ACTIVE_IN_TIME_BUCKET,
            source_type=NodeType.USER,
            target_type=NodeType.TIME_BUCKET,
            is_directed=True,
            has_weight=True,
            attrs=["activity_count", "first_activity", "last_activity"]
        ))
        
        self.add_edge_schema(EdgeSchema(
            edge_type=EdgeType.ACTIVE_IN_TIME_BUCKET,
            source_type=NodeType.CONTENT,
            target_type=NodeType.TIME_BUCKET,
            is_directed=True,
            has_timestamp=True
        ))
        
        # 캠페인/클러스터 관계
        self.add_edge_schema(EdgeSchema(
            edge_type=EdgeType.BELONGS_TO_CAMPAIGN,
            source_type=NodeType.USER,
            target_type=NodeType.CAMPAIGN,
            is_directed=True,
            has_weight=True,
            attrs=["membership_score"]
        ))
        
        self.add_edge_schema(EdgeSchema(
            edge_type=EdgeType.BELONGS_TO_CLUSTER,
            source_type=NodeType.CONTENT,
            target_type=NodeType.CLUSTER,
            is_directed=True
        ))
        
        # 내러티브 관계
        self.add_edge_schema(EdgeSchema(
            edge_type=EdgeType.EXPRESSES_NARRATIVE,
            source_type=NodeType.CONTENT,
            target_type=NodeType.NARRATIVE,
            is_directed=True,
            has_weight=True,
            attrs=["relevance_score"]
        ))
    
    def add_node_schema(self, schema: NodeSchema):
        """노드 스키마 추가"""
        self.node_schemas[schema.node_type] = schema
    
    def add_edge_schema(self, schema: EdgeSchema):
        """엣지 스키마 추가"""
        self.edge_schemas[schema.edge_type] = schema
    
    def get_node_schema(self, node_type: NodeType) -> Optional[NodeSchema]:
        """노드 스키마 조회"""
        return self.node_schemas.get(node_type)
    
    def get_edge_schema(self, edge_type: EdgeType) -> Optional[EdgeSchema]:
        """엣지 스키마 조회"""
        return self.edge_schemas.get(edge_type)
    
    def get_edge_types_for_node(self, node_type: NodeType) -> list[EdgeType]:
        """특정 노드 타입과 연결된 엣지 타입 조회"""
        edge_types = []
        for edge_type, schema in self.edge_schemas.items():
            if schema.source_type == node_type or schema.target_type == node_type:
                edge_types.append(edge_type)
        return edge_types
    
    def get_metapaths(self) -> list[tuple]:
        """가능한 메타패스 생성"""
        metapaths = []
        
        # 간단한 2-hop 메타패스 생성
        for e1_type, e1_schema in self.edge_schemas.items():
            for e2_type, e2_schema in self.edge_schemas.items():
                if e1_schema.target_type == e2_schema.source_type:
                    metapath = (
                        e1_schema.source_type,
                        e1_type,
                        e1_schema.target_type,
                        e2_type,
                        e2_schema.target_type
                    )
                    metapaths.append(metapath)
        
        return metapaths
    
    def to_pyg_schema(self) -> dict:
        """PyTorch Geometric용 스키마 변환"""
        node_types = [nt.value for nt in self.node_schemas.keys()]
        
        edge_types = []
        for et, schema in self.edge_schemas.items():
            edge_types.append((
                schema.source_type.value,
                et.value,
                schema.target_type.value
            ))
        
        return {
            "node_types": node_types,
            "edge_types": edge_types
        }
    
    def __repr__(self) -> str:
        return (
            f"HeteroGraphSchema("
            f"nodes={len(self.node_schemas)}, "
            f"edges={len(self.edge_schemas)})"
        )


# 기본 스키마 인스턴스
DEFAULT_SCHEMA = HeteroGraphSchema()


# 모듈 테스트용
if __name__ == "__main__":
    schema = HeteroGraphSchema()
    print(schema)
    print(f"\nNode types: {list(schema.node_schemas.keys())}")
    print(f"\nEdge types: {list(schema.edge_schemas.keys())}")
    print(f"\nPyG Schema: {schema.to_pyg_schema()}")

