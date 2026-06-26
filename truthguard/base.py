import importlib
import sys
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

class AnalysisResult(BaseModel):
    """
    모든 분석기 결과의 공통 데이터 규격
    """
    is_manipulated: bool = Field(..., description="조작 또는 허위정보 여부")
    credibility_score: float = Field(..., description="신뢰도 점수 (0.0 ~ 1.0)")
    risk_level: str = Field("LOW", description="위험 수준 (LOW, MEDIUM, HIGH, CRITICAL)")
    ai_probability: float = Field(..., description="AI 생성/합성 가능성 확률 (0.0 ~ 1.0)")
    analysis_details: Dict[str, Any] = Field(default_factory=dict, description="각 분석 모듈 고유의 상세 세부 지표")
    reasons: List[str] = Field(default_factory=list, description="탐지 및 판정 근거 메시지")

class BaseAnalyzer(ABC):
    """
    TruthGuard의 모든 분석기가 반드시 상속받고 구현해야 하는 인터페이스
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {}
        self.initialize_model()

    @abstractmethod
    def initialize_model(self) -> None:
        """
        모델 가중치 로드, API 키 설정 등 분석기의 초기화 작업을 담당합니다.
        """
        pass

    @abstractmethod
    def analyze(self, data: Any, **kwargs) -> AnalysisResult:
        """
        입력 데이터를 분석하여 통일된 AnalysisResult 규격으로 반환합니다.
        """
        pass

    @abstractmethod
    def supported_formats(self) -> List[str]:
        """
        해당 분석기가 처리할 수 있는 입력 데이터 포맷 목록을 반환합니다.
        """
        pass

    def _determine_risk_level(self, credibility_score: float, ai_probability: float) -> str:
        """
        점수 기반으로 위험 수준을 자동으로 결정합니다.
        """
        if credibility_score < 0.35 or ai_probability > 0.85:
            return "CRITICAL"
        elif credibility_score < 0.6 or ai_probability > 0.6:
            return "HIGH"
        elif credibility_score < 0.8 or ai_probability > 0.3:
            return "MEDIUM"
        return "LOW"

class LazyModuleImporter:
    """
    필요한 의존성 패키지가 없는 경우 사용자에게 적절한 install 명령어를 안내하고
    임포트를 지연시키는 도우미 클래스
    """
    @staticmethod
    def import_module(module_name: str, extra_group: str) -> Any:
        try:
            return importlib.import_module(module_name)
        except ImportError:
            print(
                f"[Error] '{module_name}' 패키지가 누락되었습니다. "
                f"이 기능을 사용하려면 다음 명령어로 추가 패키지를 설치하십시오:\n"
                f"pip install truthguard-sdk[{extra_group}]",
                file=sys.stderr
            )
            raise ImportError(f"Missing dependency for extra group: {extra_group}")
