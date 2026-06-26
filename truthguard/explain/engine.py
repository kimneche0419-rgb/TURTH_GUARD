from typing import Any, Dict, List
from truthguard.base import AnalysisResult

class ExplainEngine:
    """
    모듈별 분석 리포트를 기반으로 최종 설명 JSON 데이터 포맷팅 및 검증 수행
    """
    
    @staticmethod
    def format_explanations(
        target_file: str, 
        media_type: str, 
        result: AnalysisResult,
        anomalies: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        AnalysisResult 객체와 세부 에러 코드를 결합하여 표준화된 JSON 데이터 빌드
        """
        response_data = {
            "target_file": target_file,
            "media_type": media_type,
            "decision": {
                "is_manipulated": result.is_manipulated,
                "credibility_score": round(result.credibility_score, 2),
                "risk_level": result.risk_level
            },
            "metrics": {
                "ai_generation_probability": round(result.ai_probability, 4),
                "editing_artifact_score": round(result.analysis_details.get("artifact_score", 0.0), 4),
                "semantic_consistency_score": round(result.analysis_details.get("semantic_score", 1.0), 4)
            },
            "explanations": []
        }
        
        for anomaly in anomalies:
            response_data["explanations"].append({
                "code": anomaly.get("code", "UNKNOWN_ERR"),
                "severity": anomaly.get("severity", "INFO"),
                "message": anomaly.get("message", ""),
                "location": anomaly.get("location", "global")
            })
            
        return response_data
