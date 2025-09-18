from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
import uuid
import structlog
from sqlalchemy.orm import Session

from app.models.internal_models import ModelPrediction
from app.models.response_models import (
    SleepAnalysisResponse,
    SleepStageInterval,
    StageProbabilities,
    SleepSummaryStatistics,
    SleepStage
)
from app.models.database_models import SleepStageInterval as DBSleepStageInterval
from app.models.database_models import StageProbability as DBStageProbability
from app.models.database_models import SleepAnalysis
from app.config.settings import settings

logger = structlog.get_logger()


class PostprocessorService:
    """수면 분석 결과 후처리 서비스"""
    
    def __init__(self):
        self.stage_interval_seconds = settings.stage_interval_seconds
    
    async def format_analysis_response(
        self,
        analysis_id: str,
        user_id: str,
        recording_start: datetime,
        recording_end: datetime,
        predictions: ModelPrediction,
        model_version: str,
        data_quality_score: float
    ) -> SleepAnalysisResponse:
        """분석 결과를 응답 형식으로 변환"""
        try:
            logger.info("분석 결과 후처리 시작", analysis_id=analysis_id)
            
            # 수면 단계 구간 생성
            stage_intervals = await self._create_stage_intervals(
                recording_start, predictions
            )
            
            # 시간대별 확률 생성
            stage_probabilities = await self._create_stage_probabilities(
                recording_start, predictions
            )
            
            # 요약 통계 계산
            summary_statistics = await self._calculate_summary_statistics(
                stage_intervals, recording_start, recording_end
            )
            
            response = SleepAnalysisResponse(
                user_id=user_id,
                analysis_id=analysis_id,
                analysis_timestamp=datetime.utcnow(),
                recording_start=recording_start,
                recording_end=recording_end,
                stage_intervals=stage_intervals,
                stage_probabilities=stage_probabilities,
                summary_statistics=summary_statistics,
                model_version=model_version,
                data_quality_score=data_quality_score
            )
            
            logger.info("분석 결과 후처리 완료", analysis_id=analysis_id)
            return response
            
        except Exception as e:
            logger.error(f"분석 결과 후처리 중 오류: {str(e)}")
            raise
    
    async def _create_stage_intervals(
        self,
        recording_start: datetime,
        predictions: ModelPrediction
    ) -> List[SleepStageInterval]:
        """수면 단계 구간 생성"""
        try:
            intervals = []
            
            if not predictions.predictions:
                return intervals
            
            current_stage = predictions.predictions[0]
            current_start = recording_start
            current_confidence_sum = predictions.confidence_scores[0]
            current_count = 1
            
            for i in range(1, len(predictions.predictions)):
                stage = predictions.predictions[i]
                confidence = predictions.confidence_scores[i]
                
                if stage == current_stage:
                    # 같은 단계 계속
                    current_confidence_sum += confidence
                    current_count += 1
                else:
                    # 단계 변경 -> 이전 구간 완료
                    interval_end = recording_start + timedelta(
                        seconds=i * self.stage_interval_seconds
                    )
                    
                    avg_confidence = current_confidence_sum / current_count
                    
                    intervals.append(SleepStageInterval(
                        start_time=current_start,
                        end_time=interval_end,
                        stage=SleepStage(current_stage),
                        confidence=avg_confidence
                    ))
                    
                    # 새 구간 시작
                    current_stage = stage
                    current_start = interval_end
                    current_confidence_sum = confidence
                    current_count = 1
            
            # 마지막 구간 처리
            if current_count > 0:
                interval_end = recording_start + timedelta(
                    seconds=len(predictions.predictions) * self.stage_interval_seconds
                )
                
                avg_confidence = current_confidence_sum / current_count
                
                intervals.append(SleepStageInterval(
                    start_time=current_start,
                    end_time=interval_end,
                    stage=SleepStage(current_stage),
                    confidence=avg_confidence
                ))
            
            logger.debug(f"수면 단계 구간 생성 완료: {len(intervals)}개 구간")
            return intervals
            
        except Exception as e:
            logger.error(f"수면 단계 구간 생성 중 오류: {str(e)}")
            raise
    
    async def _create_stage_probabilities(
        self,
        recording_start: datetime,
        predictions: ModelPrediction
    ) -> List[StageProbabilities]:
        """시간대별 수면 단계 확률 생성"""
        try:
            probabilities = []
            
            class_names = ["Wake", "N1", "N2", "N3", "REM"]
            
            for i, probs in enumerate(predictions.probabilities):
                timestamp = recording_start + timedelta(
                    seconds=i * self.stage_interval_seconds
                )
                
                # 확률을 클래스 이름에 매핑
                prob_dict = {}
                for j, class_name in enumerate(class_names):
                    prob_dict[class_name.lower()] = probs[j] if j < len(probs) else 0.0
                
                probabilities.append(StageProbabilities(
                    timestamp=timestamp,
                    wake=prob_dict.get('wake', 0.0),
                    n1=prob_dict.get('n1', 0.0),
                    n2=prob_dict.get('n2', 0.0),
                    n3=prob_dict.get('n3', 0.0),
                    rem=prob_dict.get('rem', 0.0)
                ))
            
            logger.debug(f"시간대별 확률 생성 완료: {len(probabilities)}개 시점")
            return probabilities
            
        except Exception as e:
            logger.error(f"시간대별 확률 생성 중 오류: {str(e)}")
            raise
    
    async def _calculate_summary_statistics(
        self,
        stage_intervals: List[SleepStageInterval],
        recording_start: datetime,
        recording_end: datetime
    ) -> SleepSummaryStatistics:
        """수면 요약 통계 계산"""
        try:
            # 각 단계별 시간 계산 (분 단위)
            stage_durations = {
                "Wake": 0,
                "N1": 0,
                "N2": 0,
                "N3": 0,
                "REM": 0
            }
            
            for interval in stage_intervals:
                duration_seconds = (interval.end_time - interval.start_time).total_seconds()
                duration_minutes = int(duration_seconds / 60)
                stage_durations[interval.stage.value] += duration_minutes
            
            # 총 기록 시간
            total_recording_time = int((recording_end - recording_start).total_seconds() / 60)
            
            # 총 수면 시간 (각성 제외)
            total_sleep_time = sum(
                duration for stage, duration in stage_durations.items() 
                if stage != "Wake"
            )
            
            # 수면 효율성
            sleep_efficiency = total_sleep_time / total_recording_time if total_recording_time > 0 else 0.0
            
            # 수면 개시 잠복기 (첫 번째 수면 단계까지의 시간)
            sleep_onset_latency = 0
            for interval in stage_intervals:
                if interval.stage.value != "Wake":
                    sleep_onset_latency = int((interval.start_time - recording_start).total_seconds() / 60)
                    break
            
            # 수면 중 각성 시간 (첫 수면 이후의 각성 시간)
            wake_after_sleep_onset = 0
            sleep_started = False
            
            for interval in stage_intervals:
                if interval.stage.value != "Wake":
                    sleep_started = True
                elif sleep_started and interval.stage.value == "Wake":
                    duration_minutes = int((interval.end_time - interval.start_time).total_seconds() / 60)
                    wake_after_sleep_onset += duration_minutes
            
            # 각 단계별 비율 계산
            stage_percentages = {}
            for stage, duration in stage_durations.items():
                percentage = (duration / total_recording_time * 100) if total_recording_time > 0 else 0.0
                stage_percentages[stage] = round(percentage, 1)
            
            return SleepSummaryStatistics(
                total_sleep_time=total_sleep_time,
                sleep_efficiency=round(sleep_efficiency, 3),
                sleep_onset_latency=sleep_onset_latency,
                wake_after_sleep_onset=wake_after_sleep_onset,
                
                wake_time=stage_durations["Wake"],
                n1_time=stage_durations["N1"],
                n2_time=stage_durations["N2"],
                n3_time=stage_durations["N3"],
                rem_time=stage_durations["REM"],
                
                wake_percentage=stage_percentages["Wake"],
                n1_percentage=stage_percentages["N1"],
                n2_percentage=stage_percentages["N2"],
                n3_percentage=stage_percentages["N3"],
                rem_percentage=stage_percentages["REM"]
            )
            
        except Exception as e:
            logger.error(f"요약 통계 계산 중 오류: {str(e)}")
            raise
    
    async def save_detailed_results(
        self,
        db: Session,
        analysis_id: str,
        response: SleepAnalysisResponse
    ):
        """상세 분석 결과를 데이터베이스에 저장"""
        try:
            logger.info("상세 분석 결과 저장 시작", analysis_id=analysis_id)
            
            # 분석 레코드 조회
            analysis = db.query(SleepAnalysis).filter(
                SleepAnalysis.analysis_id == analysis_id
            ).first()
            
            if not analysis:
                raise ValueError(f"분석 레코드를 찾을 수 없습니다: {analysis_id}")
            
            # 수면 단계 구간 저장
            for interval in response.stage_intervals:
                db_interval = DBSleepStageInterval(
                    analysis_id=analysis.id,
                    start_time=interval.start_time,
                    end_time=interval.end_time,
                    stage=interval.stage.value,
                    confidence=interval.confidence
                )
                db.add(db_interval)
            
            # 시간대별 확률 저장
            for prob in response.stage_probabilities:
                db_prob = DBStageProbability(
                    analysis_id=analysis.id,
                    timestamp=prob.timestamp,
                    wake=prob.wake,
                    n1=prob.n1,
                    n2=prob.n2,
                    n3=prob.n3,
                    rem=prob.rem
                )
                db.add(db_prob)
            
            # 요약 통계 업데이트
            analysis.summary_statistics = response.summary_statistics.dict()
            analysis.status = "completed"
            
            db.commit()
            logger.info("상세 분석 결과 저장 완료", analysis_id=analysis_id)
            
        except Exception as e:
            logger.error(f"상세 분석 결과 저장 중 오류: {str(e)}")
            db.rollback()
            raise
    
    async def get_detailed_analysis_result(
        self,
        db: Session,
        analysis_id: str
    ) -> SleepAnalysisResponse:
        """데이터베이스에서 상세 분석 결과 조회"""
        try:
            # 기본 분석 정보 조회
            analysis = db.query(SleepAnalysis).filter(
                SleepAnalysis.analysis_id == analysis_id
            ).first()
            
            if not analysis:
                raise ValueError(f"분석 결과를 찾을 수 없습니다: {analysis_id}")
            
            # 수면 단계 구간 조회
            db_intervals = db.query(DBSleepStageInterval).filter(
                DBSleepStageInterval.analysis_id == analysis.id
            ).order_by(DBSleepStageInterval.start_time).all()
            
            stage_intervals = [
                SleepStageInterval(
                    start_time=interval.start_time,
                    end_time=interval.end_time,
                    stage=SleepStage(interval.stage),
                    confidence=interval.confidence
                )
                for interval in db_intervals
            ]
            
            # 시간대별 확률 조회
            db_probs = db.query(DBStageProbability).filter(
                DBStageProbability.analysis_id == analysis.id
            ).order_by(DBStageProbability.timestamp).all()
            
            stage_probabilities = [
                StageProbabilities(
                    timestamp=prob.timestamp,
                    wake=prob.wake,
                    n1=prob.n1,
                    n2=prob.n2,
                    n3=prob.n3,
                    rem=prob.rem
                )
                for prob in db_probs
            ]
            
            # 요약 통계 복원
            summary_stats = SleepSummaryStatistics(**analysis.summary_statistics)
            
            return SleepAnalysisResponse(
                user_id=str(analysis.user_id),
                analysis_id=analysis.analysis_id,
                analysis_timestamp=analysis.analysis_timestamp,
                recording_start=analysis.recording_start,
                recording_end=analysis.recording_end,
                stage_intervals=stage_intervals,
                stage_probabilities=stage_probabilities,
                summary_statistics=summary_stats,
                model_version=analysis.model_version,
                data_quality_score=analysis.data_quality_score
            )
            
        except Exception as e:
            logger.error(f"상세 분석 결과 조회 중 오류: {str(e)}")
            raise
    
    async def apply_smoothing(
        self,
        predictions: List[str],
        window_size: int = 3
    ) -> List[str]:
        """예측 결과 스무딩 (노이즈 제거)"""
        try:
            if len(predictions) < window_size:
                return predictions
            
            smoothed = predictions.copy()
            
            for i in range(window_size // 2, len(predictions) - window_size // 2):
                window_start = i - window_size // 2
                window_end = i + window_size // 2 + 1
                window_predictions = predictions[window_start:window_end]
                
                # 윈도우 내에서 가장 빈번한 예측값 선택
                from collections import Counter
                most_common = Counter(window_predictions).most_common(1)
                
                if most_common:
                    smoothed[i] = most_common[0][0]
            
            return smoothed
            
        except Exception as e:
            logger.error(f"예측 결과 스무딩 중 오류: {str(e)}")
            return predictions  # 원본 반환

