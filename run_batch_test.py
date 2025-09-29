#!/usr/bin/env python3
"""
NEULBO ML Server 배치 테스트 러너

전체 테스트 데이터셋을 사용하여 시스템 성능을 종합적으로 평가합니다.
"""

import json
import requests
import time
import pandas as pd
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any
import statistics

class BatchTester:
    """배치 테스트 실행기"""
    
    def __init__(self, server_url: str = "http://localhost:8000"):
        self.server_url = server_url
        self.results = []
        
    def check_server_health(self) -> bool:
        """서버 상태 확인"""
        try:
            response = requests.get(f"{self.server_url}/api/ml/health/check", timeout=10)
            if response.status_code == 200:
                health = response.json()
                print(f"✅ 서버 상태: {health['status']}")
                print(f"   데이터베이스: {health['database_status']}")
                print(f"   모델: {health['model_status']}")
                return health['status'] == 'healthy'
            return False
        except Exception as e:
            print(f"❌ 서버 연결 실패: {str(e)}")
            return False
    
    def run_single_test(self, test_file: Path) -> Dict[str, Any]:
        """단일 테스트 실행"""
        try:
            # 테스트 데이터 로딩
            with open(test_file, 'r', encoding='utf-8') as f:
                test_data = json.load(f)
            
            print(f"🧪 테스트 실행: {test_file.name}")
            print(f"   📝 {test_data.get('description', 'No description')}")
            print(f"   ⏱️  시간: {test_data['metadata']['duration_hours']:.1f}시간")
            print(f"   📊 데이터: {test_data['metadata']['data_points']}개 포인트")
            
            # API 호출
            start_time = time.time()
            response = requests.post(
                f"{self.server_url}/api/ml/sleep/analyze",
                json={k: v for k, v in test_data.items() 
                      if k not in ['description', 'expected_stages', 'metadata']},
                timeout=120  # 2분 타임아웃
            )
            end_time = time.time()
            
            processing_time = end_time - start_time
            
            # 결과 처리
            if response.status_code == 200:
                result = response.json()
                
                test_result = {
                    'test_file': test_file.name,
                    'user_id': test_data['user_id'],
                    'description': test_data.get('description', ''),
                    'status': 'success',
                    'processing_time': round(processing_time, 2),
                    'analysis_id': result['analysis_id'],
                    'data_quality_score': result['data_quality_score'],
                    'total_sleep_time': result['summary_statistics']['total_sleep_time'],
                    'sleep_efficiency': result['summary_statistics']['sleep_efficiency'],
                    'wake_time': result['summary_statistics']['wake_time'],
                    'n1_time': result['summary_statistics']['n1_time'],
                    'n2_time': result['summary_statistics']['n2_time'],
                    'n3_time': result['summary_statistics']['n3_time'],
                    'rem_time': result['summary_statistics']['rem_time'],
                    'wake_percentage': result['summary_statistics']['wake_percentage'],
                    'n1_percentage': result['summary_statistics']['n1_percentage'],
                    'n2_percentage': result['summary_statistics']['n2_percentage'],
                    'n3_percentage': result['summary_statistics']['n3_percentage'],
                    'rem_percentage': result['summary_statistics']['rem_percentage'],
                    'model_version': result['model_version'],
                    'input_duration_hours': test_data['metadata']['duration_hours'],
                    'input_data_points': test_data['metadata']['data_points'],
                    'noise_level': test_data['metadata']['noise_level'],
                    'movement_level': test_data['metadata']['movement_level']
                }
                
                print(f"   ✅ 성공 ({processing_time:.1f}초)")
                print(f"      🎯 품질점수: {result['data_quality_score']:.3f}")
                print(f"      💤 총수면: {result['summary_statistics']['total_sleep_time']}분")
                print(f"      📈 효율성: {result['summary_statistics']['sleep_efficiency']:.1%}")
                
            else:
                test_result = {
                    'test_file': test_file.name,
                    'user_id': test_data['user_id'],
                    'description': test_data.get('description', ''),
                    'status': 'failed',
                    'processing_time': round(processing_time, 2),
                    'error_code': response.status_code,
                    'error_message': response.text[:200],
                    'input_duration_hours': test_data['metadata']['duration_hours'],
                    'input_data_points': test_data['metadata']['data_points']
                }
                
                print(f"   ❌ 실패 ({response.status_code})")
                print(f"      오류: {response.text[:100]}...")
            
            return test_result
            
        except Exception as e:
            print(f"   💥 예외 발생: {str(e)}")
            return {
                'test_file': test_file.name,
                'status': 'error',
                'error_message': str(e)
            }
    
    def run_batch_tests(self, dataset_dir: Path) -> List[Dict[str, Any]]:
        """모든 테스트 실행"""
        
        print(f"🚀 배치 테스트 시작")
        print(f"📁 데이터셋 디렉토리: {dataset_dir}")
        print("=" * 60)
        
        # 테스트 파일 목록
        test_files = list(dataset_dir.glob("*.json"))
        test_files = [f for f in test_files if f.name != "dataset_summary.json"]
        
        if not test_files:
            print("❌ 테스트 파일을 찾을 수 없습니다.")
            return []
        
        print(f"📊 총 {len(test_files)}개 테스트 케이스 발견")
        print()
        
        results = []
        
        for i, test_file in enumerate(test_files, 1):
            print(f"[{i}/{len(test_files)}] ", end="")
            result = self.run_single_test(test_file)
            results.append(result)
            print()
            
            # 테스트 간 잠시 대기 (서버 부하 방지)
            if i < len(test_files):
                time.sleep(1)
        
        return results
    
    def generate_report(self, results: List[Dict[str, Any]]) -> None:
        """테스트 결과 리포트 생성"""
        
        print("=" * 60)
        print("📊 배치 테스트 결과 리포트")
        print("=" * 60)
        
        # 기본 통계
        total_tests = len(results)
        successful_tests = len([r for r in results if r.get('status') == 'success'])
        failed_tests = total_tests - successful_tests
        
        print(f"📈 전체 결과:")
        print(f"   총 테스트: {total_tests}개")
        print(f"   성공: {successful_tests}개 ({successful_tests/total_tests*100:.1f}%)")
        print(f"   실패: {failed_tests}개 ({failed_tests/total_tests*100:.1f}%)")
        print()
        
        # 성공한 테스트들의 성능 분석
        successful_results = [r for r in results if r.get('status') == 'success']
        
        if successful_results:
            print("⚡ 성능 분석:")
            
            processing_times = [r['processing_time'] for r in successful_results]
            quality_scores = [r['data_quality_score'] for r in successful_results]
            sleep_efficiencies = [r['sleep_efficiency'] for r in successful_results]
            
            print(f"   처리 시간: 평균 {statistics.mean(processing_times):.1f}초")
            print(f"            최소 {min(processing_times):.1f}초, 최대 {max(processing_times):.1f}초")
            print(f"   품질 점수: 평균 {statistics.mean(quality_scores):.3f}")
            print(f"            최소 {min(quality_scores):.3f}, 최대 {max(quality_scores):.3f}")
            print(f"   수면 효율: 평균 {statistics.mean(sleep_efficiencies):.1%}")
            print(f"            최소 {min(sleep_efficiencies):.1%}, 최대 {max(sleep_efficiencies):.1%}")
            print()
        
        # 수면 단계 분포 분석
        if successful_results:
            print("💤 수면 단계 분석:")
            
            for stage in ['wake', 'n1', 'n2', 'n3', 'rem']:
                percentages = [r[f'{stage}_percentage'] for r in successful_results]
                avg_percentage = statistics.mean(percentages)
                print(f"   {stage.upper():4s}: 평균 {avg_percentage:5.1f}%")
            print()
        
        # 개별 테스트 결과
        print("📋 개별 테스트 결과:")
        print(f"{'파일명':<25} {'상태':<8} {'시간':<6} {'품질':<6} {'효율':<6} {'설명'}")
        print("-" * 80)
        
        for result in results:
            filename = result['test_file'][:24]
            status = "✅ 성공" if result.get('status') == 'success' else "❌ 실패"
            
            if result.get('status') == 'success':
                time_str = f"{result['processing_time']:.1f}s"
                quality_str = f"{result['data_quality_score']:.3f}"
                efficiency_str = f"{result['sleep_efficiency']:.1%}"
            else:
                time_str = quality_str = efficiency_str = "-"
            
            description = result.get('description', '')[:30]
            
            print(f"{filename:<25} {status:<8} {time_str:<6} {quality_str:<6} {efficiency_str:<6} {description}")
        
        # CSV 파일 저장
        self.save_results_csv(results)
        
        print()
        print("💾 결과가 batch_test_results.csv에 저장되었습니다.")
    
    def save_results_csv(self, results: List[Dict[str, Any]]) -> None:
        """결과를 CSV 파일로 저장"""
        
        df = pd.DataFrame(results)
        
        # 컬럼 순서 정리
        column_order = [
            'test_file', 'user_id', 'description', 'status', 'processing_time',
            'data_quality_score', 'total_sleep_time', 'sleep_efficiency',
            'wake_percentage', 'n1_percentage', 'n2_percentage', 'n3_percentage', 'rem_percentage',
            'input_duration_hours', 'input_data_points', 'noise_level', 'movement_level',
            'analysis_id', 'model_version', 'error_code', 'error_message'
        ]
        
        # 존재하는 컬럼만 선택
        available_columns = [col for col in column_order if col in df.columns]
        df = df[available_columns]
        
        # CSV 저장
        csv_filename = f"batch_test_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        df.to_csv(csv_filename, index=False, encoding='utf-8-sig')
        
        print(f"📊 상세 결과가 {csv_filename}에 저장되었습니다.")

def main():
    """메인 함수"""
    
    print("🧪 NEULBO ML Server 배치 테스트")
    print("=" * 50)
    
    # 데이터셋 디렉토리 확인
    dataset_dir = Path("test_dataset")
    
    if not dataset_dir.exists():
        print("❌ test_dataset 디렉토리가 없습니다.")
        print("   먼저 테스트 데이터셋을 생성하세요:")
        print("   python generate_test_dataset.py")
        return
    
    # 배치 테스터 초기화
    tester = BatchTester()
    
    # 서버 상태 확인
    if not tester.check_server_health():
        print("❌ 서버가 준비되지 않았습니다.")
        print("   서버를 먼저 시작하세요: python run_server.py")
        return
    
    print()
    
    # 배치 테스트 실행
    results = tester.run_batch_tests(dataset_dir)
    
    if results:
        # 리포트 생성
        tester.generate_report(results)
    else:
        print("❌ 실행할 테스트가 없습니다.")
    
    print("\n🏁 배치 테스트 완료!")

if __name__ == "__main__":
    main()
