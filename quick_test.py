#!/usr/bin/env python3
"""
포트 8002에서 실행 중인 서버를 위한 빠른 테스트
"""

import requests
import json
from datetime import datetime, timedelta

def test_quick_analysis():
    """빠른 수면 분석 테스트"""
    
    # 1시간 테스트 데이터 생성
    start_time = datetime(2024, 1, 15, 22, 0, 0)
    end_time = start_time + timedelta(hours=1)
    
    # 120개 데이터 포인트 (30초 간격)
    accelerometer_data = []
    audio_data = []
    
    for i in range(120):
        current_time = start_time + timedelta(seconds=i * 30)
        
        # 간단한 패턴 (처음엔 각성, 나중엔 수면)
        if i < 20:  # 처음 10분 - 각성
            acc_noise = 0.2
            audio_amp = 0.1
        else:  # 나머지 50분 - 수면
            acc_noise = 0.05
            audio_amp = 0.03
        
        accelerometer_data.append({
            "timestamp": current_time.isoformat(),
            "x": 0.05 + (acc_noise * (0.5 - __import__('random').random())),
            "y": -0.1 + (acc_noise * (0.5 - __import__('random').random())),
            "z": 9.8 + (acc_noise * 0.1 * (0.5 - __import__('random').random()))
        })
        
        audio_data.append({
            "timestamp": current_time.isoformat(),
            "amplitude": audio_amp + __import__('random').random() * 0.02,
            "frequency_bands": [
                0.05, 0.1, 0.15, 0.1, 0.08, 0.05, 0.03, 0.02
            ]
        })
    
    test_request = {
        "user_id": "550e8400-e29b-41d4-a716-446655440000",  # UUID 형태로 수정
        "recording_start": start_time.isoformat(),
        "recording_end": end_time.isoformat(),
        "accelerometer_data": accelerometer_data,
        "audio_data": audio_data
    }
    
    print("🚀 실제 XGBoost 모델로 수면 분석 테스트 시작...")
    print(f"📊 데이터: {len(accelerometer_data)}개 포인트 (1시간)")
    
    try:
        response = requests.post(
            "http://localhost:8002/api/ml/sleep/analyze",
            json=test_request,
            timeout=60
        )
        
        if response.status_code == 200:
            result = response.json()
            
            print("✅ 수면 분석 성공!")
            print(f"📋 분석 ID: {result['analysis_id']}")
            print(f"🤖 모델 버전: {result['model_version']}")
            print(f"🎯 데이터 품질: {result['data_quality_score']:.3f}")
            print(f"⏱️ 총 수면시간: {result['summary_statistics']['total_sleep_time']}분")
            print(f"📈 수면 효율: {result['summary_statistics']['sleep_efficiency']:.1%}")
            
            print("\n💤 수면 단계별 분석:")
            stats = result['summary_statistics']
            print(f"   각성: {stats['wake_time']}분 ({stats['wake_percentage']:.1f}%)")
            print(f"   N1:   {stats['n1_time']}분 ({stats['n1_percentage']:.1f}%)")
            print(f"   N2:   {stats['n2_time']}분 ({stats['n2_percentage']:.1f}%)")
            print(f"   N3:   {stats['n3_time']}분 ({stats['n3_percentage']:.1f}%)")
            print(f"   REM:  {stats['rem_time']}분 ({stats['rem_percentage']:.1f}%)")
            
            print(f"\n🔍 수면 단계 구간: {len(result['stage_intervals'])}개")
            print(f"📊 확률 데이터: {len(result['stage_probabilities'])}개")
            
            return result
            
        else:
            print(f"❌ 분석 실패: {response.status_code}")
            print(f"오류: {response.text}")
            return None
            
    except Exception as e:
        print(f"💥 오류 발생: {str(e)}")
        return None

def test_health():
    """헬스체크 테스트"""
    try:
        response = requests.get("http://localhost:8002/api/ml/health/check")
        if response.status_code == 200:
            health = response.json()
            print("✅ 헬스체크 성공")
            print(f"   상태: {health['status']}")
            print(f"   DB: {health['database_status']}")
            print(f"   모델: {health['model_status']}")
            return True
        else:
            print(f"❌ 헬스체크 실패: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ 헬스체크 오류: {str(e)}")
        return False

if __name__ == "__main__":
    print("🧪 NEULBO ML Server 실제 모델 테스트")
    print("=" * 50)
    
    # 1. 헬스체크
    if not test_health():
        print("서버가 준비되지 않았습니다.")
        exit(1)
    
    print()
    
    # 2. 수면 분석 테스트
    result = test_quick_analysis()
    
    if result:
        print("\n🎉 실제 XGBoost 모델 테스트 성공!")
        print("🔥 NEULBO ML Server가 정상 작동합니다!")
    else:
        print("\n⚠️ 테스트 실패")
    
    print("\n" + "=" * 50)
