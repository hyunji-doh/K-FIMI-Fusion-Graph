"""
GNN 모델 추론 파이프라인

학습된 GNN 모델을 사용하여 캠페인 연루 가능성 점수를 산출합니다.
"""

import torch
import torch.nn.functional as F
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, field
from pathlib import Path
import json

from loguru import logger

from .gnn_classifier import GNNType, GraphSAGEClassifier, HeteroGNNClassifier
from torch_geometric.data import HeteroData, Data


@dataclass
class NodePrediction:
    """노드별 예측 결과"""
    node_id: str
    node_type: str
    campaign_probability: float
    is_campaign: bool
    confidence: float
    features: Optional[Dict] = None
    
    def to_dict(self) -> dict:
        return {
            "node_id": self.node_id,
            "node_type": self.node_type,
            "campaign_probability": self.campaign_probability,
            "is_campaign": self.is_campaign,
            "confidence": self.confidence,
            "features": self.features
        }


@dataclass
class CampaignCandidate:
    """의심 캠페인 후보"""
    campaign_id: str
    node_ids: List[str]
    average_probability: float
    size: int
    confidence: float
    top_narratives: List[str] = field(default_factory=list)
    related_domains: List[str] = field(default_factory=list)
    
    def to_dict(self) -> dict:
        return {
            "campaign_id": self.campaign_id,
            "node_ids": self.node_ids,
            "average_probability": self.average_probability,
            "size": self.size,
            "confidence": self.confidence,
            "top_narratives": self.top_narratives,
            "related_domains": self.related_domains
        }


class GNNInferencePipeline:
    """
    GNN 추론 파이프라인
    
    학습된 모델을 사용하여 캠페인 탐지를 수행합니다.
    """
    
    def __init__(
        self,
        model_path: Optional[str] = None,
        model_type: GNNType = GNNType.GRAPHSAGE,
        device: str = "cpu"
    ):
        """
        GNNInferencePipeline 초기화
        
        Args:
            model_path: 모델 체크포인트 경로
            model_type: 모델 타입
            device: 디바이스 ('cpu' or 'cuda')
        """
        self.model_path = model_path
        self.model_type = model_type
        self.device = torch.device(device)
        self.model = None
        self.model_config = None
        
        if model_path and Path(model_path).exists():
            self.load_model(model_path)
        else:
            logger.warning(f"Model not loaded. Path: {model_path}")
    
    def load_model(self, model_path: str):
        """모델 로드"""
        checkpoint = torch.load(model_path, map_location=self.device)
        
        # 모델 설정 로드
        if "config" in checkpoint:
            self.model_config = checkpoint["config"]
            self.model_type = GNNType(self.model_config.get("model_type", "graphsage"))
        
        # 모델 아키텍처 재구성
        if self.model_type == GNNType.GRAPHSAGE:
            in_channels = self.model_config.get("in_channels", 64)
            hidden_channels = self.model_config.get("hidden_channels", 256)
            out_channels = self.model_config.get("out_channels", 2)
            num_layers = self.model_config.get("num_layers", 3)
            
            self.model = GraphSAGEClassifier(
                in_channels=in_channels,
                hidden_channels=hidden_channels,
                out_channels=out_channels,
                num_layers=num_layers
            )
        else:
            # HeteroGNN 사용
            self.model = HeteroGNNClassifier(
                hidden_channels=self.model_config.get("hidden_channels", 256),
                out_channels=self.model_config.get("out_channels", 2),
                num_layers=self.model_config.get("num_layers", 3)
            )
        
        # 가중치 로드
        if "model_state_dict" in checkpoint:
            self.model.load_state_dict(checkpoint["model_state_dict"])
        else:
            self.model.load_state_dict(checkpoint)
        
        self.model.to(self.device)
        self.model.eval()
        
        logger.info(f"Model loaded from {model_path}")
    
    def predict_nodes(
        self,
        data: HeteroData,
        threshold: float = 0.5,
        node_ids: Optional[List[str]] = None
    ) -> List[NodePrediction]:
        """
        노드별 캠페인 예측
        
        Args:
            data: HeteroData 그래프
            threshold: 캠페인 분류 임계값
            node_ids: 예측할 노드 ID 리스트 (None이면 전체)
        
        Returns:
            예측 결과 리스트
        """
        if self.model is None:
            raise ValueError("Model not loaded. Call load_model() first.")
        
        # 데이터를 디바이스로 이동
        data = data.to(self.device)
        
        predictions = []
        
        # Homogeneous 그래프로 변환 (간단한 경우)
        if self.model_type == GNNType.GRAPHSAGE:
            # 모든 노드를 하나로 합침
            all_features = []
            all_node_ids = []
            node_offset = {}
            current_offset = 0
            
            for node_type in data.node_types:
                if hasattr(data[node_type], 'x'):
                    all_features.append(data[node_type].x)
                    if hasattr(data[node_type], 'node_ids'):
                        all_node_ids.extend(data[node_type].node_ids)
                    else:
                        all_node_ids.extend([f"{node_type}_{i}" for i in range(data[node_type].num_nodes)])
                    node_offset[node_type] = current_offset
                    current_offset += data[node_type].num_nodes
            
            if not all_features:
                logger.warning("No node features found")
                return []
            
            x = torch.cat(all_features, dim=0).to(self.device)
            
            # 엣지 합치기
            edge_list = [[], []]
            for edge_type in data.edge_types:
                if hasattr(data[edge_type], 'edge_index'):
                    src_type, _, tgt_type = edge_type
                    src_offset = node_offset.get(src_type, 0)
                    tgt_offset = node_offset.get(tgt_type, 0)
                    
                    ei = data[edge_type].edge_index
                    edge_list[0].extend((ei[0] + src_offset).tolist())
                    edge_list[1].extend((ei[1] + tgt_offset).tolist())
            
            edge_index = torch.tensor(edge_list, dtype=torch.long).to(self.device)
            
            # 예측 수행
            with torch.no_grad():
                logits = self.model(x, edge_index)
                probs = F.softmax(logits, dim=1)
                campaign_probs = probs[:, 1].cpu().numpy()  # 캠페인 클래스 확률
            
            # 결과 생성
            for i, node_id in enumerate(all_node_ids):
                if node_ids and node_id not in node_ids:
                    continue
                
                campaign_prob = float(campaign_probs[i])
                is_campaign = campaign_prob >= threshold
                
                prediction = NodePrediction(
                    node_id=node_id,
                    node_type=node_id.split('_')[0] if '_' in node_id else "unknown",
                    campaign_probability=campaign_prob,
                    is_campaign=is_campaign,
                    confidence=abs(campaign_prob - threshold)  # 임계값과의 거리
                )
                predictions.append(prediction)
        
        # 확률 순 정렬
        predictions.sort(key=lambda x: x.campaign_probability, reverse=True)
        
        return predictions
    
    def detect_campaign_candidates(
        self,
        predictions: List[NodePrediction],
        min_size: int = 3,
        min_probability: float = 0.7
    ) -> List[CampaignCandidate]:
        """
        의심 캠페인 후보 탐지
        
        Args:
            predictions: 노드 예측 결과
            min_size: 최소 캠페인 크기
            min_probability: 최소 확률
        
        Returns:
            캠페인 후보 리스트
        """
        # 임계값 이상인 노드만 필터링
        flagged_nodes = [
            p for p in predictions
            if p.is_campaign and p.campaign_probability >= min_probability
        ]
        
        if len(flagged_nodes) < min_size:
            return []
        
        # 클러스터링 (간단한 방법: 확률 기반 그룹핑)
        # 실제로는 그래프 구조 기반 클러스터링이 더 정확
        candidates = []
        
        # 확률 범위별로 그룹핑
        prob_ranges = [
            (0.9, 1.0),
            (0.8, 0.9),
            (0.7, 0.8)
        ]
        
        campaign_counter = 0
        for min_prob, max_prob in prob_ranges:
            group = [
                p for p in flagged_nodes
                if min_prob <= p.campaign_probability < max_prob
            ]
            
            if len(group) >= min_size:
                import uuid
                campaign_id = f"campaign_{str(uuid.uuid4())[:8]}"
                
                avg_prob = sum(p.campaign_probability for p in group) / len(group)
                avg_confidence = sum(p.confidence for p in group) / len(group)
                
                candidate = CampaignCandidate(
                    campaign_id=campaign_id,
                    node_ids=[p.node_id for p in group],
                    average_probability=avg_prob,
                    size=len(group),
                    confidence=avg_confidence
                )
                candidates.append(candidate)
                campaign_counter += 1
        
        # 확률 순 정렬
        candidates.sort(key=lambda x: x.average_probability, reverse=True)
        
        return candidates
    
    def predict_and_detect(
        self,
        data: HeteroData,
        threshold: float = 0.5,
        min_campaign_size: int = 3,
        min_campaign_probability: float = 0.7
    ) -> Tuple[List[NodePrediction], List[CampaignCandidate]]:
        """
        예측 및 캠페인 탐지 (통합)
        
        Returns:
            (노드 예측 결과, 캠페인 후보 리스트)
        """
        predictions = self.predict_nodes(data, threshold=threshold)
        candidates = self.detect_campaign_candidates(
            predictions,
            min_size=min_campaign_size,
            min_probability=min_campaign_probability
        )
        
        return predictions, candidates


# 모듈 테스트용
if __name__ == "__main__":
    # 테스트용 더미 데이터
    import numpy as np
    
    data = HeteroData()
    data['user'].x = torch.randn(10, 64)
    data['user'].num_nodes = 10
    
    # 간단한 엣지
    edge_index = torch.tensor([[0, 1, 2], [1, 2, 0]], dtype=torch.long)
    data['user', 'follows', 'user'].edge_index = edge_index
    
    # 추론 파이프라인 테스트 (모델 없이)
    print("GNN Inference Pipeline Test:")
    print("=" * 60)
    print("Note: Model loading required for actual inference")
