"""
학습 데이터 라벨링 도구

해외 공개 FIMI 사례 기반 라벨링 및 "캠페인" vs "정상 활동" 라벨링을 지원합니다.
"""

import json
from typing import List, Dict, Optional, Set
from dataclasses import dataclass, field, asdict
from datetime import datetime
from pathlib import Path
from enum import Enum

from loguru import logger


class LabelType(str, Enum):
    """레이블 타입"""
    CAMPAIGN = "campaign"      # 조직적 캠페인
    NORMAL = "normal"          # 정상적인 다수 시민 활동
    UNKNOWN = "unknown"        # 미확인


class LabelSource(str, Enum):
    """레이블 출처"""
    MANUAL = "manual"          # 수동 라벨링
    FIMI_CASE = "fimi_case"   # 해외 공개 FIMI 사례
    AUTO = "auto"             # 자동 라벨링


@dataclass
class Label:
    """레이블 데이터"""
    label_id: str
    node_id: str
    node_type: str  # 'user', 'content', 'cluster'
    label_type: LabelType
    label_source: LabelSource
    confidence: float = 1.0  # 레이블 신뢰도
    campaign_id: Optional[str] = None
    case_reference: Optional[str] = None  # 참조 사례 (예: "US_2016_election")
    notes: Optional[str] = None
    labeled_by: Optional[str] = None
    labeled_at: datetime = field(default_factory=datetime.now)
    
    def to_dict(self) -> dict:
        data = asdict(self)
        data['labeled_at'] = self.labeled_at.isoformat()
        return data


@dataclass
class FIMICase:
    """해외 공개 FIMI 사례"""
    case_id: str
    case_name: str
    country: str
    year: int
    description: str
    source_url: Optional[str] = None
    node_ids: List[str] = field(default_factory=list)  # 해당 사례에 연루된 노드 ID
    narrative: Optional[str] = None
    
    def to_dict(self) -> dict:
        return asdict(self)


class LabelingTool:
    """
    라벨링 도구
    
    학습 데이터 라벨링을 지원합니다.
    """
    
    # 알려진 FIMI 사례
    KNOWN_FIMI_CASES = [
        FIMICase(
            case_id="US_2016_election",
            case_name="2016년 미국 대선 러시아 개입",
            country="US",
            year=2016,
            description="러시아가 소셜 미디어를 통해 미국 대선에 개입한 사례",
            source_url="https://www.intelligence.senate.gov/sites/default/files/documents/Report_Volume2.pdf",
            narrative="선거 개입, 정치적 분열 조장"
        ),
        FIMICase(
            case_id="UK_brexit",
            case_name="영국 브렉시트 캠페인",
            country="UK",
            year=2016,
            description="브렉시트 관련 허위정보 캠페인",
            narrative="정치적 분열, 허위정보 유포"
        ),
        FIMICase(
            case_id="FR_2017_election",
            case_name="2017년 프랑스 대선 개입",
            country="FR",
            year=2017,
            description="프랑스 대선 관련 정보공작",
            narrative="선거 개입, 후보 비방"
        ),
    ]
    
    def __init__(self, labels_file: Optional[str] = None):
        """
        LabelingTool 초기화
        
        Args:
            labels_file: 레이블 파일 경로 (JSON)
        """
        self.labels: Dict[str, Label] = {}  # {label_id: Label}
        self.node_labels: Dict[str, List[str]] = {}  # {node_id: [label_id]}
        self.fimi_cases: Dict[str, FIMICase] = {}
        
        # 알려진 FIMI 사례 로드
        for case in self.KNOWN_FIMI_CASES:
            self.fimi_cases[case.case_id] = case
        
        # 레이블 로드
        if labels_file:
            self.load_labels(labels_file)
        
        logger.info(f"LabelingTool initialized: {len(self.labels)} labels")
    
    def add_label(
        self,
        node_id: str,
        node_type: str,
        label_type: LabelType,
        label_source: LabelSource,
        confidence: float = 1.0,
        campaign_id: Optional[str] = None,
        case_reference: Optional[str] = None,
        notes: Optional[str] = None,
        labeled_by: Optional[str] = None
    ) -> str:
        """
        레이블 추가
        
        Returns:
            label_id
        """
        import uuid
        label_id = str(uuid.uuid4())[:8]
        
        label = Label(
            label_id=label_id,
            node_id=node_id,
            node_type=node_type,
            label_type=label_type,
            label_source=label_source,
            confidence=confidence,
            campaign_id=campaign_id,
            case_reference=case_reference,
            notes=notes,
            labeled_by=labeled_by
        )
        
        self.labels[label_id] = label
        
        # 노드별 레이블 인덱스
        if node_id not in self.node_labels:
            self.node_labels[node_id] = []
        self.node_labels[node_id].append(label_id)
        
        logger.info(f"Label added: {label_id} for node {node_id} ({label_type.value})")
        
        return label_id
    
    def add_labels_from_fimi_case(
        self,
        case_id: str,
        node_ids: List[str],
        node_type: str = "user"
    ):
        """
        FIMI 사례에서 레이블 추가
        
        Args:
            case_id: FIMI 사례 ID
            node_ids: 레이블링할 노드 ID 리스트
            node_type: 노드 타입
        """
        if case_id not in self.fimi_cases:
            logger.warning(f"Unknown FIMI case: {case_id}")
            return
        
        case = self.fimi_cases[case_id]
        
        for node_id in node_ids:
            self.add_label(
                node_id=node_id,
                node_type=node_type,
                label_type=LabelType.CAMPAIGN,
                label_source=LabelSource.FIMI_CASE,
                confidence=0.9,  # FIMI 사례 기반은 높은 신뢰도
                case_reference=case_id,
                notes=f"From FIMI case: {case.case_name}"
            )
        
        # 사례에 노드 ID 추가
        case.node_ids.extend(node_ids)
        
        logger.info(f"Added {len(node_ids)} labels from FIMI case: {case_id}")
    
    def get_label(self, node_id: str) -> Optional[Label]:
        """노드의 레이블 조회 (가장 최근 것)"""
        label_ids = self.node_labels.get(node_id, [])
        if not label_ids:
            return None
        
        # 가장 최근 레이블
        labels = [self.labels[lid] for lid in label_ids]
        return max(labels, key=lambda l: l.labeled_at)
    
    def get_all_labels(self, node_id: str) -> List[Label]:
        """노드의 모든 레이블 조회"""
        label_ids = self.node_labels.get(node_id, [])
        return [self.labels[lid] for lid in label_ids]
    
    def get_labels_by_type(self, label_type: LabelType) -> List[Label]:
        """타입별 레이블 조회"""
        return [l for l in self.labels.values() if l.label_type == label_type]
    
    def get_campaign_labels(self) -> List[Label]:
        """캠페인 레이블만 조회"""
        return self.get_labels_by_type(LabelType.CAMPAIGN)
    
    def get_normal_labels(self) -> List[Label]:
        """정상 활동 레이블만 조회"""
        return self.get_labels_by_type(LabelType.NORMAL)
    
    def load_labels(self, filepath: str):
        """레이블 파일 로드"""
        if not Path(filepath).exists():
            logger.warning(f"Labels file not found: {filepath}")
            return
        
        with open(filepath, "r", encoding="utf-8") as f:
            data = json.load(f)
        
        for label_data in data:
            label = Label(
                label_id=label_data["label_id"],
                node_id=label_data["node_id"],
                node_type=label_data["node_type"],
                label_type=LabelType(label_data["label_type"]),
                label_source=LabelSource(label_data["label_source"]),
                confidence=label_data.get("confidence", 1.0),
                campaign_id=label_data.get("campaign_id"),
                case_reference=label_data.get("case_reference"),
                notes=label_data.get("notes"),
                labeled_by=label_data.get("labeled_by"),
                labeled_at=datetime.fromisoformat(label_data["labeled_at"])
            )
            
            self.labels[label.label_id] = label
            
            if label.node_id not in self.node_labels:
                self.node_labels[label.node_id] = []
            self.node_labels[label.node_id].append(label.label_id)
        
        logger.info(f"Loaded {len(data)} labels from {filepath}")
    
    def save_labels(self, filepath: str):
        """레이블 저장"""
        data = [label.to_dict() for label in self.labels.values()]
        
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        
        logger.info(f"Saved {len(data)} labels to {filepath}")
    
    def export_for_training(
        self,
        output_file: str,
        node_type: str = "user"
    ):
        """
        학습용 레이블 내보내기
        
        Args:
            output_file: 출력 파일 경로
            node_type: 노드 타입 필터
        """
        training_data = []
        
        for label in self.labels.values():
            if label.node_type != node_type:
                continue
            
            # 학습용 형식: {node_id: label}
            training_data.append({
                "node_id": label.node_id,
                "label": 1 if label.label_type == LabelType.CAMPAIGN else 0,
                "confidence": label.confidence,
                "source": label.label_source.value
            })
        
        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(training_data, f, ensure_ascii=False, indent=2)
        
        logger.info(f"Exported {len(training_data)} labels for training to {output_file}")
    
    def get_statistics(self) -> dict:
        """통계 반환"""
        total = len(self.labels)
        campaign_count = len(self.get_campaign_labels())
        normal_count = len(self.get_normal_labels())
        
        by_source = {}
        for label in self.labels.values():
            source = label.label_source.value
            by_source[source] = by_source.get(source, 0) + 1
        
        return {
            "total_labels": total,
            "campaign_labels": campaign_count,
            "normal_labels": normal_count,
            "unknown_labels": total - campaign_count - normal_count,
            "by_source": by_source,
            "fimi_cases": len(self.fimi_cases)
        }


# 모듈 테스트용
if __name__ == "__main__":
    tool = LabelingTool()
    
    # 테스트: FIMI 사례에서 레이블 추가
    tool.add_labels_from_fimi_case(
        "US_2016_election",
        ["user_001", "user_002", "user_003"],
        "user"
    )
    
    # 테스트: 수동 레이블 추가
    tool.add_label(
        node_id="user_004",
        node_type="user",
        label_type=LabelType.NORMAL,
        label_source=LabelSource.MANUAL,
        notes="정상 사용자 활동 확인"
    )
    
    print("Labeling Tool Test:")
    print("=" * 60)
    print(tool.get_statistics())
    print(f"\nCampaign labels: {len(tool.get_campaign_labels())}")
    print(f"Normal labels: {len(tool.get_normal_labels())}")
