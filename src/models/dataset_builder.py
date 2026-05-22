"""
데이터셋 빌더 모듈

Fusion Graph에서 GNN 학습용 데이터셋을 구축합니다.
"""

from typing import Optional, Union
from dataclasses import dataclass, field
from pathlib import Path
import json

import numpy as np
import torch
from torch.utils.data import Dataset
from torch_geometric.data import HeteroData, Data
from torch_geometric.transforms import RandomNodeSplit, ToUndirected
from sklearn.model_selection import train_test_split
from loguru import logger


@dataclass
class CampaignLabel:
    """캠페인 레이블 데이터"""
    node_id: str
    node_type: str
    label: int
    campaign_id: Optional[str] = None
    confidence: float = 1.0
    
    def to_dict(self) -> dict:
        return {
            "node_id": self.node_id,
            "node_type": self.node_type,
            "label": self.label,
            "campaign_id": self.campaign_id,
            "confidence": self.confidence
        }


class CampaignDataset(Dataset):
    """
    캠페인 탐지 데이터셋
    
    그래프 데이터와 레이블을 관리합니다.
    """
    
    def __init__(
        self,
        data: Union[HeteroData, Data],
        labels: Optional[torch.Tensor] = None,
        node_ids: Optional[list[str]] = None,
        transform=None
    ):
        """
        CampaignDataset 초기화
        
        Args:
            data: PyG 그래프 데이터
            labels: 레이블 텐서
            node_ids: 노드 ID 리스트
            transform: 데이터 변환 함수
        """
        self.data = data
        self.labels = labels
        self.node_ids = node_ids
        self.transform = transform
    
    def __len__(self) -> int:
        if self.labels is not None:
            return len(self.labels)
        return 1  # 전체 그래프
    
    def __getitem__(self, idx):
        if self.transform:
            return self.transform(self.data)
        return self.data
    
    def get_split_masks(
        self,
        train_ratio: float = 0.6,
        val_ratio: float = 0.2,
        test_ratio: float = 0.2,
        random_state: int = 42
    ) -> tuple[torch.Tensor, torch.Tensor, torch.Tensor]:
        """
        학습/검증/테스트 마스크 생성
        
        Args:
            train_ratio: 학습 데이터 비율
            val_ratio: 검증 데이터 비율
            test_ratio: 테스트 데이터 비율
            random_state: 랜덤 시드
        
        Returns:
            (train_mask, val_mask, test_mask) 튜플
        """
        if self.labels is None:
            raise ValueError("Labels required for split")
        
        n_nodes = len(self.labels)
        indices = np.arange(n_nodes)
        
        # 학습/나머지 분할
        train_idx, temp_idx = train_test_split(
            indices,
            train_size=train_ratio,
            random_state=random_state,
            stratify=self.labels.numpy() if self.labels is not None else None
        )
        
        # 검증/테스트 분할
        val_size = val_ratio / (val_ratio + test_ratio)
        val_idx, test_idx = train_test_split(
            temp_idx,
            train_size=val_size,
            random_state=random_state
        )
        
        # 마스크 생성
        train_mask = torch.zeros(n_nodes, dtype=torch.bool)
        val_mask = torch.zeros(n_nodes, dtype=torch.bool)
        test_mask = torch.zeros(n_nodes, dtype=torch.bool)
        
        train_mask[train_idx] = True
        val_mask[val_idx] = True
        test_mask[test_idx] = True
        
        return train_mask, val_mask, test_mask


class CampaignDatasetBuilder:
    """
    캠페인 탐지용 데이터셋 빌더
    
    Fusion Graph를 GNN 학습용 데이터셋으로 변환합니다.
    """
    
    def __init__(
        self,
        output_dir: str = "data/processed"
    ):
        """
        DatasetBuilder 초기화
        
        Args:
            output_dir: 데이터셋 저장 경로
        """
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        self.labels: list[CampaignLabel] = []
        self.label_mapping: dict[str, int] = {}
        
        logger.info(f"CampaignDatasetBuilder initialized. Output: {self.output_dir}")
    
    def add_label(
        self,
        node_id: str,
        node_type: str,
        label: int,
        campaign_id: Optional[str] = None,
        confidence: float = 1.0
    ):
        """
        레이블 추가
        
        Args:
            node_id: 노드 ID
            node_type: 노드 타입
            label: 레이블 (0: 정상, 1: 캠페인)
            campaign_id: 캠페인 ID
            confidence: 레이블 신뢰도
        """
        label_data = CampaignLabel(
            node_id=node_id,
            node_type=node_type,
            label=label,
            campaign_id=campaign_id,
            confidence=confidence
        )
        self.labels.append(label_data)
        self.label_mapping[node_id] = label
    
    def add_labels_from_file(self, filepath: str):
        """
        파일에서 레이블 로드
        
        Args:
            filepath: 레이블 파일 경로 (JSON 형식)
        """
        with open(filepath, "r", encoding="utf-8") as f:
            data = json.load(f)
        
        for item in data:
            self.add_label(**item)
        
        logger.info(f"Loaded {len(data)} labels from {filepath}")
    
    def build_dataset(
        self,
        hetero_data: HeteroData,
        target_node_type: str = "user",
        include_unlabeled: bool = True
    ) -> CampaignDataset:
        """
        HeteroData로부터 데이터셋 구축
        
        Args:
            hetero_data: PyG HeteroData 객체
            target_node_type: 분류 대상 노드 타입
            include_unlabeled: 레이블 없는 노드 포함 여부
        
        Returns:
            CampaignDataset 객체
        """
        # 타겟 노드 수
        num_nodes = hetero_data[target_node_type].num_nodes
        
        # 레이블 텐서 생성 (-1: 미레이블)
        labels = torch.full((num_nodes,), -1, dtype=torch.long)
        
        # 노드 ID 매핑 (있는 경우)
        node_ids = getattr(hetero_data[target_node_type], 'node_ids', None)
        
        if node_ids is not None:
            node_id_to_idx = {nid: idx for idx, nid in enumerate(node_ids)}
            
            for label_data in self.labels:
                if label_data.node_type == target_node_type:
                    if label_data.node_id in node_id_to_idx:
                        idx = node_id_to_idx[label_data.node_id]
                        labels[idx] = label_data.label
        
        # 레이블된 노드 마스크
        labeled_mask = labels >= 0
        
        if not include_unlabeled:
            # 레이블된 노드만 사용
            labels = labels[labeled_mask]
        
        logger.info(
            f"Dataset built: {num_nodes} nodes, "
            f"{labeled_mask.sum().item()} labeled"
        )
        
        return CampaignDataset(
            data=hetero_data,
            labels=labels,
            node_ids=node_ids
        )
    
    def build_homogeneous_dataset(
        self,
        data: Data,
        labels: Optional[torch.Tensor] = None
    ) -> CampaignDataset:
        """
        Homogeneous 그래프 데이터셋 구축
        
        Args:
            data: PyG Data 객체
            labels: 레이블 텐서
        
        Returns:
            CampaignDataset 객체
        """
        return CampaignDataset(data=data, labels=labels)
    
    def create_train_val_test_split(
        self,
        dataset: CampaignDataset,
        train_ratio: float = 0.6,
        val_ratio: float = 0.2,
        test_ratio: float = 0.2,
        random_state: int = 42
    ) -> tuple:
        """
        학습/검증/테스트 분할 생성
        
        Args:
            dataset: CampaignDataset
            train_ratio: 학습 비율
            val_ratio: 검증 비율
            test_ratio: 테스트 비율
            random_state: 랜덤 시드
        
        Returns:
            (train_mask, val_mask, test_mask) 튜플
        """
        return dataset.get_split_masks(
            train_ratio=train_ratio,
            val_ratio=val_ratio,
            test_ratio=test_ratio,
            random_state=random_state
        )
    
    def apply_node_split_transform(
        self,
        hetero_data: HeteroData,
        target_node_type: str = "user",
        num_train_per_class: int = 20,
        num_val: float = 0.1,
        num_test: float = 0.1
    ) -> HeteroData:
        """
        RandomNodeSplit 변환 적용
        
        Args:
            hetero_data: HeteroData 객체
            target_node_type: 대상 노드 타입
            num_train_per_class: 클래스당 학습 샘플 수
            num_val: 검증 비율
            num_test: 테스트 비율
        
        Returns:
            분할된 HeteroData
        """
        transform = RandomNodeSplit(
            split="train_rest",
            num_train_per_class=num_train_per_class,
            num_val=num_val,
            num_test=num_test
        )
        return transform(hetero_data)
    
    def generate_negative_samples(
        self,
        hetero_data: HeteroData,
        target_node_type: str = "user",
        positive_label: int = 1,
        negative_ratio: float = 1.0
    ) -> torch.Tensor:
        """
        네거티브 샘플 생성
        
        레이블이 없는 노드를 네거티브(정상)로 간주합니다.
        
        Args:
            hetero_data: HeteroData
            target_node_type: 대상 노드 타입
            positive_label: 포지티브 레이블 값
            negative_ratio: 포지티브 대비 네거티브 비율
        
        Returns:
            업데이트된 레이블 텐서
        """
        num_nodes = hetero_data[target_node_type].num_nodes
        
        # 현재 레이블 가져오기 또는 생성
        if hasattr(hetero_data[target_node_type], 'y'):
            labels = hetero_data[target_node_type].y.clone()
        else:
            labels = torch.full((num_nodes,), -1, dtype=torch.long)
        
        # 포지티브 샘플 인덱스
        positive_mask = labels == positive_label
        num_positive = positive_mask.sum().item()
        
        # 네거티브 샘플 수 계산
        num_negative = int(num_positive * negative_ratio)
        
        # 미레이블 노드에서 네거티브 샘플링
        unlabeled_mask = labels == -1
        unlabeled_indices = torch.where(unlabeled_mask)[0]
        
        if len(unlabeled_indices) > 0:
            # 랜덤 샘플링
            perm = torch.randperm(len(unlabeled_indices))[:num_negative]
            negative_indices = unlabeled_indices[perm]
            
            # 네거티브 레이블 할당
            labels[negative_indices] = 0
        
        logger.info(
            f"Generated labels: {num_positive} positive, "
            f"{(labels == 0).sum().item()} negative"
        )
        
        return labels
    
    def save_dataset(
        self,
        dataset: CampaignDataset,
        name: str
    ):
        """
        데이터셋 저장
        
        Args:
            dataset: CampaignDataset
            name: 데이터셋 이름
        """
        filepath = self.output_dir / f"{name}.pt"
        torch.save({
            "data": dataset.data,
            "labels": dataset.labels,
            "node_ids": dataset.node_ids
        }, filepath)
        
        logger.info(f"Dataset saved to {filepath}")
    
    def load_dataset(self, name: str) -> CampaignDataset:
        """
        데이터셋 로드
        
        Args:
            name: 데이터셋 이름
        
        Returns:
            CampaignDataset 객체
        """
        filepath = self.output_dir / f"{name}.pt"
        
        if not filepath.exists():
            raise FileNotFoundError(f"Dataset not found: {filepath}")
        
        checkpoint = torch.load(filepath)
        
        return CampaignDataset(
            data=checkpoint["data"],
            labels=checkpoint["labels"],
            node_ids=checkpoint["node_ids"]
        )
    
    def save_labels(self, filename: str):
        """
        레이블을 파일로 저장
        
        Args:
            filename: 파일명 (확장자 제외)
        """
        filepath = self.output_dir / f"{filename}.json"
        
        data = [label.to_dict() for label in self.labels]
        
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        
        logger.info(f"Labels saved to {filepath}")
    
    def get_class_weights(
        self,
        labels: torch.Tensor
    ) -> torch.Tensor:
        """
        클래스 불균형을 위한 가중치 계산
        
        Args:
            labels: 레이블 텐서
        
        Returns:
            클래스 가중치 텐서
        """
        # 유효한 레이블만
        valid_mask = labels >= 0
        valid_labels = labels[valid_mask]
        
        if len(valid_labels) == 0:
            return torch.ones(2)
        
        # 클래스별 개수
        class_counts = torch.bincount(valid_labels)
        
        # 역빈도 가중치
        total = valid_labels.shape[0]
        weights = total / (len(class_counts) * class_counts.float())
        
        return weights
    
    def get_statistics(self) -> dict:
        """데이터셋 통계 반환"""
        label_counts = {}
        for label_data in self.labels:
            label = label_data.label
            label_counts[label] = label_counts.get(label, 0) + 1
        
        return {
            "total_labels": len(self.labels),
            "label_distribution": label_counts,
            "num_campaigns": len(set(
                l.campaign_id for l in self.labels if l.campaign_id
            ))
        }


# 모듈 테스트용
if __name__ == "__main__":
    # 테스트 데이터셋 생성
    builder = CampaignDatasetBuilder()
    
    # 샘플 레이블 추가
    for i in range(100):
        builder.add_label(
            node_id=f"user_{i}",
            node_type="user",
            label=1 if i < 20 else 0,
            campaign_id="campaign_1" if i < 20 else None
        )
    
    print(builder.get_statistics())

