import os
import asyncio
from datetime import datetime
from typing import Dict, List, Optional, Any, Tuple
import joblib
import numpy as np
import structlog

from app.config.settings import settings
from app.models.internal_models import (
    ProcessedSensorData, 
    ModelPrediction, 
    ModelMetrics
)

logger = structlog.get_logger()


class ModelService:
    """ML 모델 서비스"""
    
    def __init__(self):
        self.sleep_stage_model = None
        self.preprocessing_params = None
        self.model_metadata = {}
        self._is_ready = False
        
    async def load_models(self):
        """모델 로딩"""
        try:
            logger.info("ML 모델 로딩 시작...")
            
            # 실제 모델 파일 경로
            model_path = os.path.join(settings.model_path, "final_xgb_gpu_single.joblib")
            feature_meta_path = os.path.join(settings.model_path, "feature_meta_single.json")
            model_config_path = os.path.join(settings.model_path, "final_xgb_gpu_single.json")
            
            # 모델 파일 존재 확인
            if not os.path.exists(model_path):
                raise FileNotFoundError(f"모델 파일을 찾을 수 없습니다: {model_path}")
            
            # XGBoost 모델 로딩 (비동기적으로 실행)
            self.sleep_stage_model = await asyncio.get_event_loop().run_in_executor(
                None, joblib.load, model_path
            )
            
            # 특성 메타데이터 로딩
            if os.path.exists(feature_meta_path):
                import json
                with open(feature_meta_path, 'r', encoding='utf-8') as f:
                    feature_meta = json.load(f)
                self.preprocessing_params = {
                    "feature_meta": feature_meta,
                    "scaler": None  # 필요시 별도 로딩
                }
                logger.info("특성 메타데이터 로딩 완료")
            else:
                logger.warning("특성 메타데이터 파일이 없습니다. 기본값을 사용합니다.")
                self.preprocessing_params = self._get_default_preprocessing_params()
            
            # 모델 설정 로딩
            if os.path.exists(model_config_path):
                import json
                with open(model_config_path, 'r', encoding='utf-8') as f:
                    model_config = json.load(f)
                self.model_metadata = {
                    "model_version": "xgb_gpu_single_v1.0",
                    "class_names": ["Wake", "N1", "N2", "N3", "REM"],
                    "training_date": model_config.get("training_date", "unknown"),
                    "model_config": model_config,
                    "model_type": "XGBoost"
                }
                logger.info("모델 설정 로딩 완료")
            else:
                self.model_metadata = self._get_default_metadata()
            
            self._is_ready = True
            logger.info(f"XGBoost 모델 로딩 완료: {model_path}")
            
        except Exception as e:
            logger.error(f"모델 로딩 중 오류: {str(e)}")
            self._is_ready = False
            raise
    
    async def predict_sleep_stages(
        self, 
        processed_data: ProcessedSensorData
    ) -> ModelPrediction:
        """수면 단계 예측"""
        if not self._is_ready:
            raise RuntimeError("모델이 준비되지 않았습니다")
        
        try:
            logger.info("수면 단계 예측 시작")
            
            # 특성 데이터 준비
            features = self._prepare_features(processed_data)
            
            # 모델 예측 (비동기적으로 실행)
            predictions = await asyncio.get_event_loop().run_in_executor(
                None, self.sleep_stage_model.predict, features
            )
            
            # 확률 예측 (XGBoost의 경우 predict_proba 확인)
            try:
                if hasattr(self.sleep_stage_model, 'predict_proba'):
                    probabilities = await asyncio.get_event_loop().run_in_executor(
                        None, self.sleep_stage_model.predict_proba, features
                    )
                else:
                    # XGBoost classifier의 경우 predict_proba 대신 predict 사용하여 확률 얻기
                    probabilities = await asyncio.get_event_loop().run_in_executor(
                        None, lambda x: self.sleep_stage_model.predict(x, output_margin=False), features
                    )
                    # 단일 값인 경우 더미 확률 생성
                    if probabilities.ndim == 1:
                        n_classes = len(self.model_metadata.get("class_names", ["Wake", "N1", "N2", "N3", "REM"]))
                        dummy_probs = np.zeros((len(predictions), n_classes))
                        for i, pred in enumerate(predictions):
                            dummy_probs[i, int(pred)] = 1.0  # 예측된 클래스에 100% 확률
                        probabilities = dummy_probs
            except Exception as prob_error:
                logger.warning(f"확률 예측 실패, 더미 확률 사용: {str(prob_error)}")
                # 더미 확률 생성
                n_classes = len(self.model_metadata.get("class_names", ["Wake", "N1", "N2", "N3", "REM"]))
                probabilities = np.zeros((len(predictions), n_classes))
                for i, pred in enumerate(predictions):
                    probabilities[i, int(pred)] = 1.0
            
            # 신뢰도 점수 계산
            confidence_scores = np.max(probabilities, axis=1).tolist()
            
            # 클래스 이름 매핑
            class_names = self.model_metadata.get("class_names", ["Wake", "N1", "N2", "N3", "REM"])
            predicted_stages = [class_names[pred] for pred in predictions]
            
            logger.info(f"수면 단계 예측 완료: {len(predicted_stages)}개 구간")
            
            return ModelPrediction(
                predictions=predicted_stages,
                probabilities=probabilities.tolist(),
                confidence_scores=confidence_scores,
                model_version=self.get_model_version(),
                prediction_timestamp=datetime.utcnow()
            )
            
        except Exception as e:
            logger.error(f"수면 단계 예측 중 오류: {str(e)}")
            raise
    
    def _prepare_features(self, processed_data: ProcessedSensorData) -> np.ndarray:
        """특성 데이터 준비"""
        try:
            # 이미 전처리에서 모델에 맞는 6개 특성으로 변환됨
            features = np.array(processed_data.accelerometer_features)
            
            logger.debug(f"준비된 특성 형태: {features.shape}")
            
            # 특성 수 확인 (6개여야 함)
            if features.shape[1] != 6:
                logger.warning(f"예상과 다른 특성 수: {features.shape[1]} (예상: 6)")
            
            return features
            
        except Exception as e:
            logger.error(f"특성 데이터 준비 중 오류: {str(e)}")
            raise
    
    
    def _get_default_preprocessing_params(self) -> Dict[str, Any]:
        """기본 전처리 파라미터"""
        return {
            "window_size": 30,
            "overlap": 0.5,
            "sampling_rate": 1.0,
            "normalization": "z-score"
        }
    
    def _get_default_metadata(self) -> Dict[str, Any]:
        """기본 메타데이터"""
        return {
            "model_version": "xgb_gpu_single_v1.0",
            "class_names": ["Wake", "N1", "N2", "N3", "REM"],
            "training_date": "unknown",
            "model_type": "XGBoost",
            "accuracy": 0.0
        }
    
    def get_model_version(self) -> str:
        """모델 버전 반환"""
        return self.model_metadata.get("model_version", "unknown")
    
    def is_ready(self) -> bool:
        """모델 준비 상태 확인"""
        return self._is_ready
    
    async def get_model_info(self) -> Dict[str, Any]:
        """모델 정보 반환"""
        return {
            "is_ready": self._is_ready,
            "model_version": self.get_model_version(),
            "metadata": self.model_metadata,
            "preprocessing_params": self.preprocessing_params
        }
    
    async def cleanup(self):
        """모델 서비스 정리"""
        logger.info("모델 서비스 정리 중...")
        
        self.sleep_stage_model = None
        self.preprocessing_params = None
        self.model_metadata = {}
        self._is_ready = False
        
        logger.info("모델 서비스 정리 완료")
    
    async def validate_model_health(self) -> bool:
        """모델 상태 검증"""
        try:
            if not self._is_ready:
                return False
            
            # 간단한 더미 데이터로 예측 테스트 (6개 특성)
            dummy_features = np.random.randn(1, 6)
            
            prediction = await asyncio.get_event_loop().run_in_executor(
                None, self.sleep_stage_model.predict, dummy_features
            )
            
            return len(prediction) == 1
            
        except Exception as e:
            logger.error(f"모델 헬스체크 실패: {str(e)}")
            return False

