import asyncio
import logging
from contextlib import asynccontextmanager
from datetime import datetime

from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import JSONResponse
import structlog

from app.config import settings, create_tables, close_db_connection
from app.routers import sleep_analysis, health, llm_feedback
from app.dependencies import model_service
from app.models.response_models import ErrorResponse

# 로깅 설정
logging.basicConfig(level=getattr(logging, settings.log_level.upper()))
logger = structlog.get_logger()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """앱 생명주기 관리"""
    logger.info("🚀 NEULBO ML Server 시작 중...")
    
    try:
        # 데이터베이스 테이블 생성
        await create_tables()
        logger.info("✅ 데이터베이스 테이블 초기화 완료")
        
        # ML 모델 로딩
        await model_service.load_models()
        logger.info("✅ ML 모델 로딩 완료")
        
        logger.info("🎉 서버 초기화 완료")
        
    except Exception as e:
        logger.error(f"❌ 서버 초기화 실패: {str(e)}")
        raise
    
    yield
    
    # 종료 시 정리 작업
    logger.info("🔄 서버 종료 중...")
    
    try:
        await close_db_connection()
        logger.info("✅ 데이터베이스 연결 종료")
        
        # 모델 정리 (필요한 경우)
        await model_service.cleanup()
        logger.info("✅ 모델 서비스 정리 완료")
        
    except Exception as e:
        logger.error(f"❌ 서버 종료 중 오류: {str(e)}")
    
    logger.info("👋 서버 종료 완료")


# FastAPI 앱 초기화
app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description="수면 분석을 위한 ML 백엔드 서버",
    docs_url="/docs" if settings.debug else None,
    redoc_url="/redoc" if settings.debug else None,
    lifespan=lifespan
)

# Docker 컨테이너 환경에서는 CORS 불필요

# 신뢰할 수 있는 호스트 미들웨어 (보안)
if not settings.debug:
    app.add_middleware(
        TrustedHostMiddleware,
        allowed_hosts=["localhost", "127.0.0.1", "*.neulbo.com"]
    )


# 전역 예외 처리기
@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    """HTTP 예외 처리"""
    error_response = ErrorResponse(
        error_code=f"HTTP_{exc.status_code}",
        error_message=exc.detail,
        timestamp=datetime.utcnow(),
        request_id=getattr(request.state, "request_id", None)
    )
    return JSONResponse(
        status_code=exc.status_code,
        content=error_response.model_dump(mode='json')
    )


@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    """일반 예외 처리"""
    logger.error(f"예상치 못한 오류 발생: {str(exc)}", exc_info=True)
    
    error_response = ErrorResponse(
        error_code="INTERNAL_SERVER_ERROR",
        error_message="내부 서버 오류가 발생했습니다",
        timestamp=datetime.utcnow(),
        request_id=getattr(request.state, "request_id", None)
    )
    return JSONResponse(
        status_code=500,
        content=error_response.model_dump(mode='json')
    )


# 미들웨어: 요청 로깅 및 성능 모니터링
@app.middleware("http")
async def log_requests(request: Request, call_next):
    """요청 로깅 및 처리 시간 측정"""
    import time
    import uuid
    
    # 요청 ID 생성
    request_id = str(uuid.uuid4())
    request.state.request_id = request_id
    
    # 처리 시작 시간
    start_time = time.time()
    
    # 요청 로깅
    logger.info(
        "요청 시작",
        request_id=request_id,
        method=request.method,
        url=str(request.url),
        client_ip=request.client.host if request.client else None
    )
    
    # 요청 처리
    response = await call_next(request)
    
    # 처리 시간 계산
    process_time = time.time() - start_time
    
    # 응답 로깅
    logger.info(
        "요청 완료",
        request_id=request_id,
        status_code=response.status_code,
        process_time=f"{process_time:.3f}s"
    )
    
    # 응답 헤더에 처리 시간 추가
    response.headers["X-Process-Time"] = str(process_time)
    response.headers["X-Request-ID"] = request_id
    
    return response


# 라우터 등록
app.include_router(
    health.router,
    prefix="/api/ml/health",
    tags=["헬스체크"]
)

app.include_router(
    sleep_analysis.router,
    prefix="/api/ml/sleep",
    tags=["수면 분석"]
)

app.include_router(
    llm_feedback.router,
    prefix="/api/ml/llm",
    tags=["LLM 피드백"]
)


# 루트 엔드포인트
@app.get("/", include_in_schema=False)
async def root():
    """루트 엔드포인트"""
    return {
        "message": "NEULBO ML Server에 오신 것을 환영합니다!",
        "version": settings.app_version,
        "docs": "/docs",
        "health": "/api/ml/health/check"
    }




if __name__ == "__main__":
    import uvicorn
    
    logger.info(f"🚀 서버 시작: {settings.host}:{settings.port}")
    uvicorn.run(
        "app.main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.debug,
        log_level=settings.log_level.lower()
    )

