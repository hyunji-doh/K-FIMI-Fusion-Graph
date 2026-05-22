"""
GNN 분류기 모듈

GraphSAGE, HGT, HAN 등 다양한 GNN 아키텍처를 제공합니다.
"""

from typing import Optional, Union
from enum import Enum

import torch
import torch.nn as nn
import torch.nn.functional as F
from torch_geometric.nn import (
    SAGEConv, GATConv, GCNConv, Linear,
    HeteroConv, HANConv, HGTConv,
    global_mean_pool, global_max_pool, global_add_pool
)
from torch_geometric.data import HeteroData
from loguru import logger


class GNNType(str, Enum):
    """GNN 아키텍처 타입"""
    GRAPHSAGE = "graphsage"
    GAT = "gat"
    GCN = "gcn"
    HGT = "hgt"
    HAN = "han"


class GraphSAGEClassifier(nn.Module):
    """
    GraphSAGE 기반 분류기
    
    Homogeneous 그래프에서 노드/그래프 분류를 수행합니다.
    """
    
    def __init__(
        self,
        in_channels: int,
        hidden_channels: int = 256,
        out_channels: int = 2,
        num_layers: int = 3,
        dropout: float = 0.5,
        aggregator: str = "mean"
    ):
        """
        GraphSAGE 분류기 초기화
        
        Args:
            in_channels: 입력 특성 차원
            hidden_channels: 히든 레이어 차원
            out_channels: 출력 클래스 수
            num_layers: GNN 레이어 수
            dropout: 드롭아웃 비율
            aggregator: 집계 함수 (mean, max, lstm)
        """
        super().__init__()
        
        self.num_layers = num_layers
        self.dropout = dropout
        
        # GNN 레이어
        self.convs = nn.ModuleList()
        self.convs.append(SAGEConv(in_channels, hidden_channels, aggr=aggregator))
        
        for _ in range(num_layers - 2):
            self.convs.append(SAGEConv(hidden_channels, hidden_channels, aggr=aggregator))
        
        self.convs.append(SAGEConv(hidden_channels, hidden_channels, aggr=aggregator))
        
        # Batch normalization
        self.bns = nn.ModuleList([
            nn.BatchNorm1d(hidden_channels) for _ in range(num_layers)
        ])
        
        # 분류 헤드
        self.classifier = nn.Sequential(
            nn.Linear(hidden_channels, hidden_channels // 2),
            nn.ReLU(),
            nn.Dropout(dropout),
            nn.Linear(hidden_channels // 2, out_channels)
        )
        
        logger.info(f"GraphSAGE classifier: {in_channels} -> {hidden_channels} -> {out_channels}")
    
    def forward(
        self,
        x: torch.Tensor,
        edge_index: torch.Tensor,
        batch: Optional[torch.Tensor] = None
    ) -> torch.Tensor:
        """
        순전파
        
        Args:
            x: 노드 특성 [N, in_channels]
            edge_index: 엣지 인덱스 [2, E]
            batch: 배치 인덱스 (그래프 분류용)
        
        Returns:
            분류 로짓 [N, out_channels] 또는 [B, out_channels]
        """
        # GNN 레이어
        for i, conv in enumerate(self.convs):
            x = conv(x, edge_index)
            x = self.bns[i](x)
            x = F.relu(x)
            x = F.dropout(x, p=self.dropout, training=self.training)
        
        # 그래프 레벨 분류
        if batch is not None:
            x = global_mean_pool(x, batch)
        
        # 분류
        return self.classifier(x)
    
    def get_embeddings(
        self,
        x: torch.Tensor,
        edge_index: torch.Tensor
    ) -> torch.Tensor:
        """노드 임베딩 추출"""
        for i, conv in enumerate(self.convs[:-1]):
            x = conv(x, edge_index)
            x = self.bns[i](x)
            x = F.relu(x)
        
        x = self.convs[-1](x, edge_index)
        return x


class HGTClassifier(nn.Module):
    """
    Heterogeneous Graph Transformer (HGT) 기반 분류기
    
    Heterogeneous 그래프에서 노드 분류를 수행합니다.
    """
    
    def __init__(
        self,
        node_types: list[str],
        edge_types: list[tuple],
        in_channels: Union[int, dict],
        hidden_channels: int = 256,
        out_channels: int = 2,
        num_heads: int = 4,
        num_layers: int = 2,
        dropout: float = 0.5,
        target_node_type: str = "user"
    ):
        """
        HGT 분류기 초기화
        
        Args:
            node_types: 노드 타입 리스트
            edge_types: 엣지 타입 리스트 [(src, rel, dst), ...]
            in_channels: 입력 차원 (int 또는 노드별 dict)
            hidden_channels: 히든 차원
            out_channels: 출력 클래스 수
            num_heads: 어텐션 헤드 수
            num_layers: HGT 레이어 수
            dropout: 드롭아웃 비율
            target_node_type: 분류 대상 노드 타입
        """
        super().__init__()
        
        self.node_types = node_types
        self.edge_types = edge_types
        self.target_node_type = target_node_type
        self.dropout = dropout
        
        # 노드별 입력 차원 설정
        if isinstance(in_channels, int):
            in_channels_dict = {nt: in_channels for nt in node_types}
        else:
            in_channels_dict = in_channels
        
        # 입력 프로젝션
        self.lin_dict = nn.ModuleDict()
        for node_type in node_types:
            self.lin_dict[node_type] = Linear(
                in_channels_dict.get(node_type, hidden_channels),
                hidden_channels
            )
        
        # HGT 레이어
        self.convs = nn.ModuleList()
        for _ in range(num_layers):
            conv = HGTConv(
                in_channels=hidden_channels,
                out_channels=hidden_channels,
                metadata=(node_types, edge_types),
                heads=num_heads
            )
            self.convs.append(conv)
        
        # 분류 헤드
        self.classifier = nn.Sequential(
            nn.Linear(hidden_channels, hidden_channels // 2),
            nn.ReLU(),
            nn.Dropout(dropout),
            nn.Linear(hidden_channels // 2, out_channels)
        )
        
        logger.info(f"HGT classifier: {len(node_types)} node types, {len(edge_types)} edge types")
    
    def forward(self, data: HeteroData) -> torch.Tensor:
        """
        순전파
        
        Args:
            data: HeteroData 객체
        
        Returns:
            타겟 노드의 분류 로짓
        """
        x_dict = {}
        
        # 입력 프로젝션
        for node_type in self.node_types:
            if node_type in data.node_types and hasattr(data[node_type], 'x'):
                x_dict[node_type] = self.lin_dict[node_type](data[node_type].x)
        
        # HGT 레이어
        for conv in self.convs:
            x_dict = conv(x_dict, data.edge_index_dict)
            x_dict = {key: F.relu(x) for key, x in x_dict.items()}
            x_dict = {
                key: F.dropout(x, p=self.dropout, training=self.training)
                for key, x in x_dict.items()
            }
        
        # 타겟 노드 분류
        out = self.classifier(x_dict[self.target_node_type])
        return out
    
    def get_embeddings(self, data: HeteroData) -> dict:
        """모든 노드 타입의 임베딩 추출"""
        x_dict = {}
        
        for node_type in self.node_types:
            if node_type in data.node_types and hasattr(data[node_type], 'x'):
                x_dict[node_type] = self.lin_dict[node_type](data[node_type].x)
        
        for conv in self.convs:
            x_dict = conv(x_dict, data.edge_index_dict)
            x_dict = {key: F.relu(x) for key, x in x_dict.items()}
        
        return x_dict


class HANClassifier(nn.Module):
    """
    Heterogeneous Attention Network (HAN) 기반 분류기
    
    메타패스 기반 어텐션을 사용합니다.
    """
    
    def __init__(
        self,
        in_channels: Union[int, dict],
        hidden_channels: int = 256,
        out_channels: int = 2,
        metadata: tuple = None,
        num_heads: int = 8,
        dropout: float = 0.5,
        target_node_type: str = "user"
    ):
        """
        HAN 분류기 초기화
        
        Args:
            in_channels: 입력 차원
            hidden_channels: 히든 차원
            out_channels: 출력 클래스 수
            metadata: (node_types, edge_types) 튜플
            num_heads: 어텐션 헤드 수
            dropout: 드롭아웃 비율
            target_node_type: 분류 대상 노드 타입
        """
        super().__init__()
        
        self.target_node_type = target_node_type
        self.dropout = dropout
        
        if metadata is None:
            raise ValueError("metadata (node_types, edge_types) is required")
        
        node_types, edge_types = metadata
        
        # 노드별 입력 차원 설정
        if isinstance(in_channels, int):
            in_channels = {nt: in_channels for nt in node_types}
        
        # HAN 레이어
        self.han_conv = HANConv(
            in_channels=in_channels,
            out_channels=hidden_channels,
            metadata=metadata,
            heads=num_heads,
            dropout=dropout
        )
        
        # 분류 헤드
        self.classifier = nn.Sequential(
            nn.Linear(hidden_channels, hidden_channels // 2),
            nn.ReLU(),
            nn.Dropout(dropout),
            nn.Linear(hidden_channels // 2, out_channels)
        )
        
        logger.info(f"HAN classifier initialized")
    
    def forward(self, data: HeteroData) -> torch.Tensor:
        """
        순전파
        
        Args:
            data: HeteroData 객체
        
        Returns:
            타겟 노드의 분류 로짓
        """
        x_dict = {
            node_type: data[node_type].x
            for node_type in data.node_types
            if hasattr(data[node_type], 'x')
        }
        
        # HAN 컨볼루션
        x_dict = self.han_conv(x_dict, data.edge_index_dict)
        
        # 타겟 노드 분류
        out = self.classifier(x_dict[self.target_node_type])
        return out


class HeteroGNNClassifier(nn.Module):
    """
    범용 Heterogeneous GNN 분류기
    
    HeteroConv를 사용하여 다양한 동종 GNN 레이어를 조합합니다.
    """
    
    def __init__(
        self,
        node_types: list[str],
        edge_types: list[tuple],
        in_channels: Union[int, dict],
        hidden_channels: int = 256,
        out_channels: int = 2,
        num_layers: int = 2,
        conv_type: str = "sage",
        dropout: float = 0.5,
        target_node_type: str = "user"
    ):
        """
        HeteroGNN 분류기 초기화
        
        Args:
            node_types: 노드 타입 리스트
            edge_types: 엣지 타입 리스트
            in_channels: 입력 차원
            hidden_channels: 히든 차원
            out_channels: 출력 클래스 수
            num_layers: GNN 레이어 수
            conv_type: 기본 GNN 타입 (sage, gat, gcn)
            dropout: 드롭아웃 비율
            target_node_type: 분류 대상 노드 타입
        """
        super().__init__()
        
        self.node_types = node_types
        self.edge_types = edge_types
        self.target_node_type = target_node_type
        self.dropout = dropout
        
        # 노드별 입력 차원 설정
        if isinstance(in_channels, int):
            in_channels_dict = {nt: in_channels for nt in node_types}
        else:
            in_channels_dict = in_channels
        
        # 입력 프로젝션
        self.lin_dict = nn.ModuleDict()
        for node_type in node_types:
            self.lin_dict[node_type] = Linear(
                in_channels_dict.get(node_type, hidden_channels),
                hidden_channels
            )
        
        # Hetero 컨볼루션 레이어
        self.convs = nn.ModuleList()
        
        for _ in range(num_layers):
            conv_dict = {}
            
            for edge_type in edge_types:
                if conv_type == "sage":
                    conv_dict[edge_type] = SAGEConv(hidden_channels, hidden_channels)
                elif conv_type == "gat":
                    conv_dict[edge_type] = GATConv(
                        hidden_channels, hidden_channels // 4, heads=4
                    )
                elif conv_type == "gcn":
                    conv_dict[edge_type] = GCNConv(hidden_channels, hidden_channels)
                else:
                    raise ValueError(f"Unknown conv_type: {conv_type}")
            
            self.convs.append(HeteroConv(conv_dict, aggr="sum"))
        
        # 분류 헤드
        self.classifier = nn.Sequential(
            nn.Linear(hidden_channels, hidden_channels // 2),
            nn.ReLU(),
            nn.Dropout(dropout),
            nn.Linear(hidden_channels // 2, out_channels)
        )
        
        logger.info(f"HeteroGNN ({conv_type}) classifier initialized")
    
    def forward(self, data: HeteroData) -> torch.Tensor:
        """순전파"""
        x_dict = {}
        
        # 입력 프로젝션
        for node_type in self.node_types:
            if node_type in data.node_types and hasattr(data[node_type], 'x'):
                x_dict[node_type] = self.lin_dict[node_type](data[node_type].x)
        
        # Hetero 컨볼루션
        for conv in self.convs:
            x_dict = conv(x_dict, data.edge_index_dict)
            x_dict = {key: F.relu(x) for key, x in x_dict.items()}
            x_dict = {
                key: F.dropout(x, p=self.dropout, training=self.training)
                for key, x in x_dict.items()
            }
        
        # 타겟 노드 분류
        out = self.classifier(x_dict[self.target_node_type])
        return out


class GNNClassifier:
    """
    GNN 분류기 팩토리
    
    다양한 GNN 아키텍처를 통합 인터페이스로 제공합니다.
    """
    
    @staticmethod
    def create(
        gnn_type: GNNType,
        **kwargs
    ) -> nn.Module:
        """
        GNN 분류기 생성
        
        Args:
            gnn_type: GNN 아키텍처 타입
            **kwargs: 아키텍처별 파라미터
        
        Returns:
            GNN 모듈
        """
        if gnn_type == GNNType.GRAPHSAGE:
            return GraphSAGEClassifier(**kwargs)
        elif gnn_type == GNNType.HGT:
            return HGTClassifier(**kwargs)
        elif gnn_type == GNNType.HAN:
            return HANClassifier(**kwargs)
        elif gnn_type in [GNNType.GAT, GNNType.GCN]:
            kwargs["conv_type"] = gnn_type.value
            return HeteroGNNClassifier(**kwargs)
        else:
            raise ValueError(f"Unknown GNN type: {gnn_type}")
    
    @staticmethod
    def available_types() -> list[str]:
        """사용 가능한 GNN 타입 반환"""
        return [t.value for t in GNNType]


# 모듈 테스트용
if __name__ == "__main__":
    # GraphSAGE 테스트
    print("Testing GraphSAGE...")
    model = GraphSAGEClassifier(
        in_channels=768,
        hidden_channels=256,
        out_channels=2,
        num_layers=3
    )
    
    x = torch.randn(100, 768)
    edge_index = torch.randint(0, 100, (2, 500))
    
    output = model(x, edge_index)
    print(f"Output shape: {output.shape}")
    
    # HGT 테스트
    print("\nTesting HGT...")
    node_types = ["user", "content"]
    edge_types = [
        ("user", "posts", "content"),
        ("content", "rev_posts", "user")
    ]
    
    hgt_model = HGTClassifier(
        node_types=node_types,
        edge_types=edge_types,
        in_channels=768,
        hidden_channels=256,
        out_channels=2,
        target_node_type="user"
    )
    
    print("HGT model created successfully")

