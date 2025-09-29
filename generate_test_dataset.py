#!/usr/bin/env python3
"""
NEULBO ML Server 테스트 데이터셋 생성기

다양한 수면 패턴과 시나리오를 포함한 포괄적인 테스트 데이터셋을 생성합니다.
"""

import json
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from pathlib import Path
import random

class SleepDataGenerator:
    """수면 데이터 생성기"""
    
    def __init__(self):
        self.sampling_interval = 30  # 30초 간격
        
    def generate_normal_sleep(self, user_id: str, date: str = "2024-01-15") -> dict:
        """정상적인 8시간 수면 패턴"""
        start_time = datetime.fromisoformat(f"{date}T22:00:00")
        end_time = start_time + timedelta(hours=8)
        
        # 정상 수면 사이클 (90분 사이클 x 5-6회)
        sleep_stages = self._create_normal_sleep_cycle()
        
        return self._generate_sleep_data(
            user_id, start_time, end_time, sleep_stages,
            description="정상적인 8시간 수면"
        )
    
    def generate_insomnia_sleep(self, user_id: str, date: str = "2024-01-16") -> dict:
        """불면증 패턴 - 자주 깨는 수면"""
        start_time = datetime.fromisoformat(f"{date}T23:30:00")
        end_time = start_time + timedelta(hours=6.5)
        
        # 불면증 패턴: 자주 각성, 얕은 잠 위주
        sleep_stages = []
        current_hour = 0
        
        while current_hour < 6.5:
            if current_hour < 0.5:
                sleep_stages.extend(["wake"] * 60)  # 30분 각성
            elif current_hour < 1.5:
                sleep_stages.extend(["n1"] * 40 + ["wake"] * 20)  # 얕은 잠 + 각성
            elif current_hour < 3:
                sleep_stages.extend(["n2"] * 30 + ["n1"] * 20 + ["wake"] * 10)
            elif current_hour < 4.5:
                sleep_stages.extend(["wake"] * 15 + ["n1"] * 25 + ["n2"] * 20)
            elif current_hour < 5.5:
                sleep_stages.extend(["n2"] * 35 + ["rem"] * 25)
            else:
                sleep_stages.extend(["wake"] * 30 + ["n1"] * 30)
            
            current_hour += 1
        
        return self._generate_sleep_data(
            user_id, start_time, end_time, sleep_stages,
            description="불면증 패턴 - 자주 깨는 수면"
        )
    
    def generate_deep_sleeper(self, user_id: str, date: str = "2024-01-17") -> dict:
        """깊은 잠 위주의 수면 패턴"""
        start_time = datetime.fromisoformat(f"{date}T21:30:00")
        end_time = start_time + timedelta(hours=9)
        
        # 깊은 잠이 많은 패턴
        sleep_stages = []
        current_hour = 0
        
        while current_hour < 9:
            if current_hour < 0.5:
                sleep_stages.extend(["wake"] * 20 + ["n1"] * 40)
            elif current_hour < 1.5:
                sleep_stages.extend(["n1"] * 20 + ["n2"] * 40)
            elif current_hour < 4:
                sleep_stages.extend(["n3"] * 50 + ["n2"] * 10)  # 많은 깊은 잠
            elif current_hour < 6:
                sleep_stages.extend(["n3"] * 30 + ["rem"] * 30)
            elif current_hour < 8:
                sleep_stages.extend(["rem"] * 40 + ["n2"] * 20)
            else:
                sleep_stages.extend(["n1"] * 30 + ["wake"] * 30)
            
            current_hour += 1
        
        return self._generate_sleep_data(
            user_id, start_time, end_time, sleep_stages,
            description="깊은 잠 위주의 건강한 수면"
        )
    
    def generate_short_sleep(self, user_id: str, date: str = "2024-01-18") -> dict:
        """짧은 수면 (4시간)"""
        start_time = datetime.fromisoformat(f"{date}T02:00:00")
        end_time = start_time + timedelta(hours=4)
        
        # 짧지만 효율적인 수면
        sleep_stages = []
        current_hour = 0
        
        while current_hour < 4:
            if current_hour < 0.5:
                sleep_stages.extend(["wake"] * 10 + ["n1"] * 20 + ["n2"] * 30)
            elif current_hour < 2:
                sleep_stages.extend(["n3"] * 40 + ["n2"] * 20)  # 빠른 깊은 잠
            elif current_hour < 3.5:
                sleep_stages.extend(["rem"] * 35 + ["n2"] * 25)
            else:
                sleep_stages.extend(["n1"] * 20 + ["wake"] * 40)
            
            current_hour += 1
        
        return self._generate_sleep_data(
            user_id, start_time, end_time, sleep_stages,
            description="짧은 수면 (4시간)"
        )
    
    def generate_elderly_sleep(self, user_id: str, date: str = "2024-01-19") -> dict:
        """고령자 수면 패턴 - 얕고 자주 깨는 패턴"""
        start_time = datetime.fromisoformat(f"{date}T21:00:00")
        end_time = start_time + timedelta(hours=7)
        
        # 고령자 특성: N3 적음, 자주 각성
        sleep_stages = []
        current_hour = 0
        
        while current_hour < 7:
            if current_hour < 1:
                sleep_stages.extend(["wake"] * 30 + ["n1"] * 30)
            elif current_hour < 2.5:
                sleep_stages.extend(["n1"] * 25 + ["n2"] * 25 + ["wake"] * 10)
            elif current_hour < 4:
                sleep_stages.extend(["n2"] * 35 + ["n3"] * 10 + ["wake"] * 15)  # 적은 N3
            elif current_hour < 5.5:
                sleep_stages.extend(["rem"] * 20 + ["n1"] * 20 + ["wake"] * 20)
            else:
                sleep_stages.extend(["n1"] * 25 + ["wake"] * 35)
            
            current_hour += 1
        
        return self._generate_sleep_data(
            user_id, start_time, end_time, sleep_stages,
            description="고령자 수면 패턴"
        )
    
    def generate_shift_worker_sleep(self, user_id: str, date: str = "2024-01-20") -> dict:
        """교대근무자 낮잠 패턴"""
        start_time = datetime.fromisoformat(f"{date}T14:00:00")
        end_time = start_time + timedelta(hours=6)
        
        # 낮잠의 특성: REM 적음, 얕은 잠 많음
        sleep_stages = []
        current_hour = 0
        
        while current_hour < 6:
            if current_hour < 0.5:
                sleep_stages.extend(["wake"] * 40 + ["n1"] * 20)
            elif current_hour < 2:
                sleep_stages.extend(["n1"] * 30 + ["n2"] * 30)
            elif current_hour < 4:
                sleep_stages.extend(["n2"] * 35 + ["n3"] * 25)
            elif current_hour < 5:
                sleep_stages.extend(["n3"] * 20 + ["rem"] * 15 + ["n2"] * 25)  # 적은 REM
            else:
                sleep_stages.extend(["n1"] * 30 + ["wake"] * 30)
            
            current_hour += 1
        
        return self._generate_sleep_data(
            user_id, start_time, end_time, sleep_stages,
            description="교대근무자 낮잠"
        )
    
    def generate_noisy_environment(self, user_id: str, date: str = "2024-01-21") -> dict:
        """소음 환경에서의 수면"""
        start_time = datetime.fromisoformat(f"{date}T23:00:00")
        end_time = start_time + timedelta(hours=7)
        
        # 소음으로 인한 수면 방해
        sleep_stages = self._create_normal_sleep_cycle()
        
        return self._generate_sleep_data(
            user_id, start_time, end_time, sleep_stages,
            description="소음 환경에서의 수면",
            noise_level="high"
        )
    
    def generate_restless_sleep(self, user_id: str, date: str = "2024-01-22") -> dict:
        """뒤척임이 많은 수면"""
        start_time = datetime.fromisoformat(f"{date}T22:30:00")
        end_time = start_time + timedelta(hours=8)
        
        # 정상 패턴이지만 움직임이 많음
        sleep_stages = self._create_normal_sleep_cycle()
        
        return self._generate_sleep_data(
            user_id, start_time, end_time, sleep_stages,
            description="뒤척임이 많은 수면",
            movement_level="high"
        )
    
    def _create_normal_sleep_cycle(self) -> list:
        """정상적인 수면 사이클 생성"""
        stages = []
        
        # 8시간 = 480분 = 960개 30초 구간
        # 각성 (30분)
        stages.extend(["wake"] * 60)
        
        # 1사이클 (90분): N1->N2->N3->REM
        for cycle in range(5):  # 5사이클
            if cycle == 0:  # 첫 사이클: N3 많음
                stages.extend(["n1"] * 10 + ["n2"] * 40 + ["n3"] * 120 + ["rem"] * 10)
            elif cycle <= 2:  # 2-3사이클: N3 보통
                stages.extend(["n1"] * 5 + ["n2"] * 30 + ["n3"] * 80 + ["rem"] * 65)
            else:  # 4-5사이클: REM 많음
                stages.extend(["n1"] * 5 + ["n2"] * 25 + ["n3"] * 30 + ["rem"] * 120)
        
        # 아침 각성 (30분)
        stages.extend(["wake"] * 60)
        
        return stages[:960]  # 정확히 8시간
    
    def _generate_sleep_data(
        self, 
        user_id: str, 
        start_time: datetime, 
        end_time: datetime, 
        sleep_stages: list,
        description: str = "",
        noise_level: str = "normal",
        movement_level: str = "normal"
    ) -> dict:
        """실제 센서 데이터 생성"""
        
        duration_minutes = int((end_time - start_time).total_seconds() / 60)
        data_points = duration_minutes * 2  # 30초마다
        
        accelerometer_data = []
        audio_data = []
        
        for i in range(data_points):
            current_time = start_time + timedelta(seconds=i * 30)
            
            # 현재 수면 단계
            stage_idx = min(i, len(sleep_stages) - 1)
            stage = sleep_stages[stage_idx] if sleep_stages else "n2"
            
            # 가속도계 데이터 생성
            acc_data = self._generate_accelerometer_reading(stage, movement_level)
            acc_data["timestamp"] = current_time.isoformat()
            accelerometer_data.append(acc_data)
            
            # 오디오 데이터 생성
            audio_data_point = self._generate_audio_reading(stage, noise_level)
            audio_data_point["timestamp"] = current_time.isoformat()
            audio_data.append(audio_data_point)
        
        return {
            "user_id": user_id,
            "recording_start": start_time.isoformat(),
            "recording_end": end_time.isoformat(),
            "accelerometer_data": accelerometer_data,
            "audio_data": audio_data,
            "description": description,
            "expected_stages": sleep_stages,
            "metadata": {
                "duration_hours": duration_minutes / 60,
                "data_points": data_points,
                "noise_level": noise_level,
                "movement_level": movement_level
            }
        }
    
    def _generate_accelerometer_reading(self, stage: str, movement_level: str) -> dict:
        """수면 단계별 가속도계 데이터 생성"""
        
        # 기본 중력 벡터
        base_x, base_y, base_z = 0.0, 0.0, 9.8
        
        # 단계별 기본 자세
        if stage == "wake":
            base_x, base_y, base_z = 0.1, -0.2, 9.7
            base_noise = 0.3
        elif stage == "n1":
            base_x, base_y, base_z = 0.05, -0.1, 9.8
            base_noise = 0.15
        elif stage == "n2":
            base_x, base_y, base_z = 0.02, -0.05, 9.81
            base_noise = 0.08
        elif stage == "n3":
            base_x, base_y, base_z = 0.01, -0.02, 9.82
            base_noise = 0.04
        else:  # rem
            base_x, base_y, base_z = 0.03, -0.08, 9.79
            base_noise = 0.12
        
        # 움직임 수준 조정
        if movement_level == "high":
            base_noise *= 2.5
        elif movement_level == "low":
            base_noise *= 0.5
        
        # 간헐적 큰 움직임 (뒤척임)
        if random.random() < 0.05:  # 5% 확률
            base_noise *= 3
        
        # 노이즈 추가
        x = base_x + np.random.normal(0, base_noise)
        y = base_y + np.random.normal(0, base_noise)
        z = base_z + np.random.normal(0, base_noise * 0.3)  # Z축은 덜 변함
        
        return {
            "x": round(x, 3),
            "y": round(y, 3),
            "z": round(z, 3)
        }
    
    def _generate_audio_reading(self, stage: str, noise_level: str) -> dict:
        """수면 단계별 오디오 데이터 생성"""
        
        # 단계별 기본 소음 수준
        if stage == "wake":
            base_amplitude = 0.12
            base_freq = [0.08, 0.15, 0.25, 0.18, 0.12, 0.08, 0.05, 0.03]
        elif stage == "n1":
            base_amplitude = 0.07
            base_freq = [0.05, 0.10, 0.16, 0.12, 0.08, 0.05, 0.03, 0.02]
        elif stage == "n2":
            base_amplitude = 0.05
            base_freq = [0.03, 0.08, 0.12, 0.09, 0.06, 0.04, 0.02, 0.01]
        elif stage == "n3":
            base_amplitude = 0.04
            base_freq = [0.02, 0.06, 0.09, 0.07, 0.05, 0.03, 0.02, 0.01]
        else:  # rem
            base_amplitude = 0.06
            base_freq = [0.04, 0.08, 0.13, 0.10, 0.07, 0.04, 0.03, 0.02]
        
        # 소음 수준 조정
        if noise_level == "high":
            base_amplitude *= 2.0
            base_freq = [f * 1.8 for f in base_freq]
        elif noise_level == "low":
            base_amplitude *= 0.6
            base_freq = [f * 0.7 for f in base_freq]
        
        # 코골이 시뮬레이션 (N2, N3에서 가끔 발생)
        if stage in ["n2", "n3"] and random.random() < 0.15:  # 15% 확률
            base_amplitude *= 2.5
            base_freq[0] *= 3  # 저주파 증가
        
        # 노이즈 추가
        amplitude = base_amplitude + np.random.normal(0, 0.02)
        frequency_bands = [
            f + np.random.normal(0, 0.01) for f in base_freq
        ]
        
        # 값 범위 제한
        amplitude = max(0.0, min(1.0, amplitude))
        frequency_bands = [max(0.0, min(1.0, f)) for f in frequency_bands]
        
        return {
            "amplitude": round(amplitude, 3),
            "frequency_bands": [round(f, 3) for f in frequency_bands]
        }

def generate_complete_dataset():
    """완전한 테스트 데이터셋 생성"""
    
    generator = SleepDataGenerator()
    
    # 다양한 테스트 케이스
    test_cases = [
        ("normal_sleeper_1", generator.generate_normal_sleep, "2024-01-15"),
        ("normal_sleeper_2", generator.generate_normal_sleep, "2024-01-16"), 
        ("insomnia_patient", generator.generate_insomnia_sleep, "2024-01-17"),
        ("deep_sleeper", generator.generate_deep_sleeper, "2024-01-18"),
        ("short_sleeper", generator.generate_short_sleep, "2024-01-19"),
        ("elderly_person", generator.generate_elderly_sleep, "2024-01-20"),
        ("shift_worker", generator.generate_shift_worker_sleep, "2024-01-21"),
        ("noisy_environment", generator.generate_noisy_environment, "2024-01-22"),
        ("restless_sleeper", generator.generate_restless_sleep, "2024-01-23"),
    ]
    
    # 데이터셋 디렉토리 생성
    dataset_dir = Path("test_dataset")
    dataset_dir.mkdir(exist_ok=True)
    
    dataset_summary = {
        "dataset_info": {
            "name": "NEULBO Sleep Analysis Test Dataset",
            "version": "1.0",
            "created_date": datetime.now().isoformat(),
            "total_cases": len(test_cases),
            "description": "다양한 수면 패턴을 포함한 포괄적인 테스트 데이터셋"
        },
        "test_cases": []
    }
    
    print("🏗️  테스트 데이터셋 생성 중...")
    
    for user_id, generator_func, date in test_cases:
        print(f"   📁 {user_id} 데이터 생성 중...")
        
        # 데이터 생성
        test_data = generator_func(user_id, date)
        
        # 개별 파일 저장
        filename = f"{user_id}.json"
        filepath = dataset_dir / filename
        
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(test_data, f, indent=2, ensure_ascii=False)
        
        # 요약 정보 추가
        case_summary = {
            "user_id": user_id,
            "filename": filename,
            "description": test_data["description"],
            "duration_hours": test_data["metadata"]["duration_hours"],
            "data_points": test_data["metadata"]["data_points"],
            "recording_start": test_data["recording_start"],
            "recording_end": test_data["recording_end"],
            "noise_level": test_data["metadata"]["noise_level"],
            "movement_level": test_data["metadata"]["movement_level"]
        }
        dataset_summary["test_cases"].append(case_summary)
    
    # 데이터셋 요약 파일 저장
    with open(dataset_dir / "dataset_summary.json", 'w', encoding='utf-8') as f:
        json.dump(dataset_summary, f, indent=2, ensure_ascii=False)
    
    # README 파일 생성
    readme_content = f"""# NEULBO Sleep Analysis Test Dataset

## 📋 개요
이 데이터셋은 NEULBO ML Server의 수면 분석 기능을 테스트하기 위한 다양한 수면 패턴 데이터를 포함합니다.

## 📁 파일 구조
```
test_dataset/
├── dataset_summary.json    # 데이터셋 전체 요약
├── README.md              # 이 파일
├── normal_sleeper_1.json  # 정상 수면 패턴 #1
├── normal_sleeper_2.json  # 정상 수면 패턴 #2
├── insomnia_patient.json  # 불면증 패턴
├── deep_sleeper.json      # 깊은 잠 위주 패턴
├── short_sleeper.json     # 짧은 수면 (4시간)
├── elderly_person.json    # 고령자 수면 패턴
├── shift_worker.json      # 교대근무자 낮잠
├── noisy_environment.json # 소음 환경 수면
└── restless_sleeper.json  # 뒤척임 많은 수면
```

## 🧪 테스트 케이스

### 1. 정상 수면 패턴 (normal_sleeper_1, normal_sleeper_2)
- **시간**: 22:00-06:00 (8시간)
- **특징**: 정상적인 수면 사이클 (N1→N2→N3→REM)
- **용도**: 기본 기능 테스트

### 2. 불면증 패턴 (insomnia_patient)
- **시간**: 23:30-06:00 (6.5시간)
- **특징**: 자주 깨는 패턴, 얕은 잠 위주
- **용도**: 수면 장애 감지 테스트

### 3. 깊은 잠 패턴 (deep_sleeper)
- **시간**: 21:30-06:30 (9시간)
- **특징**: N3 단계가 많은 건강한 수면
- **용도**: 깊은 잠 감지 성능 테스트

### 4. 짧은 수면 (short_sleeper)
- **시간**: 02:00-06:00 (4시간)
- **특징**: 짧지만 효율적인 수면
- **용도**: 최소 시간 요구사항 테스트

### 5. 고령자 패턴 (elderly_person)
- **시간**: 21:00-04:00 (7시간)
- **특징**: N3 적음, 자주 각성
- **용도**: 연령별 수면 패턴 구분

### 6. 교대근무자 (shift_worker)
- **시간**: 14:00-20:00 (6시간, 낮잠)
- **특징**: REM 적음, 얕은 잠 많음
- **용도**: 비정상적 수면 시간 테스트

### 7. 소음 환경 (noisy_environment)
- **시간**: 23:00-06:00 (7시간)
- **특징**: 높은 오디오 노이즈 레벨
- **용도**: 환경 요인 영향 테스트

### 8. 뒤척임 많음 (restless_sleeper)
- **시간**: 22:30-06:30 (8시간)
- **특징**: 높은 움직임 레벨
- **용도**: 움직임 패턴 분석 테스트

## 🚀 사용 방법

### 개별 파일 테스트
```bash
curl -X POST "http://localhost:8000/api/ml/sleep/analyze" \\
     -H "Content-Type: application/json" \\
     -d @test_dataset/normal_sleeper_1.json
```

### 배치 테스트 (Python)
```python
import json
import requests
from pathlib import Path

dataset_dir = Path("test_dataset")
for json_file in dataset_dir.glob("*.json"):
    if json_file.name == "dataset_summary.json":
        continue
    
    with open(json_file) as f:
        test_data = json.load(f)
    
    response = requests.post(
        "http://localhost:8000/api/ml/sleep/analyze",
        json=test_data
    )
    
    print(f"{{json_file.name}}: {{response.status_code}}")
```

## 📊 데이터 형식

각 JSON 파일은 다음 구조를 가집니다:

```json
{{
  "user_id": "사용자_ID",
  "recording_start": "2024-01-15T22:00:00",
  "recording_end": "2024-01-16T06:00:00",
  "accelerometer_data": [...],
  "audio_data": [...],
  "description": "설명",
  "expected_stages": [...],
  "metadata": {{
    "duration_hours": 8.0,
    "data_points": 960,
    "noise_level": "normal",
    "movement_level": "normal"
  }}
}}
```

## 🎯 예상 결과

각 테스트 케이스는 특정한 수면 패턴을 시뮬레이션하므로, 모델의 예측 결과가 해당 패턴과 일치하는지 확인할 수 있습니다.

생성일: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
"""
    
    with open(dataset_dir / "README.md", 'w', encoding='utf-8') as f:
        f.write(readme_content)
    
    print(f"✅ 테스트 데이터셋 생성 완료!")
    print(f"   📁 저장 위치: {dataset_dir.absolute()}")
    print(f"   📊 총 {len(test_cases)}개 테스트 케이스")
    print(f"   📄 요약 파일: dataset_summary.json")
    print(f"   📖 사용 가이드: README.md")
    
    return dataset_summary

if __name__ == "__main__":
    generate_complete_dataset()
