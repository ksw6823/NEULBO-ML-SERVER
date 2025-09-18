from typing import Optional
from pydantic import Field
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """애플리케이션 설정"""
    
    # 앱 기본 설정
    app_name: str = "NEULBO ML Server"
    app_version: str = "1.0.0"
    debug: bool = False
    
    # 서버 설정
    host: str = "0.0.0.0"
    port: int = 8001
    
    # 데이터베이스 설정
    database_url: str = Field(
        default="postgresql://neulbo:your_password_here@postgres:5432/neulbodb",
        description="PostgreSQL 데이터베이스 연결 URL"
    )
    database_echo: bool = False  # SQLAlchemy 로깅
    
    # ML 모델 설정
    model_path: str = "app/ml_models/"
    max_recording_duration: int = 43200  # 12시간 (초)
    min_recording_duration: int = 3600   # 1시간 (초)
    sensor_sampling_rate: float = 1.0    # Hz
    stage_interval_seconds: int = 30
    
    # 모델 추론 설정
    model_confidence_threshold: float = 0.7
    enable_model_caching: bool = True
    
    # LLM 설정
    ollama_url: str = Field(
        default="http://neulbo-llm:11434",
        description="OLLAMA 서버 URL"
    )
    llm_model: str = Field(
        default="gpt-oss:20b",
        description="사용할 LLM 모델 이름"
    )
    llm_timeout: float = Field(
        default=30.0,
        description="LLM API 타임아웃(초)"
    )
    
    # 보안 설정
    secret_key: str = Field(
        default="your-secret-key-change-in-production",
        description="JWT 토큰 암호화에 사용되는 비밀 키"
    )
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
    
    # 로깅 설정
    log_level: str = "INFO"
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False


# 전역 설정 인스턴스
settings = Settings()

