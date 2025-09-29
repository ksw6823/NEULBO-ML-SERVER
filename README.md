# NEULBO ML Server

수면 분석을 위한 FastAPI 기반 머신러닝 백엔드 서버입니다.

## 🚀 주요 기능

- **수면 단계 분석**: 가속도계와 오디오 센서 데이터를 이용한 실시간 수면 단계 예측
- **데이터 품질 검증**: 센서 데이터의 품질을 자동으로 평가하고 개선 방안 제시
- **RESTful API**: 표준 REST API를 통한 쉬운 통합
- **PostgreSQL 지원**: 안정적인 데이터 저장 및 관리
- **비동기 처리**: 고성능 비동기 데이터 처리
- **자동 문서화**: FastAPI 기반 자동 API 문서 생성

## 📋 시스템 요구사항

- Python 3.9+
- PostgreSQL 12+
- 메모리: 최소 4GB RAM
- 디스크: 최소 10GB 여유 공간

## 🛠️ 설치 및 설정

### 1. 저장소 클론

```bash
git clone <repository-url>
cd NEULBO-ML-SERVER
```

### 2. Python 가상환경 생성

```bash
python -m venv venv

# Windows
venv\Scripts\activate

# macOS/Linux
source venv/bin/activate
```

### 3. 의존성 설치

```bash
pip install -r requirements.txt
```

### 4. 환경 설정

```bash
# 환경 설정 파일 복사
cp env.example .env

# .env 파일 편집 (데이터베이스 설정 등)
notepad .env  # Windows
nano .env     # macOS/Linux
```

### 5. 데이터베이스 설정

PostgreSQL 데이터베이스를 생성하고 연결 정보를 `.env` 파일에 설정하세요:

```bash
# PostgreSQL 접속
psql -U postgres

# 데이터베이스 생성
CREATE DATABASE neulbo_db;
CREATE USER neulbo_user WITH PASSWORD 'your_password';
GRANT ALL PRIVILEGES ON DATABASE neulbo_db TO neulbo_user;
```

## 🏃‍♂️ 실행

### 개발 모드

```bash
python run_server.py
```

또는

```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### 프로덕션 모드

```bash
# .env 파일에서 DEBUG=False 설정 후
python run_server.py
```

서버가 시작되면 다음 주소에서 접근할 수 있습니다:

- **메인 페이지**: http://localhost:8000
- **API 문서**: http://localhost:8000/docs
- **헬스체크**: http://localhost:8000/api/ml/health/check

## 📚 API 사용법

### 수면 데이터 분석

```python
import requests
from datetime import datetime

# 수면 분석 요청
response = requests.post("http://localhost:8000/api/ml/sleep/analyze", json={
    "user_id": "user123",
    "recording_start": "2023-12-01T22:00:00",
    "recording_end": "2023-12-02T06:00:00",
    "accelerometer_data": [
        {
            "timestamp": "2023-12-01T22:00:00",
            "x": 0.1,
            "y": 0.2,
            "z": 9.8
        }
        # ... 더 많은 데이터
    ],
    "audio_data": [
        {
            "timestamp": "2023-12-01T22:00:00",
            "amplitude": 0.05,
            "frequency_bands": [0.1, 0.2, 0.15, 0.08, 0.05, 0.03, 0.02, 0.01]
        }
        # ... 더 많은 데이터
    ]
})

result = response.json()
print(f"분석 ID: {result['analysis_id']}")
print(f"총 수면 시간: {result['summary_statistics']['total_sleep_time']}분")
```

### 분석 결과 조회

```python
# 분석 결과 상세 조회
analysis_id = "your-analysis-id"
response = requests.get(f"http://localhost:8000/api/ml/sleep/result/{analysis_id}")
result = response.json()

# 수면 단계별 시간 출력
stats = result['summary_statistics']
print(f"REM 수면: {stats['rem_time']}분 ({stats['rem_percentage']}%)")
print(f"깊은 수면: {stats['n3_time']}분 ({stats['n3_percentage']}%)")
```

## 🏗️ 프로젝트 구조

```
NEULBO-ML-SERVER/
├── app/
│   ├── config/          # 설정 파일들
│   ├── models/          # Pydantic 모델들
│   ├── routers/         # API 라우터들
│   ├── services/        # 비즈니스 로직
│   ├── utils/           # 유틸리티 함수들
│   ├── ml_models/       # ML 모델 파일들
│   └── main.py          # FastAPI 앱
├── requirements.txt     # Python 의존성
├── run_server.py       # 서버 실행 스크립트
├── env.example         # 환경 설정 예시
└── README.md
```

## 🔧 개발 가이드

### 코드 스타일

이 프로젝트는 다음 코딩 스타일을 따릅니다:

- **Type Hints**: 모든 함수에 타입 힌트 사용
- **Async/Await**: I/O 바운드 작업에는 비동기 처리 사용
- **Pydantic**: 데이터 검증과 직렬화에 Pydantic 사용
- **Structured Logging**: structlog를 사용한 구조화된 로깅

### 새로운 API 추가

1. `app/models/` 에 요청/응답 모델 정의
2. `app/routers/` 에 라우터 구현
3. `app/services/` 에 비즈니스 로직 구현
4. `app/main.py` 에 라우터 등록

### 테스트

```bash
# 테스트 실행 (구현 예정)
pytest tests/

# 커버리지 확인
pytest --cov=app tests/
```

## 🐛 문제 해결

### 일반적인 문제들

1. **데이터베이스 연결 오류**
   ```
   해결: .env 파일의 DATABASE_URL을 확인하고 PostgreSQL이 실행 중인지 확인
   ```

2. **모델 로딩 실패**
   ```
   해결: app/ml_models/ 디렉토리에 모델 파일이 있는지 확인
   없으면 더미 모델이 자동 생성됩니다
   ```

3. **포트 충돌**
   ```
   해결: .env 파일에서 PORT 설정을 변경하거나 기존 프로세스 종료
   ```

### 로그 확인

```bash
# 서버 로그는 콘솔에 출력됩니다
# 로그 레벨 조정은 .env 파일의 LOG_LEVEL 설정
```

## 📖 API 문서

서버 실행 후 http://localhost:8000/docs 에서 Swagger UI를 통해 상세한 API 문서를 확인할 수 있습니다.

주요 엔드포인트:

- `POST /api/ml/sleep/analyze` - 수면 데이터 분석
- `GET /api/ml/sleep/result/{analysis_id}` - 분석 결과 조회
- `GET /api/ml/sleep/history/{user_id}` - 사용자 분석 이력
- `GET /api/ml/health/check` - 시스템 상태 확인

## 🤝 기여하기

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add some amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## 📄 라이선스

이 프로젝트는 MIT 라이선스 하에 배포됩니다. 자세한 내용은 `LICENSE` 파일을 참조하세요.

## 📞 지원

- 이슈 제기: [GitHub Issues](github-url/issues)
- 이메일: support@neulbo.com
- 문서: [프로젝트 위키](github-url/wiki)

---

🔥 **Happy Coding!** 🔥