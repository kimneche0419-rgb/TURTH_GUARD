# -*- coding: utf-8 -*-
import math
import urllib.parse
from typing import Any, Dict, List, Optional
import requests

from truthguard.base import BaseAnalyzer, AnalysisResult, LazyModuleImporter

class TextAnalyzer(BaseAnalyzer):
    """
    텍스트 데이터의 신뢰성, 출처 및 AI 생성 가능성을 종합 분석하는 분석기 클래스
    """

    def initialize_model(self) -> None:
        self.api_key = self.config.get("api_key")
        self.backend = self.config.get("backend", "local")
        self.fact_check_api_key = self.config.get("fact_check_api_key")
        
        # 가중치 설정 (합 1.0)
        self.weights = self.config.get("weights", {
            "fact_weight": 0.4,
            "sensationalism_weight": 0.3,
            "source_weight": 0.3
        })

    def analyze(self, data: str, context: Optional[str] = None, **kwargs) -> AnalysisResult:
        if not isinstance(data, str):
            raise ValueError("TextAnalyzer는 문자열(str) 데이터만 처리할 수 있습니다.")

        # 1. AI 생성 가능성 분석
        ai_results = self.detect_ai_generation(data)
        ai_prob = ai_results.get("ai_probability", 0.0)

        # 2. 팩트체크 분석
        fact_results = self.analyze_fact_consistency(data, context)
        consistency_score = fact_results.get("consistency_score", 1.0)

        # 3. 자극성 분석
        sensationalism_results = self.analyze_sensationalism(data)
        sensation_index = sensationalism_results.get("sensationalism_index", 0.0)

        # 4. 출처 신뢰도 분석
        source_results = self.verify_source_credibility(data)
        source_score = source_results.get("credibility_score", 0.5)

        # 가중합 스코어링 공식 적용
        credibility_score = (
            self.weights["fact_weight"] * consistency_score +
            self.weights["sensationalism_weight"] * (1.0 - sensation_index) +
            self.weights["source_weight"] * source_score
        )

        # 위험도 산출
        risk_level = self._determine_risk_level(credibility_score, ai_prob)

        # 판단 근거 작성
        reasons = []
        if ai_prob > 0.85:
            reasons.append(f"AI 생성 문장 패턴 발견 (확률: {ai_prob * 100:.1f}%)")
        if consistency_score < 0.4:
            reasons.append("주변 맥락 및 기보도 팩트와 배치되는 주장 발견")
        if sensation_index > 0.7:
            reasons.append(f"과장 및 선동적 감정 단어 다수 검출 (선동성 지수: {sensation_index * 100:.1f}%)")
        if not source_results.get("has_valid_source", True):
            reasons.append("신뢰도 높은 출처 정보(URL 링크 등) 식별 불가")

        return AnalysisResult(
            is_manipulated=(credibility_score < 0.5) or (ai_prob > 0.85),
            credibility_score=round(credibility_score, 4),
            risk_level=risk_level,
            ai_probability=round(ai_prob, 4),
            analysis_details={
                "fact_consistency": fact_results,
                "sensationalism": sensationalism_results,
                "source_credibility": source_results,
                "ai_generation": ai_results
            },
            reasons=reasons
        )

    def supported_formats(self) -> List[str]:
        return ["txt", "md", "html"]

    def analyze_fact_consistency(self, text: str, context: Optional[str] = None) -> Dict[str, Any]:
        """
        주장의 정합성을 평가합니다. Google Fact Check API 연동을 활용합니다.
        """
        if self.fact_check_api_key:
            try:
                # 텍스트의 앞부분에서 대표 키워드 추출 (간이)
                query = " ".join(text.split()[:5])
                claims = self._search_fact_check_claims(query)
                if claims:
                    # 매칭되는 팩트체크 기사 중 "거짓", "허위" 레이팅이 있는 경우 신뢰 점수 감점
                    for claim in claims:
                        review = claim.get("review", "").lower()
                        if any(x in review for x in ["거짓", "false", "허위", "조작"]):
                            return {"consistency_score": 0.1, "matched_claims": claims}
            except Exception:
                pass
        
        # 기본 스코어 리턴
        return {"consistency_score": 0.8, "matched_claims": []}

    def analyze_sensationalism(self, text: str) -> Dict[str, Any]:
        """
        감정적이고 자극적인 형용사/부사 비율을 측정합니다.
        """
        sensational_keywords = ["충격", "경악", "발칵", "결국", "분통", "비밀", "속보"]
        words = text.split()
        if not words:
            return {"sensationalism_index": 0.0, "matched_count": 0}
            
        matched = [w for w in words if any(sk in w for sk in sensational_keywords)]
        index = len(matched) / len(words)
        
        # 지수 정규화 (10% 이상 포함 시 높은 자극성)
        normalized_index = min(index / 0.1, 1.0)
        
        return {
            "sensationalism_index": round(normalized_index, 4),
            "matched_count": len(matched)
        }

    def verify_source_credibility(self, text: str) -> Dict[str, Any]:
        """
        신뢰할 수 있는 도메인(뉴스, 학술 기관 등)의 URL이 들어있는지 분석합니다.
        """
        urls = [w for w in text.split() if w.startswith("http://") or w.startswith("https://")]
        if not urls:
            return {"has_valid_source": False, "credibility_score": 0.3, "urls": []}
            
        trusted_domains = [".gov", ".edu", ".or.kr", "news", "journal"]
        score = 0.5
        for url in urls:
            if any(domain in url for domain in trusted_domains):
                score = 0.9
                break
                
        return {"has_valid_source": True, "credibility_score": score, "urls": urls}

    def detect_ai_generation(self, text: str) -> Dict[str, Any]:
        """
        지연 로딩을 활용하여 AI가 작성한 문맥인지 탐지합니다.
        가중치 패키지(transformers, torch) 부재 시 Lexical Diversity 룰셋으로 폴백합니다.
        """
        try:
            torch = LazyModuleImporter.import_module("torch", "text")
            transformers = LazyModuleImporter.import_module("transformers", "text")
            
            # 실제 모델 계산 시뮬레이션 또는 계산 수행
            # (테스트 속도 및 의존성 방지를 위해 transformers 로드 성공 시에만 동작)
            tokenizer = transformers.AutoTokenizer.from_pretrained("gpt2")
            model = transformers.AutoModelForCausalLM.from_pretrained("gpt2")
            
            encodings = tokenizer(text, return_tensors="pt")
            input_ids = encodings.input_ids
            with torch.no_grad():
                outputs = model(input_ids, labels=input_ids.clone())
                loss = outputs.loss
            ppl = math.exp(loss.item())
            
            # AI일수록 PPL이 낮음 (GPT2 기준 PPL < 50 일 시 의심)
            ai_prob = 1.0 - (1.0 / (1.0 + math.exp(-(ppl - 40) / 10)))
            return {"ai_probability": ai_prob, "perplexity": ppl, "burstiness": 0.1, "method": "perplexity"}
            
        except (ImportError, Exception):
            # 폴백: Lexical Diversity (어휘 다양도 지수)
            words = text.lower().split()
            if len(words) < 10:
                return {"ai_probability": 0.5, "perplexity": 0.0, "burstiness": 0.0, "method": "fallback_lexical"}
                
            unique_ratio = len(set(words)) / len(words)
            # 어휘 다양성이 비정상적으로 낮고 단어 패턴이 고정적일수록 AI 확률 업
            ai_prob = min(max(1.0 - (unique_ratio * 1.2), 0.0), 1.0)
            return {
                "ai_probability": round(ai_prob, 4),
                "perplexity": 0.0,
                "burstiness": 0.0,
                "method": "fallback_lexical"
            }

    def _search_fact_check_claims(self, query: str) -> List[Dict[str, str]]:
        encoded_query = urllib.parse.quote(query)
        url = f"https://factchecktools.googleapis.com/v1alpha1/claims:search?query={encoded_query}&key={self.fact_check_api_key}"
        response = requests.get(url, timeout=5)
        if response.status_code == 200:
            data = response.json()
            claims = data.get("claims", [])
            parsed = []
            for claim in claims:
                parsed.append({
                    "text": claim.get("text", ""),
                    "review": claim.get("claimReview", [{}])[0].get("textualRating", "")
                })
            return parsed
        return []
