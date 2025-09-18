from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import StaticPool
from typing import Generator

from app.config.settings import settings

# SQLAlchemy 엔진 생성
engine = create_engine(
    settings.database_url,
    echo=settings.database_echo,
    poolclass=StaticPool,
    connect_args={
        "check_same_thread": False,  # SQLite용 (PostgreSQL에서는 무시됨)
    } if "sqlite" in settings.database_url else {},
)

# 세션 로컬 클래스
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Base 클래스 (모든 ORM 모델의 부모 클래스)
Base = declarative_base()


def get_db() -> Generator[Session, None, None]:
    """
    데이터베이스 세션 의존성
    
    FastAPI 라우터에서 Depends(get_db)로 사용
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


async def create_tables():
    """테이블 생성 (애플리케이션 시작 시 호출)"""
    Base.metadata.create_all(bind=engine)


async def close_db_connection():
    """데이터베이스 연결 종료 (애플리케이션 종료 시 호출)"""
    engine.dispose()

