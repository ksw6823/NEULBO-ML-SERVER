import asyncio
from datetime import datetime, timedelta
from typing import List, Dict, Any, Tuple
import numpy as np
import pandas as pd
from scipy import signal
from scipy.stats import skew, kurtosis
import structlog

from app.models.request_models import AccelerometerReading, AudioReading
from app.models.internal_models import ProcessedSensorData, PreprocessingParams
from app.config.settings import settings

logger = structlog.get_logger()


class PreprocessorService:
    """센서 데이터 전처리 서비스"""
    
    def __init__(self):
        self.params = PreprocessingParams()
        
    async def process_sensor_data(
        self,
        accelerometer_data: List[AccelerometerReading],
        audio_data: List[AudioReading]
    ) -> ProcessedSensorData:
        """센서 데이터 전처리"""
        try:
            logger.info("센서 데이터 전처리 시작")
            
            # 병렬로 가속도계와 오디오 데이터 처리
            accel_task = asyncio.create_task(
                self._process_accelerometer_data(accelerometer_data)
            )
            audio_task = asyncio.create_task(
                self._process_audio_data(audio_data)
            )
            
            accel_features, audio_features = await asyncio.gather(
                accel_task, audio_task
            )
            
            # 모델에 맞는 특성 추출 (6개 특성)
            combined_features = self._extract_model_specific_features(
                accel_features, audio_features
            )
            
            # 특성 이름 (실제 모델 기준)
            feature_names = [
                "mean_acc_x", "mean_acc_y", "mean_acc_z", 
                "acc_std_total", "acc_energy_total", "audio_z"
            ]
            
            # 결과 반환
            result = ProcessedSensorData(
                user_id=accelerometer_data[0].timestamp.isoformat() if accelerometer_data else "unknown",
                recording_start=accelerometer_data[0].timestamp if accelerometer_data else datetime.utcnow(),
                recording_end=accelerometer_data[-1].timestamp if accelerometer_data else datetime.utcnow(),
                accelerometer_features=combined_features,
                audio_features=[],  # 이미 combined_features에 포함됨
                sampling_rate=self.params.window_size,
                feature_names=feature_names,
                preprocessing_version="xgb_single_v1.0"
            )
            
            logger.info(
                "센서 데이터 전처리 완료",
                accel_features_count=len(accel_features),
                audio_features_count=len(audio_features)
            )
            
            return result
            
        except Exception as e:
            logger.error(f"센서 데이터 전처리 중 오류: {str(e)}")
            raise
    
    async def _process_accelerometer_data(
        self, 
        accelerometer_data: List[AccelerometerReading]
    ) -> List[List[float]]:
        """가속도계 데이터 처리"""
        try:
            logger.debug("가속도계 데이터 처리 시작")
            
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
            
            # 시간순 정렬
            df = df.sort_values('timestamp').reset_index(drop=True)
            
            # 윈도우 기반 특성 추출
            features = await self._extract_windowed_features(
                df, ['x', 'y', 'z'], self.params.window_size, self.params.overlap
            )
            
            logger.debug(f"가속도계 특성 추출 완료: {len(features)}개 윈도우")
            
            return features
            
        except Exception as e:
            logger.error(f"가속도계 데이터 처리 중 오류: {str(e)}")
            raise
    
    async def _process_audio_data(
        self, 
        audio_data: List[AudioReading]
    ) -> List[List[float]]:
        """오디오 데이터 처리"""
        try:
            logger.debug("오디오 데이터 처리 시작")
            
            # DataFrame으로 변환
            df = pd.DataFrame([
                {
                    'timestamp': reading.timestamp,
                    'amplitude': reading.amplitude,
                    **{f'freq_band_{i}': band for i, band in enumerate(reading.frequency_bands)}
                }
                for reading in audio_data
            ])
            
            # 시간순 정렬
            df = df.sort_values('timestamp').reset_index(drop=True)
            
            # 특성 컬럼 정의
            feature_columns = ['amplitude'] + [f'freq_band_{i}' for i in range(8)]
            
            # 윈도우 기반 특성 추출
            features = await self._extract_windowed_features(
                df, feature_columns, self.params.window_size, self.params.overlap
            )
            
            logger.debug(f"오디오 특성 추출 완료: {len(features)}개 윈도우")
            
            return features
            
        except Exception as e:
            logger.error(f"오디오 데이터 처리 중 오류: {str(e)}")
            raise
    
    async def _extract_windowed_features(
        self,
        df: pd.DataFrame,
        feature_columns: List[str],
        window_size: int,
        overlap: float
    ) -> List[List[float]]:
        """윈도우 기반 특성 추출"""
        try:
            features = []
            
            # 윈도우 크기를 초 단위에서 데이터 포인트 수로 변환
            window_samples = int(window_size * settings.sensor_sampling_rate)
            step_size = int(window_samples * (1 - overlap))
            
            for start_idx in range(0, len(df) - window_samples + 1, step_size):
                end_idx = start_idx + window_samples
                window_data = df.iloc[start_idx:end_idx]
                
                # 각 컬럼에 대해 특성 추출
                window_features = []
                
                for column in feature_columns:
                    values = window_data[column].values
                    
                    # 통계적 특성
                    if self.params.extract_statistical_features:
                        window_features.extend(self._extract_statistical_features(values))
                    
                    # 주파수 도메인 특성
                    if self.params.extract_frequency_features:
                        window_features.extend(self._extract_frequency_features(values))
                
                features.append(window_features)
            
            return features
            
        except Exception as e:
            logger.error(f"윈도우 특성 추출 중 오류: {str(e)}")
            raise
    
    def _extract_statistical_features(self, values: np.ndarray) -> List[float]:
        """통계적 특성 추출"""
        try:
            features = []
            
            # 기본 통계량
            features.extend([
                np.mean(values),           # 평균
                np.std(values),            # 표준편차
                np.min(values),            # 최솟값
                np.max(values),            # 최댓값
                np.median(values),         # 중앙값
                np.percentile(values, 25), # 25분위수
                np.percentile(values, 75), # 75분위수
            ])
            
            # 형태 특성
            features.extend([
                skew(values),              # 왜도
                kurtosis(values),          # 첨도
            ])
            
            # 변화량 특성
            if len(values) > 1:
                diff = np.diff(values)
                features.extend([
                    np.mean(np.abs(diff)),     # 평균 절댓값 변화
                    np.sum(np.abs(diff)),      # 총 변화량
                    np.std(diff),              # 변화량 표준편차
                ])
            else:
                features.extend([0.0, 0.0, 0.0])
            
            # NaN 값 처리
            features = [float(f) if not np.isnan(f) and not np.isinf(f) else 0.0 for f in features]
            
            return features
            
        except Exception as e:
            logger.error(f"통계적 특성 추출 중 오류: {str(e)}")
            return [0.0] * 12  # 기본값 반환
    
    def _extract_frequency_features(self, values: np.ndarray) -> List[float]:
        """주파수 도메인 특성 추출"""
        try:
            features = []
            
            if len(values) < 4:  # FFT를 위한 최소 데이터 포인트
                return [0.0] * 8  # 기본값 반환
            
            # FFT 계산
            fft = np.fft.fft(values)
            power_spectrum = np.abs(fft) ** 2
            freqs = np.fft.fftfreq(len(values), 1/settings.sensor_sampling_rate)
            
            # 양의 주파수만 사용
            positive_freqs_idx = freqs > 0
            positive_freqs = freqs[positive_freqs_idx]
            positive_power = power_spectrum[positive_freqs_idx]
            
            if len(positive_power) == 0:
                return [0.0] * 8
            
            # 주파수 대역 특성
            total_power = np.sum(positive_power)
            
            # 대역별 파워 (0-0.1Hz, 0.1-0.2Hz, ..., 0.7-0.8Hz)
            num_bands = 8
            max_freq = min(0.8, np.max(positive_freqs))
            band_width = max_freq / num_bands
            
            for i in range(num_bands):
                band_start = i * band_width
                band_end = (i + 1) * band_width
                
                band_mask = (positive_freqs >= band_start) & (positive_freqs < band_end)
                band_power = np.sum(positive_power[band_mask])
                
                # 상대적 파워 비율
                band_ratio = band_power / total_power if total_power > 0 else 0.0
                features.append(float(band_ratio))
            
            # NaN 값 처리
            features = [f if not np.isnan(f) and not np.isinf(f) else 0.0 for f in features]
            
            return features
            
        except Exception as e:
            logger.error(f"주파수 특성 추출 중 오류: {str(e)}")
            return [0.0] * 8  # 기본값 반환
    
    def _generate_feature_names(self) -> List[str]:
        """특성 이름 생성"""
        names = []
        
        # 가속도계 특성 (x, y, z 각각)
        for axis in ['x', 'y', 'z']:
            if self.params.extract_statistical_features:
                names.extend([
                    f'accel_{axis}_mean', f'accel_{axis}_std', 
                    f'accel_{axis}_min', f'accel_{axis}_max',
                    f'accel_{axis}_median', f'accel_{axis}_q25', f'accel_{axis}_q75',
                    f'accel_{axis}_skew', f'accel_{axis}_kurtosis',
                    f'accel_{axis}_mad', f'accel_{axis}_total_variation', f'accel_{axis}_diff_std'
                ])
            
            if self.params.extract_frequency_features:
                names.extend([f'accel_{axis}_freq_band_{i}' for i in range(8)])
        
        # 오디오 특성
        for feature in ['amplitude'] + [f'freq_band_{i}' for i in range(8)]:
            if self.params.extract_statistical_features:
                names.extend([
                    f'audio_{feature}_mean', f'audio_{feature}_std',
                    f'audio_{feature}_min', f'audio_{feature}_max',
                    f'audio_{feature}_median', f'audio_{feature}_q25', f'audio_{feature}_q75',
                    f'audio_{feature}_skew', f'audio_{feature}_kurtosis',
                    f'audio_{feature}_mad', f'audio_{feature}_total_variation', f'audio_{feature}_diff_std'
                ])
            
            if self.params.extract_frequency_features:
                names.extend([f'audio_{feature}_freq_band_{i}' for i in range(8)])
        
        return names
    
    async def apply_filters(self, data: np.ndarray) -> np.ndarray:
        """신호 필터링 적용"""
        try:
            # 저역통과 필터
            if self.params.lowpass_freq > 0:
                nyquist = settings.sensor_sampling_rate / 2
                low_cutoff = self.params.lowpass_freq / nyquist
                if low_cutoff < 1.0:
                    b, a = signal.butter(4, low_cutoff, btype='low')
                    data = signal.filtfilt(b, a, data, axis=0)
            
            # 고역통과 필터
            if self.params.highpass_freq > 0:
                nyquist = settings.sensor_sampling_rate / 2
                high_cutoff = self.params.highpass_freq / nyquist
                if high_cutoff < 1.0:
                    b, a = signal.butter(4, high_cutoff, btype='high')
                    data = signal.filtfilt(b, a, data, axis=0)
            
            return data
            
        except Exception as e:
            logger.error(f"필터링 적용 중 오류: {str(e)}")
            return data  # 원본 데이터 반환
    
    async def normalize_features(self, features: List[List[float]]) -> List[List[float]]:
        """특성 정규화"""
        try:
            if not features:
                return features
            
            features_array = np.array(features)
            
            if self.params.normalization_method == "z-score":
                # Z-score 정규화
                mean = np.mean(features_array, axis=0)
                std = np.std(features_array, axis=0)
                
                # 표준편차가 0인 경우 처리
                std[std == 0] = 1.0
                
                normalized = (features_array - mean) / std
            
            elif self.params.normalization_method == "min-max":
                # Min-Max 정규화
                min_vals = np.min(features_array, axis=0)
                max_vals = np.max(features_array, axis=0)
                
                # 범위가 0인 경우 처리
                range_vals = max_vals - min_vals
                range_vals[range_vals == 0] = 1.0
                
                normalized = (features_array - min_vals) / range_vals
            
            else:
                # 정규화 없음
                normalized = features_array
            
            return normalized.tolist()
            
        except Exception as e:
            logger.error(f"특성 정규화 중 오류: {str(e)}")
            return features  # 원본 특성 반환
    
    def _extract_model_specific_features(
        self,
        accel_features: List[List[float]],
        audio_features: List[List[float]]
    ) -> List[List[float]]:
        """모델에 맞는 6개 특성 추출"""
        try:
            model_features = []
            
            for i in range(len(accel_features)):
                # 가속도계 특성에서 필요한 것들 추출
                accel_window = accel_features[i]
                
                # 가속도계 데이터가 충분히 있다고 가정하고 계산
                # mean_acc_x, mean_acc_y, mean_acc_z (처음 3개 특성이 평균이라고 가정)
                mean_acc_x = accel_window[0] if len(accel_window) > 0 else 0.0
                mean_acc_y = accel_window[1] if len(accel_window) > 1 else 0.0  
                mean_acc_z = accel_window[2] if len(accel_window) > 2 else 0.0
                
                # acc_std_total (전체 가속도 표준편차)
                acc_std_total = accel_window[3] if len(accel_window) > 3 else 0.0
                
                # acc_energy_total (전체 가속도 에너지)
                acc_energy_total = accel_window[4] if len(accel_window) > 4 else 0.0
                
                # audio_z (오디오 특성, 마지막 특성이라고 가정)
                audio_z = 0.0
                if i < len(audio_features) and len(audio_features[i]) > 0:
                    audio_z = audio_features[i][-1]  # 마지막 오디오 특성
                
                # 6개 특성으로 구성
                window_features = [
                    mean_acc_x,
                    mean_acc_y, 
                    mean_acc_z,
                    acc_std_total,
                    acc_energy_total,
                    audio_z
                ]
                
                model_features.append(window_features)
            
            logger.debug(f"모델 특성 추출 완료: {len(model_features)}개 윈도우, 6개 특성")
            return model_features
            
        except Exception as e:
            logger.error(f"모델 특성 추출 중 오류: {str(e)}")
            # 기본값 반환
            return [[0.0, 0.0, 0.0, 0.0, 0.0, 0.0] for _ in range(len(accel_features))]

