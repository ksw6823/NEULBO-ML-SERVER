#!/usr/bin/env python3
"""
사용자 ID를 Integer에서 UUID로 마이그레이션하는 스크립트

⚠️ 주의사항:
1. 이 스크립트는 프로덕션 환경에서 실행하기 전에 반드시 백업을 수행하세요.
2. Spring Boot API 서버와 동시에 실행 중인 경우 서비스를 중단하고 실행하세요.
3. 기존 데이터가 있는 경우 데이터 손실이 발생할 수 있습니다.

사용법:
    python migrate_user_id_to_uuid.py --confirm
"""

import sys
import uuid
import asyncio
import argparse
from datetime import datetime
from sqlalchemy import create_engine, text, MetaData, Table, Column, Integer, String, DateTime, Float, Boolean, Text, ForeignKey, JSON
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import sessionmaker
from sqlalchemy.exc import SQLAlchemyError

from app.config.settings import settings

def create_migration_engine():
    """마이그레이션용 데이터베이스 엔진 생성"""
    return create_engine(
        settings.database_url,
        echo=True,  # SQL 로그 출력
        pool_pre_ping=True
    )

def backup_existing_data(engine):
    """기존 데이터 백업"""
    print("📦 기존 데이터 백업 중...")
    
    backup_queries = [
        "CREATE TABLE IF NOT EXISTS users_backup AS SELECT * FROM users;",
        "CREATE TABLE IF NOT EXISTS sleep_analyses_backup AS SELECT * FROM sleep_analyses;",
        "CREATE TABLE IF NOT EXISTS api_usage_backup AS SELECT * FROM api_usage;",
        "CREATE TABLE IF NOT EXISTS llm_feedbacks_backup AS SELECT * FROM llm_feedbacks;"
    ]
    
    with engine.connect() as conn:
        for query in backup_queries:
            try:
                conn.execute(text(query))
                conn.commit()
                print(f"✅ 백업 완료: {query.split()[5]}")
            except Exception as e:
                print(f"❌ 백업 실패: {e}")
                return False
    
    return True

def create_uuid_mapping(engine):
    """기존 Integer ID를 UUID로 매핑하는 테이블 생성"""
    print("🗺️  ID 매핑 테이블 생성 중...")
    
    mapping_query = """
    CREATE TABLE IF NOT EXISTS user_id_mapping (
        old_id INTEGER PRIMARY KEY,
        new_id UUID NOT NULL UNIQUE DEFAULT gen_random_uuid()
    );
    """
    
    with engine.connect() as conn:
        try:
            conn.execute(text(mapping_query))
            
            # 기존 사용자들에 대한 UUID 매핑 생성
            insert_mapping = """
            INSERT INTO user_id_mapping (old_id)
            SELECT DISTINCT id FROM users
            ON CONFLICT (old_id) DO NOTHING;
            """
            conn.execute(text(insert_mapping))
            conn.commit()
            
            print("✅ ID 매핑 테이블 생성 완료")
            return True
        except Exception as e:
            print(f"❌ 매핑 테이블 생성 실패: {e}")
            return False

def migrate_users_table(engine):
    """users 테이블 마이그레이션"""
    print("👤 users 테이블 마이그레이션 중...")
    
    migration_queries = [
        # 1. 새로운 UUID 컬럼 추가
        "ALTER TABLE users ADD COLUMN IF NOT EXISTS new_id UUID;",
        
        # 2. 매핑 테이블에서 UUID 값 복사
        """
        UPDATE users 
        SET new_id = user_id_mapping.new_id 
        FROM user_id_mapping 
        WHERE users.id = user_id_mapping.old_id;
        """,
        
        # 3. 기존 id 컬럼을 old_id로 이름 변경
        "ALTER TABLE users RENAME COLUMN id TO old_id;",
        
        # 4. new_id를 id로 이름 변경
        "ALTER TABLE users RENAME COLUMN new_id TO id;",
        
        # 5. 새로운 기본키 설정
        "ALTER TABLE users DROP CONSTRAINT IF EXISTS users_pkey;",
        "ALTER TABLE users ADD PRIMARY KEY (id);",
        
        # 6. 인덱스 재생성
        "CREATE UNIQUE INDEX IF NOT EXISTS users_id_idx ON users (id);",
        "CREATE UNIQUE INDEX IF NOT EXISTS users_username_idx ON users (username);",
        "CREATE UNIQUE INDEX IF NOT EXISTS users_email_idx ON users (email);"
    ]
    
    with engine.connect() as conn:
        for query in migration_queries:
            try:
                conn.execute(text(query))
                conn.commit()
                print(f"✅ 실행 완료: {query[:50]}...")
            except Exception as e:
                print(f"❌ 실행 실패: {e}")
                return False
    
    return True

def migrate_foreign_keys(engine):
    """외래키 테이블들 마이그레이션"""
    print("🔗 외래키 테이블들 마이그레이션 중...")
    
    # 각 테이블별 마이그레이션
    tables_to_migrate = [
        {
            "table": "sleep_analyses",
            "fk_column": "user_id",
            "reference": "users(id)"
        },
        {
            "table": "api_usage", 
            "fk_column": "user_id",
            "reference": "users(id)"
        },
        {
            "table": "llm_feedbacks",
            "fk_column": "user_id", 
            "reference": "users(id)"
        }
    ]
    
    with engine.connect() as conn:
        for table_info in tables_to_migrate:
            table = table_info["table"]
            fk_column = table_info["fk_column"]
            
            migration_queries = [
                # 1. 새로운 UUID 컬럼 추가
                f"ALTER TABLE {table} ADD COLUMN IF NOT EXISTS new_{fk_column} UUID;",
                
                # 2. 매핑 테이블을 통해 UUID 값 업데이트
                f"""
                UPDATE {table} 
                SET new_{fk_column} = user_id_mapping.new_id 
                FROM user_id_mapping 
                WHERE {table}.{fk_column} = user_id_mapping.old_id;
                """,
                
                # 3. 기존 외래키 제약조건 제거
                f"ALTER TABLE {table} DROP CONSTRAINT IF EXISTS {table}_{fk_column}_fkey;",
                
                # 4. 기존 컬럼 삭제
                f"ALTER TABLE {table} DROP COLUMN IF EXISTS {fk_column};",
                
                # 5. 새 컬럼을 원래 이름으로 변경
                f"ALTER TABLE {table} RENAME COLUMN new_{fk_column} TO {fk_column};",
                
                # 6. 새로운 외래키 제약조건 추가
                f"ALTER TABLE {table} ADD CONSTRAINT {table}_{fk_column}_fkey FOREIGN KEY ({fk_column}) REFERENCES users(id);"
            ]
            
            for query in migration_queries:
                try:
                    conn.execute(text(query))
                    conn.commit()
                    print(f"✅ {table} 마이그레이션 단계 완료")
                except Exception as e:
                    print(f"❌ {table} 마이그레이션 실패: {e}")
                    return False
    
    return True

def cleanup_migration(engine):
    """마이그레이션 정리"""
    print("🧹 마이그레이션 정리 중...")
    
    cleanup_queries = [
        "ALTER TABLE users DROP COLUMN IF EXISTS old_id;",
        "DROP TABLE IF EXISTS user_id_mapping;"
    ]
    
    with engine.connect() as conn:
        for query in cleanup_queries:
            try:
                conn.execute(text(query))
                conn.commit()
                print(f"✅ 정리 완료: {query}")
            except Exception as e:
                print(f"⚠️  정리 중 오류 (무시 가능): {e}")

def verify_migration(engine):
    """마이그레이션 검증"""
    print("🔍 마이그레이션 검증 중...")
    
    verification_queries = [
        "SELECT COUNT(*) as user_count FROM users;",
        "SELECT COUNT(*) as analysis_count FROM sleep_analyses;",
        "SELECT COUNT(*) as api_usage_count FROM api_usage;",
        "SELECT COUNT(*) as feedback_count FROM llm_feedbacks;",
        "SELECT pg_typeof(id) as user_id_type FROM users LIMIT 1;"
    ]
    
    with engine.connect() as conn:
        for query in verification_queries:
            try:
                result = conn.execute(text(query)).fetchone()
                print(f"✅ 검증: {query} -> {result}")
            except Exception as e:
                print(f"❌ 검증 실패: {e}")
                return False
    
    return True

def main():
    parser = argparse.ArgumentParser(description="User ID를 UUID로 마이그레이션")
    parser.add_argument("--confirm", action="store_true", help="마이그레이션 실행 확인")
    parser.add_argument("--backup-only", action="store_true", help="백업만 수행")
    
    args = parser.parse_args()
    
    if not args.confirm and not args.backup_only:
        print("⚠️  이 스크립트는 데이터베이스를 변경합니다.")
        print("   실행하려면 --confirm 플래그를 사용하세요.")
        print("   백업만 하려면 --backup-only 플래그를 사용하세요.")
        return 1
    
    print("🚀 User ID UUID 마이그레이션 시작")
    print(f"📅 시작 시간: {datetime.now()}")
    print(f"🗄️  데이터베이스: {settings.database_url}")
    
    try:
        engine = create_migration_engine()
        
        # 1. 백업
        if not backup_existing_data(engine):
            print("❌ 백업 실패로 마이그레이션 중단")
            return 1
        
        if args.backup_only:
            print("✅ 백업 완료 (백업만 수행)")
            return 0
        
        # 2. UUID 매핑 생성
        if not create_uuid_mapping(engine):
            print("❌ UUID 매핑 생성 실패")
            return 1
        
        # 3. users 테이블 마이그레이션
        if not migrate_users_table(engine):
            print("❌ users 테이블 마이그레이션 실패")
            return 1
        
        # 4. 외래키 테이블들 마이그레이션
        if not migrate_foreign_keys(engine):
            print("❌ 외래키 마이그레이션 실패")
            return 1
        
        # 5. 검증
        if not verify_migration(engine):
            print("❌ 마이그레이션 검증 실패")
            return 1
        
        # 6. 정리
        cleanup_migration(engine)
        
        print("🎉 마이그레이션 완료!")
        print(f"📅 완료 시간: {datetime.now()}")
        
        return 0
        
    except Exception as e:
        print(f"❌ 마이그레이션 중 오류 발생: {e}")
        return 1

if __name__ == "__main__":
    sys.exit(main())
