# 대시보드 실행 가이드

## 빠른 시작

### 1단계: API 서버 실행

터미널에서 다음 명령어를 실행하세요:

**방법 1: 직접 실행 (권장)**
```bash
# 프로젝트 디렉토리로 이동
cd "프로젝트 경로"

# API 서버 실행
python api/server_minimal.py
```

**방법 2: uvicorn으로 실행**
```bash
# 프로젝트 디렉토리로 이동
cd "프로젝트 경로"

# API 서버 실행
python -m uvicorn api.server_minimal:app --host 0.0.0.0 --port 8000 --reload
```

**Windows PowerShell 사용 시:**
```powershell
cd "프로젝트 경로"
python api\server_minimal.py
```

### 2단계: 브라우저에서 접속

서버가 실행되면 브라우저에서 다음 URL로 접속하세요:

- **대시보드**: http://localhost:8000/dashboard
- **API 문서**: http://localhost:8000/docs
- **헬스체크**: http://localhost:8000/health

서버 실행 시 터미널에 다음 메시지가 표시됩니다:
```
Starting K-FIMI API server on 0.0.0.0:
```

## 사전 요구사항

### 필수 패키지 설치

```powershell
pip install fastapi uvicorn[standard] pydantic loguru python-dotenv pandas networkx numpy
```

## 문제 해결

### API 서버가 시작되지 않는 경우

1. **포트 충돌 확인**
   ```powershell
   netstat -ano | findstr :8000
   ```
   다른 프로세스가 8000 포트를 사용 중이면 종료하거나 다른 포트 사용:
   ```powershell
   python -m uvicorn api.server:app --port 8001
   ```

2. **필수 모듈 확인**
   ```powershell
   python -c "import fastapi, uvicorn, pandas; print('OK')"
   ```

3. **API 서버 파일 확인**
   `api/server.py` 파일이 손상된 경우, 최소한의 서버 코드를 사용하세요 (아래 참조)

### 대시보드가 데이터를 로드하지 못하는 경우

1. **API 엔드포인트 확인**
   브라우저 개발자 도구(F12)에서 Network 탭을 확인하세요.
   `/api/v1/dashboard/data` 요청이 404 에러를 반환하는지 확인합니다.

2. **CSV 파일 경로 확인**
   `data/raw/` 디렉토리에 CSV 파일이 있는지 확인하세요.

## 최소 API 서버 코드

`api/server.py` 파일이 손상된 경우, 다음 최소 코드로 대시보드를 실행할 수 있습니다:

```python
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pathlib import Path

app = FastAPI()

# 정적 파일 마운트
STATIC_DIR = Path(__file__).parent.parent / "static"
if STATIC_DIR.exists():
    app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

# 대시보드 라우트
@app.get("/dashboard")
async def dashboard():
    dashboard_path = STATIC_DIR / "dashboard.html"
    if dashboard_path.exists():
        return FileResponse(dashboard_path)
    return {"error": "Dashboard not found"}

# 헬스체크
@app.get("/health")
async def health():
    return {"status": "healthy"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
```

이 코드를 `api/server_minimal.py`로 저장하고 실행:

```powershell
python api/server_minimal.py
```

##  대시보드 기능

대시보드에서 확인할 수 있는 정보:

1. **통계 카드**
   - 총 게시물 수
   - 의심 게시물 수
   - 의심 계정 수
   - 위험 URL 수
   - 협응 공격 수

2. **차트**
   - 플랫폼별 게시물 분포
   - 주요 토픽 태그 분포

3. **의심 게시물 목록**
   - 플랫폼, 계정, 텍스트, 태그, 위험도, 탐지 횟수

4. **의심 계정 목록**
   - 플랫폼, 계정 해시, 계정 나이, 팔로워, 팔로잉, 게시물 수, 의심 사유

5. **시간대별 협응 공격 탐지**
   - 시간대, 게시물, 언어, 플랫폼, 계정 수, 샘플텍스트, 심각도

6. **URL 신뢰도 분석**
   - 도메인, URL, 카테고리, 신뢰도 점수, 상태

##  데이터 새로고침

대시보드에서:
- ** 새로고침** 버튼 클릭
- 또는 브라우저 새로고침 (F5)

##  CSV 파일 선택

대시보드 상단에서 분석할 CSV 파일을 선택할 수 있습니다:

##  디버깅

### 브라우저 콘솔 확인

1. 브라우저에서 F12 키를 눌러 개발자 도구 열기
2. Console 탭에서 JavaScript 오류 확인
3. Network 탭에서 API 요청 상태 확인

### 서버 로그 확인

서버를 실행한 터미널에서 오류 메시지를 확인하세요.



