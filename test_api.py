#!/usr/bin/env python3
"""
간단한 API 테스트 스크립트

빠르게 API를 테스트할 수 있는 스크립트입니다.
"""

import requests
import json

def test_health_check():
    """헬스체크 테스트"""
    print("🔍 헬스체크 테스트...")
    try:
        response = requests.get("http://localhost:8000/api/ml/health/check", timeout=10)
        
        if response.status_code == 200:
            result = response.json()
            print(f"✅ 서버 상태: {result['status']}")
            print(f"   데이터베이스: {result['database_status']}")
            print(f"   모델 상태: {result['model_status']}")
            print(f"   버전: {result['version']}")
            return True
        else:
            print(f"❌ 헬스체크 실패: {response.status_code}")
            return False
            
    except Exception as e:
        print(f"❌ 연결 오류: {str(e)}")
        return False

def test_simple_analysis():
    """간단한 분석 테스트"""
    print("\n🧪 간단한 수면 분석 테스트...")
    
    # 간단한 테스트 데이터 (30분간)
    test_data = {
        "user_id": "test_user_quick",
        "recording_start": "2024-01-15T22:00:00",
        "recording_end": "2024-01-16T06:00:00",  # 8시간으로 변경 (최소 1시간 필요)
        "accelerometer_data": [],
        "audio_data": []
    }
    
    # 8시간 동안 5분 간격으로 데이터 생성 (96개 포인트)
    from datetime import datetime, timedelta
    start_time = datetime(2024, 1, 15, 22, 0, 0)
    
    for i in range(96):  # 8시간 * 12포인트/시간
        current_time = start_time + timedelta(minutes=i * 5)
        
        # 시간에 따른 수면 패턴 시뮬레이션
        hour = i // 12  # 경과 시간
        if hour < 1:
            # 첫 1시간: 각성 -> 얕은 잠
            x, y, z = 0.1, -0.2, 9.8
            amplitude = 0.1
        elif hour < 3:
            # 1-3시간: 깊은 잠
            x, y, z = 0.02, -0.05, 9.8
            amplitude = 0.04
        elif hour < 5:
            # 3-5시간: REM 수면
            x, y, z = 0.05, -0.1, 9.78
            amplitude = 0.06
        elif hour < 7:
            # 5-7시간: 다시 깊은 잠
            x, y, z = 0.01, -0.03, 9.81
            amplitude = 0.03
        else:
            # 7-8시간: 아침 각성
            x, y, z = 0.08, -0.15, 9.75
            amplitude = 0.08
        
        test_data["accelerometer_data"].append({
            "timestamp": current_time.isoformat(),
            "x": x,
            "y": y,
            "z": z
        })
        
        test_data["audio_data"].append({
            "timestamp": current_time.isoformat(),
            "amplitude": amplitude,
            "frequency_bands": [0.05, 0.1, 0.15, 0.1, 0.08, 0.05, 0.03, 0.02]
        })
    
    try:
        print(f"   📤 {len(test_data['accelerometer_data'])}개 데이터 포인트 전송 중...")
        response = requests.post(
            "http://localhost:8000/api/ml/sleep/analyze",
            json=test_data,
            timeout=60
        )
        
        if response.status_code == 200:
            result = response.json()
            print("✅ 분석 성공!")
            print(f"   📋 분석 ID: {result['analysis_id']}")
            print(f"   ⏱️  총 수면 시간: {result['summary_statistics']['total_sleep_time']}분")
            print(f"   📊 수면 효율성: {result['summary_statistics']['sleep_efficiency']:.1%}")
            print(f"   🎯 데이터 품질: {result['data_quality_score']:.3f}")
            
            # 수면 단계 요약
            stats = result['summary_statistics']
            print("\n   💤 수면 단계별 분석:")
            stages = [
                ("각성", stats['wake_time'], stats['wake_percentage']),
                ("N1", stats['n1_time'], stats['n1_percentage']),
                ("N2", stats['n2_time'], stats['n2_percentage']),
                ("N3", stats['n3_time'], stats['n3_percentage']),
                ("REM", stats['rem_time'], stats['rem_percentage'])
            ]
            
            for stage_name, time_min, percentage in stages:
                print(f"      {stage_name:3s}: {time_min:3d}분 ({percentage:4.1f}%)")
            
            return result['analysis_id']
            
        else:
            print(f"❌ 분석 실패: {response.status_code}")
            print(f"   오류: {response.text}")
            return None
            
    except Exception as e:
        print(f"❌ 요청 오류: {str(e)}")
        return None

def test_result_lookup(analysis_id):
    """분석 결과 조회 테스트"""
    print(f"\n🔎 분석 결과 조회 테스트 (ID: {analysis_id})...")
    
    try:
        response = requests.get(
            f"http://localhost:8000/api/ml/sleep/result/{analysis_id}",
            timeout=10
        )
        
        if response.status_code == 200:
            result = response.json()
            print("✅ 결과 조회 성공!")
            print(f"   📅 분석 시간: {result['analysis_timestamp']}")
            print(f"   🤖 모델 버전: {result['model_version']}")
            print(f"   📊 수면 구간: {len(result['stage_intervals'])}개")
            print(f"   📈 확률 데이터: {len(result['stage_probabilities'])}개")
            return True
        else:
            print(f"❌ 조회 실패: {response.status_code}")
            return False
            
    except Exception as e:
        print(f"❌ 조회 오류: {str(e)}")
        return False

def main():
    """메인 테스트 함수"""
    print("🧪 NEULBO ML Server API 테스트")
    print("=" * 50)
    
    # 1. 헬스체크
    if not test_health_check():
        print("\n❌ 서버가 실행되지 않았습니다.")
        print("   서버를 먼저 시작하세요: python run_server.py")
        return
    
    # 2. 수면 분석 테스트
    analysis_id = test_simple_analysis()
    
    if analysis_id:
        # 3. 결과 조회 테스트
        test_result_lookup(analysis_id)
        
        print("\n🎉 모든 테스트 완료!")
        print(f"   📋 생성된 분석 ID: {analysis_id}")
        print(f"   🌐 API 문서: http://localhost:8000/docs")
    else:
        print("\n⚠️  분석 테스트 실패")
    
    print("\n" + "=" * 50)

if __name__ == "__main__":
    main()
