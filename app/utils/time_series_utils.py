from datetime import datetime, timedelta
from typing import List, Dict, Any, Tuple
import numpy as np
import pandas as pd
from scipy import stats
import structlog

from app.models.request_models import AccelerometerReading, AudioReading
from app.models.internal_models import DataQualityReport
from app.config.settings import settings

logger = structlog.get_logger()


async def check_data_quality(
    accelerometer_data: List[AccelerometerReading],
    audio_data: List[AudioReading]
) -> DataQualityReport:
    """데이터 품질 평가"""
    try:
        logger.info("데이터 품질 평가 시작")
        
        # 가속도계 데이터 품질 평가
        accel_quality = await _assess_accelerometer_quality(accelerometer_data)
        
        # 오디오 데이터 품질 평가
        audio_quality = await _assess_audio_quality(audio_data)
        
        # 전체 품질 점수 계산
        overall_score = (accel_quality["overall_score"] + audio_quality["overall_score"]) / 2
        
        # 누락 데이터 비율 계산
        missing_data_percentage = await _calculate_missing_data_percentage(
            accelerometer_data, audio_data
        )
        
        # 이상값 비율 계산
        outlier_percentage = await _calculate_outlier_percentage(
            accelerometer_data, audio_data
        )
        
        # 노이즈 수준 평가
        noise_level = await _assess_noise_level(accelerometer_data, audio_data)
        
        # 권장사항 생성
        recommendations = await _generate_recommendations(
            overall_score, accel_quality, audio_quality, 
            missing_data_percentage, outlier_percentage, noise_level
        )
        
        report = DataQualityReport(
            overall_score=overall_score,
            accelerometer_quality=accel_quality,
            audio_quality=audio_quality,
            missing_data_percentage=missing_data_percentage,
            outlier_percentage=outlier_percentage,
            noise_level=noise_level,
            recommendations=recommendations
        )
        
        logger.info(f"데이터 품질 평가 완료: 전체 점수 {overall_score:.3f}")
        return report
        
    except Exception as e:
        logger.error(f"데이터 품질 평가 중 오류: {str(e)}")
        # 기본 보고서 반환
        return DataQualityReport(
            overall_score=0.5,
            accelerometer_quality={"overall_score": 0.5, "error": str(e)},
            audio_quality={"overall_score": 0.5, "error": str(e)},
            missing_data_percentage=0.0,
            outlier_percentage=0.0,
            noise_level=0.5,
            recommendations=["데이터 품질 평가 중 오류가 발생했습니다"]
        )


async def _assess_accelerometer_quality(
    accelerometer_data: List[AccelerometerReading]
) -> Dict[str, float]:
    """가속도계 데이터 품질 평가"""
    try:
        if not accelerometer_data:
            return {"overall_score": 0.0, "error": "데이터 없음"}
        
        # DataFrame으로 변환
        df = pd.DataFrame([
            {
                'timestamp': reading.timestamp,
                'x': reading.x,
                'y': reading.y,
                'z': reading.z
            }
            for reading in accelerometer_data
        ])
        
        quality_scores = {}
        
        # 1. 데이터 완정성 (시간 간격 일관성)
        time_consistency_score = await _calculate_time_consistency_score(df['timestamp'])
        quality_scores['time_consistency'] = time_consistency_score
        
        # 2. 신호 품질 (적절한 변동성)
        signal_quality_score = await _calculate_signal_quality_score(
            df[['x', 'y', 'z']].values
        )
        quality_scores['signal_quality'] = signal_quality_score
        
        # 3. 포화 없음 (센서 한계 내 값들)
        saturation_score = await _calculate_saturation_score(
            df[['x', 'y', 'z']].values, threshold=18.0
        )
        quality_scores['no_saturation'] = saturation_score
        
        # 4. 노이즈 수준
        noise_score = await _calculate_noise_score(df[['x', 'y', 'z']].values)
        quality_scores['low_noise'] = noise_score
        
        # 5. 움직임 감지 (수면 중 예상되는 움직임 패턴)
        movement_score = await _calculate_movement_score(df[['x', 'y', 'z']].values)
        quality_scores['movement_pattern'] = movement_score
        
        # 전체 점수 계산 (가중 평균)
        weights = {
            'time_consistency': 0.3,
            'signal_quality': 0.2,
            'no_saturation': 0.2,
            'low_noise': 0.2,
            'movement_pattern': 0.1
        }
        
        overall_score = sum(
            quality_scores[key] * weights[key] 
            for key in weights
        )
        
        quality_scores['overall_score'] = overall_score
        
        return quality_scores
        
    except Exception as e:
        logger.error(f"가속도계 품질 평가 중 오류: {str(e)}")
        return {"overall_score": 0.0, "error": str(e)}


async def _assess_audio_quality(
    audio_data: List[AudioReading]
) -> Dict[str, float]:
    """오디오 데이터 품질 평가"""
    try:
        if not audio_data:
            return {"overall_score": 0.0, "error": "데이터 없음"}
        
        # 기본 데이터 추출
        amplitudes = [reading.amplitude for reading in audio_data]
        freq_bands = [reading.frequency_bands for reading in audio_data]
        timestamps = [reading.timestamp for reading in audio_data]
        
        quality_scores = {}
        
        # 1. 시간 일관성
        time_consistency_score = await _calculate_time_consistency_score(timestamps)
        quality_scores['time_consistency'] = time_consistency_score
        
        # 2. 신호 레벨 (적절한 음성 입력 레벨)
        signal_level_score = await _calculate_audio_signal_level_score(amplitudes)
        quality_scores['signal_level'] = signal_level_score
        
        # 3. 주파수 대역 품질
        freq_quality_score = await _calculate_frequency_quality_score(freq_bands)
        quality_scores['frequency_quality'] = freq_quality_score
        
        # 4. 포화 없음
        saturation_score = await _calculate_saturation_score(
            np.array(amplitudes).reshape(-1, 1), threshold=0.95
        )
        quality_scores['no_saturation'] = saturation_score
        
        # 5. 노이즈 수준
        noise_score = await _calculate_audio_noise_score(amplitudes)
        quality_scores['low_noise'] = noise_score
        
        # 전체 점수 계산
        weights = {
            'time_consistency': 0.25,
            'signal_level': 0.25,
            'frequency_quality': 0.25,
            'no_saturation': 0.15,
            'low_noise': 0.1
        }
        
        overall_score = sum(
            quality_scores[key] * weights[key] 
            for key in weights
        )
        
        quality_scores['overall_score'] = overall_score
        
        return quality_scores
        
    except Exception as e:
        logger.error(f"오디오 품질 평가 중 오류: {str(e)}")
        return {"overall_score": 0.0, "error": str(e)}


async def _calculate_time_consistency_score(timestamps: List[datetime]) -> float:
    """시간 일관성 점수 계산"""
    try:
        if len(timestamps) < 2:
            return 0.0
        
        # 시간 간격 계산
        intervals = [
            (timestamps[i] - timestamps[i-1]).total_seconds()
            for i in range(1, len(timestamps))
        ]
        
        if not intervals:
            return 0.0
        
        expected_interval = 1.0 / settings.sensor_sampling_rate
        
        # 간격의 표준편차 계산
        std_dev = np.std(intervals)
        
        # 표준편차가 작을수록 높은 점수
        max_acceptable_std = expected_interval * 0.1  # 10% 허용
        
        if std_dev <= max_acceptable_std:
            return 1.0
        else:
            # 지수적으로 감소
            return max(0.0, np.exp(-std_dev / max_acceptable_std))
        
    except Exception:
        return 0.0


async def _calculate_signal_quality_score(data: np.ndarray) -> float:
    """신호 품질 점수 계산"""
    try:
        if data.size == 0:
            return 0.0
        
        # 신호의 동적 범위 계산
        signal_range = np.max(data) - np.min(data)
        
        # 적절한 범위 (0.1g ~ 10g)
        ideal_min, ideal_max = 0.1, 10.0
        
        if ideal_min <= signal_range <= ideal_max:
            return 1.0
        elif signal_range < ideal_min:
            # 너무 작은 신호
            return signal_range / ideal_min
        else:
            # 너무 큰 신호
            return max(0.0, 1.0 - (signal_range - ideal_max) / ideal_max)
        
    except Exception:
        return 0.0


async def _calculate_saturation_score(data: np.ndarray, threshold: float) -> float:
    """포화 점수 계산"""
    try:
        if data.size == 0:
            return 0.0
        
        # 포화 근처 값들의 비율 계산
        saturated_count = np.sum(np.abs(data) >= threshold)
        saturation_ratio = saturated_count / data.size
        
        # 포화 비율이 낮을수록 높은 점수
        return max(0.0, 1.0 - saturation_ratio * 10)  # 10% 포화 시 0점
        
    except Exception:
        return 0.0


async def _calculate_noise_score(data: np.ndarray) -> float:
    """노이즈 점수 계산"""
    try:
        if data.size == 0:
            return 0.0
        
        # 고주파 노이즈 추정 (연속 차분의 표준편차)
        if len(data) > 1:
            diff = np.diff(data.flatten())
            noise_level = np.std(diff)
            
            # 적절한 노이즈 수준 (0.1g 이하)
            max_acceptable_noise = 0.1
            
            if noise_level <= max_acceptable_noise:
                return 1.0
            else:
                return max(0.0, 1.0 - noise_level / max_acceptable_noise)
        
        return 1.0
        
    except Exception:
        return 0.0


async def _calculate_movement_score(data: np.ndarray) -> float:
    """움직임 패턴 점수 계산"""
    try:
        if data.size == 0:
            return 0.0
        
        # 움직임의 변동성 계산
        magnitude = np.sqrt(np.sum(data**2, axis=1))
        movement_variance = np.var(magnitude)
        
        # 수면 중 예상되는 움직임 범위 (0.01 ~ 1.0)
        ideal_min, ideal_max = 0.01, 1.0
        
        if ideal_min <= movement_variance <= ideal_max:
            return 1.0
        elif movement_variance < ideal_min:
            # 너무 적은 움직임 (센서 문제 가능성)
            return movement_variance / ideal_min
        else:
            # 너무 많은 움직임
            return max(0.0, 1.0 - (movement_variance - ideal_max) / ideal_max)
        
    except Exception:
        return 0.0


async def _calculate_audio_signal_level_score(amplitudes: List[float]) -> float:
    """오디오 신호 레벨 점수 계산"""
    try:
        if not amplitudes:
            return 0.0
        
        mean_amplitude = np.mean(amplitudes)
        max_amplitude = np.max(amplitudes)
        
        # 적절한 신호 레벨 (0.01 ~ 0.8)
        if 0.01 <= mean_amplitude <= 0.8 and max_amplitude < 0.95:
            return 1.0
        elif mean_amplitude < 0.01:
            # 너무 작은 신호
            return mean_amplitude / 0.01
        else:
            # 너무 큰 신호 또는 포화
            return max(0.0, 1.0 - (mean_amplitude - 0.8) / 0.2)
        
    except Exception:
        return 0.0


async def _calculate_frequency_quality_score(freq_bands: List[List[float]]) -> float:
    """주파수 대역 품질 점수 계산"""
    try:
        if not freq_bands:
            return 0.0
        
        freq_array = np.array(freq_bands)
        
        # 각 밴드의 변동성 확인
        band_variances = np.var(freq_array, axis=0)
        
        # 적절한 변동성 (너무 일정하지도 않고 너무 변동적이지도 않음)
        ideal_variance = 0.1
        
        scores = []
        for variance in band_variances:
            if variance <= ideal_variance:
                scores.append(1.0)
            else:
                scores.append(max(0.0, 1.0 - (variance - ideal_variance) / ideal_variance))
        
        return np.mean(scores)
        
    except Exception:
        return 0.0


async def _calculate_audio_noise_score(amplitudes: List[float]) -> float:
    """오디오 노이즈 점수 계산"""
    try:
        if len(amplitudes) < 2:
            return 1.0
        
        # 급격한 변화 감지
        diffs = np.abs(np.diff(amplitudes))
        mean_diff = np.mean(diffs)
        
        # 적절한 변화 수준 (0.05 이하)
        max_acceptable_diff = 0.05
        
        if mean_diff <= max_acceptable_diff:
            return 1.0
        else:
            return max(0.0, 1.0 - mean_diff / max_acceptable_diff)
        
    except Exception:
        return 0.0


async def _calculate_missing_data_percentage(
    accelerometer_data: List[AccelerometerReading],
    audio_data: List[AudioReading]
) -> float:
    """누락 데이터 비율 계산"""
    try:
        if not accelerometer_data or not audio_data:
            return 100.0
        
        # 예상 데이터 포인트 수 계산
        accel_start = min(r.timestamp for r in accelerometer_data)
        accel_end = max(r.timestamp for r in accelerometer_data)
        duration = (accel_end - accel_start).total_seconds()
        
        expected_count = int(duration * settings.sensor_sampling_rate)
        actual_count = len(accelerometer_data)
        
        missing_percentage = max(0.0, (expected_count - actual_count) / expected_count * 100)
        
        return min(100.0, missing_percentage)
        
    except Exception:
        return 0.0


async def _calculate_outlier_percentage(
    accelerometer_data: List[AccelerometerReading],
    audio_data: List[AudioReading]
) -> float:
    """이상값 비율 계산"""
    try:
        outlier_count = 0
        total_count = 0
        
        # 가속도계 이상값 검출
        accel_values = []
        for reading in accelerometer_data:
            accel_values.extend([reading.x, reading.y, reading.z])
        
        if accel_values:
            # IQR 방법으로 이상값 검출
            q1, q3 = np.percentile(accel_values, [25, 75])
            iqr = q3 - q1
            lower_bound = q1 - 1.5 * iqr
            upper_bound = q3 + 1.5 * iqr
            
            outlier_count += sum(
                1 for v in accel_values 
                if v < lower_bound or v > upper_bound
            )
            total_count += len(accel_values)
        
        # 오디오 이상값 검출
        audio_amplitudes = [reading.amplitude for reading in audio_data]
        
        if audio_amplitudes:
            q1, q3 = np.percentile(audio_amplitudes, [25, 75])
            iqr = q3 - q1
            lower_bound = q1 - 1.5 * iqr
            upper_bound = q3 + 1.5 * iqr
            
            outlier_count += sum(
                1 for v in audio_amplitudes 
                if v < lower_bound or v > upper_bound
            )
            total_count += len(audio_amplitudes)
        
        if total_count == 0:
            return 0.0
        
        return (outlier_count / total_count) * 100
        
    except Exception:
        return 0.0


async def _assess_noise_level(
    accelerometer_data: List[AccelerometerReading],
    audio_data: List[AudioReading]
) -> float:
    """전체 노이즈 수준 평가"""
    try:
        noise_scores = []
        
        # 가속도계 노이즈
        if len(accelerometer_data) > 1:
            accel_changes = []
            for i in range(1, len(accelerometer_data)):
                prev = accelerometer_data[i-1]
                curr = accelerometer_data[i]
                change = abs(curr.x - prev.x) + abs(curr.y - prev.y) + abs(curr.z - prev.z)
                accel_changes.append(change)
            
            if accel_changes:
                avg_change = np.mean(accel_changes)
                # 0.5g 이하 변화를 정상으로 간주
                accel_noise_score = min(1.0, avg_change / 0.5)
                noise_scores.append(accel_noise_score)
        
        # 오디오 노이즈
        if len(audio_data) > 1:
            amplitude_changes = [
                abs(audio_data[i].amplitude - audio_data[i-1].amplitude)
                for i in range(1, len(audio_data))
            ]
            
            if amplitude_changes:
                avg_change = np.mean(amplitude_changes)
                # 0.1 이하 변화를 정상으로 간주
                audio_noise_score = min(1.0, avg_change / 0.1)
                noise_scores.append(audio_noise_score)
        
        return np.mean(noise_scores) if noise_scores else 0.0
        
    except Exception:
        return 0.5


async def _generate_recommendations(
    overall_score: float,
    accel_quality: Dict[str, float],
    audio_quality: Dict[str, float],
    missing_data_percentage: float,
    outlier_percentage: float,
    noise_level: float
) -> List[str]:
    """품질 개선 권장사항 생성"""
    recommendations = []
    
    try:
        if overall_score < 0.7:
            recommendations.append("전반적인 데이터 품질이 낮습니다. 센서 설정을 확인하세요.")
        
        if missing_data_percentage > 5:
            recommendations.append("데이터 누락이 많습니다. 센서 연결 상태를 확인하세요.")
        
        if outlier_percentage > 10:
            recommendations.append("이상값이 많이 감지됩니다. 센서 교정을 확인하세요.")
        
        if noise_level > 0.7:
            recommendations.append("노이즈 수준이 높습니다. 안정적인 환경에서 측정하세요.")
        
        # 가속도계 관련 권장사항
        if accel_quality.get("time_consistency", 1.0) < 0.8:
            recommendations.append("가속도계 샘플링이 불규칙합니다. 센서 드라이버를 확인하세요.")
        
        if accel_quality.get("no_saturation", 1.0) < 0.8:
            recommendations.append("가속도계 센서 포화가 감지됩니다. 센서 위치를 조정하세요.")
        
        # 오디오 관련 권장사항
        if audio_quality.get("signal_level", 1.0) < 0.7:
            recommendations.append("오디오 신호 레벨이 부적절합니다. 마이크 설정을 확인하세요.")
        
        if audio_quality.get("no_saturation", 1.0) < 0.8:
            recommendations.append("오디오 입력 포화가 감지됩니다. 마이크 감도를 조정하세요.")
        
        if not recommendations:
            recommendations.append("데이터 품질이 양호합니다.")
        
    except Exception:
        recommendations.append("품질 평가 중 오류가 발생했습니다.")
    
    return recommendations

