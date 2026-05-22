# Graph Module
"""
그래프 구축 모듈: Heterogeneous Fusion Graph를 구축하고 클러스터링합니다.
"""

from .hetero_graph_schema import HeteroGraphSchema, NodeType, EdgeType

# 선택적 import (torch 의존성)
try:
    from .fusion_graph_builder import FusionGraphBuilder
except ImportError:
    FusionGraphBuilder = None

try:
    from .clustering import GraphClusterer
except ImportError:
    GraphClusterer = None

__all__ = [
    "FusionGraphBuilder",
    "HeteroGraphSchema",
    "NodeType",
    "EdgeType",
    "GraphClusterer",
]

