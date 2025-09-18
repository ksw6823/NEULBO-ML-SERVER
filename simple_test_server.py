#!/usr/bin/env python3
"""
간단한 테스트 서버 - 모델 없이 기본 API만 테스트
"""

from fastapi import FastAPI
from datetime import datetime
import uvicorn

app = FastAPI(title="NEULBO ML Server Test", version="1.0.0")

@app.get("/")
async def root():
    return {"message": "NEULBO ML Server Test", "status": "running", "timestamp": datetime.utcnow()}

@app.get("/api/v1/health/check")
async def health_check():
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow(),
        "version": "1.0.0",
        "database_status": "healthy",
        "model_status": "healthy"
    }

@app.post("/api/v1/sleep/analyze")
async def analyze_sleep_mock(request: dict):
    """모의 수면 분석 - 더미 응답 반환"""
    
    user_id = request.get("user_id", "unknown")
    
    # 더미 응답 생성
    dummy_response = {
        "user_id": user_id,
        "analysis_id": f"test_analysis_{datetime.utcnow().timestamp()}",
        "analysis_timestamp": datetime.utcnow().isoformat(),
        "recording_start": request.get("recording_start"),
        "recording_end": request.get("recording_end"),
        "stage_intervals": [
            {
                "start_time": request.get("recording_start"),
                "end_time": request.get("recording_end"),
                "stage": "N2",
                "confidence": 0.85
            }
        ],
        "stage_probabilities": [
            {
                "timestamp": request.get("recording_start"),
                "wake": 0.1,
                "n1": 0.15,
                "n2": 0.5,
                "n3": 0.2,
                "rem": 0.05
            }
        ],
        "summary_statistics": {
            "total_sleep_time": 480,
            "sleep_efficiency": 0.85,
            "sleep_onset_latency": 15,
            "wake_after_sleep_onset": 30,
            "wake_time": 60,
            "n1_time": 80,
            "n2_time": 200,
            "n3_time": 100,
            "rem_time": 40,
            "wake_percentage": 12.5,
            "n1_percentage": 16.7,
            "n2_percentage": 41.7,
            "n3_percentage": 20.8,
            "rem_percentage": 8.3
        },
        "model_version": "test_v1.0",
        "data_quality_score": 0.95
    }
    
    return dummy_response

if __name__ == "__main__":
    print("🧪 간단한 테스트 서버 시작...")
    uvicorn.run(app, host="0.0.0.0", port=8001)
