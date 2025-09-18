import asyncio
import uuid
from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks, Query
from sqlalchemy.orm import Session
import structlog

from app.config import get_db
from app.models.request_models import SleepAnalysisRequest
from app.models.response_models import (
    SleepAnalysisResponse, 
    SleepAnalysisHistoryResponse,
    ModelInfoResponse
)
from app.models.database_models import SleepAnalysis, User, ModelInfo
from app.services.model_service import ModelService
from app.services.preprocessor import PreprocessorService
from app.services.postprocessor import PostprocessorService
from app.dependencies import get_model_service
from app.utils.validation_utils import validate_sensor_data
from app.utils.time_series_utils import check_data_quality

router = APIRouter()
logger = structlog.get_logger()


@router.post("/analyze", response_model=SleepAnalysisResponse)
async def analyze_sleep_data(
    request: SleepAnalysisRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    model_service: ModelService = Depends(get_model_service)
):
    """
    수면 데이터 분석
    
    가속도계와 오디오 센서 데이터를 분석하여 수면 단계를 예측합니다.
    """
    try:
        # 분석 ID 생성
        analysis_id = str(uuid.uuid4())
        
        logger.info(
            "수면 분석 시작",
            analysis_id=analysis_id,
            user_id=request.user_id,
            recording_duration=(request.recording_end - request.recording_start).total_seconds()
        )
        
        # 1. 센서 데이터 유효성 검사
        logger.info("센서 데이터 유효성 검사 중...", analysis_id=analysis_id)
        
        validation_result = await validate_sensor_data(
            request.accelerometer_data,
            request.audio_data
        )
        
        if not validation_result.is_valid:
            raise HTTPException(
                status_code=422,
                detail=f"센서 데이터 유효성 검사 실패: {', '.join(validation_result.validation_errors)}"
            )
        
        # 2. 데이터 품질 확인
        logger.info("데이터 품질 확인 중...", analysis_id=analysis_id)
        
        quality_report = await check_data_quality(
            request.accelerometer_data,
            request.audio_data
        )
        
        if quality_report.overall_score < 0.5:
            logger.warning(
                "낮은 데이터 품질 감지",
                analysis_id=analysis_id,
                quality_score=quality_report.overall_score
            )
        
        # 3. 데이터베이스에 분석 기록 생성
        sleep_analysis = SleepAnalysis(
            analysis_id=analysis_id,
            user_id=request.user_id,
            recording_start=request.recording_start,
            recording_end=request.recording_end,
            model_version=model_service.get_model_version(),
            data_quality_score=quality_report.overall_score,
            status="processing",
            summary_statistics={}  # 나중에 업데이트
        )
        
        db.add(sleep_analysis)
        db.commit()
        
        # 4. 전처리 서비스 초기화
        preprocessor = PreprocessorService()
        postprocessor = PostprocessorService()
        
        # 5. 데이터 전처리
        logger.info("데이터 전처리 중...", analysis_id=analysis_id)
        
        processed_data = await preprocessor.process_sensor_data(
            request.accelerometer_data,
            request.audio_data
        )
        
        # 6. ML 모델 추론
        logger.info("ML 모델 추론 중...", analysis_id=analysis_id)
        
        predictions = await model_service.predict_sleep_stages(processed_data)
        
        # 7. 후처리 및 응답 형식화
        logger.info("결과 후처리 중...", analysis_id=analysis_id)
        
        response = await postprocessor.format_analysis_response(
            analysis_id=analysis_id,
            user_id=request.user_id,
            recording_start=request.recording_start,
            recording_end=request.recording_end,
            predictions=predictions,
            model_version=model_service.get_model_version(),
            data_quality_score=quality_report.overall_score
        )
        
        # 8. 데이터베이스 업데이트 (백그라운드 태스크)
        background_tasks.add_task(
            update_analysis_results,
            db,
            analysis_id,
            response,
            "completed"
        )
        
        logger.info(
            "수면 분석 완료",
            analysis_id=analysis_id,
            user_id=request.user_id,
            total_sleep_time=response.summary_statistics.total_sleep_time
        )
        
        return response
        
    except HTTPException:
        # HTTP 예외는 그대로 재발생
        raise
    except Exception as e:
        logger.error(
            "수면 분석 중 오류 발생",
            analysis_id=getattr(locals().get('sleep_analysis'), 'analysis_id', 'unknown'),
            error=str(e),
            exc_info=True
        )
        
        # 데이터베이스 상태 업데이트
        if 'sleep_analysis' in locals():
            background_tasks.add_task(
                update_analysis_results,
                db,
                sleep_analysis.analysis_id,
                None,
                "failed",
                str(e)
            )
        
        raise HTTPException(
            status_code=500,
            detail="수면 분석 중 내부 오류가 발생했습니다"
        )


@router.get("/history/{user_id}", response_model=SleepAnalysisHistoryResponse)
async def get_sleep_analysis_history(
    user_id: str,
    page: int = Query(1, ge=1, description="페이지 번호"),
    page_size: int = Query(10, ge=1, le=100, description="페이지 크기"),
    db: Session = Depends(get_db)
):
    """
    사용자의 수면 분석 이력 조회
    """
    try:
        # 전체 개수 조회
        total_count = db.query(SleepAnalysis).filter(
            SleepAnalysis.user_id == user_id
        ).count()
        
        # 페이지네이션된 결과 조회
        offset = (page - 1) * page_size
        analyses = db.query(SleepAnalysis).filter(
            SleepAnalysis.user_id == user_id
        ).order_by(SleepAnalysis.analysis_timestamp.desc()).offset(offset).limit(page_size).all()
        
        # 결과 형식화
        analyses_data = []
        for analysis in analyses:
            analyses_data.append({
                "analysis_id": analysis.analysis_id,
                "recording_start": analysis.recording_start,
                "recording_end": analysis.recording_end,
                "analysis_timestamp": analysis.analysis_timestamp,
                "status": analysis.status,
                "data_quality_score": analysis.data_quality_score,
                "model_version": analysis.model_version,
                "summary_statistics": analysis.summary_statistics
            })
        
        return SleepAnalysisHistoryResponse(
            analyses=analyses_data,
            total_count=total_count,
            page=page,
            page_size=page_size
        )
        
    except Exception as e:
        logger.error(f"수면 분석 이력 조회 중 오류: {str(e)}")
        raise HTTPException(status_code=500, detail="분석 이력 조회 실패")


@router.get("/result/{analysis_id}", response_model=SleepAnalysisResponse)
async def get_analysis_result(
    analysis_id: str,
    db: Session = Depends(get_db)
):
    """
    특정 분석 결과 상세 조회
    """
    try:
        # 분석 결과 조회
        analysis = db.query(SleepAnalysis).filter(
            SleepAnalysis.analysis_id == analysis_id
        ).first()
        
        if not analysis:
            raise HTTPException(status_code=404, detail="분석 결과를 찾을 수 없습니다")
        
        if analysis.status != "completed":
            raise HTTPException(
                status_code=400,
                detail=f"분석이 완료되지 않았습니다. 현재 상태: {analysis.status}"
            )
        
        # 상세 데이터 조회 (stage_intervals, stage_probabilities)
        postprocessor = PostprocessorService()
        detailed_response = await postprocessor.get_detailed_analysis_result(
            db, analysis_id
        )
        
        return detailed_response
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"분석 결과 조회 중 오류: {str(e)}")
        raise HTTPException(status_code=500, detail="분석 결과 조회 실패")


@router.get("/models", response_model=List[ModelInfoResponse])
async def get_available_models(db: Session = Depends(get_db)):
    """
    사용 가능한 ML 모델 목록 조회
    """
    try:
        models = db.query(ModelInfo).filter(
            ModelInfo.is_active == True
        ).order_by(ModelInfo.training_date.desc()).all()
        
        model_responses = []
        for model in models:
            model_responses.append(ModelInfoResponse(
                model_name=model.model_name,
                model_version=model.model_version,
                training_date=model.training_date,
                accuracy=model.accuracy or 0.0,
                status="active" if model.is_default else "available"
            ))
        
        return model_responses
        
    except Exception as e:
        logger.error(f"모델 목록 조회 중 오류: {str(e)}")
        raise HTTPException(status_code=500, detail="모델 목록 조회 실패")


@router.delete("/analysis/{analysis_id}")
async def delete_analysis(
    analysis_id: str,
    db: Session = Depends(get_db)
):
    """
    분석 결과 삭제
    """
    try:
        analysis = db.query(SleepAnalysis).filter(
            SleepAnalysis.analysis_id == analysis_id
        ).first()
        
        if not analysis:
            raise HTTPException(status_code=404, detail="분석 결과를 찾을 수 없습니다")
        
        # 관련 데이터도 함께 삭제 (CASCADE 설정으로 자동 삭제됨)
        db.delete(analysis)
        db.commit()
        
        logger.info(f"분석 결과 삭제 완료: {analysis_id}")
        
        return {"message": "분석 결과가 삭제되었습니다"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"분석 결과 삭제 중 오류: {str(e)}")
        db.rollback()
        raise HTTPException(status_code=500, detail="분석 결과 삭제 실패")


async def update_analysis_results(
    db: Session,
    analysis_id: str,
    response: Optional[SleepAnalysisResponse],
    status: str,
    error_message: Optional[str] = None
):
    """
    분석 결과를 데이터베이스에 업데이트하는 백그라운드 태스크
    """
    try:
        analysis = db.query(SleepAnalysis).filter(
            SleepAnalysis.analysis_id == analysis_id
        ).first()
        
        if analysis:
            analysis.status = status
            analysis.error_message = error_message
            
            if response and status == "completed":
                analysis.summary_statistics = response.summary_statistics.dict()
                
                # stage_intervals와 stage_probabilities도 저장
                # (이 부분은 postprocessor에서 처리하거나 별도 구현 필요)
            
            db.commit()
            logger.info(f"분석 결과 업데이트 완료: {analysis_id}, 상태: {status}")
        
    except Exception as e:
        logger.error(f"분석 결과 업데이트 중 오류: {str(e)}")
        db.rollback()

