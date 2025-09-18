"""LLM 피드백 API 라우터"""

import uuid
import structlog
from typing import List
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.config import get_db
from app.models.request_models import LLMFeedbackRequest
from app.models.response_models import LLMFeedbackResponse
from app.models.database_models import LLMFeedback, SleepAnalysis, User
from app.services.llm_service import LLMService

router = APIRouter()
logger = structlog.get_logger()


def get_llm_service() -> LLMService:
    """LLM 서비스 의존성"""
    return LLMService()


@router.post("/feedback", response_model=LLMFeedbackResponse)
async def generate_llm_feedback(
    request: LLMFeedbackRequest,
    db: Session = Depends(get_db),
    llm_service: LLMService = Depends(get_llm_service)
):
    """
    수면 분석 기반 LLM 피드백 생성
    
    사용자의 수면 분석 데이터를 바탕으로 개인화된 조언을 제공합니다.
    """
    feedback_id = str(uuid.uuid4())
    
    try:
        logger.info("LLM 피드백 요청 시작", 
                   feedback_id=feedback_id,
                   user_id=request.user_id,
                   analysis_id=request.analysis_id)
        
        # 사용자 검증
        user = db.query(User).filter(User.id == int(request.user_id)).first()
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="사용자를 찾을 수 없습니다"
            )
        
        # 수면 분석 데이터 조회
        sleep_analysis = db.query(SleepAnalysis).filter(
            SleepAnalysis.analysis_id == request.analysis_id,
            SleepAnalysis.user_id == int(request.user_id)
        ).first()
        
        if not sleep_analysis:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="해당하는 수면 분석 데이터를 찾을 수 없습니다"
            )
        
        logger.info("수면 분석 데이터 조회 완료", 
                   feedback_id=feedback_id,
                   analysis_id=request.analysis_id)
        
        # 수면 데이터 구조화
        sleep_data = {
            "analysis_id": sleep_analysis.analysis_id,
            "summary_statistics": sleep_analysis.summary_statistics,
            "data_quality_score": sleep_analysis.data_quality_score,
            "model_version": sleep_analysis.model_version,
            "recording_start": sleep_analysis.recording_start,
            "recording_end": sleep_analysis.recording_end
        }
        
        # LLM 피드백 생성
        llm_result = await llm_service.generate_sleep_feedback(
            user_prompt=request.user_prompt,
            sleep_data=sleep_data,
            analysis_id=request.analysis_id
        )
        
        # 데이터베이스에 피드백 저장
        llm_feedback = LLMFeedback(
            feedback_id=llm_result["feedback_id"],
            user_id=int(request.user_id),
            analysis_id=request.analysis_id,
            user_prompt=request.user_prompt,
            llm_model=llm_result["llm_model"],
            llm_response=llm_result["llm_response"],
            response_time_ms=llm_result["response_time_ms"]
        )
        
        db.add(llm_feedback)
        db.commit()
        db.refresh(llm_feedback)
        
        logger.info("LLM 피드백 생성 완료", 
                   feedback_id=feedback_id,
                   user_id=request.user_id,
                   response_time_ms=llm_result["response_time_ms"])
        
        # 분석 요약 생성
        analysis_summary = _create_analysis_summary(sleep_analysis)
        
        # 응답 생성
        return LLMFeedbackResponse(
            feedback_id=llm_result["feedback_id"],
            user_prompt=request.user_prompt,
            llm_response=llm_result["llm_response"],
            llm_model=llm_result["llm_model"],
            response_time_ms=llm_result["response_time_ms"],
            timestamp=llm_feedback.created_at,
            analysis_summary=analysis_summary
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("LLM 피드백 생성 실패", 
                    feedback_id=feedback_id,
                    error=str(e))
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="피드백 생성 중 오류가 발생했습니다"
        )


@router.get("/feedback/history/{user_id}", response_model=List[LLMFeedbackResponse])
async def get_feedback_history(
    user_id: str,
    limit: int = 10,
    db: Session = Depends(get_db)
):
    """
    사용자의 LLM 피드백 기록 조회
    """
    try:
        # 사용자 검증
        user = db.query(User).filter(User.id == int(user_id)).first()
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="사용자를 찾을 수 없습니다"
            )
        
        # 피드백 기록 조회
        feedbacks = db.query(LLMFeedback).filter(
            LLMFeedback.user_id == int(user_id)
        ).order_by(
            LLMFeedback.created_at.desc()
        ).limit(limit).all()
        
        # 응답 생성
        result = []
        for feedback in feedbacks:
            # 관련 수면 분석 데이터 조회
            sleep_analysis = db.query(SleepAnalysis).filter(
                SleepAnalysis.analysis_id == feedback.analysis_id
            ).first()
            
            analysis_summary = _create_analysis_summary(sleep_analysis) if sleep_analysis else "분석 데이터 없음"
            
            result.append(LLMFeedbackResponse(
                feedback_id=feedback.feedback_id,
                user_prompt=feedback.user_prompt,
                llm_response=feedback.llm_response,
                llm_model=feedback.llm_model,
                response_time_ms=feedback.response_time_ms,
                timestamp=feedback.created_at,
                analysis_summary=analysis_summary
            ))
        
        logger.info("피드백 기록 조회 완료", 
                   user_id=user_id, 
                   count=len(result))
        
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("피드백 기록 조회 실패", 
                    user_id=user_id,
                    error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="피드백 기록 조회 중 오류가 발생했습니다"
        )


@router.get("/feedback/{feedback_id}", response_model=LLMFeedbackResponse)
async def get_feedback_detail(
    feedback_id: str,
    db: Session = Depends(get_db)
):
    """
    특정 LLM 피드백 상세 조회
    """
    try:
        feedback = db.query(LLMFeedback).filter(
            LLMFeedback.feedback_id == feedback_id
        ).first()
        
        if not feedback:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="피드백을 찾을 수 없습니다"
            )
        
        # 관련 수면 분석 데이터 조회
        sleep_analysis = db.query(SleepAnalysis).filter(
            SleepAnalysis.analysis_id == feedback.analysis_id
        ).first()
        
        analysis_summary = _create_analysis_summary(sleep_analysis) if sleep_analysis else "분석 데이터 없음"
        
        return LLMFeedbackResponse(
            feedback_id=feedback.feedback_id,
            user_prompt=feedback.user_prompt,
            llm_response=feedback.llm_response,
            llm_model=feedback.llm_model,
            response_time_ms=feedback.response_time_ms,
            timestamp=feedback.created_at,
            analysis_summary=analysis_summary
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("피드백 상세 조회 실패", 
                    feedback_id=feedback_id,
                    error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="피드백 조회 중 오류가 발생했습니다"
        )


@router.get("/health/llm")
async def check_llm_health(llm_service: LLMService = Depends(get_llm_service)):
    """
    LLM 서비스 상태 확인
    """
    try:
        is_available = await llm_service.validate_model_availability()
        
        return {
            "status": "healthy" if is_available else "unhealthy",
            "model": llm_service.model_name,
            "ollama_url": llm_service.ollama_url,
            "available": is_available,
            "timestamp": datetime.utcnow()
        }
        
    except Exception as e:
        logger.error("LLM 헬스체크 실패", error=str(e))
        return {
            "status": "unhealthy",
            "model": llm_service.model_name,
            "error": str(e),
            "timestamp": datetime.utcnow()
        }


def _create_analysis_summary(sleep_analysis) -> str:
    """수면 분석 요약 생성"""
    if not sleep_analysis:
        return "분석 데이터 없음"
    
    try:
        stats = sleep_analysis.summary_statistics
        duration = (sleep_analysis.recording_end - sleep_analysis.recording_start).total_seconds() / 3600
        
        return (f"총 {duration:.1f}시간 수면 분석 "
                f"(수면효율: {stats.get('sleep_efficiency', 0)*100:.1f}%, "
                f"총 수면시간: {stats.get('total_sleep_time', 0)}분)")
    except:
        return "분석 요약 생성 실패"
