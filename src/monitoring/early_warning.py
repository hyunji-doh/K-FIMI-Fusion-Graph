"""
조기 경보 시스템

민감 시기 감지, 내러티브 급증 감지, 관계 기관 알림 발송 기능을 제공합니다.
"""

import json
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Set
from dataclasses import dataclass, field, asdict
from enum import Enum
from pathlib import Path

from loguru import logger


class AlertLevel(str, Enum):
    """경보 레벨"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class SensitivePeriodType(str, Enum):
    """민감 시기 타입"""
    ELECTION = "election"              # 선거 기간
    SECURITY_INCIDENT = "security_incident"  # 안보 사건
    DIPLOMATIC_EVENT = "diplomatic_event"    # 외교 이벤트
    CRISIS = "crisis"                  # 위기 상황
    CUSTOM = "custom"                  # 사용자 정의


@dataclass
class SensitivePeriod:
    """민감 시기 정의"""
    period_id: str
    period_type: SensitivePeriodType
    start_date: datetime
    end_date: datetime
    description: str
    keywords: List[str] = field(default_factory=list)
    alert_threshold: float = 0.7  # 경보 발령 임계값
    enabled: bool = True
    
    def is_active(self, current_time: Optional[datetime] = None) -> bool:
        """현재 시기가 활성화되어 있는지 확인"""
        if not self.enabled:
            return False
        
        if current_time is None:
            current_time = datetime.now()
        
        return self.start_date <= current_time <= self.end_date
    
    def to_dict(self) -> dict:
        data = asdict(self)
        data['start_date'] = self.start_date.isoformat()
        data['end_date'] = self.end_date.isoformat()
        return data


@dataclass
class NarrativeSurge:
    """내러티브 급증 정보"""
    narrative_id: str
    narrative_text: str
    baseline_count: int  # 평소 게시물 수
    current_count: int   # 현재 게시물 수
    surge_ratio: float   # 급증 비율
    time_window: str     # 시간 윈도우
    detected_at: datetime
    related_keywords: List[str] = field(default_factory=list)
    related_accounts: List[str] = field(default_factory=list)
    related_domains: List[str] = field(default_factory=list)
    
    def to_dict(self) -> dict:
        data = asdict(self)
        data['detected_at'] = self.detected_at.isoformat()
        return data


@dataclass
class Alert:
    """경보 정보"""
    alert_id: str
    alert_level: AlertLevel
    title: str
    message: str
    created_at: datetime
    sensitive_period: Optional[SensitivePeriod] = None
    narrative_surges: List[NarrativeSurge] = field(default_factory=list)
    metrics: Dict = field(default_factory=dict)
    sent_to: List[str] = field(default_factory=list)  # 발송 대상
    
    def to_dict(self) -> dict:
        data = asdict(self)
        data['created_at'] = self.created_at.isoformat()
        if self.sensitive_period:
            data['sensitive_period'] = self.sensitive_period.to_dict()
        data['narrative_surges'] = [ns.to_dict() for ns in self.narrative_surges]
        return data


class EarlyWarningSystem:
    """
    조기 경보 시스템
    
    민감 시기 감지, 내러티브 급증 감지, 관계 기관 알림 발송을 수행합니다.
    """
    
    def __init__(
        self,
        config_file: Optional[str] = None,
        alert_history_file: Optional[str] = None
    ):
        """
        EarlyWarningSystem 초기화
        
        Args:
            config_file: 설정 파일 경로 (JSON)
            alert_history_file: 경보 이력 파일 경로
        """
        self.sensitive_periods: Dict[str, SensitivePeriod] = {}
        self.alert_history: List[Alert] = []
        self.alert_history_file = alert_history_file
        
        # 알림 발송 설정
        self.notification_config = {
            "email": {
                "enabled": False,
                "recipients": []
            },
            "sms": {
                "enabled": False,
                "recipients": []
            },
            "webhook": {
                "enabled": False,
                "urls": []
            }
        }
        
        # 내러티브 급증 감지 설정
        self.surge_detection_config = {
            "baseline_window_days": 30,  # 기준 기간 (일)
            "current_window_hours": 24,   # 현재 기간 (시간)
            "surge_threshold_ratio": 2.0,  # 급증 임계 비율 (2배 이상)
            "min_count": 10  # 최소 게시물 수
        }
        
        # 설정 로드
        if config_file:
            self.load_config(config_file)
        
        # 경보 이력 로드
        if alert_history_file:
            self.load_alert_history(alert_history_file)
        
        logger.info("EarlyWarningSystem initialized")
    
    def load_config(self, filepath: str):
        """설정 파일 로드"""
        with open(filepath, "r", encoding="utf-8") as f:
            config = json.load(f)
        
        # 민감 시기 로드
        if "sensitive_periods" in config:
            for period_data in config["sensitive_periods"]:
                period = SensitivePeriod(
                    period_id=period_data["period_id"],
                    period_type=SensitivePeriodType(period_data["period_type"]),
                    start_date=datetime.fromisoformat(period_data["start_date"]),
                    end_date=datetime.fromisoformat(period_data["end_date"]),
                    description=period_data["description"],
                    keywords=period_data.get("keywords", []),
                    alert_threshold=period_data.get("alert_threshold", 0.7),
                    enabled=period_data.get("enabled", True)
                )
                self.sensitive_periods[period.period_id] = period
        
        # 알림 설정 로드
        if "notifications" in config:
            self.notification_config.update(config["notifications"])
        
        # 급증 감지 설정 로드
        if "surge_detection" in config:
            self.surge_detection_config.update(config["surge_detection"])
        
        logger.info(f"Loaded config: {len(self.sensitive_periods)} sensitive periods")
    
    def save_config(self, filepath: str):
        """설정 저장"""
        config = {
            "sensitive_periods": [p.to_dict() for p in self.sensitive_periods.values()],
            "notifications": self.notification_config,
            "surge_detection": self.surge_detection_config
        }
        
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(config, f, ensure_ascii=False, indent=2)
        
        logger.info(f"Saved config to {filepath}")
    
    def add_sensitive_period(self, period: SensitivePeriod):
        """민감 시기 추가"""
        self.sensitive_periods[period.period_id] = period
        logger.info(f"Added sensitive period: {period.period_id}")
    
    def get_active_periods(self, current_time: Optional[datetime] = None) -> List[SensitivePeriod]:
        """활성화된 민감 시기 조회"""
        if current_time is None:
            current_time = datetime.now()
        
        return [p for p in self.sensitive_periods.values() if p.is_active(current_time)]
    
    def detect_narrative_surge(
        self,
        narrative_counts: Dict[str, int],  # {narrative_id: count}
        baseline_counts: Dict[str, int]    # {narrative_id: baseline_count}
    ) -> List[NarrativeSurge]:
        """
        내러티브 급증 감지
        
        Args:
            narrative_counts: 현재 기간 내러티브별 게시물 수
            baseline_counts: 기준 기간 내러티브별 게시물 수
        
        Returns:
            급증한 내러티브 리스트
        """
        surges = []
        threshold_ratio = self.surge_detection_config["surge_threshold_ratio"]
        min_count = self.surge_detection_config["min_count"]
        
        for narrative_id, current_count in narrative_counts.items():
            baseline_count = baseline_counts.get(narrative_id, 0)
            
            # 최소 게시물 수 확인
            if current_count < min_count:
                continue
            
            # 급증 비율 계산
            if baseline_count > 0:
                surge_ratio = current_count / baseline_count
            else:
                # 기준 기간에 없었던 내러티브는 급증으로 간주
                surge_ratio = float('inf') if current_count >= min_count else 0.0
            
            # 임계값 이상이면 급증으로 판단
            if surge_ratio >= threshold_ratio:
                surge = NarrativeSurge(
                    narrative_id=narrative_id,
                    narrative_text=narrative_id,  # 실제로는 내러티브 텍스트
                    baseline_count=baseline_count,
                    current_count=current_count,
                    surge_ratio=surge_ratio,
                    time_window=f"{self.surge_detection_config['current_window_hours']}h",
                    detected_at=datetime.now()
                )
                surges.append(surge)
        
        # 급증 비율 순 정렬
        surges.sort(key=lambda x: x.surge_ratio, reverse=True)
        
        return surges
    
    def check_and_alert(
        self,
        narrative_counts: Dict[str, int],
        baseline_counts: Dict[str, int],
        current_time: Optional[datetime] = None
    ) -> Optional[Alert]:
        """
        경보 조건 확인 및 경보 발령
        
        Args:
            narrative_counts: 현재 내러티브별 게시물 수
            baseline_counts: 기준 내러티브별 게시물 수
            current_time: 현재 시간
        
        Returns:
            발령된 경보 (없으면 None)
        """
        if current_time is None:
            current_time = datetime.now()
        
        # 활성화된 민감 시기 확인
        active_periods = self.get_active_periods(current_time)
        
        # 내러티브 급증 감지
        narrative_surges = self.detect_narrative_surge(narrative_counts, baseline_counts)
        
        # 경보 레벨 결정
        alert_level = AlertLevel.LOW
        should_alert = False
        
        if active_periods and narrative_surges:
            # 민감 시기 + 내러티브 급증 = 높은 우선순위
            max_surge_ratio = max([s.surge_ratio for s in narrative_surges])
            
            if max_surge_ratio >= 5.0:
                alert_level = AlertLevel.CRITICAL
                should_alert = True
            elif max_surge_ratio >= 3.0:
                alert_level = AlertLevel.HIGH
                should_alert = True
            elif max_surge_ratio >= 2.0:
                alert_level = AlertLevel.MEDIUM
                should_alert = True
        
        elif narrative_surges:
            # 내러티브 급증만 있는 경우
            max_surge_ratio = max([s.surge_ratio for s in narrative_surges])
            if max_surge_ratio >= 3.0:
                alert_level = AlertLevel.MEDIUM
                should_alert = True
        
        if not should_alert:
            return None
        
        # 경보 생성
        import uuid
        alert_id = str(uuid.uuid4())[:8]
        
        period = active_periods[0] if active_periods else None
        
        title = f"FIMI 의심 캠페인 급증 감지"
        if period:
            title = f"[{period.description}] {title}"
        
        message = f"내러티브 급증이 감지되었습니다. "
        message += f"총 {len(narrative_surges)}개의 내러티브에서 급증이 확인되었습니다."
        
        alert = Alert(
            alert_id=alert_id,
            alert_level=alert_level,
            title=title,
            message=message,
            created_at=current_time,
            sensitive_period=period,
            narrative_surges=narrative_surges,
            metrics={
                "max_surge_ratio": max([s.surge_ratio for s in narrative_surges]),
                "total_surges": len(narrative_surges),
                "active_periods": len(active_periods)
            }
        )
        
        # 알림 발송
        self.send_alert(alert)
        
        # 이력 저장
        self.alert_history.append(alert)
        if self.alert_history_file:
            self.save_alert_history(self.alert_history_file)
        
        logger.warning(f"Alert issued: {alert_id} ({alert_level.value})")
        
        return alert
    
    def send_alert(self, alert: Alert):
        """경보 발송"""
        sent_to = []
        
        # 이메일 발송
        if self.notification_config["email"]["enabled"]:
            recipients = self.notification_config["email"]["recipients"]
            # 실제 이메일 발송 로직은 여기에 구현
            # send_email(recipients, alert.title, alert.message)
            sent_to.extend([f"email:{r}" for r in recipients])
            logger.info(f"Email alert sent to {len(recipients)} recipients")
        
        # SMS 발송
        if self.notification_config["sms"]["enabled"]:
            recipients = self.notification_config["sms"]["recipients"]
            # 실제 SMS 발송 로직은 여기에 구현
            # send_sms(recipients, alert.message)
            sent_to.extend([f"sms:{r}" for r in recipients])
            logger.info(f"SMS alert sent to {len(recipients)} recipients")
        
        # Webhook 발송
        if self.notification_config["webhook"]["enabled"]:
            urls = self.notification_config["webhook"]["urls"]
            # 실제 Webhook 발송 로직은 여기에 구현
            # for url in urls:
            #     send_webhook(url, alert.to_dict())
            sent_to.extend([f"webhook:{url}" for url in urls])
            logger.info(f"Webhook alert sent to {len(urls)} URLs")
        
        alert.sent_to = sent_to
    
    def load_alert_history(self, filepath: str):
        """경보 이력 로드"""
        if not Path(filepath).exists():
            return
        
        with open(filepath, "r", encoding="utf-8") as f:
            data = json.load(f)
        
        for alert_data in data:
            alert = Alert(
                alert_id=alert_data["alert_id"],
                alert_level=AlertLevel(alert_data["alert_level"]),
                title=alert_data["title"],
                message=alert_data["message"],
                created_at=datetime.fromisoformat(alert_data["created_at"]),
                narrative_surges=[
                    NarrativeSurge(**ns_data) for ns_data in alert_data.get("narrative_surges", [])
                ],
                metrics=alert_data.get("metrics", {}),
                sent_to=alert_data.get("sent_to", [])
            )
            self.alert_history.append(alert)
        
        logger.info(f"Loaded {len(self.alert_history)} alert history")
    
    def save_alert_history(self, filepath: str):
        """경보 이력 저장"""
        data = [alert.to_dict() for alert in self.alert_history]
        
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        
        logger.info(f"Saved {len(data)} alerts to history")
    
    def get_recent_alerts(self, hours: int = 24, level: Optional[AlertLevel] = None) -> List[Alert]:
        """최근 경보 조회"""
        cutoff_time = datetime.now() - timedelta(hours=hours)
        
        alerts = [
            alert for alert in self.alert_history
            if alert.created_at >= cutoff_time
        ]
        
        if level:
            alerts = [alert for alert in alerts if alert.alert_level == level]
        
        return sorted(alerts, key=lambda x: x.created_at, reverse=True)


# 모듈 테스트용
if __name__ == "__main__":
    # 테스트 설정
    config = {
        "sensitive_periods": [
            {
                "period_id": "test_election",
                "period_type": "election",
                "start_date": "2024-04-01T00:00:00",
                "end_date": "2024-04-15T23:59:59",
                "description": "2024년 총선",
                "keywords": ["선거", "투표", "후보"],
                "alert_threshold": 0.7
            }
        ],
        "notifications": {
            "email": {"enabled": True, "recipients": ["admin@example.com"]},
            "webhook": {"enabled": True, "urls": ["https://example.com/webhook"]}
        }
    }
    
    import tempfile
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
        json.dump(config, f, indent=2)
        config_file = f.name
    
    # 시스템 초기화
    ews = EarlyWarningSystem(config_file=config_file)
    
    # 테스트: 내러티브 급증 감지
    narrative_counts = {
        "동맹파기": 50,
        "선거부정": 30
    }
    baseline_counts = {
        "동맹파기": 10,
        "선거부정": 5
    }
    
    alert = ews.check_and_alert(narrative_counts, baseline_counts)
    if alert:
        print(f"Alert issued: {alert.alert_id}")
        print(f"Level: {alert.alert_level.value}")
        print(f"Surges: {len(alert.narrative_surges)}")
