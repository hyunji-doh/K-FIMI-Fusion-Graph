"""
모델 학습 모듈

GNN 모델 학습, 평가, 추론 기능을 제공합니다.
"""

from typing import Optional, Callable, Union
from dataclasses import dataclass, field
from pathlib import Path
import time

import numpy as np
import torch
import torch.nn as nn
import torch.optim as optim
from torch.optim.lr_scheduler import ReduceLROnPlateau, CosineAnnealingLR
from torch_geometric.data import HeteroData, Data
from torch_geometric.loader import NeighborLoader, HGTLoader
from sklearn.metrics import (
    accuracy_score, precision_score, recall_score, f1_score,
    roc_auc_score, confusion_matrix, classification_report
)
from loguru import logger

from .dataset_builder import CampaignDataset


@dataclass
class TrainingConfig:
    """학습 설정"""
    # 기본 설정
    epochs: int = 100
    batch_size: int = 256
    learning_rate: float = 0.001
    weight_decay: float = 5e-4
    
    # 스케줄러
    scheduler: str = "plateau"  # plateau, cosine, none
    scheduler_patience: int = 10
    scheduler_factor: float = 0.5
    
    # 조기 종료
    early_stopping: bool = True
    patience: int = 20
    min_delta: float = 0.001
    
    # 클래스 가중치
    use_class_weights: bool = True
    
    # 저장
    save_best: bool = True
    checkpoint_dir: str = "checkpoints"
    
    # 디바이스
    device: str = "auto"
    
    # 로깅
    log_interval: int = 10
    
    def get_device(self) -> torch.device:
        """디바이스 반환"""
        if self.device == "auto":
            return torch.device("cuda" if torch.cuda.is_available() else "cpu")
        return torch.device(self.device)


@dataclass
class TrainingResult:
    """학습 결과"""
    train_losses: list = field(default_factory=list)
    val_losses: list = field(default_factory=list)
    train_metrics: list = field(default_factory=list)
    val_metrics: list = field(default_factory=list)
    best_epoch: int = 0
    best_val_loss: float = float('inf')
    best_metrics: dict = field(default_factory=dict)
    training_time: float = 0.0
    
    def to_dict(self) -> dict:
        return {
            "train_losses": self.train_losses,
            "val_losses": self.val_losses,
            "train_metrics": self.train_metrics,
            "val_metrics": self.val_metrics,
            "best_epoch": self.best_epoch,
            "best_val_loss": self.best_val_loss,
            "best_metrics": self.best_metrics,
            "training_time": self.training_time
        }


class EarlyStopping:
    """조기 종료 클래스"""
    
    def __init__(
        self,
        patience: int = 10,
        min_delta: float = 0.0,
        mode: str = "min"
    ):
        self.patience = patience
        self.min_delta = min_delta
        self.mode = mode
        self.counter = 0
        self.best_score = None
        self.early_stop = False
    
    def __call__(self, score: float) -> bool:
        if self.best_score is None:
            self.best_score = score
            return False
        
        if self.mode == "min":
            improved = score < self.best_score - self.min_delta
        else:
            improved = score > self.best_score + self.min_delta
        
        if improved:
            self.best_score = score
            self.counter = 0
        else:
            self.counter += 1
            if self.counter >= self.patience:
                self.early_stop = True
        
        return self.early_stop


class Trainer:
    """
    GNN 모델 학습기
    
    다양한 GNN 모델의 학습, 평가, 추론을 수행합니다.
    """
    
    def __init__(
        self,
        model: nn.Module,
        config: Optional[TrainingConfig] = None
    ):
        """
        Trainer 초기화
        
        Args:
            model: GNN 모델
            config: 학습 설정
        """
        self.config = config or TrainingConfig()
        self.device = self.config.get_device()
        
        self.model = model.to(self.device)
        
        # 체크포인트 디렉토리
        self.checkpoint_dir = Path(self.config.checkpoint_dir)
        self.checkpoint_dir.mkdir(parents=True, exist_ok=True)
        
        # 옵티마이저
        self.optimizer = optim.Adam(
            model.parameters(),
            lr=self.config.learning_rate,
            weight_decay=self.config.weight_decay
        )
        
        # 스케줄러
        self.scheduler = self._create_scheduler()
        
        # 조기 종료
        self.early_stopping = None
        if self.config.early_stopping:
            self.early_stopping = EarlyStopping(
                patience=self.config.patience,
                min_delta=self.config.min_delta
            )
        
        logger.info(f"Trainer initialized. Device: {self.device}")
    
    def _create_scheduler(self):
        """스케줄러 생성"""
        if self.config.scheduler == "plateau":
            return ReduceLROnPlateau(
                self.optimizer,
                mode="min",
                patience=self.config.scheduler_patience,
                factor=self.config.scheduler_factor
            )
        elif self.config.scheduler == "cosine":
            return CosineAnnealingLR(
                self.optimizer,
                T_max=self.config.epochs
            )
        return None
    
    def train(
        self,
        dataset: CampaignDataset,
        train_mask: torch.Tensor,
        val_mask: torch.Tensor,
        target_node_type: str = "user"
    ) -> TrainingResult:
        """
        모델 학습
        
        Args:
            dataset: CampaignDataset
            train_mask: 학습 마스크
            val_mask: 검증 마스크
            target_node_type: 대상 노드 타입 (Hetero 그래프용)
        
        Returns:
            TrainingResult 객체
        """
        result = TrainingResult()
        start_time = time.time()
        
        data = dataset.data.to(self.device)
        train_mask = train_mask.to(self.device)
        val_mask = val_mask.to(self.device)
        
        # 레이블
        if isinstance(data, HeteroData):
            labels = data[target_node_type].y
        else:
            labels = data.y
        
        labels = labels.to(self.device)
        
        # 손실 함수
        if self.config.use_class_weights and dataset.labels is not None:
            from .dataset_builder import CampaignDatasetBuilder
            builder = CampaignDatasetBuilder()
            weights = builder.get_class_weights(dataset.labels).to(self.device)
            criterion = nn.CrossEntropyLoss(weight=weights)
        else:
            criterion = nn.CrossEntropyLoss()
        
        best_val_loss = float('inf')
        
        for epoch in range(self.config.epochs):
            # 학습
            self.model.train()
            self.optimizer.zero_grad()
            
            if isinstance(data, HeteroData):
                out = self.model(data)
            else:
                out = self.model(data.x, data.edge_index)
            
            # 학습 손실
            train_loss = criterion(out[train_mask], labels[train_mask])
            train_loss.backward()
            self.optimizer.step()
            
            # 검증
            self.model.eval()
            with torch.no_grad():
                if isinstance(data, HeteroData):
                    out = self.model(data)
                else:
                    out = self.model(data.x, data.edge_index)
                
                val_loss = criterion(out[val_mask], labels[val_mask])
            
            # 메트릭 계산
            train_metrics = self._compute_metrics(
                out[train_mask], labels[train_mask]
            )
            val_metrics = self._compute_metrics(
                out[val_mask], labels[val_mask]
            )
            
            # 결과 저장
            result.train_losses.append(train_loss.item())
            result.val_losses.append(val_loss.item())
            result.train_metrics.append(train_metrics)
            result.val_metrics.append(val_metrics)
            
            # 최상의 모델 저장
            if val_loss < best_val_loss:
                best_val_loss = val_loss.item()
                result.best_epoch = epoch
                result.best_val_loss = best_val_loss
                result.best_metrics = val_metrics
                
                if self.config.save_best:
                    self._save_checkpoint("best_model.pt")
            
            # 스케줄러 업데이트
            if self.scheduler:
                if isinstance(self.scheduler, ReduceLROnPlateau):
                    self.scheduler.step(val_loss)
                else:
                    self.scheduler.step()
            
            # 조기 종료 체크
            if self.early_stopping and self.early_stopping(val_loss.item()):
                logger.info(f"Early stopping at epoch {epoch}")
                break
            
            # 로깅
            if epoch % self.config.log_interval == 0:
                logger.info(
                    f"Epoch {epoch:3d} | "
                    f"Train Loss: {train_loss:.4f} | "
                    f"Val Loss: {val_loss:.4f} | "
                    f"Val F1: {val_metrics.get('f1', 0):.4f}"
                )
        
        result.training_time = time.time() - start_time
        
        logger.info(
            f"\nTraining completed in {result.training_time:.2f}s | "
            f"Best Epoch: {result.best_epoch} | "
            f"Best Val Loss: {result.best_val_loss:.4f}"
        )
        
        return result
    
    def evaluate(
        self,
        dataset: CampaignDataset,
        test_mask: torch.Tensor,
        target_node_type: str = "user"
    ) -> dict:
        """
        모델 평가
        
        Args:
            dataset: CampaignDataset
            test_mask: 테스트 마스크
            target_node_type: 대상 노드 타입
        
        Returns:
            평가 메트릭 딕셔너리
        """
        self.model.eval()
        
        data = dataset.data.to(self.device)
        test_mask = test_mask.to(self.device)
        
        if isinstance(data, HeteroData):
            labels = data[target_node_type].y
        else:
            labels = data.y
        
        labels = labels.to(self.device)
        
        with torch.no_grad():
            if isinstance(data, HeteroData):
                out = self.model(data)
            else:
                out = self.model(data.x, data.edge_index)
            
            metrics = self._compute_metrics(
                out[test_mask], labels[test_mask], detailed=True
            )
        
        logger.info(f"\nTest Results:")
        logger.info(f"Accuracy: {metrics['accuracy']:.4f}")
        logger.info(f"Precision: {metrics['precision']:.4f}")
        logger.info(f"Recall: {metrics['recall']:.4f}")
        logger.info(f"F1 Score: {metrics['f1']:.4f}")
        
        if 'auc' in metrics:
            logger.info(f"AUC-ROC: {metrics['auc']:.4f}")
        
        return metrics
    
    def predict(
        self,
        data: Union[HeteroData, Data],
        return_probs: bool = False
    ) -> Union[torch.Tensor, tuple]:
        """
        예측 수행
        
        Args:
            data: 그래프 데이터
            return_probs: 확률값 반환 여부
        
        Returns:
            예측 레이블 (또는 (레이블, 확률) 튜플)
        """
        self.model.eval()
        data = data.to(self.device)
        
        with torch.no_grad():
            if isinstance(data, HeteroData):
                out = self.model(data)
            else:
                out = self.model(data.x, data.edge_index)
            
            probs = torch.softmax(out, dim=1)
            preds = probs.argmax(dim=1)
        
        if return_probs:
            return preds.cpu(), probs.cpu()
        return preds.cpu()
    
    def predict_campaign_scores(
        self,
        data: Union[HeteroData, Data],
        target_node_type: str = "user"
    ) -> dict:
        """
        캠페인 점수 예측
        
        각 노드의 캠페인 소속 확률을 계산합니다.
        
        Args:
            data: 그래프 데이터
            target_node_type: 대상 노드 타입
        
        Returns:
            노드별 캠페인 점수 딕셔너리
        """
        preds, probs = self.predict(data, return_probs=True)
        
        # 캠페인 클래스 확률 (클래스 1 가정)
        campaign_probs = probs[:, 1].numpy()
        
        # 노드 ID가 있으면 매핑
        if isinstance(data, HeteroData):
            node_ids = getattr(data[target_node_type], 'node_ids', None)
        else:
            node_ids = getattr(data, 'node_ids', None)
        
        if node_ids is not None:
            return {
                node_id: float(prob)
                for node_id, prob in zip(node_ids, campaign_probs)
            }
        
        return {
            f"node_{i}": float(prob)
            for i, prob in enumerate(campaign_probs)
        }
    
    def _compute_metrics(
        self,
        outputs: torch.Tensor,
        labels: torch.Tensor,
        detailed: bool = False
    ) -> dict:
        """메트릭 계산"""
        preds = outputs.argmax(dim=1).cpu().numpy()
        labels_np = labels.cpu().numpy()
        probs = torch.softmax(outputs, dim=1).cpu().numpy()
        
        metrics = {
            "accuracy": accuracy_score(labels_np, preds),
            "precision": precision_score(labels_np, preds, average="binary", zero_division=0),
            "recall": recall_score(labels_np, preds, average="binary", zero_division=0),
            "f1": f1_score(labels_np, preds, average="binary", zero_division=0)
        }
        
        # AUC (이진 분류)
        if len(np.unique(labels_np)) == 2 and probs.shape[1] >= 2:
            try:
                metrics["auc"] = roc_auc_score(labels_np, probs[:, 1])
            except ValueError:
                pass
        
        # Precision@K, Recall@K (랭킹 메트릭)
        if probs.shape[1] >= 2:
            positive_probs = probs[:, 1]
            metrics.update(self._compute_ranking_metrics(labels_np, positive_probs))
        
        if detailed:
            metrics["confusion_matrix"] = confusion_matrix(labels_np, preds).tolist()
            metrics["classification_report"] = classification_report(
                labels_np, preds, output_dict=True
            )
        
        return metrics
    
    def _compute_ranking_metrics(
        self,
        labels: np.ndarray,
        scores: np.ndarray,
        k_values: list = None
    ) -> dict:
        """
        랭킹 메트릭 계산 (Precision@K, Recall@K, NDCG@K, MAP)
        
        Args:
            labels: 실제 레이블 (0/1)
            scores: 예측 점수 (확률)
            k_values: K 값 리스트
        
        Returns:
            랭킹 메트릭 딕셔너리
        """
        if k_values is None:
            k_values = [10, 20, 50, 100]
        
        metrics = {}
        n_samples = len(labels)
        n_positives = np.sum(labels)
        
        if n_positives == 0:
            return metrics
        
        # 점수 기준 내림차순 정렬
        sorted_indices = np.argsort(scores)[::-1]
        sorted_labels = labels[sorted_indices]
        
        for k in k_values:
            if k > n_samples:
                k = n_samples
            
            # Precision@K: 상위 K개 중 실제 양성 비율
            top_k_labels = sorted_labels[:k]
            precision_at_k = np.sum(top_k_labels) / k
            metrics[f"precision@{k}"] = float(precision_at_k)
            
            # Recall@K: 전체 양성 중 상위 K에 포함된 비율
            recall_at_k = np.sum(top_k_labels) / n_positives
            metrics[f"recall@{k}"] = float(recall_at_k)
            
            # NDCG@K (Normalized Discounted Cumulative Gain)
            dcg = np.sum(top_k_labels / np.log2(np.arange(2, k + 2)))
            ideal_labels = np.sort(labels)[::-1][:k]
            idcg = np.sum(ideal_labels / np.log2(np.arange(2, k + 2)))
            ndcg_at_k = dcg / idcg if idcg > 0 else 0
            metrics[f"ndcg@{k}"] = float(ndcg_at_k)
        
        # MAP (Mean Average Precision)
        precisions = []
        n_relevant = 0
        for i, label in enumerate(sorted_labels):
            if label == 1:
                n_relevant += 1
                precisions.append(n_relevant / (i + 1))
        
        map_score = np.mean(precisions) if precisions else 0
        metrics["map"] = float(map_score)
        
        # MRR (Mean Reciprocal Rank)
        first_positive_idx = np.where(sorted_labels == 1)[0]
        mrr = 1.0 / (first_positive_idx[0] + 1) if len(first_positive_idx) > 0 else 0
        metrics["mrr"] = float(mrr)
        
        return metrics
    
    def evaluate_campaign_detection(
        self,
        data: Union[HeteroData, Data],
        labels: torch.Tensor,
        target_node_type: str = "user",
        k_values: list = None
    ) -> dict:
        """
        캠페인 탐지 전용 평가
        
        Args:
            data: 그래프 데이터
            labels: 레이블 텐서
            target_node_type: 대상 노드 타입
            k_values: Precision@K의 K 값들
        
        Returns:
            상세 평가 메트릭
        """
        if k_values is None:
            k_values = [10, 20, 50, 100]
        
        self.model.eval()
        data = data.to(self.device)
        labels = labels.to(self.device)
        
        with torch.no_grad():
            if isinstance(data, HeteroData):
                out = self.model(data)
            else:
                out = self.model(data.x, data.edge_index)
            
            probs = torch.softmax(out, dim=1)
            preds = probs.argmax(dim=1)
            positive_probs = probs[:, 1].cpu().numpy()
        
        labels_np = labels.cpu().numpy()
        preds_np = preds.cpu().numpy()
        
        # 기본 분류 메트릭
        metrics = {
            "accuracy": float(accuracy_score(labels_np, preds_np)),
            "precision": float(precision_score(labels_np, preds_np, average="binary", zero_division=0)),
            "recall": float(recall_score(labels_np, preds_np, average="binary", zero_division=0)),
            "f1": float(f1_score(labels_np, preds_np, average="binary", zero_division=0))
        }
        
        # AUC-ROC
        try:
            metrics["auc_roc"] = float(roc_auc_score(labels_np, positive_probs))
        except ValueError:
            metrics["auc_roc"] = 0.0
        
        # AUC-PR (Precision-Recall AUC)
        try:
            from sklearn.metrics import average_precision_score
            metrics["auc_pr"] = float(average_precision_score(labels_np, positive_probs))
        except Exception:
            metrics["auc_pr"] = 0.0
        
        # 랭킹 메트릭
        ranking_metrics = self._compute_ranking_metrics(labels_np, positive_probs, k_values)
        metrics.update(ranking_metrics)
        
        # 혼동 행렬
        metrics["confusion_matrix"] = confusion_matrix(labels_np, preds_np).tolist()
        
        # 캠페인 탐지 특화 메트릭
        n_total = len(labels_np)
        n_positives = np.sum(labels_np)
        n_predicted_positives = np.sum(preds_np)
        
        metrics["campaign_stats"] = {
            "total_nodes": int(n_total),
            "actual_campaign_nodes": int(n_positives),
            "predicted_campaign_nodes": int(n_predicted_positives),
            "campaign_ratio": float(n_positives / n_total) if n_total > 0 else 0
        }
        
        return metrics
    
    def _save_checkpoint(self, filename: str):
        """체크포인트 저장"""
        filepath = self.checkpoint_dir / filename
        
        torch.save({
            "model_state_dict": self.model.state_dict(),
            "optimizer_state_dict": self.optimizer.state_dict(),
            "config": self.config
        }, filepath)
    
    def load_checkpoint(self, filename: str):
        """체크포인트 로드"""
        filepath = self.checkpoint_dir / filename
        
        if not filepath.exists():
            raise FileNotFoundError(f"Checkpoint not found: {filepath}")
        
        checkpoint = torch.load(filepath, map_location=self.device)
        self.model.load_state_dict(checkpoint["model_state_dict"])
        self.optimizer.load_state_dict(checkpoint["optimizer_state_dict"])
        
        logger.info(f"Checkpoint loaded from {filepath}")
    
    def save_model(self, filepath: str):
        """모델 저장"""
        torch.save(self.model.state_dict(), filepath)
        logger.info(f"Model saved to {filepath}")
    
    def load_model(self, filepath: str):
        """모델 로드"""
        self.model.load_state_dict(
            torch.load(filepath, map_location=self.device)
        )
        logger.info(f"Model loaded from {filepath}")


class BatchTrainer(Trainer):
    """
    미니배치 학습 지원 Trainer
    
    대규모 그래프를 위한 NeighborLoader 기반 학습을 수행합니다.
    """
    
    def __init__(
        self,
        model: nn.Module,
        config: Optional[TrainingConfig] = None,
        num_neighbors: list = None
    ):
        super().__init__(model, config)
        self.num_neighbors = num_neighbors or [15, 10, 5]
    
    def train_with_loader(
        self,
        data: Union[HeteroData, Data],
        train_mask: torch.Tensor,
        val_mask: torch.Tensor,
        target_node_type: str = "user"
    ) -> TrainingResult:
        """
        미니배치 학습
        
        Args:
            data: 그래프 데이터
            train_mask: 학습 마스크
            val_mask: 검증 마스크
            target_node_type: 대상 노드 타입
        
        Returns:
            TrainingResult
        """
        result = TrainingResult()
        start_time = time.time()
        
        # 데이터 로더 생성
        if isinstance(data, HeteroData):
            train_loader = HGTLoader(
                data,
                num_samples=self.num_neighbors,
                batch_size=self.config.batch_size,
                input_nodes=(target_node_type, train_mask),
                shuffle=True
            )
            val_loader = HGTLoader(
                data,
                num_samples=self.num_neighbors,
                batch_size=self.config.batch_size,
                input_nodes=(target_node_type, val_mask)
            )
        else:
            train_loader = NeighborLoader(
                data,
                num_neighbors=self.num_neighbors,
                batch_size=self.config.batch_size,
                input_nodes=train_mask,
                shuffle=True
            )
            val_loader = NeighborLoader(
                data,
                num_neighbors=self.num_neighbors,
                batch_size=self.config.batch_size,
                input_nodes=val_mask
            )
        
        criterion = nn.CrossEntropyLoss()
        best_val_loss = float('inf')
        
        for epoch in range(self.config.epochs):
            # 학습
            self.model.train()
            total_train_loss = 0
            
            for batch in train_loader:
                batch = batch.to(self.device)
                self.optimizer.zero_grad()
                
                if isinstance(batch, HeteroData):
                    out = self.model(batch)
                    labels = batch[target_node_type].y
                else:
                    out = self.model(batch.x, batch.edge_index)
                    labels = batch.y
                
                loss = criterion(out[:batch.batch_size], labels[:batch.batch_size])
                loss.backward()
                self.optimizer.step()
                
                total_train_loss += loss.item()
            
            train_loss = total_train_loss / len(train_loader)
            
            # 검증
            self.model.eval()
            total_val_loss = 0
            
            with torch.no_grad():
                for batch in val_loader:
                    batch = batch.to(self.device)
                    
                    if isinstance(batch, HeteroData):
                        out = self.model(batch)
                        labels = batch[target_node_type].y
                    else:
                        out = self.model(batch.x, batch.edge_index)
                        labels = batch.y
                    
                    loss = criterion(out[:batch.batch_size], labels[:batch.batch_size])
                    total_val_loss += loss.item()
            
            val_loss = total_val_loss / len(val_loader)
            
            # 결과 저장
            result.train_losses.append(train_loss)
            result.val_losses.append(val_loss)
            
            if val_loss < best_val_loss:
                best_val_loss = val_loss
                result.best_epoch = epoch
                result.best_val_loss = best_val_loss
                
                if self.config.save_best:
                    self._save_checkpoint("best_model.pt")
            
            # 스케줄러 업데이트
            if self.scheduler:
                if isinstance(self.scheduler, ReduceLROnPlateau):
                    self.scheduler.step(val_loss)
                else:
                    self.scheduler.step()
            
            # 조기 종료
            if self.early_stopping and self.early_stopping(val_loss):
                logger.info(f"Early stopping at epoch {epoch}")
                break
            
            if epoch % self.config.log_interval == 0:
                logger.info(
                    f"Epoch {epoch:3d} | "
                    f"Train Loss: {train_loss:.4f} | "
                    f"Val Loss: {val_loss:.4f}"
                )
        
        result.training_time = time.time() - start_time
        return result


# 모듈 테스트용
if __name__ == "__main__":
    from .gnn_classifier import GraphSAGEClassifier
    
    # 모델 생성
    model = GraphSAGEClassifier(
        in_channels=768,
        hidden_channels=256,
        out_channels=2,
        num_layers=3
    )
    
    # Trainer 생성
    config = TrainingConfig(
        epochs=50,
        learning_rate=0.01,
        early_stopping=True,
        patience=10
    )
    
    trainer = Trainer(model, config)
    
    print(f"Trainer ready. Device: {trainer.device}")

