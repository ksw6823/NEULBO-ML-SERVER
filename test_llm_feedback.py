#!/usr/bin/env python3
"""
LLM 피드백 기능 테스트
"""

import requests
import json

def test_llm_feedback():
    """LLM 피드백 API 테스트"""
    
    print("🤖 LLM 피드백 기능 테스트")
    print("=" * 50)
    
    # 1. LLM 헬스체크
    print("1. LLM 서비스 상태 확인...")
    try:
        response = requests.get("http://localhost:8002/api/ml/llm/health/llm")
        print(f"   응답 코드: {response.status_code}")
        
        if response.status_code == 200:
            health = response.json()
            print(f"   상태: {health['status']}")
            print(f"   모델: {health['model']}")
            print(f"   OLLAMA URL: {health['ollama_url']}")
            print(f"   사용 가능: {health['available']}")
        else:
            print(f"   오류: {response.text}")
    except Exception as e:
        print(f"   연결 오류: {str(e)}")
        print("   OLLAMA 서버가 실행되지 않았을 수 있습니다.")
    
    print()
    
    # 2. 수면 분석이 있는지 확인 (기존 분석 사용)
    print("2. 기존 수면 분석 데이터 확인...")
    # 이전 테스트에서 생성된 분석 ID 사용
    analysis_id = "1cff1b38-bb33-4d97-873b-18a42171d131"  # 이전 테스트 결과
    user_id = "1"
    
    # 3. LLM 피드백 요청
    print("3. LLM 피드백 생성 테스트...")
    
    feedback_requests = [
        {
            "user_id": user_id,
            "analysis_id": analysis_id,
            "user_prompt": "내 수면 패턴이 어떤가요? 개선할 점이 있다면 알려주세요."
        },
        {
            "user_id": user_id,
            "analysis_id": analysis_id,
            "user_prompt": "깊은 수면 시간을 늘리려면 어떻게 해야 할까요?"
        },
        {
            "user_id": user_id,
            "analysis_id": analysis_id,
            "user_prompt": "수면 효율이 낮은 이유가 무엇인지 궁금합니다."
        }
    ]
    
    feedback_ids = []
    
    for i, req in enumerate(feedback_requests, 1):
        print(f"\n   테스트 {i}: {req['user_prompt'][:30]}...")
        
        try:
            response = requests.post(
                "http://localhost:8002/api/ml/llm/feedback",
                json=req,
                timeout=60  # LLM 응답을 위해 긴 타임아웃
            )
            
            print(f"   응답 코드: {response.status_code}")
            
            if response.status_code == 200:
                result = response.json()
                feedback_ids.append(result['feedback_id'])
                
                print(f"   ✅ 피드백 생성 성공!")
                print(f"   📋 피드백 ID: {result['feedback_id']}")
                print(f"   🤖 사용 모델: {result['llm_model']}")
                print(f"   ⏱️ 응답 시간: {result['response_time_ms']:.0f}ms")
                print(f"   💬 LLM 응답 (일부): {result['llm_response'][:100]}...")
                
            else:
                error_detail = response.json() if response.status_code != 500 else response.text
                print(f"   ❌ 실패: {error_detail}")
                
        except requests.exceptions.Timeout:
            print("   ⏱️ 타임아웃 발생 (LLM 서버 응답 대기 중)")
        except Exception as e:
            print(f"   💥 오류: {str(e)}")
    
    print()
    
    # 4. 피드백 기록 조회 테스트
    if feedback_ids:
        print("4. 피드백 기록 조회 테스트...")
        
        try:
            response = requests.get(f"http://localhost:8002/api/ml/llm/feedback/history/{user_id}")
            
            if response.status_code == 200:
                history = response.json()
                print(f"   ✅ 기록 조회 성공: {len(history)}개 피드백")
                
                for i, feedback in enumerate(history[:3], 1):  # 최근 3개만
                    print(f"   📝 {i}. {feedback['user_prompt'][:30]}...")
                    print(f"      응답: {feedback['llm_response'][:50]}...")
                    print(f"      시간: {feedback['timestamp']}")
                    
            else:
                print(f"   ❌ 기록 조회 실패: {response.text}")
                
        except Exception as e:
            print(f"   💥 오류: {str(e)}")
    
    print()
    
    # 5. 개별 피드백 상세 조회
    if feedback_ids:
        print("5. 개별 피드백 상세 조회...")
        
        feedback_id = feedback_ids[0]
        try:
            response = requests.get(f"http://localhost:8002/api/ml/llm/feedback/{feedback_id}")
            
            if response.status_code == 200:
                detail = response.json()
                print(f"   ✅ 상세 조회 성공")
                print(f"   📋 ID: {detail['feedback_id']}")
                print(f"   💬 질문: {detail['user_prompt']}")
                print(f"   🤖 응답: {detail['llm_response']}")
                print(f"   📊 분석 요약: {detail['analysis_summary']}")
                
            else:
                print(f"   ❌ 상세 조회 실패: {response.text}")
                
        except Exception as e:
            print(f"   💥 오류: {str(e)}")
    
    print()
    print("🎉 LLM 피드백 테스트 완료!")
    print("=" * 50)
    
    return len(feedback_ids) > 0


if __name__ == "__main__":
    test_llm_feedback()
