#!/usr/bin/env python3
"""
NEULBO ML Server 테스트용 입력 데이터 생성

실제 XGBoost 모델에 넣을 수 있는 테스트 데이터를 생성합니다.
"""

import json
import requests
from datetime import datetime, timedelta
import numpy as np

def generate_test_input():
    """테스트용 수면 분석 입력 데이터 생성"""
    
    # 8시간 수면 시뮬레이션
    start_time = datetime(2024, 1, 15, 22, 0, 0)  # 밤 10시 시작
    end_time = start_time + timedelta(hours=8)     # 오전 6시 종료
    
    # 30초마다 데이터 포인트 생성 (8시간 = 960개 포인트)
    total_minutes = 8 * 60  # 480분
    data_points = total_minutes * 2  # 30초마다 = 960개
    
    accelerometer_data = []
    audio_data = []
    
    print("🔄 테스트 데이터 생성 중...")
    
    for i in range(data_points):
        current_time = start_time + timedelta(seconds=i * 30)
        
        # 수면 단계에 따른 시뮬레이션
        hours_elapsed = i / 120  # 시간 경과 (한 시간 = 120개 포인트)
        
        # 수면 단계 패턴 시뮬레이션
        if hours_elapsed < 0.5:
            # 초기 각성 단계 (밤 10:00-10:30)
            stage = "wake"
        elif hours_elapsed < 1.5:
            # 얕은 잠 (밤 10:30-11:30)
            stage = "n1_n2"
        elif hours_elapsed < 3.0:
            # 깊은 잠 (밤 11:30-새벽 1:00)
            stage = "n3"
        elif hours_elapsed < 4.5:
            # REM 수면 (새벽 1:00-2:30)
            stage = "rem"
        elif hours_elapsed < 6.0:
            # 다시 깊은 잠 (새벽 2:30-4:00)
            stage = "n3"
        elif hours_elapsed < 7.5:
            # REM 수면 (새벽 4:00-5:30)
            stage = "rem"
        else:
            # 아침 각성 (새벽 5:30-6:00)
            stage = "wake"
        
        # 가속도계 데이터 생성 (수면 단계별 움직임 패턴)
        if stage == "wake":
            # 각성 시: 더 많은 움직임
            base_x, base_y, base_z = 0.0, 0.0, 9.8
            noise_level = 0.5
        elif stage == "n1_n2":
            # 얕은 잠: 중간 정도 움직임
            base_x, base_y, base_z = 0.1, -0.2, 9.7
            noise_level = 0.2
        elif stage == "n3":
            # 깊은 잠: 최소 움직임
            base_x, base_y, base_z = 0.05, -0.1, 9.8
            noise_level = 0.1
        else:  # rem
            # REM 수면: 약간의 움직임
            base_x, base_y, base_z = 0.0, 0.0, 9.8
            noise_level = 0.15
        
        # 가속도계 값 생성 (중력 + 노이즈)
        acc_x = base_x + np.random.normal(0, noise_level)
        acc_y = base_y + np.random.normal(0, noise_level)
        acc_z = base_z + np.random.normal(0, noise_level * 0.5)
        
        accelerometer_data.append({
            "timestamp": current_time.isoformat(),
            "x": round(acc_x, 3),
            "y": round(acc_y, 3),
            "z": round(acc_z, 3)
        })
        
        # 오디오 데이터 생성 (수면 단계별 소음 패턴)
        if stage == "wake":
            base_amplitude = 0.15
            base_freq_pattern = [0.1, 0.2, 0.3, 0.2, 0.1, 0.05, 0.03, 0.02]
        elif stage == "n1_n2":
            base_amplitude = 0.08
            base_freq_pattern = [0.05, 0.1, 0.15, 0.1, 0.05, 0.03, 0.02, 0.01]
        elif stage == "n3":
            base_amplitude = 0.05
            base_freq_pattern = [0.03, 0.05, 0.08, 0.05, 0.03, 0.02, 0.01, 0.01]
        else:  # rem
            base_amplitude = 0.07
            base_freq_pattern = [0.04, 0.08, 0.12, 0.08, 0.04, 0.02, 0.02, 0.01]
        
        # 간헐적 코골이나 움직임 시뮬레이션
        if np.random.random() < 0.1:  # 10% 확률로 소음 증가
            amplitude = min(base_amplitude * 2, 0.95)
            freq_bands = [f * 1.5 for f in base_freq_pattern]
        else:
            amplitude = base_amplitude + np.random.normal(0, 0.02)
            freq_bands = [f + np.random.normal(0, 0.01) for f in base_freq_pattern]
        
        # 값 범위 제한
        amplitude = max(0.0, min(1.0, amplitude))
        freq_bands = [max(0.0, min(1.0, f)) for f in freq_bands]
        
        audio_data.append({
            "timestamp": current_time.isoformat(),
            "amplitude": round(amplitude, 3),
            "frequency_bands": [round(f, 3) for f in freq_bands]
        })
    
    # 테스트 요청 데이터 구성
    test_request = {
        "user_id": "550e8400-e29b-41d4-a716-446655440002",  # 테스트용 UUID
        "recording_start": start_time.isoformat(),
        "recording_end": end_time.isoformat(),
        "accelerometer_data": accelerometer_data,
        "audio_data": audio_data
    }
    
    print(f"✅ 테스트 데이터 생성 완료:")
    print(f"   - 시작 시간: {start_time}")
    print(f"   - 종료 시간: {end_time}")
    print(f"   - 총 시간: 8시간")
    print(f"   - 가속도계 데이터: {len(accelerometer_data)}개 포인트")
    print(f"   - 오디오 데이터: {len(audio_data)}개 포인트")
    print(f"   - 30초 간격 샘플링")
    
    return test_request

def save_test_data(test_data, filename="test_input.json"):
    """테스트 데이터를 JSON 파일로 저장"""
    with open(filename, 'w', encoding='utf-8') as f:
        json.dump(test_data, f, indent=2, ensure_ascii=False)
    print(f"📁 테스트 데이터가 {filename}에 저장되었습니다.")

def send_test_request(test_data, server_url="http://localhost:8000"):
    """실제 서버에 테스트 요청 전송"""
    try:
        print("🚀 서버에 테스트 요청 전송 중...")
        
        response = requests.post(
            f"{server_url}/api/ml/sleep/analyze",
            json=test_data,
            timeout=60  # 60초 타임아웃
        )
        
        if response.status_code == 200:
            result = response.json()
            print("✅ 분석 성공!")
            print(f"   - 분석 ID: {result['analysis_id']}")
            print(f"   - 총 수면 시간: {result['summary_statistics']['total_sleep_time']}분")
            print(f"   - 수면 효율성: {result['summary_statistics']['sleep_efficiency']:.1%}")
            print(f"   - 데이터 품질 점수: {result['data_quality_score']:.3f}")
            
            # 수면 단계별 시간 출력
            stats = result['summary_statistics']
            print("\n📊 수면 단계별 분석:")
            print(f"   - 각성: {stats['wake_time']}분 ({stats['wake_percentage']:.1f}%)")
            print(f"   - N1 단계: {stats['n1_time']}분 ({stats['n1_percentage']:.1f}%)")
            print(f"   - N2 단계: {stats['n2_time']}분 ({stats['n2_percentage']:.1f}%)")
            print(f"   - N3 단계: {stats['n3_time']}분 ({stats['n3_percentage']:.1f}%)")
            print(f"   - REM 단계: {stats['rem_time']}분 ({stats['rem_percentage']:.1f}%)")
            
            return result
        else:
            print(f"❌ 요청 실패: {response.status_code}")
            print(f"   오류 메시지: {response.text}")
            return None
            
    except requests.exceptions.ConnectionError:
        print("❌ 서버 연결 실패. 서버가 실행 중인지 확인하세요.")
        print("   서버 시작: python run_server.py")
        return None
    except Exception as e:
        print(f"❌ 오류 발생: {str(e)}")
        return None

def main():
    """메인 함수"""
    print("🧪 NEULBO ML Server 테스트 데이터 생성기")
    print("=" * 50)
    
    # 테스트 데이터 생성
    test_data = generate_test_input()
    
    # JSON 파일로 저장
    save_test_data(test_data)
    
    print("\n" + "=" * 50)
    print("📋 사용 방법:")
    print("1. 서버 시작: python run_server.py")
    print("2. 이 스크립트 실행: python test_input_example.py")
    print("3. 또는 생성된 test_input.json을 직접 API로 전송")
    
    # 서버 테스트 시도
    print("\n🔍 서버 테스트를 시도합니다...")
    result = send_test_request(test_data)
    
    if result:
        print("\n🎉 테스트 완료! 모델이 정상적으로 작동합니다.")
    else:
        print("\n⚠️  서버가 실행되지 않았거나 오류가 발생했습니다.")
        print("   생성된 test_input.json 파일을 수동으로 테스트할 수 있습니다.")

if __name__ == "__main__":
    main()
