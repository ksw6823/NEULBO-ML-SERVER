#!/usr/bin/env python3
"""
NEULBO ML Server 성능 벤치마크

다양한 데이터 크기와 조건에서 시스템 성능을 측정합니다.
"""

import json
import requests
import time
import threading
import numpy as np
import matplotlib.pyplot as plt
import pandas as pd
from datetime import datetime, timedelta
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import List, Dict, Any

class PerformanceBenchmark:
    """성능 벤치마크 테스트"""
    
    def __init__(self, server_url: str = "http://localhost:8000"):
        self.server_url = server_url
        self.results = []
    
    def generate_benchmark_data(self, duration_hours: float, user_id: str) -> dict:
        """벤치마크용 데이터 생성"""
        
        start_time = datetime(2024, 1, 15, 22, 0, 0)
        end_time = start_time + timedelta(hours=duration_hours)
        
        # 30초 간격 데이터 포인트
        data_points = int(duration_hours * 120)  # 시간당 120개 포인트
        
        accelerometer_data = []
        audio_data = []
        
        for i in range(data_points):
            current_time = start_time + timedelta(seconds=i * 30)
            
            # 가벼운 랜덤 데이터 (빠른 생성)
            accelerometer_data.append({
                "timestamp": current_time.isoformat(),
                "x": np.random.normal(0.05, 0.1),
                "y": np.random.normal(-0.1, 0.1),
                "z": np.random.normal(9.8, 0.1)
            })
            
            audio_data.append({
                "timestamp": current_time.isoformat(),
                "amplitude": np.random.exponential(0.05),
                "frequency_bands": np.random.exponential(0.05, 8).tolist()
            })
        
        return {
            "user_id": user_id,
            "recording_start": start_time.isoformat(),
            "recording_end": end_time.isoformat(),
            "accelerometer_data": accelerometer_data,
            "audio_data": audio_data
        }
    
    def single_request_test(self, duration_hours: float, test_id: str) -> Dict[str, Any]:
        """단일 요청 성능 테스트"""
        
        print(f"📊 {test_id}: {duration_hours}시간 데이터 테스트")
        
        # 데이터 생성 시간 측정
        data_gen_start = time.time()
        test_data = self.generate_benchmark_data(duration_hours, f"bench_{test_id}")
        data_gen_time = time.time() - data_gen_start
        
        data_size_mb = len(json.dumps(test_data).encode('utf-8')) / (1024 * 1024)
        
        print(f"   📁 데이터 크기: {data_size_mb:.2f} MB")
        print(f"   📈 데이터 포인트: {len(test_data['accelerometer_data'])}개")
        print(f"   ⏱️  데이터 생성: {data_gen_time:.2f}초")
        
        # API 요청 성능 측정
        try:
            request_start = time.time()
            response = requests.post(
                f"{self.server_url}/api/v1/sleep/analyze",
                json=test_data,
                timeout=300  # 5분 타임아웃
            )
            request_time = time.time() - request_start
            
            if response.status_code == 200:
                result = response.json()
                
                benchmark_result = {
                    'test_id': test_id,
                    'duration_hours': duration_hours,
                    'data_points': len(test_data['accelerometer_data']),
                    'data_size_mb': data_size_mb,
                    'data_gen_time': data_gen_time,
                    'request_time': request_time,
                    'total_time': data_gen_time + request_time,
                    'throughput_points_per_sec': len(test_data['accelerometer_data']) / request_time,
                    'throughput_mb_per_sec': data_size_mb / request_time,
                    'status': 'success',
                    'data_quality_score': result['data_quality_score'],
                    'analysis_id': result['analysis_id']
                }
                
                print(f"   ✅ 성공: {request_time:.2f}초")
                print(f"   🚀 처리량: {benchmark_result['throughput_points_per_sec']:.1f} points/sec")
                print(f"   💾 처리량: {benchmark_result['throughput_mb_per_sec']:.2f} MB/sec")
                
            else:
                benchmark_result = {
                    'test_id': test_id,
                    'duration_hours': duration_hours,
                    'data_points': len(test_data['accelerometer_data']),
                    'data_size_mb': data_size_mb,
                    'request_time': request_time,
                    'status': 'failed',
                    'error_code': response.status_code,
                    'error_message': response.text[:100]
                }
                
                print(f"   ❌ 실패: {response.status_code}")
        
        except Exception as e:
            benchmark_result = {
                'test_id': test_id,
                'duration_hours': duration_hours,
                'status': 'error',
                'error_message': str(e)
            }
            print(f"   💥 오류: {str(e)}")
        
        return benchmark_result
    
    def data_size_scaling_test(self) -> List[Dict[str, Any]]:
        """데이터 크기별 확장성 테스트"""
        
        print("📈 데이터 크기별 확장성 테스트")
        print("=" * 50)
        
        # 다양한 데이터 크기 테스트
        test_durations = [1, 2, 4, 6, 8, 10, 12]  # 시간
        results = []
        
        for i, duration in enumerate(test_durations):
            print(f"\n[{i+1}/{len(test_durations)}] ", end="")
            result = self.single_request_test(duration, f"scale_{i+1}")
            results.append(result)
        
        return results
    
    def concurrent_load_test(self, num_concurrent: int = 5, duration_hours: float = 4) -> List[Dict[str, Any]]:
        """동시 요청 부하 테스트"""
        
        print(f"\n🔄 동시 요청 부하 테스트 ({num_concurrent}개 동시 요청)")
        print("=" * 50)
        
        def single_concurrent_request(request_id: int) -> Dict[str, Any]:
            return self.single_request_test(duration_hours, f"concurrent_{request_id}")
        
        # 동시 요청 실행
        start_time = time.time()
        
        with ThreadPoolExecutor(max_workers=num_concurrent) as executor:
            futures = [
                executor.submit(single_concurrent_request, i) 
                for i in range(num_concurrent)
            ]
            
            results = []
            for i, future in enumerate(as_completed(futures)):
                result = future.result()
                results.append(result)
                print(f"완료: {i+1}/{num_concurrent}")
        
        total_time = time.time() - start_time
        
        print(f"\n📊 동시 요청 테스트 결과:")
        print(f"   총 시간: {total_time:.2f}초")
        print(f"   성공 요청: {len([r for r in results if r.get('status') == 'success'])}개")
        print(f"   실패 요청: {len([r for r in results if r.get('status') != 'success'])}개")
        
        return results
    
    def memory_stress_test(self) -> Dict[str, Any]:
        """메모리 스트레스 테스트 (매우 큰 데이터)"""
        
        print("\n💾 메모리 스트레스 테스트 (24시간 데이터)")
        print("=" * 50)
        
        # 24시간 데이터 (매우 큰 데이터셋)
        return self.single_request_test(24, "memory_stress")
    
    def generate_performance_report(self, scaling_results: List[Dict], concurrent_results: List[Dict], stress_result: Dict):
        """성능 리포트 생성"""
        
        print("\n" + "=" * 60)
        print("📊 성능 벤치마크 리포트")
        print("=" * 60)
        
        # 확장성 테스트 분석
        successful_scaling = [r for r in scaling_results if r.get('status') == 'success']
        
        if successful_scaling:
            print("\n📈 데이터 크기별 확장성:")
            print(f"{'시간':<6} {'포인트':<8} {'크기(MB)':<10} {'처리시간':<8} {'처리량(pts/s)':<12}")
            print("-" * 50)
            
            for result in successful_scaling:
                print(f"{result['duration_hours']:<6.1f} "
                      f"{result['data_points']:<8} "
                      f"{result['data_size_mb']:<10.2f} "
                      f"{result['request_time']:<8.2f} "
                      f"{result['throughput_points_per_sec']:<12.1f}")
            
            # 선형성 분석
            durations = [r['duration_hours'] for r in successful_scaling]
            times = [r['request_time'] for r in successful_scaling]
            
            if len(durations) > 1:
                correlation = np.corrcoef(durations, times)[0, 1]
                print(f"\n   📊 선형성 (상관계수): {correlation:.3f}")
                
                if correlation > 0.9:
                    print("   ✅ 좋은 선형 확장성")
                elif correlation > 0.7:
                    print("   ⚠️  적당한 확장성")
                else:
                    print("   ❌ 비선형 확장성 - 최적화 필요")
        
        # 동시 요청 테스트 분석
        successful_concurrent = [r for r in concurrent_results if r.get('status') == 'success']
        
        if successful_concurrent:
            avg_time = np.mean([r['request_time'] for r in successful_concurrent])
            min_time = min([r['request_time'] for r in successful_concurrent])
            max_time = max([r['request_time'] for r in successful_concurrent])
            
            print(f"\n🔄 동시 요청 성능:")
            print(f"   평균 처리 시간: {avg_time:.2f}초")
            print(f"   최소 처리 시간: {min_time:.2f}초")
            print(f"   최대 처리 시간: {max_time:.2f}초")
            print(f"   시간 편차: {max_time - min_time:.2f}초")
        
        # 스트레스 테스트 결과
        if stress_result.get('status') == 'success':
            print(f"\n💾 메모리 스트레스 테스트:")
            print(f"   24시간 데이터 처리: ✅ 성공")
            print(f"   처리 시간: {stress_result['request_time']:.2f}초")
            print(f"   데이터 크기: {stress_result['data_size_mb']:.2f} MB")
            print(f"   처리량: {stress_result['throughput_points_per_sec']:.1f} points/sec")
        else:
            print(f"\n💾 메모리 스트레스 테스트: ❌ 실패")
        
        # 성능 지표 요약
        all_successful = successful_scaling + successful_concurrent
        if stress_result.get('status') == 'success':
            all_successful.append(stress_result)
        
        if all_successful:
            all_times = [r['request_time'] for r in all_successful]
            all_throughputs = [r['throughput_points_per_sec'] for r in all_successful]
            
            print(f"\n🎯 전체 성능 요약:")
            print(f"   평균 처리 시간: {np.mean(all_times):.2f}초")
            print(f"   최고 처리량: {max(all_throughputs):.1f} points/sec")
            print(f"   최저 처리량: {min(all_throughputs):.1f} points/sec")
        
        # CSV 저장
        self.save_benchmark_csv(scaling_results + concurrent_results + [stress_result])
    
    def save_benchmark_csv(self, results: List[Dict]):
        """벤치마크 결과를 CSV로 저장"""
        
        df = pd.DataFrame(results)
        csv_filename = f"benchmark_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        df.to_csv(csv_filename, index=False, encoding='utf-8-sig')
        
        print(f"\n💾 벤치마크 결과가 {csv_filename}에 저장되었습니다.")

def main():
    """메인 함수"""
    
    print("⚡ NEULBO ML Server 성능 벤치마크")
    print("=" * 50)
    
    # 서버 상태 확인
    try:
        response = requests.get("http://localhost:8000/api/v1/health/check", timeout=10)
        if response.status_code != 200:
            print("❌ 서버가 준비되지 않았습니다.")
            return
    except:
        print("❌ 서버에 연결할 수 없습니다.")
        print("   서버를 먼저 시작하세요: python run_server.py")
        return
    
    benchmark = PerformanceBenchmark()
    
    print("🚀 벤치마크 테스트를 시작합니다...")
    print("⚠️  주의: 이 테스트는 시간이 오래 걸릴 수 있습니다.")
    
    # 1. 데이터 크기별 확장성 테스트
    scaling_results = benchmark.data_size_scaling_test()
    
    # 2. 동시 요청 부하 테스트
    concurrent_results = benchmark.concurrent_load_test(num_concurrent=3, duration_hours=2)
    
    # 3. 메모리 스트레스 테스트 (선택적)
    print("\n❓ 메모리 스트레스 테스트를 실행하시겠습니까? (24시간 데이터, 매우 오래 걸림)")
    run_stress = input("   y/N: ").lower().strip() == 'y'
    
    if run_stress:
        stress_result = benchmark.memory_stress_test()
    else:
        stress_result = {'status': 'skipped', 'test_id': 'memory_stress'}
    
    # 4. 리포트 생성
    benchmark.generate_performance_report(scaling_results, concurrent_results, stress_result)
    
    print("\n🏁 성능 벤치마크 완료!")

if __name__ == "__main__":
    main()
