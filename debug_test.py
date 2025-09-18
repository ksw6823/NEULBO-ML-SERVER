#!/usr/bin/env python3
"""
디버깅용 상세 테스트
"""

import requests
import json
from datetime import datetime, timedelta

def test_with_detailed_error():
    """상세 오류 정보를 포함한 테스트"""
    
    # 1시간 데이터 (120개 포인트, 30초 간격)
    start_time = datetime(2024, 1, 15, 22, 0, 0)
    end_time = start_time + timedelta(hours=1)
    
    # 1시간 동안 30초마다 데이터 포인트 생성
    accelerometer_data = []
    audio_data = []
    
    for i in range(120):  # 1시간 = 120 * 30초
        current_time = start_time + timedelta(seconds=i * 30)
        
        accelerometer_data.append({
            "timestamp": current_time.isoformat(),
            "x": 0.1 + (i * 0.001),  # 미세한 변화
            "y": -0.1 + (i * 0.0005),
            "z": 9.8 + (i * 0.0002)
        })
        
        audio_data.append({
            "timestamp": current_time.isoformat(),
            "amplitude": 0.05 + (i * 0.0001),
            "frequency_bands": [0.05, 0.1, 0.15, 0.1, 0.08, 0.05, 0.03, 0.02]
        })
    
    test_request = {
        "user_id": "1",  # 숫자 문자열로 수정
        "recording_start": start_time.isoformat(),
        "recording_end": end_time.isoformat(),
        "accelerometer_data": accelerometer_data,
        "audio_data": audio_data
    }
    
    print("🔍 디버그 테스트 시작...")
    print(f"📊 1시간 데이터: {len(test_request['accelerometer_data'])}개 포인트")
    
    try:
        response = requests.post(
            "http://localhost:8002/api/v1/sleep/analyze",
            json=test_request,
            timeout=30
        )
        
        print(f"📡 응답 코드: {response.status_code}")
        print(f"📄 응답 헤더: {dict(response.headers)}")
        
        if response.status_code == 200:
            result = response.json()
            print("✅ 성공!")
            print(f"📋 분석 ID: {result.get('analysis_id', 'N/A')}")
            return result
            
        else:
            print(f"❌ 실패: {response.status_code}")
            try:
                error_detail = response.json()
                print(f"📄 오류 상세:")
                print(json.dumps(error_detail, indent=2, ensure_ascii=False))
            except:
                print(f"📄 오류 텍스트: {response.text}")
            return None
            
    except requests.exceptions.Timeout:
        print("⏱️ 타임아웃 발생 (30초)")
        return None
    except Exception as e:
        print(f"💥 예외 발생: {str(e)}")
        return None

if __name__ == "__main__":
    test_with_detailed_error()
