# K-FIMI Fusion Graph

## 프로젝트 개요

**K-FIMI (Korea Foreign Information Manipulation and Interference) Fusion Graph**는 외국발 영향·허위정보 캠페인을 탐지하기 위한 그래프 기반 AI 시스템입니다.

### 주요 기능

- **다중 플랫폼 데이터 수집**: X/Twitter, YouTube, Telegram
- **Fusion Graph 구축**: Heterogeneous Graph 기반 정보 융합 (User, Content, URL, Hashtag, Domain, Time Bucket)
- **캠페인 클러스터링**: K-Means 기반 GNN 임베딩 클러스터링
- **GNN 기반 탐지**: GraphSAGE, HGT, HAN 모델 지원 (PyTorch Geometric)
- **대시보드**: 실시간 캠페인 탐지 결과 시각화
- **REST API 서버**: FastAPI 기반 서비스

## 시스템 아키텍처

```
┌─────────────────────────────────────────────────────────────────┐
│                    Data Collection Layer                        │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐           │
│  │ Twitter  │ │ YouTube  │ │ Telegram │ │   Web    │           │
│  └────┬─────┘ └────┬─────┘ └────┬─────┘ └────┬─────┘           │
└───────┼────────────┼────────────┼────────────┼──────────────────┘
        │            │            │            │
        v            v            v            v
┌─────────────────────────────────────────────────────────────────┐
│                    Fusion Graph Builder                         │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │  Heterogeneous Graph (User, Content, URL, Hashtag, ...)  │  │
│  └──────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
        │
        v
┌─────────────────────────────────────────────────────────────────┐
│                    Analysis & Detection                         │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────────┐ │
│  │ Clustering  │  │  GNN Model  │  │  Campaign Detection     │ │
│  │  (Louvain)  │  │ (GraphSAGE) │  │  & Classification       │ │
│  └─────────────┘  └─────────────┘  └─────────────────────────┘ │
└─────────────────────────────────────────────────────────────────┘
        │
        v
┌─────────────────────────────────────────────────────────────────┐
│                    API Service Layer                            │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │              FastAPI REST Endpoints                       │  │
│  └──────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
```

## 프로젝트 구조

```
k-fimi-fusion-graph/
├── data/
│   ├── raw/              # 원본 수집 데이터 
│   ├── processed/        # 전처리된 데이터 및 GNN 탐지 결과
│   └── graphs/           # 생성된 그래프 파일 (JSON, GraphML)
├── src/
│   ├── ingest/           # 데이터 수집 모듈
│   │   ├── csv_ingest.py      # CSV 데이터 수집 (주요)
│   │   ├── twitter_ingest.py
│   │   ├── youtube_ingest.py
│   │   └── telegram_ingest.py
│   ├── graph/            # 그래프 구축 모듈
│   │   ├── fusion_graph_builder.py    # Fusion Graph 빌더
│   │   ├── hetero_graph_schema.py     # 그래프 스키마 정의
│   │   ├── clustering.py               # 클러스터링 알고리즘
│   │   └── narrative_extractor.py     # 내러티브 추출
│   ├── models/           # GNN 모델 모듈
│   │   ├── gnn_classifier.py          # GNN 분류기 (GraphSAGE, HGT, HAN)
│   │   ├── dataset_builder.py         # 데이터셋 빌더
│   │   ├── train.py                   # 모델 학습
│   │   └── inference.py               # 추론
│   ├── utils/            # 유틸리티 모듈
│   │   ├── text_embedding.py          # 텍스트 임베딩
│   │   ├── domain_scoring.py          # 도메인 신뢰도 점수
│   │   ├── preprocess.py              # 전처리
│   │   ├── keyword_sets.py            # 키워드 세트
│   │   └── template_extractor.py     # 템플릿 추출
│   ├── labeling/         # 라벨링 도구
│   ├── monitoring/       # 모니터링
│   └── reporting/        # 리포팅
├── api/
│   ├── server_minimal.py # FastAPI 서버 (대시보드 포함)
│   └── server.py         # 전체 기능 API 서버
├── scripts/
│   └── run_gnn_detection.py  # GNN 탐지 실행 스크립트
├── static/
│   └── dashboard.html    # 대시보드 HTML
├── requirements.txt
├── Dockerfile
├── Dockerfile.gpu
├── docker-compose.yml
├── DASHBOARD_GUIDE.md    # 대시보드 실행 가이드
└── README.md
```

## 설치 및 실행

### 사전 요구사항

- Python 3.11 이상
- CUDA 지원 GPU (선택사항, GNN 학습 시 권장)

### 로컬 설치

```bash
# 저장소 클론
git clone https://github.com/your-org/k-fimi-fusion-graph.git
cd k-fimi-fusion-graph

# 가상환경 생성
python3.11 -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# 의존성 설치
pip install -r requirements.txt
```


### 실행 방법

#### 1. GNN 기반 캠페인 탐지 실행

```bash
# GNN 탐지 스크립트 실행
python scripts/run_gnn_detection.py
```

이 스크립트는 다음을 수행합니다:
- CSV 데이터 로드
- Fusion Graph 구축
- GNN 모델 학습 (자기지도 학습)
- 캠페인 클러스터링 및 탐지
- 결과를 `data/processed/gnn_detection_result.json`에 저장

#### 2. 대시보드 실행

```bash
# API 서버 실행 (대시보드 포함)
python api/server_minimal.py
```

또는 uvicorn으로 실행:

```bash
python -m uvicorn api.server_minimal:app --host 0.0.0.0 --port 8000 --reload
```

서버 실행 후 브라우저에서 접속:
- **대시보드**: http://localhost:8000/dashboard
- **API 문서**: http://localhost:8000/docs
- **헬스체크**: http://localhost:8000/health

자세한 대시보드 실행 가이드는 [DASHBOARD_GUIDE.md](DASHBOARD_GUIDE.md)를 참조하세요.

### Docker 실행

```bash
# 이미지 빌드
docker build -t k-fimi-fusion-graph .

# 컨테이너 실행
docker run -d -p 8000:8000 --name k-fimi k-fimi-fusion-graph
```

GPU 지원이 필요한 경우:

```bash
# GPU Dockerfile로 빌드
docker build -f Dockerfile.gpu -t k-fimi-fusion-graph:gpu .

# GPU 컨테이너 실행
docker run -d --gpus all -p 8000:8000 --name k-fimi-gpu k-fimi-fusion-graph:gpu
```

## API 엔드포인트

### 시스템

| 엔드포인트 | 메소드 | 설명 |
|------------|--------|------|
| `/` | GET | API 루트 정보 |
| `/health` | GET | 서버 상태 확인 |
| `/dashboard` | GET | 대시보드 HTML 페이지 |

### 대시보드 데이터

| 엔드포인트 | 메소드 | 설명 |
|------------|--------|------|
| `/api/v1/dashboard/data` | GET | 대시보드용 분석 데이터 (의심 게시물, 계정, URL, 협응 공격 등) |
| `?csv_file=security_disinfo.csv` | Query | 분석할 CSV 파일명 지정 |

### GNN 탐지 결과

| 엔드포인트 | 메소드 | 설명 |
|------------|--------|------|
| `/api/v1/gnn/results` | GET | GNN 캠페인 탐지 결과 조회 |

### 상세 API 문서

API 서버 실행 후 http://localhost:8000/docs 에서 Swagger UI를 통해 모든 엔드포인트를 확인할 수 있습니다.

## 그래프 스키마

### 노드 타입

| 노드 | 설명 | 주요 속성 |
|------|------|-----------|
| `User` | 소셜 미디어 사용자 | user_id, platform, username, followers_count, following_count, verified, created_at |
| `Content` | 게시물/트윗/영상 | content_id, platform, text, author_id, created_at, engagement_score, view_count, like_count |
| `URL` | 공유된 링크 | url, domain, first_seen, title |
| `Domain` | 도메인 | domain, credibility_score, category, country |
| `Hashtag` | 해시태그 | tag, usage_count, first_seen |
| `Time Bucket` | 시간대 버킷 | time_bucket_id, timestamp, bucket_type, event_type, post_count, intensity_score |

### 엣지 타입

| 엣지 | 설명 |
|------|------|
| `User → POSTS → Content` | 사용자가 콘텐츠 게시 |
| `User → FOLLOWS → User` | 팔로우 관계 |
| `User → RETWEETS → Content` | 리트윗/공유 |
| `Content → CONTAINS_URL → URL` | 콘텐츠에 URL 포함 |
| `Content → CONTAINS_HASHTAG → Hashtag` | 콘텐츠에 해시태그 사용 |
| `Content → SIMILAR_TEXT → Content` | 텍스트 유사도 |
| `Content → SIMILAR_MEDIA → Content` | 미디어 유사도 |
| `URL → URL_BELONGS_TO → Domain` | URL이 도메인에 속함 |
| `User → ACTIVE_IN_TIME_BUCKET → Time Bucket` | 사용자의 시간대별 활동 |
| `Content → ACTIVE_IN_TIME_BUCKET → Time Bucket` | 콘텐츠의 시간대별 활동 |

## 주요 기능 상세

### 1. 데이터 수집(예시자료)


```python
from src.ingest.csv_ingest import CSVIngester

ingester = CSVIngester()
df = ingester.load_csv("data/raw/security_disinfo.csv")
posts = ingester.parse_posts(df)
```

### 2. Fusion Graph 구축

다양한 플랫폼의 데이터를 통합하여 Heterogeneous Graph를 구축합니다.

```python
from src.graph.fusion_graph_builder import FusionGraphBuilder

builder = FusionGraphBuilder()

# 사용자 추가
user_id = builder.add_user(
    platform="twitter",
    user_id="user123",
    followers_count=1000
)

# 콘텐츠 추가
content_id = builder.add_content(
    platform="twitter",
    content_id="tweet456",
    text="게시물 내용",
    author_id=user_id
)

# 그래프 저장
builder.save("sample_fusion_graph")
```

### 3. GNN 모델 학습 및 탐지

GraphSAGE, HGT, HAN 등 다양한 GNN 아키텍처를 사용하여 캠페인을 탐지합니다.

```python
from src.models.gnn_classifier import GNNClassifier, GNNType

# GraphSAGE 모델 생성
model = GNNClassifier.create(
    gnn_type=GNNType.GRAPHSAGE,
    in_channels=768,
    hidden_channels=256,
    out_channels=2,
    num_layers=3
)
```

### 4. 대시보드

실시간으로 탐지된 캠페인, 의심 계정, 협응 공격 등을 시각화합니다.

- 통계 카드
- 차트
- 의심 게시물 목록
- 의심 계정 목록
- 시간대별 협응 공격 탐지
- URL 신뢰도 분석

## 환경 변수 (선택사항)

API 키가 필요한 경우 `.env` 파일을 생성하세요:

```env
# Twitter/X API (선택사항)
TWITTER_API_KEY=your_api_key
TWITTER_API_SECRET=your_api_secret
TWITTER_ACCESS_TOKEN=your_access_token
TWITTER_ACCESS_SECRET=your_access_secret

# YouTube API (선택사항)
YOUTUBE_API_KEY=your_youtube_api_key

# Telegram API (선택사항)
TELEGRAM_API_ID=your_telegram_api_id
TELEGRAM_API_HASH=your_telegram_api_hash

# Model Settings (선택사항)
EMBEDDING_MODEL=sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2
GNN_HIDDEN_DIM=256
GNN_NUM_LAYERS=3
```

## 사용 예시

### 전체 워크플로우

```bash
# 1. 데이터 준비
# data/raw/security_disinfo.csv 파일 배치

# 2. GNN 탐지 실행
python scripts/run_gnn_detection.py

# 3. 대시보드 실행
python api/server_minimal.py

# 4. 브라우저에서 접속
# http://localhost:8000/dashboard
```

### Python 코드 예시

```python
# Fusion Graph 구축 및 GNN 탐지
from src.ingest.csv_ingest import CSVIngester
from src.graph.fusion_graph_builder import FusionGraphBuilder
from scripts.run_gnn_detection import main

# CSV 데이터 로드
ingester = CSVIngester()
df = ingester.load_csv("data/raw/security_disinfo.csv")
posts = ingester.parse_posts(df)

# Fusion Graph 구축
builder = FusionGraphBuilder()
for post in posts:
    user_id = builder.add_user(
        platform=post.platform,
        user_id=post.account_hash,
        followers_count=post.followers
    )
    content_id = builder.add_content(
        platform=post.platform,
        content_id=post.post_id,
        text=post.text,
        author_id=user_id,
        created_at=post.created_at
    )

# 그래프 저장
builder.save("detection_graph")
```

## 문제 해결

### 일반적인 문제

1. **의존성 설치 오류**
   ```bash
   # PyTorch Geometric 설치 문제 시
   pip install torch torch-geometric --index-url https://download.pytorch.org/whl/cu118
   ```

## 참고 문서

- [대시보드 실행 가이드](DASHBOARD_GUIDE.md) - 대시보드 사용법 상세 가이드
- [API 문서](http://localhost:8000/docs) - 서버 실행 후 접속 가능
