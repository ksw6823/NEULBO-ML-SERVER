"""LLM 서비스 모듈"""

import json
import time
import uuid
import httpx
import structlog
from typing import Dict, Any, Optional
from datetime import datetime

from app.config.settings import settings

logger = structlog.get_logger()


class LLMService:
    """OLLAMA LLM 서비스 클래스"""
    
    def __init__(self):
        self.ollama_url = getattr(settings, 'ollama_url', 'http://localhost:11434')
        self.model_name = getattr(settings, 'llm_model', 'gpt-oss:20b')
        self.timeout = getattr(settings, 'llm_timeout', 30.0)
    
    async def generate_sleep_feedback(
        self,
        user_prompt: str,
        sleep_data: Dict[str, Any],
        analysis_id: str
    ) -> Dict[str, Any]:
        """
        수면 데이터 기반 LLM 피드백 생성
        
        Args:
            user_prompt: 사용자 질문
            sleep_data: 수면 분석 데이터
            analysis_id: 분석 ID
            
        Returns:
            LLM 응답 데이터
        """
        start_time = time.time()
        
        try:
            logger.info("LLM 피드백 생성 시작", 
                       analysis_id=analysis_id, 
                       model=self.model_name)
            
            # 프롬프트 구성
            system_prompt = self._build_system_prompt()
            formatted_prompt = self._format_prompt(user_prompt, sleep_data)
            
            # OLLAMA API 호출
            response = await self._call_ollama_api(system_prompt, formatted_prompt)
            
            end_time = time.time()
            response_time_ms = (end_time - start_time) * 1000
            
            logger.info("LLM 피드백 생성 완료", 
                       analysis_id=analysis_id,
                       response_time_ms=response_time_ms)
            
            return {
                "feedback_id": str(uuid.uuid4()),
                "llm_response": response,
                "llm_model": self.model_name,
                "response_time_ms": response_time_ms,
                "timestamp": datetime.utcnow()
            }
            
        except Exception as e:
            logger.error("LLM 피드백 생성 실패", 
                        analysis_id=analysis_id,
                        error=str(e))
            raise
    
    def _build_system_prompt(self) -> str:
        """시스템 프롬프트 구성"""
        return """
당신은 수면 전문 AI 어시스턴트입니다. 
사용자의 수면 분석 데이터를 바탕으로 개인화된 수면 개선 조언을 제공합니다.

역할:
- 수면 데이터 해석 및 패턴 분석
- 과학적 근거에 기반한 수면 개선 제안
- 친근하고 이해하기 쉬운 언어로 설명
- 의료 진단은 하지 않으며, 필요시 전문의 상담 권유

응답 가이드라인:
1. 사용자의 질문에 직접적으로 답변
2. 제공된 수면 데이터 활용
3. 구체적이고 실행 가능한 조언 제공
4. 한국어로 친근하게 응답
5. 500자 이내로 간결하게 작성
"""
    
    def _format_prompt(self, user_prompt: str, sleep_data: Dict[str, Any]) -> str:
        """사용자 프롬프트와 수면 데이터를 결합"""
        
        # 수면 데이터 요약 생성
        summary = self._create_sleep_summary(sleep_data)
        
        formatted_prompt = f"""
수면 분석 데이터:
{summary}

사용자 질문: {user_prompt}

위의 수면 데이터를 바탕으로 사용자의 질문에 답변해주세요.
"""
        return formatted_prompt
    
    def _create_sleep_summary(self, sleep_data: Dict[str, Any]) -> str:
        """수면 데이터 요약 생성"""
        try:
            stats = sleep_data.get('summary_statistics', {})
            
            summary = f"""
- 총 수면시간: {stats.get('total_sleep_time', 0)}분
- 수면 효율: {stats.get('sleep_efficiency', 0)*100:.1f}%
- 각성 시간: {stats.get('wake_time', 0)}분 ({stats.get('wake_percentage', 0):.1f}%)
- 얕은 수면(N1): {stats.get('n1_time', 0)}분 ({stats.get('n1_percentage', 0):.1f}%)
- 보통 수면(N2): {stats.get('n2_time', 0)}분 ({stats.get('n2_percentage', 0):.1f}%)
- 깊은 수면(N3): {stats.get('n3_time', 0)}분 ({stats.get('n3_percentage', 0):.1f}%)
- REM 수면: {stats.get('rem_time', 0)}분 ({stats.get('rem_percentage', 0):.1f}%)
- 데이터 품질: {sleep_data.get('data_quality_score', 0):.3f}
- 분석 모델: {sleep_data.get('model_version', 'N/A')}
"""
            return summary.strip()
            
        except Exception as e:
            logger.warning("수면 데이터 요약 생성 실패", error=str(e))
            return "수면 데이터 요약을 생성할 수 없습니다."
    
    async def _call_ollama_api(self, system_prompt: str, user_prompt: str) -> str:
        """OLLAMA API 호출"""
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                payload = {
                    "model": self.model_name,
                    "messages": [
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt}
                    ],
                    "stream": False
                }
                
                response = await client.post(
                    f"{self.ollama_url}/api/chat",
                    json=payload
                )
                response.raise_for_status()
                
                result = response.json()
                return result.get('message', {}).get('content', '응답을 생성할 수 없습니다.')
                
        except httpx.TimeoutException:
            logger.error("OLLAMA API 타임아웃")
            raise Exception("LLM 응답 시간이 초과되었습니다. 잠시 후 다시 시도해주세요.")
        except httpx.HTTPStatusError as e:
            logger.error("OLLAMA API HTTP 오류", status_code=e.response.status_code)
            raise Exception("LLM 서비스에 일시적인 문제가 발생했습니다.")
        except Exception as e:
            logger.error("OLLAMA API 호출 실패", error=str(e))
            raise Exception("LLM 서비스 연결에 실패했습니다.")

    async def validate_model_availability(self) -> bool:
        """LLM 모델 사용 가능 여부 확인"""
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.get(f"{self.ollama_url}/api/tags")
                response.raise_for_status()
                
                models = response.json().get('models', [])
                available_models = [model.get('name') for model in models]
                
                is_available = self.model_name in available_models
                logger.info("LLM 모델 가용성 확인", 
                           model=self.model_name, 
                           available=is_available)
                
                return is_available
                
        except Exception as e:
            logger.error("LLM 모델 가용성 확인 실패", error=str(e))
            return False
