# 분석관용 상세 조회 API 추가 (기존 코드에 추가)

@app.get("/api/v1/campaigns/{campaign_id}/details", tags=["Campaign Detection"])
async def get_campaign_details(campaign_id: str):
    """
    캠페인 상세 분석 정보 조회
    
    분석관이 세부 내러티브, 연관 국가, 관련 도메인, 시간적 패턴 등을 검토할 수 있는 상세 정보를 반환합니다.
    """
    result_path = PROJECT_ROOT / "data" / "processed" / "gnn_detection_result.json"
    
    if not result_path.exists():
        raise HTTPException(status_code=404, detail="Analysis results not found")
    
    with open(result_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    detection = data.get('detection', {})
    clusters = detection.get('clusters', [])
    
    # 캠페인 찾기
    campaign_cluster = None
    for cluster in clusters:
        if str(cluster.get('cluster_id', '')) == campaign_id or f"campaign_{campaign_id}" in str(cluster.get('cluster_id', '')):
            campaign_cluster = cluster
            break
    
    if not campaign_cluster:
        raise HTTPException(status_code=404, detail="Campaign not found")
    
    # 상세 정보 구성
    details = {
        "campaign_id": campaign_id,
        "basic_info": {
            "size": campaign_cluster.get('size', 0),
            "risk_score": campaign_cluster.get('risk_score', 0),
            "risk_reasons": campaign_cluster.get('risk_reasons', []),
            "avg_similarity": campaign_cluster.get('avg_similarity', 0)
        },
        "narratives": {
            "top_narratives": campaign_cluster.get('sample_contents', [])[:10],
            "narrative_count": len(campaign_cluster.get('sample_contents', []))
        },
        "platforms": campaign_cluster.get('platforms', {}),
        "node_types": campaign_cluster.get('node_types', {}),
        "accounts": {
            "total": campaign_cluster.get('num_accounts', 0),
            "suspicious_indicators": []
        },
        "temporal_pattern": {
            "activity_period": None,
            "peak_times": []
        },
        "related_entities": {
            "domains": [],
            "hashtags": [],
            "urls": []
        },
        "country_analysis": {
            "related_countries": ['KR', 'RU', 'CN'],  # 샘플
            "country_distribution": {}
        }
    }
    
    return details


@app.get("/api/v1/analytics/narrative-trends", tags=["Analytics"])
async def get_narrative_trends(
    days: int = Query(7, ge=1, le=90, description="분석 기간 (일)")
):
    """
    내러티브 트렌드 분석
    
    기간별 내러티브 출현 빈도와 트렌드를 분석합니다.
    """
    # 실제 구현에서는 데이터베이스에서 조회
    return {
        "period_days": days,
        "trends": [
            {
                "narrative_id": "alliance_breakdown",
                "narrative_text": "동맹 파기",
                "count": 50,
                "trend": "increasing",
                "change_percentage": 25.5
            },
            {
                "narrative_id": "election_fraud",
                "narrative_text": "선거 부정",
                "count": 30,
                "trend": "stable",
                "change_percentage": 2.1
            }
        ]
    }


@app.get("/api/v1/analytics/country-distribution", tags=["Analytics"])
async def get_country_distribution():
    """
    국가별 분포 분석
    
    계정 및 게시물의 국가별 분포를 분석합니다.
    """
    # 실제 구현에서는 데이터베이스에서 조회
    return {
        "distribution": [
            {
                "country_code": "KR",
                "account_count": 500,
                "post_count": 2000,
                "suspicion_ratio": 0.05
            },
            {
                "country_code": "RU",
                "account_count": 50,
                "post_count": 200,
                "suspicion_ratio": 0.35
            }
        ]
    }
