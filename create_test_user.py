#!/usr/bin/env python3
"""
테스트용 사용자 생성 스크립트
"""

import asyncio
from sqlalchemy.orm import Session
from app.config.database import get_db
from app.models.database_models import User

def create_test_user():
    """테스트용 사용자 생성"""
    try:
        db_gen = get_db()
        db = next(db_gen)
        
        # 기존 사용자 확인
        existing_user = db.query(User).filter(User.id == 1).first()
        
        if existing_user:
            print(f"✅ 테스트 사용자가 이미 존재합니다: {existing_user.username}")
            return
        
        # 새 사용자 생성
        test_user = User(
            id=1,
            username="test_user",
            email="test@example.com",
            hashed_password="hashed_test_password",
            full_name="테스트 사용자",
            age=30,
            height=170.0,
            weight=65.0
        )
        
        db.add(test_user)
        db.commit()
        
        print("✅ 테스트 사용자 생성 완료:")
        print(f"   ID: {test_user.id}")
        print(f"   사용자명: {test_user.username}")
        print(f"   이메일: {test_user.email}")
            
    except Exception as e:
        print(f"❌ 테스트 사용자 생성 실패: {str(e)}")

if __name__ == "__main__":
    create_test_user()
