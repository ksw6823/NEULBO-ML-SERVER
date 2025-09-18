#!/usr/bin/env python3
"""
데이터베이스 마이그레이션 스크립트
새로운 LLM 피드백 테이블 생성
"""

from sqlalchemy import create_engine
from app.config.database import Base
from app.config.settings import settings
from app.models.database_models import LLMFeedback
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def create_llm_feedback_table():
    """LLM 피드백 테이블 생성"""
    try:
        # 데이터베이스 연결
        engine = create_engine(settings.database_url)
        
        logger.info("LLM 피드백 테이블 생성 중...")
        
        # 새 테이블만 생성 (기존 테이블은 건드리지 않음)
        LLMFeedback.__table__.create(bind=engine, checkfirst=True)
        
        logger.info("✅ LLM 피드백 테이블 생성 완료!")
        
        # 테이블 확인
        with engine.connect() as conn:
            result = conn.execute(
                "SELECT COUNT(*) FROM information_schema.tables WHERE table_name = 'llm_feedbacks'"
            )
            count = result.scalar()
            
            if count > 0:
                logger.info("✅ llm_feedbacks 테이블이 성공적으로 생성되었습니다.")
            else:
                logger.error("❌ 테이블 생성 실패")
                
    except Exception as e:
        logger.error(f"❌ 마이그레이션 실패: {str(e)}")
        raise

if __name__ == "__main__":
    create_llm_feedback_table()
