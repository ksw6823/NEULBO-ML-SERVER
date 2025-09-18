from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import text
import structlog

from app.config import get_db, settings
from app.models.response_models import HealthCheckResponse
from app.models.database_models import SystemHealth, User
from app.dependencies import get_model_service
from app.services.model_service import ModelService

router = APIRouter()
logger = structlog.get_logger()


@router.get("/check", response_model=HealthCheckResponse)
async def health_check(
    db: Session = Depends(get_db),
    model_service: ModelService = Depends(get_model_service)
):
    """
    시스템 헬스체크
    
    데이터베이스, ML 모델 등 주요 구성요소의 상태를 확인합니다.
    """
    try:
        # 데이터베이스 상태 확인
        db_status = "healthy"
        try:
            # 간단한 쿼리로 데이터베이스 연결 확인
            db.execute(text("SELECT 1"))
            db.commit()
        except Exception as e:
            logger.error(f"데이터베이스 헬스체크 실패: {str(e)}")
            db_status = "unhealthy"
        
        # 모델 상태 확인
        model_status = "healthy"
        try:
            if not model_service.is_ready():
                model_status = "loading"
        except Exception as e:
            logger.error(f"모델 헬스체크 실패: {str(e)}")
            model_status = "unhealthy"
        
        # 전체 상태 결정
        overall_status = "healthy"
        if db_status != "healthy" or model_status == "unhealthy":
            overall_status = "unhealthy"
        elif model_status == "loading":
            overall_status = "starting"
        
        return HealthCheckResponse(
            status=overall_status,
            timestamp=datetime.utcnow(),
            version=settings.app_version,
            database_status=db_status,
            model_status=model_status
        )
        
    except Exception as e:
        logger.error(f"헬스체크 중 예상치 못한 오류: {str(e)}")
        raise HTTPException(status_code=500, detail="헬스체크 실패")


@router.get("/detailed")
async def detailed_health_check(
    db: Session = Depends(get_db),
    model_service: ModelService = Depends(get_model_service)
):
    """
    상세 헬스체크 정보
    
    시스템의 상세한 상태 정보를 반환합니다.
    """
    try:
        # 데이터베이스 상세 정보
        db_info = {}
        try:
            # 활성 사용자 수
            user_count = db.query(User).filter(User.is_active == True).count()
            db_info["active_users"] = user_count
            
            # 최근 시스템 헬스 데이터
            recent_health = db.query(SystemHealth).order_by(
                SystemHealth.timestamp.desc()
            ).first()
            
            if recent_health:
                db_info.update({
                    "cpu_usage": recent_health.cpu_usage,
                    "memory_usage": recent_health.memory_usage,
                    "disk_usage": recent_health.disk_usage,
                    "active_analysis_count": recent_health.active_analysis_count,
                    "last_health_check": recent_health.timestamp
                })
                
        except Exception as e:
            logger.error(f"데이터베이스 상세 정보 조회 실패: {str(e)}")
            db_info["error"] = str(e)
        
        # 모델 상세 정보
        model_info = {}
        try:
            model_info = await model_service.get_model_info()
        except Exception as e:
            logger.error(f"모델 정보 조회 실패: {str(e)}")
            model_info["error"] = str(e)
        
        return {
            "timestamp": datetime.utcnow(),
            "app_version": settings.app_version,
            "environment": "production" if not settings.debug else "development",
            "database": db_info,
            "models": model_info,
            "configuration": {
                "model_confidence_threshold": settings.model_confidence_threshold,
                "max_recording_duration": settings.max_recording_duration,
                "min_recording_duration": settings.min_recording_duration,
                "stage_interval_seconds": settings.stage_interval_seconds
            }
        }
        
    except Exception as e:
        logger.error(f"상세 헬스체크 중 오류: {str(e)}")
        raise HTTPException(status_code=500, detail="상세 헬스체크 실패")


@router.get("/metrics")
async def get_system_metrics(db: Session = Depends(get_db)):
    """
    시스템 메트릭스 조회
    
    시스템 성능 지표를 반환합니다.
    """
    try:
        # 최근 24시간의 시스템 헬스 데이터
        from sqlalchemy import desc
        from datetime import timedelta
        
        twenty_four_hours_ago = datetime.utcnow() - timedelta(hours=24)
        
        recent_metrics = db.query(SystemHealth).filter(
            SystemHealth.timestamp >= twenty_four_hours_ago
        ).order_by(desc(SystemHealth.timestamp)).limit(100).all()
        
        if not recent_metrics:
            return {
                "message": "최근 메트릭스 데이터가 없습니다",
                "timestamp": datetime.utcnow()
            }
        
        # 평균 계산
        avg_cpu = sum(m.cpu_usage for m in recent_metrics if m.cpu_usage) / len(recent_metrics)
        avg_memory = sum(m.memory_usage for m in recent_metrics if m.memory_usage) / len(recent_metrics)
        avg_disk = sum(m.disk_usage for m in recent_metrics if m.disk_usage) / len(recent_metrics)
        
        return {
            "timestamp": datetime.utcnow(),
            "period": "24hours",
            "metrics": {
                "cpu_usage": {
                    "average": round(avg_cpu, 2),
                    "current": recent_metrics[0].cpu_usage if recent_metrics else None
                },
                "memory_usage": {
                    "average": round(avg_memory, 2),
                    "current": recent_metrics[0].memory_usage if recent_metrics else None
                },
                "disk_usage": {
                    "average": round(avg_disk, 2),
                    "current": recent_metrics[0].disk_usage if recent_metrics else None
                },
                "total_data_points": len(recent_metrics)
            }
        }
        
    except Exception as e:
        logger.error(f"메트릭스 조회 중 오류: {str(e)}")
        raise HTTPException(status_code=500, detail="메트릭스 조회 실패")


@router.post("/record-metrics")
async def record_system_metrics(
    cpu_usage: float = None,
    memory_usage: float = None,
    disk_usage: float = None,
    db: Session = Depends(get_db)
):
    """
    시스템 메트릭스 기록
    
    외부 모니터링 시스템에서 메트릭스를 기록할 때 사용합니다.
    """
    try:
        health_record = SystemHealth(
            cpu_usage=cpu_usage,
            memory_usage=memory_usage,
            disk_usage=disk_usage,
            timestamp=datetime.utcnow()
        )
        
        db.add(health_record)
        db.commit()
        
        return {
            "message": "메트릭스 기록 완료",
            "timestamp": datetime.utcnow()
        }
        
    except Exception as e:
        logger.error(f"메트릭스 기록 중 오류: {str(e)}")
        db.rollback()
        raise HTTPException(status_code=500, detail="메트릭스 기록 실패")

