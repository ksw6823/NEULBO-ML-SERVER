"""의존성 주입 모듈"""

from app.services.model_service import ModelService

# 전역 모델 서비스 인스턴스
model_service = ModelService()


def get_model_service() -> ModelService:
    """모델 서비스 의존성 반환"""
    return model_service
