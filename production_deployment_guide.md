# 🚀 NEULBO ML Server 프로덕션 배포 가이드

## 📋 배포 전 체크리스트

### ✅ **현재 준비 완료 사항**
- [x] FastAPI 서버 구축 완료
- [x] PostgreSQL 데이터베이스 연동
- [x] XGBoost ML 모델 통합
- [x] 수면 분석 API 완성
- [x] LLM 피드백 기능 추가
- [x] 로깅 및 모니터링 설정
- [x] 에러 핸들링 구현
- [x] API 문서 자동 생성 (FastAPI Swagger)

### 🔧 **사전 준비 필수 사항**

#### 1. **환경 설정**
```bash
# 1. 환경 변수 파일 생성
cp env.example .env

# 2. 프로덕션 설정 수정
vim .env
```

**주요 설정값:**
```env
# 데이터베이스 (프로덕션 DB 정보로 변경)
DATABASE_URL="postgresql://username:password@localhost:5432/neulbo_db"

# 보안 (반드시 변경!)
SECRET_KEY="your-production-secret-key-here"

# 서버 설정
HOST="0.0.0.0"
PORT=8000
LOG_LEVEL="INFO"

# OLLAMA LLM 서버
OLLAMA_URL="http://ollama-container:11434"  # 도커 환경
LLM_MODEL="gpt-oss:20b"
```

#### 2. **데이터베이스 마이그레이션**
```bash
# LLM 피드백 테이블 생성
python create_migration.py
```

#### 3. **OLLAMA 서버 설정**
```bash
# OLLAMA 도커 컨테이너 실행
docker run -d --name ollama-server \
  -p 11434:11434 \
  -v ollama:/root/.ollama \
  ollama/ollama

# gpt-oss:20b 모델 다운로드
docker exec -it ollama-server ollama pull gpt-oss:20b
```

#### 4. **의존성 설치**
```bash
pip install -r requirements.txt
```

## 🐳 **Docker 배포 (권장)**

### Dockerfile 생성
```dockerfile
FROM python:3.11-slim

WORKDIR /app

# 시스템 의존성 설치
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    && rm -rf /var/lib/apt/lists/*

# Python 의존성 설치
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 애플리케이션 코드 복사
COPY . .

# 포트 노출
EXPOSE 8000

# 서버 실행
CMD ["python", "-m", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

### docker-compose.yml
```yaml
version: '3.8'

services:
  ml-server:
    build: .
    ports:
      - "8000:8000"
    environment:
      - DATABASE_URL=postgresql://postgres:password@db:5432/neulbo_db
      - OLLAMA_URL=http://ollama:11434
    depends_on:
      - db
      - ollama
    volumes:
      - ./app/ml_models:/app/app/ml_models
    networks:
      - neulbo-network

  db:
    image: postgres:15
    environment:
      POSTGRES_DB: neulbo_db
      POSTGRES_USER: postgres
      POSTGRES_PASSWORD: password
    volumes:
      - postgres_data:/var/lib/postgresql/data
    ports:
      - "5432:5432"
    networks:
      - neulbo-network

  ollama:
    image: ollama/ollama
    ports:
      - "11434:11434"
    volumes:
      - ollama_data:/root/.ollama
    networks:
      - neulbo-network

volumes:
  postgres_data:
  ollama_data:

networks:
  neulbo-network:
    driver: bridge
```

### 배포 명령어
```bash
# 1. 컨테이너 빌드 및 실행
docker-compose up -d

# 2. 데이터베이스 테이블 생성
docker-compose exec ml-server python create_migration.py

# 3. OLLAMA 모델 다운로드
docker-compose exec ollama ollama pull gpt-oss:20b

# 4. 상태 확인
docker-compose ps
```

## 🔧 **직접 배포 (서버에서)**

### 1. 서버 환경 준비
```bash
# PostgreSQL 설치 및 설정
sudo apt update
sudo apt install postgresql postgresql-contrib

# 데이터베이스 생성
sudo -u postgres createdb neulbo_db
```

### 2. OLLAMA 설치
```bash
# OLLAMA 설치
curl -fsSL https://ollama.ai/install.sh | sh

# 모델 다운로드
ollama pull gpt-oss:20b
```

### 3. 애플리케이션 실행
```bash
# 프로덕션 서버 실행
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 4
```

## 🚦 **배포 후 확인사항**

### 1. **헬스체크**
```bash
# API 서버 상태
curl http://localhost:8000/api/v1/health/check

# LLM 서비스 상태  
curl http://localhost:8000/api/v1/llm/health/llm
```

### 2. **기능 테스트**
```bash
# 수면 분석 테스트
python quick_test.py

# LLM 피드백 테스트
python test_llm_feedback.py
```

### 3. **로그 모니터링**
```bash
# 실시간 로그 확인
tail -f logs/app.log

# 도커 로그 확인
docker-compose logs -f ml-server
```

## ⚠️ **주의사항**

### 보안
- [ ] `SECRET_KEY` 반드시 변경
- [ ] 데이터베이스 비밀번호 강화
- [ ] CORS 설정 확인
- [ ] 방화벽 포트 설정

### 성능
- [ ] Worker 프로세스 수 조정 (CPU 코어 수에 맞게)
- [ ] 데이터베이스 커넥션 풀 설정
- [ ] 로드밸런서 구성 (필요시)

### 모니터링
- [ ] 로그 수집 시스템 구축
- [ ] 메트릭 모니터링 설정
- [ ] 알림 시스템 구성

## 🤝 **SpringBoot 서버와 연동**

### 공유 데이터베이스 테이블 분리
```
SpringBoot 서버 담당:
- users (사용자 관리)
- 기타 앱 기능들

ML Server 담당:
- sleep_analyses (수면 분석)
- sleep_stage_intervals
- stage_probabilities  
- llm_feedbacks (LLM 피드백)
- model_info
- system_health
```

### API 통신
- SpringBoot → ML Server: 필요시 HTTP API 호출
- 공유 DB를 통한 데이터 교환 가능

## 📊 **성능 예상**

**예상 처리량:**
- 수면 분석: ~10-20 요청/분
- LLM 피드백: ~5-10 요청/분
- 동시 사용자: ~50-100명

**리소스 요구사항:**
- CPU: 4 코어 (XGBoost + LLM)
- RAM: 8GB (모델 로딩 + 처리)
- 디스크: 50GB (로그, 모델 파일)
