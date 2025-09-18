from typing import List, Dict, Any, Tuple
import numpy as np
import pandas as pd
from scipy import signal, fft
from scipy.stats import entropy
import structlog

from app.models.request_models import AccelerometerReading, AudioReading

logger = structlog.get_logger()


class SensorProcessor:
    """센서 데이터 처리 유틸리티"""
    
    @staticmethod
    async def calculate_magnitude(
        accelerometer_data: List[AccelerometerReading]
    ) -> List[float]:
        """가속도계 크기 계산 (3축 벡터의 크기)"""
        try:
            magnitudes = []
            for reading in accelerometer_data:
                magnitude = np.sqrt(reading.x**2 + reading.y**2 + reading.z**2)
                magnitudes.append(float(magnitude))
            
            return magnitudes
            
        except Exception as e:
            logger.error(f"가속도계 크기 계산 중 오류: {str(e)}")
            return []
    
    @staticmethod
    async def calculate_tilt_angles(
        accelerometer_data: List[AccelerometerReading]
    ) -> List[Dict[str, float]]:
        """기울기 각도 계산"""
        try:
            angles = []
            
            for reading in accelerometer_data:
                # 중력 벡터에 대한 기울기 각도 계산
                magnitude = np.sqrt(reading.x**2 + reading.y**2 + reading.z**2)
                
                if magnitude > 0:
                    # 각 축에 대한 기울기 각도 (라디안 -> 도)
                    pitch = np.arcsin(reading.x / magnitude) * 180 / np.pi
                    roll = np.arcsin(reading.y / magnitude) * 180 / np.pi
                    
                    angles.append({
                        "pitch": float(pitch),
                        "roll": float(roll),
                        "magnitude": float(magnitude)
                    })
                else:
                    angles.append({
                        "pitch": 0.0,
                        "roll": 0.0,
                        "magnitude": 0.0
                    })
            
            return angles
            
        except Exception as e:
            logger.error(f"기울기 각도 계산 중 오류: {str(e)}")
            return []
    
    @staticmethod
    async def detect_movement_events(
        accelerometer_data: List[AccelerometerReading],
        threshold: float = 0.5,
        min_duration: int = 3
    ) -> List[Dict[str, Any]]:
        """움직임 이벤트 감지"""
        try:
            # 가속도계 크기 계산
            magnitudes = await SensorProcessor.calculate_magnitude(accelerometer_data)
            
            if not magnitudes:
                return []
            
            # 움직임 감지 (임계값 초과)
            movement_mask = np.array(magnitudes) > threshold
            
            # 연속된 움직임 구간 찾기
            events = []
            in_movement = False
            start_idx = 0
            
            for i, is_moving in enumerate(movement_mask):
                if is_moving and not in_movement:
                    # 움직임 시작
                    in_movement = True
                    start_idx = i
                elif not is_moving and in_movement:
                    # 움직임 종료
                    duration = i - start_idx
                    if duration >= min_duration:
                        events.append({
                            "start_time": accelerometer_data[start_idx].timestamp,
                            "end_time": accelerometer_data[i-1].timestamp,
                            "duration_seconds": duration,
                            "max_magnitude": max(magnitudes[start_idx:i]),
                            "mean_magnitude": np.mean(magnitudes[start_idx:i])
                        })
                    in_movement = False
            
            # 마지막 구간 처리
            if in_movement:
                duration = len(movement_mask) - start_idx
                if duration >= min_duration:
                    events.append({
                        "start_time": accelerometer_data[start_idx].timestamp,
                        "end_time": accelerometer_data[-1].timestamp,
                        "duration_seconds": duration,
                        "max_magnitude": max(magnitudes[start_idx:]),
                        "mean_magnitude": np.mean(magnitudes[start_idx:])
                    })
            
            logger.debug(f"움직임 이벤트 감지 완료: {len(events)}개 이벤트")
            return events
            
        except Exception as e:
            logger.error(f"움직임 이벤트 감지 중 오류: {str(e)}")
            return []
    
    @staticmethod
    async def calculate_activity_level(
        accelerometer_data: List[AccelerometerReading],
        window_minutes: int = 5
    ) -> List[Dict[str, Any]]:
        """활동 수준 계산 (시간 구간별)"""
        try:
            if not accelerometer_data:
                return []
            
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
            
            df = df.sort_values('timestamp').reset_index(drop=True)
            
            # 가속도계 크기 계산
            df['magnitude'] = np.sqrt(df['x']**2 + df['y']**2 + df['z']**2)
            
            # 시간 윈도우별로 활동 수준 계산
            activity_levels = []
            window_seconds = window_minutes * 60
            start_time = df['timestamp'].iloc[0]
            
            while start_time < df['timestamp'].iloc[-1]:
                end_time = start_time + pd.Timedelta(seconds=window_seconds)
                
                # 해당 시간 구간 데이터 추출
                mask = (df['timestamp'] >= start_time) & (df['timestamp'] < end_time)
                window_data = df[mask]
                
                if len(window_data) > 0:
                    # 활동 지표 계산
                    mean_magnitude = window_data['magnitude'].mean()
                    std_magnitude = window_data['magnitude'].std()
                    max_magnitude = window_data['magnitude'].max()
                    
                    # 움직임 변화량
                    magnitude_diff = window_data['magnitude'].diff().abs().sum()
                    
                    # 활동 수준 분류
                    if mean_magnitude < 0.1:
                        activity_level = "매우 낮음"
                    elif mean_magnitude < 0.3:
                        activity_level = "낮음"
                    elif mean_magnitude < 0.7:
                        activity_level = "중간"
                    elif mean_magnitude < 1.5:
                        activity_level = "높음"
                    else:
                        activity_level = "매우 높음"
                    
                    activity_levels.append({
                        "start_time": start_time,
                        "end_time": end_time,
                        "mean_magnitude": float(mean_magnitude),
                        "std_magnitude": float(std_magnitude),
                        "max_magnitude": float(max_magnitude),
                        "total_movement": float(magnitude_diff),
                        "activity_level": activity_level,
                        "data_points": len(window_data)
                    })
                
                start_time = end_time
            
            return activity_levels
            
        except Exception as e:
            logger.error(f"활동 수준 계산 중 오류: {str(e)}")
            return []


class AudioProcessor:
    """오디오 데이터 처리 유틸리티"""
    
    @staticmethod
    async def analyze_sound_events(
        audio_data: List[AudioReading],
        amplitude_threshold: float = 0.1
    ) -> List[Dict[str, Any]]:
        """소리 이벤트 분석"""
        try:
            sound_events = []
            
            in_sound = False
            start_idx = 0
            
            for i, reading in enumerate(audio_data):
                if reading.amplitude > amplitude_threshold and not in_sound:
                    # 소리 시작
                    in_sound = True
                    start_idx = i
                elif reading.amplitude <= amplitude_threshold and in_sound:
                    # 소리 종료
                    duration = i - start_idx
                    if duration >= 3:  # 최소 3초
                        event_data = audio_data[start_idx:i]
                        
                        # 이벤트 특성 계산
                        max_amplitude = max(r.amplitude for r in event_data)
                        mean_amplitude = np.mean([r.amplitude for r in event_data])
                        
                        # 주파수 대역 분석
                        freq_analysis = await AudioProcessor._analyze_frequency_bands(event_data)
                        
                        sound_events.append({
                            "start_time": audio_data[start_idx].timestamp,
                            "end_time": audio_data[i-1].timestamp,
                            "duration_seconds": duration,
                            "max_amplitude": float(max_amplitude),
                            "mean_amplitude": float(mean_amplitude),
                            "frequency_analysis": freq_analysis
                        })
                    
                    in_sound = False
            
            return sound_events
            
        except Exception as e:
            logger.error(f"소리 이벤트 분석 중 오류: {str(e)}")
            return []
    
    @staticmethod
    async def _analyze_frequency_bands(
        audio_data: List[AudioReading]
    ) -> Dict[str, float]:
        """주파수 대역 분석"""
        try:
            # 모든 주파수 밴드 데이터 수집
            all_bands = []
            for reading in audio_data:
                all_bands.append(reading.frequency_bands)
            
            bands_array = np.array(all_bands)
            
            # 각 밴드별 평균 에너지
            band_names = [
                "매우_낮은_주파수", "낮은_주파수", "중간_낮은_주파수", "중간_주파수",
                "중간_높은_주파수", "높은_주파수", "매우_높은_주파수", "초고주파수"
            ]
            
            analysis = {}
            for i, band_name in enumerate(band_names):
                if i < bands_array.shape[1]:
                    analysis[band_name] = float(np.mean(bands_array[:, i]))
            
            # 주파수 특성 분석
            analysis["주요_주파수_대역"] = band_names[np.argmax(np.mean(bands_array, axis=0))]
            analysis["주파수_다양성"] = float(entropy(np.mean(bands_array, axis=0)))
            
            return analysis
            
        except Exception as e:
            logger.error(f"주파수 대역 분석 중 오류: {str(e)}")
            return {}
    
    @staticmethod
    async def detect_snoring_patterns(
        audio_data: List[AudioReading]
    ) -> Dict[str, Any]:
        """코골이 패턴 감지"""
        try:
            if not audio_data:
                return {"snoring_detected": False}
            
            # 진폭 데이터 추출
            amplitudes = [reading.amplitude for reading in audio_data]
            
            # 주기적 패턴 감지 (FFT 사용)
            fft_result = fft.fft(amplitudes)
            freqs = fft.fftfreq(len(amplitudes), 1.0)  # 1Hz 샘플링 가정
            
            # 0.1-2Hz 범위에서 피크 찾기 (코골이 주파수 범위)
            snoring_freq_mask = (freqs >= 0.1) & (freqs <= 2.0)
            snoring_power = np.abs(fft_result[snoring_freq_mask])
            
            if len(snoring_power) > 0:
                peak_freq = freqs[snoring_freq_mask][np.argmax(snoring_power)]
                peak_power = np.max(snoring_power)
                
                # 코골이 감지 기준
                snoring_detected = peak_power > np.mean(np.abs(fft_result)) * 3
                
                return {
                    "snoring_detected": bool(snoring_detected),
                    "peak_frequency": float(peak_freq),
                    "peak_power": float(peak_power),
                    "average_amplitude": float(np.mean(amplitudes)),
                    "max_amplitude": float(np.max(amplitudes))
                }
            
            return {"snoring_detected": False}
            
        except Exception as e:
            logger.error(f"코골이 패턴 감지 중 오류: {str(e)}")
            return {"snoring_detected": False, "error": str(e)}


class SignalProcessor:
    """일반적인 신호 처리 유틸리티"""
    
    @staticmethod
    async def apply_butterworth_filter(
        data: np.ndarray,
        cutoff_freq: float,
        sampling_rate: float,
        filter_type: str = "low",
        order: int = 4
    ) -> np.ndarray:
        """버터워스 필터 적용"""
        try:
            nyquist = sampling_rate / 2
            normal_cutoff = cutoff_freq / nyquist
            
            if normal_cutoff >= 1.0:
                logger.warning(f"차단 주파수가 나이퀴스트 주파수보다 높습니다: {cutoff_freq}")
                return data
            
            b, a = signal.butter(order, normal_cutoff, btype=filter_type)
            filtered_data = signal.filtfilt(b, a, data, axis=0)
            
            return filtered_data
            
        except Exception as e:
            logger.error(f"버터워스 필터 적용 중 오류: {str(e)}")
            return data
    
    @staticmethod
    async def calculate_spectral_features(
        data: np.ndarray,
        sampling_rate: float
    ) -> Dict[str, float]:
        """스펙트럼 특성 계산"""
        try:
            # FFT 계산
            fft_result = fft.fft(data.flatten())
            freqs = fft.fftfreq(len(data.flatten()), 1/sampling_rate)
            
            # 양의 주파수만 사용
            positive_freqs_idx = freqs > 0
            positive_freqs = freqs[positive_freqs_idx]
            power_spectrum = np.abs(fft_result[positive_freqs_idx]) ** 2
            
            if len(power_spectrum) == 0:
                return {}
            
            # 스펙트럼 특성 계산
            total_power = np.sum(power_spectrum)
            
            # 주요 주파수 (최대 파워)
            dominant_freq = positive_freqs[np.argmax(power_spectrum)]
            
            # 스펙트럼 중심 (가중 평균 주파수)
            spectral_centroid = np.sum(positive_freqs * power_spectrum) / total_power
            
            # 스펙트럼 대역폭
            spectral_bandwidth = np.sqrt(
                np.sum(((positive_freqs - spectral_centroid) ** 2) * power_spectrum) / total_power
            )
            
            # 스펙트럼 기울기
            if len(positive_freqs) > 1:
                slope, _ = np.polyfit(positive_freqs, 10 * np.log10(power_spectrum + 1e-10), 1)
                spectral_rolloff = positive_freqs[
                    np.where(np.cumsum(power_spectrum) >= 0.85 * total_power)[0][0]
                ]
            else:
                slope = 0.0
                spectral_rolloff = 0.0
            
            return {
                "dominant_frequency": float(dominant_freq),
                "spectral_centroid": float(spectral_centroid),
                "spectral_bandwidth": float(spectral_bandwidth),
                "spectral_rolloff": float(spectral_rolloff),
                "spectral_slope": float(slope),
                "total_power": float(total_power)
            }
            
        except Exception as e:
            logger.error(f"스펙트럼 특성 계산 중 오류: {str(e)}")
            return {}
    
    @staticmethod
    async def calculate_entropy_features(data: np.ndarray) -> Dict[str, float]:
        """엔트로피 기반 특성 계산"""
        try:
            # 샘플 엔트로피
            def _sample_entropy(data, m=2, r=0.2):
                """샘플 엔트로피 계산"""
                try:
                    N = len(data)
                    patterns = np.array([data[i:i+m] for i in range(N-m+1)])
                    
                    def _maxdist(xi, xj):
                        return max([abs(ua - va) for ua, va in zip(xi, xj)])
                    
                    phi = np.zeros(2)
                    for m_i in [m, m+1]:
                        patterns_m = np.array([data[i:i+m_i] for i in range(N-m_i+1)])
                        C = np.zeros(N-m_i+1)
                        
                        for i in range(N-m_i+1):
                            template = patterns_m[i]
                            for j in range(N-m_i+1):
                                if _maxdist(template, patterns_m[j]) <= r:
                                    C[i] += 1
                        
                        phi[m_i-m] = np.mean(np.log(C / (N-m_i+1)))
                    
                    return phi[0] - phi[1]
                except:
                    return 0.0
            
            sample_ent = _sample_entropy(data.flatten())
            
            # 근사 엔트로피
            def _approximate_entropy(data, m=2, r=0.2):
                """근사 엔트로피 계산"""
                try:
                    N = len(data)
                    
                    def _maxdist(xi, xj):
                        return max([abs(ua - va) for ua, va in zip(xi, xj)])
                    
                    phi = np.zeros(2)
                    for m_i in [m, m+1]:
                        patterns = np.array([data[i:i+m_i] for i in range(N-m_i+1)])
                        C = np.zeros(N-m_i+1)
                        
                        for i in range(N-m_i+1):
                            template = patterns[i]
                            for j in range(N-m_i+1):
                                if _maxdist(template, patterns[j]) <= r:
                                    C[i] += 1
                        
                        phi[m_i-m] = np.mean(np.log(C / (N-m_i+1)))
                    
                    return phi[0] - phi[1]
                except:
                    return 0.0
            
            approx_ent = _approximate_entropy(data.flatten())
            
            return {
                "sample_entropy": float(sample_ent),
                "approximate_entropy": float(approx_ent)
            }
            
        except Exception as e:
            logger.error(f"엔트로피 특성 계산 중 오류: {str(e)}")
            return {"sample_entropy": 0.0, "approximate_entropy": 0.0}

