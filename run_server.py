#!/usr/bin/env python3
"""
NEULBO ML Server 실행 스크립트

이 스크립트는 FastAPI 서버를 시작합니다.
개발 모드와 프로덕션 모드를 지원합니다.
"""

import asyncio
import sys
import os
from pathlib import Path

# 프로젝트 루트를 Python 경로에 추가
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

import uvicorn
from app.config.settings import settings

def main():
    """메인 실행 함수"""
    
    print("🚀 NEULBO ML Server 시작 중...")
    print(f"📍 서버 주소: {settings.host}:{settings.port}")
    print(f"🐛 디버그 모드: {settings.debug}")
    print(f"📊 로그 레벨: {settings.log_level}")
    
    # uvicorn 설정
    uvicorn_config = {
        "app": "app.main:app",
        "host": settings.host,
        "port": settings.port,
        "reload": settings.debug,
        "log_level": settings.log_level.lower(),
        "access_log": True,
    }
    
    # 프로덕션 환경에서는 추가 설정
    if not settings.debug:
        uvicorn_config.update({
            "workers": 1,  # 단일 워커로 시작 (필요시 증가)
            "loop": "asyncio",
            "http": "httptools",
        })
    
    print("✨ 서버 설정 완료")
    print("📡 서버에 접속하려면 브라우저에서 다음 주소를 열어주세요:")
    print(f"   - 메인 페이지: http://{settings.host}:{settings.port}")
    print(f"   - API 문서: http://{settings.host}:{settings.port}/docs")
    print(f"   - 헬스체크: http://{settings.host}:{settings.port}/api/ml/health/check")
    print("\n종료하려면 Ctrl+C를 누르세요.")
    print("-" * 50)
    
    try:
        uvicorn.run(**uvicorn_config)
    except KeyboardInterrupt:
        print("\n👋 서버 종료 중...")
    except Exception as e:
        print(f"❌ 서버 시작 중 오류 발생: {e}")
        return 1
    
    return 0


if __name__ == "__main__":
    sys.exit(main())

