# ============================================
# K-FIMI Fusion Graph - Multi-stage Dockerfile
# 외국발 영향·허위정보 캠페인 탐지 시스템
# ============================================

# ============================================
# Stage 1: Builder (의존성 설치)
# ============================================
FROM python:3.11-slim AS builder

WORKDIR /build

# 빌드 의존성 설치
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    git \
    && rm -rf /var/lib/apt/lists/*

# pip 업그레이드
RUN pip install --no-cache-dir --upgrade pip wheel setuptools

# 의존성 파일 복사 및 설치
COPY requirements.txt .

# PyTorch CPU 버전 설치 (GPU 버전은 별도 Dockerfile 사용)
RUN pip install --no-cache-dir torch --index-url https://download.pytorch.org/whl/cpu

# PyG (PyTorch Geometric) 설치
RUN pip install --no-cache-dir torch-geometric

# 나머지 의존성 설치
RUN pip install --no-cache-dir -r requirements.txt

# ============================================
# Stage 2: Runtime (최종 이미지)
# ============================================
FROM python:3.11-slim AS runtime

LABEL maintainer="K-FIMI Team"
LABEL description="K-FIMI Fusion Graph - Foreign Information Manipulation Detection System"
LABEL version="0.1.0"

WORKDIR /app

# 런타임 의존성 설치
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

# 빌더에서 설치된 Python 패키지 복사
COPY --from=builder /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

# 애플리케이션 코드 복사
COPY . .

# 데이터 디렉토리 생성
RUN mkdir -p data/raw data/processed data/graphs checkpoints logs

# 비root 사용자 생성
RUN useradd -m -u 1000 appuser && \
    chown -R appuser:appuser /app

USER appuser

# 환경 변수
ENV PYTHONPATH=/app
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

# API 포트
EXPOSE 8000

# 헬스체크
HEALTHCHECK --interval=30s --timeout=10s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# 기본 명령어: API 서버 실행
CMD ["uvicorn", "api.server:app", "--host", "0.0.0.0", "--port", "8000"]


# ============================================
# GPU 버전 (NVIDIA CUDA)
# docker build -f Dockerfile.gpu -t k-fimi:gpu .
# ============================================
# FROM nvidia/cuda:12.1-cudnn8-runtime-ubuntu22.04 AS gpu-runtime
# ... (GPU 버전은 별도 파일로 관리)
