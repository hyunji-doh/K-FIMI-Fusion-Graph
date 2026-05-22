"""
리포트 생성 시스템

일/주/월 단위 자동 리포트를 생성합니다.
"""

import json
from typing import Dict, List, Optional
from dataclasses import dataclass, field, asdict
from datetime import datetime, timedelta
from pathlib import Path
from enum import Enum

from loguru import logger


class ReportPeriod(str, Enum):
    """리포트 기간"""
    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"


@dataclass
class ReportMetrics:
    """리포트 메트릭"""
    total_posts: int = 0
    total_accounts: int = 0
    suspicious_posts: int = 0
    suspicious_accounts: int = 0
    detected_campaigns: int = 0
    narrative_surges: int = 0
    coordinated_attacks: int = 0
    dangerous_urls: int = 0
    
    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class NarrativeTrend:
    """내러티브 트렌드"""
    narrative_id: str
    narrative_text: str
    count: int
    trend: str  # 'increasing', 'decreasing', 'stable'
    change_percentage: float
    
    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class DomainDistribution:
    """도메인 분포"""
    domain: str
    count: int
    credibility_score: float
    category: Optional[str] = None
    
    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class CountryDistribution:
    """국가 분포"""
    country_code: str
    account_count: int
    post_count: int
    suspicion_ratio: float
    
    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class Report:
    """리포트 데이터"""
    report_id: str
    period: ReportPeriod
    start_date: datetime
    end_date: datetime
    generated_at: datetime
    metrics: ReportMetrics
    top_narratives: List[NarrativeTrend] = field(default_factory=list)
    domain_distribution: List[DomainDistribution] = field(default_factory=list)
    country_distribution: List[CountryDistribution] = field(default_factory=list)
    alerts_issued: int = 0
    summary: str = ""
    
    def to_dict(self) -> dict:
        data = asdict(self)
        data['start_date'] = self.start_date.isoformat()
        data['end_date'] = self.end_date.isoformat()
        data['generated_at'] = self.generated_at.isoformat()
        return data


class ReportGenerator:
    """
    리포트 생성기
    
    기간별 리포트를 자동으로 생성합니다.
    """
    
    def __init__(self, output_dir: str = "data/reports"):
        """
        ReportGenerator 초기화
        
        Args:
            output_dir: 리포트 저장 디렉토리
        """
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        logger.info(f"ReportGenerator initialized. Output: {self.output_dir}")
    
    def generate_daily_report(
        self,
        date: Optional[datetime] = None,
        metrics_data: Optional[Dict] = None
    ) -> Report:
        """일일 리포트 생성"""
        if date is None:
            date = datetime.now()
        
        start_date = date.replace(hour=0, minute=0, second=0, microsecond=0)
        end_date = start_date + timedelta(days=1)
        
        metrics = ReportMetrics()
        if metrics_data:
            metrics = ReportMetrics(**metrics_data)
        
        import uuid
        report_id = f"daily_{date.strftime('%Y%m%d')}_{str(uuid.uuid4())[:8]}"
        
        report = Report(
            report_id=report_id,
            period=ReportPeriod.DAILY,
            start_date=start_date,
            end_date=end_date,
            generated_at=datetime.now(),
            metrics=metrics,
            summary=self._generate_summary(metrics, ReportPeriod.DAILY)
        )
        
        return report
    
    def generate_weekly_report(
        self,
        week_start: Optional[datetime] = None,
        metrics_data: Optional[Dict] = None
    ) -> Report:
        """주간 리포트 생성"""
        if week_start is None:
            week_start = datetime.now() - timedelta(days=datetime.now().weekday())
        
        start_date = week_start.replace(hour=0, minute=0, second=0, microsecond=0)
        end_date = start_date + timedelta(days=7)
        
        metrics = ReportMetrics()
        if metrics_data:
            metrics = ReportMetrics(**metrics_data)
        
        import uuid
        report_id = f"weekly_{start_date.strftime('%Y%m%d')}_{str(uuid.uuid4())[:8]}"
        
        report = Report(
            report_id=report_id,
            period=ReportPeriod.WEEKLY,
            start_date=start_date,
            end_date=end_date,
            generated_at=datetime.now(),
            metrics=metrics,
            summary=self._generate_summary(metrics, ReportPeriod.WEEKLY)
        )
        
        return report
    
    def generate_monthly_report(
        self,
        month: Optional[int] = None,
        year: Optional[int] = None,
        metrics_data: Optional[Dict] = None
    ) -> Report:
        """월간 리포트 생성"""
        if month is None:
            month = datetime.now().month
        if year is None:
            year = datetime.now().year
        
        start_date = datetime(year, month, 1)
        if month == 12:
            end_date = datetime(year + 1, 1, 1)
        else:
            end_date = datetime(year, month + 1, 1)
        
        metrics = ReportMetrics()
        if metrics_data:
            metrics = ReportMetrics(**metrics_data)
        
        import uuid
        report_id = f"monthly_{year}{month:02d}_{str(uuid.uuid4())[:8]}"
        
        report = Report(
            report_id=report_id,
            period=ReportPeriod.MONTHLY,
            start_date=start_date,
            end_date=end_date,
            generated_at=datetime.now(),
            metrics=metrics,
            summary=self._generate_summary(metrics, ReportPeriod.MONTHLY)
        )
        
        return report
    
    def _generate_summary(self, metrics: ReportMetrics, period: ReportPeriod) -> str:
        """리포트 요약 생성"""
        period_name = {
            ReportPeriod.DAILY: "일일",
            ReportPeriod.WEEKLY: "주간",
            ReportPeriod.MONTHLY: "월간"
        }[period]
        
        summary = f"{period_name} 리포트 요약\n\n"
        summary += f"총 게시물: {metrics.total_posts:,}개\n"
        summary += f"총 계정: {metrics.total_accounts:,}개\n"
        summary += f"의심 게시물: {metrics.suspicious_posts:,}개\n"
        summary += f"의심 계정: {metrics.suspicious_accounts:,}개\n"
        summary += f"탐지된 캠페인: {metrics.detected_campaigns}개\n"
        summary += f"내러티브 급증: {metrics.narrative_surges}건\n"
        summary += f"협응 공격: {metrics.coordinated_attacks}건\n"
        summary += f"위험 URL: {metrics.dangerous_urls}개\n"
        
        if metrics.detected_campaigns > 0:
            summary += f"\n⚠️ {metrics.detected_campaigns}개의 의심 캠페인이 탐지되었습니다."
        
        if metrics.narrative_surges > 0:
            summary += f"\n📈 {metrics.narrative_surges}건의 내러티브 급증이 감지되었습니다."
        
        return summary
    
    def save_report(self, report: Report, format: str = "json"):
        """리포트 저장"""
        if format == "json":
            filepath = self.output_dir / f"{report.report_id}.json"
            with open(filepath, "w", encoding="utf-8") as f:
                json.dump(report.to_dict(), f, ensure_ascii=False, indent=2)
        elif format == "markdown":
            filepath = self.output_dir / f"{report.report_id}.md"
            self._save_markdown(report, filepath)
        else:
            raise ValueError(f"Unsupported format: {format}")
        
        logger.info(f"Report saved: {filepath}")
    
    def _save_markdown(self, report: Report, filepath: Path):
        """마크다운 형식으로 저장"""
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(f"# {report.period.value.upper()} 리포트\n\n")
            f.write(f"**기간**: {report.start_date.strftime('%Y-%m-%d')} ~ {report.end_date.strftime('%Y-%m-%d')}\n\n")
            f.write(f"**생성일시**: {report.generated_at.strftime('%Y-%m-%d %H:%M:%S')}\n\n")
            f.write("## 요약\n\n")
            f.write(report.summary)
            f.write("\n\n")
            f.write("## 메트릭\n\n")
            f.write(f"- 총 게시물: {report.metrics.total_posts:,}개\n")
            f.write(f"- 총 계정: {report.metrics.total_accounts:,}개\n")
            f.write(f"- 의심 게시물: {report.metrics.suspicious_posts:,}개\n")
            f.write(f"- 의심 계정: {report.metrics.suspicious_accounts:,}개\n")
            f.write(f"- 탐지된 캠페인: {report.metrics.detected_campaigns}개\n")
    
    def load_report(self, report_id: str) -> Optional[Report]:
        """리포트 로드"""
        filepath = self.output_dir / f"{report_id}.json"
        
        if not filepath.exists():
            return None
        
        with open(filepath, "r", encoding="utf-8") as f:
            data = json.load(f)
        
        # 리포트 재구성
        report = Report(
            report_id=data["report_id"],
            period=ReportPeriod(data["period"]),
            start_date=datetime.fromisoformat(data["start_date"]),
            end_date=datetime.fromisoformat(data["end_date"]),
            generated_at=datetime.fromisoformat(data["generated_at"]),
            metrics=ReportMetrics(**data["metrics"]),
            summary=data.get("summary", "")
        )
        
        return report


# 모듈 테스트용
if __name__ == "__main__":
    generator = ReportGenerator()
    
    # 일일 리포트 생성
    daily_report = generator.generate_daily_report(
        metrics_data={
            "total_posts": 1000,
            "total_accounts": 500,
            "suspicious_posts": 50,
            "suspicious_accounts": 10,
            "detected_campaigns": 2
        }
    )
    
    print("Report Generator Test:")
    print("=" * 60)
    print(daily_report.summary)
    
    # 리포트 저장
    generator.save_report(daily_report, format="json")
    generator.save_report(daily_report, format="markdown")


