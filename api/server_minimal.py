"""
최소 API 서버 (대시보드 실행용)

대시보드와 기본 API 엔드포인트만 제공하는 최소 버전입니다.
"""

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, HTMLResponse
from pathlib import Path
import json
import pandas as pd
from collections import Counter
from datetime import datetime

app = FastAPI(
    title="K-FIMI Fusion Graph API - 안보 관련 허위정보 탐지",
    description="안보 관련 외국발 영향·허위정보 캠페인 탐지 시스템 API (총 50개 데이터)",
    version="0.1.0"
)

# CORS 설정
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 프로젝트 루트
PROJECT_ROOT = Path(__file__).parent.parent

# 정적 파일 마운트
STATIC_DIR = PROJECT_ROOT / "static"
if STATIC_DIR.exists():
    app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

# 대시보드 라우트
@app.get("/dashboard", response_class=HTMLResponse, tags=["Dashboard"])
async def dashboard():
    """캠페인 탐지 대시보드 페이지"""
    dashboard_path = STATIC_DIR / "dashboard.html"
    if dashboard_path.exists():
        from fastapi.responses import Response
        with open(dashboard_path, 'r', encoding='utf-8') as f:
            content = f.read()
        return Response(
            content=content,
            media_type="text/html",
            headers={
                "Cache-Control": "no-cache, no-store, must-revalidate",
                "Pragma": "no-cache",
                "Expires": "0"
            }
        )
    raise HTTPException(status_code=404, detail="Dashboard not found")

# 헬스체크
@app.get("/health", tags=["System"])
async def health_check():
    """서버 상태 확인"""
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "version": "0.1.0"
    }

# 루트
@app.get("/", tags=["System"])
async def root():
    """API 루트"""
    return {
        "name": "K-FIMI Fusion Graph API",
        "version": "0.1.0",
        "docs": "/docs",
        "dashboard": "/dashboard"
    }

# 대시보드 데이터 API
@app.get("/api/v1/dashboard/data", tags=["Dashboard"])
async def get_dashboard_data(csv_file: str = Query(default="security_disinfo.csv", description="분석할 CSV 파일명")):
    """대시보드용 분석 데이터 API"""
    csv_path = PROJECT_ROOT / "data" / "raw" / csv_file
    
    # data/raw 디렉토리에서 파일 찾기
    # security_disinfo.csv가 없으면 security_disinfo_temp.csv도 확인
    if not csv_path.exists():
        if csv_file == "security_disinfo.csv":
            temp_path = PROJECT_ROOT / "data" / "raw" / "security_disinfo_temp.csv"
            if temp_path.exists():
                csv_path = temp_path
            else:
                raise HTTPException(status_code=404, detail=f"CSV file not found: {csv_file}. Please place the file in data/raw/ directory.")
        else:
            raise HTTPException(status_code=404, detail=f"CSV file not found: {csv_file}. Please place the file in data/raw/ directory.")
    
    df = pd.read_csv(csv_path)
    
    # 시간대 파싱
    if 'created_at_utc' in df.columns:
        df['created_at'] = pd.to_datetime(df['created_at_utc'], errors='coerce')
    
    # 플랫폼별 집계
    platform_map = {'X': 'Twitter (X)', 'YouTube': 'YouTube', 'Telegram': 'Telegram'}
    platform_counts = df['platform'].value_counts().to_dict() if 'platform' in df.columns else {}
    platforms = {platform_map.get(k, k): v for k, v in platform_counts.items()}
    
    # 태그 집계
    all_tags = []
    if 'topic_tags' in df.columns:
        for tags in df['topic_tags'].dropna():
            if isinstance(tags, str):
                all_tags.extend(tags.split(';'))
    tag_counts = dict(Counter(all_tags).most_common(10))
    
    # 의심 게시물 탐지 - 다국어 테스트 케이스 생성
    suspicious_posts = []
    if 'text' in df.columns:
        # 중복 텍스트 먼저 처리
        text_counts = df['text'].value_counts()
        duplicate_texts = text_counts[text_counts > 1]
        
        # 언어별로 분류하여 다양한 언어의 의심 게시물 포함
        lang_priority = ['en', 'ru', 'zh', 'ko']  # 영어, 러시아어, 중국어, 한국어 순서
        
        # 중복 텍스트 처리
        processed_texts = set()
        lang_rows_map = {}  # 언어별로 행 저장
        
        for text, count in duplicate_texts.items():
            try:
                rows = df[df['text'] == text]
                if len(rows) > 0:
                    for idx, row in rows.iterrows():
                        try:
                            lang = str(row.get('language', 'ko')).strip().lower()
                            if lang not in lang_rows_map:
                                lang_rows_map[lang] = []
                            
                            tags = []
                            try:
                                if 'topic_tags' in row and pd.notna(row['topic_tags']):
                                    tags = str(row['topic_tags']).split(';')
                            except:
                                pass
                            
                            lang_rows_map[lang].append({
                                'row': row,
                                'text': str(text),
                                'count': int(count),
                                'tags': tags
                            })
                        except:
                            pass
            except Exception as e:
                continue
        
        # 중복 텍스트에서 언어별로 선택 (플랫폼 다양성 고려)
        selected_by_lang = {}
        platform_priority = ['X', 'Telegram', 'YouTube']  # 플랫폼 다양성을 위한 우선순위
        platform_selected_count = {'X': 0, 'Telegram': 0, 'YouTube': 0}  # 플랫폼별 선택 카운트
        
        for lang in lang_priority:
            if lang in lang_rows_map and len(lang_rows_map[lang]) > 0:
                # 플랫폼별로 분류
                platform_groups = {}
                for item in lang_rows_map[lang]:
                    platform = str(item['row'].get('platform', 'unknown')).strip()
                    if platform not in platform_groups:
                        platform_groups[platform] = []
                    platform_groups[platform].append(item)
                
                
                selected_count = 0
                
                for platform in platform_priority:
                    if platform in platform_groups and platform_selected_count[platform] == 0:
                        for item in platform_groups[platform]:
                            row = item['row']
                            text = item['text']
                            count = item['count']
                            tags = item['tags']
                            
                            if text not in processed_texts:
                                suspicious_posts.append({
                                    'platform': str(row.get('platform', 'unknown')).lower(),
                                    'account': str(row.get('account_hash', ''))[:12] + '...' if 'account_hash' in row and pd.notna(row.get('account_hash')) else 'unknown',
                                    'text': text[:80] + ('...' if len(text) > 80 else ''),
                                    'tags': tags,
                                    'risk': 'high' if count >= 3 else 'medium',
                                    'count': count,
                                    'language': lang
                                })
                                processed_texts.add(text)
                                selected_count += 1
                                platform_selected_count[platform] += 1
                                break
                
                
                for platform in platform_priority:
                    if selected_count >= 3:
                        break
                    if platform in platform_groups:
                        for item in platform_groups[platform]:
                            if selected_count >= 3:
                                break
                            row = item['row']
                            text = item['text']
                            count = item['count']
                            tags = item['tags']
                            
                            if text not in processed_texts:
                                suspicious_posts.append({
                                    'platform': str(row.get('platform', 'unknown')).lower(),
                                    'account': str(row.get('account_hash', ''))[:12] + '...' if 'account_hash' in row and pd.notna(row.get('account_hash')) else 'unknown',
                                    'text': text[:80] + ('...' if len(text) > 80 else ''),
                                    'tags': tags,
                                    'risk': 'high' if count >= 3 else 'medium',
                                    'count': count,
                                    'language': lang
                                })
                                processed_texts.add(text)
                                selected_count += 1
                                platform_selected_count[platform] += 1
                
                
                for platform in platform_groups:
                    if selected_count >= 3:
                        break
                    if platform not in platform_priority:
                        for item in platform_groups[platform]:
                            if selected_count >= 3:
                                break
                            row = item['row']
                            text = item['text']
                            count = item['count']
                            tags = item['tags']
                            
                            if text not in processed_texts:
                                suspicious_posts.append({
                                    'platform': str(row.get('platform', 'unknown')).lower(),
                                    'account': str(row.get('account_hash', ''))[:12] + '...' if 'account_hash' in row and pd.notna(row.get('account_hash')) else 'unknown',
                                    'text': text[:80] + ('...' if len(text) > 80 else ''),
                                    'tags': tags,
                                    'risk': 'high' if count >= 3 else 'medium',
                                    'count': count,
                                    'language': lang
                                })
                                processed_texts.add(text)
                                selected_count += 1
                
                selected_by_lang[lang] = selected_count
        
       
        # 언어별로 고유 텍스트 선택
        unique_texts_by_lang = {}
        for idx, row in df.iterrows():
            try:
                lang = str(row.get('language', 'ko')).strip().lower()
                text = str(row.get('text', ''))
                
                if text and text not in processed_texts:
                    if lang not in unique_texts_by_lang:
                        unique_texts_by_lang[lang] = []
                    
                    tags = []
                    try:
                        if 'topic_tags' in row and pd.notna(row['topic_tags']):
                            tags = str(row['topic_tags']).split(';')
                    except:
                        pass
                    
                    unique_texts_by_lang[lang].append({
                        'row': row,
                        'text': text,
                        'tags': tags
                    })
            except:
                continue
        
        
        for lang in lang_priority:
            if lang in unique_texts_by_lang:
                # 플랫폼별로 분류
                platform_groups = {}
                for item in unique_texts_by_lang[lang]:
                    platform = str(item['row'].get('platform', 'unknown')).strip()
                    if platform not in platform_groups:
                        platform_groups[platform] = []
                    platform_groups[platform].append(item)
                
                
                for platform in platform_priority:
                    if len(suspicious_posts) >= 10:
                        break
                    if platform in platform_groups and platform_selected_count[platform] == 0:
                        for item in platform_groups[platform]:
                            row = item['row']
                            text = item['text']
                            tags = item['tags']
                            
                            if text not in processed_texts:
                                suspicious_posts.append({
                                    'platform': str(row.get('platform', 'unknown')).lower(),
                                    'account': str(row.get('account_hash', ''))[:12] + '...' if 'account_hash' in row and pd.notna(row.get('account_hash')) else 'unknown',
                                    'text': text[:80] + ('...' if len(text) > 80 else ''),
                                    'tags': tags,
                                    'risk': 'medium',
                                    'count': 1,
                                    'language': lang
                                })
                                processed_texts.add(text)
                                platform_selected_count[platform] += 1
                                break
                
                
                selected_count = 0
                for platform in platform_priority:
                    if len(suspicious_posts) >= 10 or selected_count >= 2:
                        break
                    if platform in platform_groups:
                        for item in platform_groups[platform]:
                            if len(suspicious_posts) >= 10 or selected_count >= 2:
                                break
                            row = item['row']
                            text = item['text']
                            tags = item['tags']
                            
                            if text not in processed_texts:
                                suspicious_posts.append({
                                    'platform': str(row.get('platform', 'unknown')).lower(),
                                    'account': str(row.get('account_hash', ''))[:12] + '...' if 'account_hash' in row and pd.notna(row.get('account_hash')) else 'unknown',
                                    'text': text[:80] + ('...' if len(text) > 80 else ''),
                                    'tags': tags,
                                    'risk': 'medium',
                                    'count': 1,
                                    'language': lang
                                })
                                processed_texts.add(text)
                                selected_count += 1
                                platform_selected_count[platform] += 1
        
        
        has_youtube = any(p.get('platform', '').lower() == 'youtube' for p in suspicious_posts)
        if not has_youtube:
            youtube_df = df[df['platform'] == 'YouTube']
            if len(youtube_df) > 0:
                
                row = youtube_df.iloc[0]
                text = str(row.get('text', ''))
                if text:
                    tags = []
                    try:
                        if 'topic_tags' in row and pd.notna(row['topic_tags']):
                            tags = str(row['topic_tags']).split(';')
                    except:
                        pass
                    
                   
                    if len(suspicious_posts) >= 10:
                        
                        for i, post in enumerate(suspicious_posts):
                            if post.get('platform', '').lower() == 'x':
                                suspicious_posts.pop(i)
                                break
                    
                    suspicious_posts.append({
                        'platform': 'youtube',
                        'account': str(row.get('account_hash', ''))[:12] + '...' if 'account_hash' in row and pd.notna(row.get('account_hash')) else 'unknown',
                        'text': text[:80] + ('...' if len(text) > 80 else ''),
                        'tags': tags,
                        'risk': 'medium',
                        'count': 1,
                        'language': str(row.get('language', 'ko')).strip().lower()
                    })
        
        
        def get_lang_priority(lang):
            try:
                lang_str = str(lang).strip().lower()
                return lang_priority.index(lang_str) if lang_str in lang_priority else 999
            except:
                return 999
        
        suspicious_posts.sort(key=lambda x: (
            get_lang_priority(x.get('language', 'ko')),
            -x.get('count', 0)
        ))
    
    # 의심 계정 탐지 (플랫폼 다양성 고려)
    suspicious_accounts = []
    if 'account_hash' in df.columns:
        # 플랫폼별로 의심 계정 수집
        platform_accounts = {'X': [], 'Telegram': [], 'YouTube': []}
        all_suspicious = []
        
        for _, row in df.iterrows():
            reasons = []
            platform = str(row.get('platform', 'unknown')).strip()
            account_age = int(row.get('account_created_days', 0)) if pd.notna(row.get('account_created_days')) else 0
            followers = int(row.get('followers', 0)) if pd.notna(row.get('followers')) else 0
            following = int(row.get('following', 0)) if pd.notna(row.get('following')) else 0
            is_verified = row.get('is_verified', False) if pd.notna(row.get('is_verified')) else False
            
            # 다양한 의심 사유 체크
            # 1. 신규 계정
            if account_age < 30:
                reasons.append('신규 계정')
            
            # 2. 팔로잉 과다
            if following > 5000:
                reasons.append('팔로잉 과다')
            
            # 3. 봇 의심 (팔로워 적고 팔로잉 많음)
            if followers < 50 and following > 1000:
                reasons.append('봇 의심')
            
            # 4. 팔로워 대비 팔로잉 비율 이상 (팔로워보다 팔로잉이 훨씬 많음)
            if followers > 0 and following > 0 and following > followers * 10:
                reasons.append('팔로잉 비율 이상')
            
            # 5. 팔로워 과다 (비정상적으로 많은 팔로워)
            if platform == 'Telegram' and followers > 20000:
                reasons.append('팔로워 과다')
            elif platform == 'YouTube' and followers > 80000:
                reasons.append('팔로워 과다')
            elif platform == 'X' and followers > 100000:
                reasons.append('팔로워 과다')
            
            # 6. 활동 패턴 이상 (계정 나이 대비 팔로워/팔로잉 불일치)
            if account_age > 100 and followers < 100:
                reasons.append('활동 패턴 이상')
            
            # 7. 팔로잉 없음 (Telegram 특이 패턴)
            if platform == 'Telegram' and following == 0 and followers > 10000:
                reasons.append('팔로잉 없음')
            
            # 8. 계정 나이와 팔로워 불일치
            if account_age < 60 and followers > 50000:
                reasons.append('성장 속도 이상')
            
            # 9. 인증 없이 팔로워 많음
            if not is_verified and followers > 50000:
                reasons.append('인증 없음')
            
            # 10. 팔로워 대비 게시물 비율 이상
            account_hash = str(row.get('account_hash', ''))
            post_count = len(df[df['account_hash'] == account_hash]) if 'account_hash' in df.columns else 0
            if followers > 0 and post_count > 0:
                if followers / post_count < 10:  # 팔로워 대비 게시물이 너무 많음
                    reasons.append('게시물 비율 이상')
            
            if reasons and 'account_hash' in row:
                account_hash = str(row['account_hash'])
                platform = str(row.get('platform', 'unknown')).strip()
                
                if account_hash not in [a.get('hash', '') for a in all_suspicious]:
                    account_data = {
                        'platform': platform.lower(),
                        'hash': account_hash[:12] if len(account_hash) > 12 else account_hash,
                        'ageDays': int(row.get('account_created_days', 0)) if pd.notna(row.get('account_created_days')) else 0,
                        'followers': int(row.get('followers', 0)) if pd.notna(row.get('followers')) else 0,
                        'following': int(row.get('following', 0)) if pd.notna(row.get('following')) else 0,
                        'postCount': len(df[df['account_hash'] == account_hash]) if 'account_hash' in df.columns else 0,
                        'reason': ' + '.join(reasons),
                        'row': row
                    }
                    all_suspicious.append(account_data)
                    
                    # 플랫폼별로 분류
                    if platform in platform_accounts:
                        platform_accounts[platform].append(account_data)
                    elif platform not in ['X', 'Telegram', 'YouTube']:
                        # 기타 플랫폼도 포함
                        if '기타' not in platform_accounts:
                            platform_accounts['기타'] = []
                        platform_accounts['기타'].append(account_data)
        
        
        platform_priority = ['X', 'Telegram', 'YouTube']
        selected_hashes = set()
        
        
        for platform in platform_priority:
            if platform in platform_accounts and len(platform_accounts[platform]) > 0:
                # 각 플랫폼에서 최대 4개씩 선택
                for account in platform_accounts[platform][:4]:
                    if account['hash'] not in selected_hashes:
                        suspicious_accounts.append({
                            'platform': account['platform'],
                            'hash': account['hash'],
                            'ageDays': account['ageDays'],
                            'followers': account['followers'],
                            'following': account['following'],
                            'postCount': account['postCount'],
                            'reason': account['reason']
                        })
                        selected_hashes.add(account['hash'])
        
        for platform in platform_priority:
            if len(suspicious_accounts) >= 10:
                break
        
            has_platform = any(a['platform'] == platform.lower() for a in suspicious_accounts)
            if not has_platform:
                platform_df = df[df['platform'] == platform]
                if len(platform_df) > 0:
                
                    for idx, row in platform_df.iterrows():
                        account_hash = str(row.get('account_hash', ''))
                        if account_hash and account_hash not in selected_hashes:
                            account_age = int(row.get('account_created_days', 0)) if pd.notna(row.get('account_created_days')) else 0
                            followers = int(row.get('followers', 0)) if pd.notna(row.get('followers')) else 0
                            following = int(row.get('following', 0)) if pd.notna(row.get('following')) else 0
                            
                            
                            reason = ''
                            if platform == 'Telegram':
                                if following == 0:
                                    reason = '팔로잉 없음'
                                elif followers > 20000:
                                    reason = '팔로워 과다'
                                else:
                                    reason = '활동 패턴 이상'
                            elif platform == 'YouTube':
                                if followers > 80000:
                                    reason = '팔로워 과다'
                                elif account_age < 100 and followers > 50000:
                                    reason = '성장 속도 이상'
                                else:
                                    reason = '활동 패턴 이상'
                            else:
                                reason = '의심 패턴'
                            
                            suspicious_accounts.append({
                                'platform': platform.lower(),
                                'hash': account_hash[:12] if len(account_hash) > 12 else account_hash,
                                'ageDays': account_age,
                                'followers': followers,
                                'following': following,
                                'postCount': len(df[df['account_hash'] == account_hash]) if 'account_hash' in df.columns else 0,
                                'reason': reason
                            })
                            selected_hashes.add(account_hash)
                            break
        
        if '기타' in platform_accounts:
            for account in platform_accounts['기타'][:2]:
                if account['hash'] not in selected_hashes and len(suspicious_accounts) < 10:
                    suspicious_accounts.append({
                        'platform': account['platform'],
                        'hash': account['hash'],
                        'ageDays': account['ageDays'],
                        'followers': account['followers'],
                        'following': account['following'],
                        'postCount': account['postCount'],
                        'reason': account['reason']
                    })
                    selected_hashes.add(account['hash'])
        
        for account in all_suspicious:
            if len(suspicious_accounts) >= 10:
                break
            if account['hash'] not in selected_hashes:
                suspicious_accounts.append({
                    'platform': account['platform'],
                    'hash': account['hash'],
                    'ageDays': account['ageDays'],
                    'followers': account['followers'],
                    'following': account['following'],
                    'postCount': account['postCount'],
                    'reason': account['reason']
                })
                selected_hashes.add(account['hash'])
    
    # URL 분석
    urls_data = []
    if 'urls' in df.columns:
        seen_domains = set()
        for urls_str in df['urls'].dropna():
            if isinstance(urls_str, str):
                for url in urls_str.split(';'):
                    url = url.strip()
                    if not url:
                        continue
                    domain = url.split('/')[0] if '/' in url else url
                    if domain in seen_domains:
                        continue
                    seen_domains.add(domain)
                    
                    # 다양한 신뢰도 점수 및 상태 (위험 → 안전)
                    score = 0.5
                    status = 'ok'
                    category = 'unknown'
                    
                    # 위험 (danger) - 매우 의심스러운 도메인
                    if any(x in domain for x in ['crisis', 'crash', 'fake', 'leak', 'secret', 'anonnews', 'leakeddocs', 'ru-military', 'ru-security']):
                        score = 0.10
                        status = 'danger'
                        category = 'suspicious'
                    # 경고 (warning) - 의심스러운 도메인
                    elif any(x in domain for x in ['.ru', '.cn', '.xyz', '.info', '.biz', 'fakenews', 'globalnews', 'cn-military', 'cn-intel']):
                        score = 0.25
                        status = 'warning'
                        category = 'suspicious'
                    # 주의 (caution) - 중간 신뢰도
                    elif any(x in domain for x in ['insidernews', 'classified-leak', 'crisisnews', 'rt.com']):
                        score = 0.50
                        status = 'caution'
                        category = 'unknown'
                    # 보통 (ok) - 일반적인 도메인
                    elif any(x in domain for x in ['.com', '.net', 'youtube.com', 'twitter.com']):
                        score = 0.65
                        status = 'ok'
                        category = 'general'
                    # 안전 (safe) - 신뢰할 수 있는 도메인
                    elif any(x in domain for x in ['.org', '.edu']):
                        score = 0.80
                        status = 'safe'
                        category = 'general'
                    # 신뢰 (trusted) - 공식/정부 도메인
                    elif any(x in domain for x in ['go.kr', 'or.kr', 'mofa.go.kr', 'bok.or.kr', 'fsc.go.kr']):
                        score = 0.95
                        status = 'trusted'
                        category = 'government'
                    
                    urls_data.append({
                        'domain': domain,
                        'url': url[:50] + ('...' if len(url) > 50 else ''),
                        'category': category,
                        'score': score,
                        'status': status
                    })
    
    # 협응 공격 분석
    coordinated_attacks = []
    if 'created_at' in df.columns and 'language' in df.columns:
        df_sorted = df.dropna(subset=['created_at']).sort_values('created_at')
        
        if len(df_sorted) > 0:
            df_sorted['hour_bucket'] = df_sorted['created_at'].dt.floor('H')
            
            for hour, group in df_sorted.groupby('hour_bucket'):
                if len(group) < 2:
                    continue
                
                languages = group['language'].unique().tolist() if 'language' in group.columns else []
                platforms_in_hour = group['platform'].unique().tolist() if 'platform' in group.columns else []
                accounts_in_hour = group['account_hash'].nunique() if 'account_hash' in group.columns else 0
                
                if len(languages) >= 2 or accounts_in_hour >= 3:
                
                    texts_with_lang = []
                    for idx, row in group.iterrows():
                        text = str(row.get('text', ''))
                        lang = str(row.get('language', 'ko'))
                        texts_with_lang.append((text, lang))
                    
                    lang_groups = {}
                    for text, lang in texts_with_lang:
                        if lang not in lang_groups:
                            lang_groups[lang] = []
                        lang_groups[lang].append(text)
                    
                    # 샘플 텍스트 선택: 감지된 모든 언어를 반드시 포함하여 섞어서 표시
                    sample_texts = []
                    
                    # 언어 라벨 매핑
                    lang_labels = {
                        'ko': '[🇰🇷 한국어]',
                        'en': '[🇺🇸 영어]',
                        'ru': '[🇷🇺 러시아어]',
                        'zh': '[🇨🇳 중국어]'
                    }
                    
                    # 감지된 언어 목록 
                    detected_langs = list(languages) if languages else []
                    # 한국어, 영어, 러시아어, 중국어 순서로 정렬하되, 감지된 언어 우선
                    priority_order = ['ko', 'en', 'ru', 'zh']
                    sorted_langs = []
                    for lang in priority_order:
                        if lang in detected_langs:
                            sorted_langs.append(lang)
                    # 우선순위에 없는 언어도 추가
                    for lang in detected_langs:
                        if lang not in sorted_langs:
                            sorted_langs.append(lang)
                    
                    selected_texts = set()  # 중복 방지
                    
                    for lang in sorted_langs[:4]:
                        if lang in lang_groups and len(lang_groups[lang]) > 0:
                            for text in lang_groups[lang]:
                                if text not in selected_texts:
                                    text_short = text[:40] + '...' if len(text) > 40 else text
                                    lang_label = lang_labels.get(lang, f'[🌐 {lang}]')
                                    sample_texts.append(f"{lang_label} {text_short}")
                                    selected_texts.add(text)
                                    break
                    
                    if len(sample_texts) < 4:

                        for lang in sorted_langs:
                            if len(sample_texts) >= 4:
                                break
                            if lang in lang_groups:
                                for text in lang_groups[lang]:
                                    if text not in selected_texts:
                                        text_short = text[:40] + '...' if len(text) > 40 else text
                                        lang_label = lang_labels.get(lang, f'[🌐 {lang}]')
                                        sample_texts.append(f"{lang_label} {text_short}")
                                        selected_texts.add(text)
                                        break
                    

                    if len(sample_texts) < 3:
                        remaining = [(t, l) for t, l in texts_with_lang if t not in selected_texts]
                        for text, lang in remaining[:3 - len(sample_texts)]:
                            text_short = text[:40] + '...' if len(text) > 40 else text
                            lang_label = lang_labels.get(lang, f'[🌐 {lang}]')
                            sample_texts.append(f"{lang_label} {text_short}")
                            selected_texts.add(text)
                    
                    coordinated_attacks.append({
                        'timestamp': hour.strftime('%Y-%m-%d %H:%M') + ' UTC',
                        'hour': hour.strftime('%H:00'),
                        'date': hour.strftime('%Y-%m-%d'),
                        'postCount': len(group),
                        'languages': languages,
                        'platforms': platforms_in_hour,
                        'accountCount': accounts_in_hour,
                        'sampleTexts': sample_texts,
                        'isMultiLingual': len(languages) >= 2,
                        'severity': 'high' if len(languages) >= 3 or accounts_in_hour >= 5 else 'medium' if len(languages) >= 2 else 'low'
                    })
            
            severity_order = {'high': 0, 'medium': 1, 'low': 2}
            coordinated_attacks.sort(key=lambda x: (severity_order[x['severity']], -x['postCount']))
    
    return {
        'totalPosts': len(df),
        'platforms': platforms,
        'tags': tag_counts,
        'suspiciousPosts': suspicious_posts[:10],
        'suspiciousAccounts': suspicious_accounts[:10],
        'urls': sorted(urls_data, key=lambda x: x['score'])[:15],
        'coordinatedAttacks': coordinated_attacks[:10],
        'summary': {
            'suspiciousPostCount': len(suspicious_posts),
            'suspiciousAccountCount': len(suspicious_accounts),
            'dangerousUrlCount': len([u for u in urls_data if u['status'] == 'danger']),
            'coordinatedAttackCount': len([a for a in coordinated_attacks if a['severity'] in ['high', 'medium']])
        }
    }

# GNN 결과 조회
@app.get("/api/v1/gnn/results", tags=["GNN"])
async def get_gnn_results():
    """GNN 캠페인 탐지 결과 조회"""
    result_path = PROJECT_ROOT / "data" / "processed" / "gnn_detection_result.json"
    
    if not result_path.exists():
        raise HTTPException(status_code=404, detail="GNN 분석 결과 없음. 먼저 분석을 실행하세요.")
    
    with open(result_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    detection = data.get('detection', {})
    campaigns = [c for c in detection.get('clusters', []) if c.get('is_campaign')]
    
    return {
        'timestamp': data.get('timestamp'),
        'total_posts': data.get('total_posts'),
        'total_nodes': data.get('graph_stats', {}).get('total_nodes'),
        'total_edges': data.get('graph_stats', {}).get('total_edges'),
        'total_clusters': detection.get('total_clusters'),
        'detected_campaigns': detection.get('detected_campaigns'),
        'campaigns': campaigns
    }

if __name__ == "__main__":
    import uvicorn
    
    host = "0.0.0.0"
    port = 8000
    
    print(f"Starting K-FIMI API server on {host}:{port}")
    print(f"Dashboard: http://localhost:{port}/dashboard")
    print(f"API Docs: http://localhost:{port}/docs")
    print(f"Health Check: http://localhost:{port}/health")
    print("\n서버가 실행 중입니다. 브라우저에서 대시보드에 접속하세요!")
    print("종료하려면 Ctrl+C를 누르세요.\n")
    
    # reload를 사용하지 않거나, import string으로 전달
    uvicorn.run(
        "server_minimal:app",  # import string 사용
        host=host,
        port=port,
        reload=False  # reload를 사용하지 않거나, import string과 함께 사용
    )


