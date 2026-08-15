# -*- coding: utf-8 -*-
import math
import os
import urllib.parse
from typing import Any, Dict, List, Optional
import requests

from truthhistory.base import BaseAnalyzer, AnalysisResult, LazyModuleImporter

class TextAnalyzer(BaseAnalyzer):
    """
    텍스트 데이터의 신뢰성, 출처 및 AI 생성 가능성을 종합 분석하는 분석기 클래스
    """

    def initialize_model(self) -> None:
        self.api_key = self.config.get("api_key")
        self.backend = self.config.get("backend", "local")
        self.fact_check_api_key = self.config.get("fact_check_api_key") or os.environ.get("FACT_CHECK_API_KEY")
        self.naver_client_id = self.config.get("naver_client_id") or os.environ.get("NAVER_CLIENT_ID")
        self.naver_client_secret = self.config.get("naver_client_secret") or os.environ.get("NAVER_CLIENT_SECRET")
        self.openrouter_api_key = self.config.get("openrouter_api_key") or os.environ.get("OPENROUTER_API_KEY")
        self.openrouter_model = self.config.get("openrouter_model") or os.environ.get("OPENROUTER_MODEL")

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
        # OpenRouter 무료 LLM 고증 심사 (키 있을 때만, 실패·미설정 시 기존 경로 유지)
        llm_judge = {"available": False, "error": "비활성"}
        if self.openrouter_api_key:
            from truthhistory.text.llm import verify_with_openrouter
            llm_judge = verify_with_openrouter(data, self.openrouter_api_key, self.openrouter_model)
            if llm_judge.get("available") and llm_judge.get("confidence", 0.0) >= 0.7:
                if llm_judge.get("is_hallucination"):
                    credibility_score = min(credibility_score, 0.35)
                else:
                    credibility_score = min(1.0, credibility_score + 0.05)

        # 위험도 산출

        risk_level = self._determine_risk_level(credibility_score, ai_prob)

        # 판단 근거 작성
        reasons = []
        if ai_prob > 0.85:
            reasons.append(f"AI 생성 문장 패턴 발견 (확률: {ai_prob * 100:.1f}%)")
        if consistency_score < 0.4 or fact_results.get("contradiction"):
            srcs = ", ".join(fact_results.get("sources_used", [])) or "외부 검색"
            reasons.append(f"외부 검색 증거({srcs})와 상충·불일치 — 역사적 정합성 의심")
        elif fact_results.get("evidence_count", 0) > 0 and consistency_score >= 0.7 \
                and not fact_results.get("anachronism", {}).get("anachronism"):
            srcs = ", ".join(fact_results.get("sources_used", [])) or "외부 검색"
            reasons.append(f"외부 검색 증거({srcs})와 정합 — 사료 교차 검증 양호")
        ana = fact_results.get("anachronism", {})
        if ana.get("anachronism"):
            terms = "+".join(ana.get("modern_terms", [])) or "현대 대상"
            if fact_results.get("debunked"):
                reasons.append(f"시대착오 주제({terms}) 감지 — 본문이 가짜/할루시네이션으로 정정 서술함")
            else:
                reasons.append(f"시대착오(Anachronism) 강력 의심: {terms} 등 현대 대상이 역사 시대와 동시 등장 — 할루시네이션")
        chrono = fact_results.get("chronology", {})
        for c in chrono.get("contradictions", [])[:2]:
            reasons.append(f"한국사 연표 KB 검증 상충 — {c.get('detail', '사건/인물 × 연도 부정합')}")
        if chrono.get("verified_count") and not chrono.get("contradiction_count"):
            reasons.append(f"한국사 연표 KB 검증 일치({chrono['verified_count']}건) — 사료 정합성 확증")
        if sensation_index > 0.7:
            reasons.append(f"과장 및 선동적 감정 단어 다수 검출 (선동성 지수: {sensation_index * 100:.1f}%)")
        # 검증가능성(Verifiability) — FEVER 3분류(Supported/Refuted/NEI) 기반:
        # '출처·증거 부재'는 부정 판정이 아니라 중립(NEI) 상태이며, 다른 검증 경로
        # (외부 증거·KB 연표)가 이미 작동했다면 이 경고는 표시하지 않는다.
        chrono = fact_results.get("chronology", {})
        kb_engaged = (chrono.get("verified_count", 0) + chrono.get("contradiction_count", 0)) > 0
        if not source_results.get("urls") and fact_results.get("evidence_count", 0) == 0 and not kb_engaged:
            reasons.append("검증 가능한 출처·증거 미확보(NEI) — 신뢰도는 중립 처리되었으며, "
                           "독자의 횡적 검증(SIFT: 출처 조사·타 보도 확인)을 권장")
        if llm_judge.get("available"):
            if llm_judge.get("is_hallucination"):
                errs = "; ".join(e.get("problem", "") for e in llm_judge.get("errors", [])[:2] if e)
                reasons.append(f"OpenRouter LLM 고증 심사: 할루시네이션 판정(신뢰도 {llm_judge['confidence'] * 100:.0f}%)"
                               + (f" — {errs}" if errs else ""))
            else:
                reasons.append(f"OpenRouter LLM 고증 심사: 정합 판정({llm_judge.get('summary', '')})")

        # 피드백 보장 — 어떤 신호도 발화하지 않은 경우 중립 상태를 명시(FEVER NEI와 동일 맥락)
        if not reasons:
            n_evidence = fact_results.get("evidence_count", 0)
            if n_evidence:
                reasons.append(f"이상 징후 미검출 — 외부 증거 {n_evidence}건 수집되었으나 주장과의 커버리지가 낮아 "
                               "단정적 판정은 보류(중립 처리)")
            else:
                reasons.append("이상 징후 미검출 — 명확한 검증 신호 없음(중립 처리), 독자의 횡적 검증 권장")
        return AnalysisResult(
            is_manipulated=(credibility_score < 0.5) or (ai_prob > 0.85),
            credibility_score=round(credibility_score, 4),
            risk_level=risk_level,
            ai_probability=round(ai_prob, 4),
            analysis_details={
                "fact_consistency": fact_results,
                "sensationalism": sensationalism_results,
                "source_credibility": source_results,
                "ai_generation": ai_results,
                "llm_judge": llm_judge
            },
            reasons=reasons
        )

    def supported_formats(self) -> List[str]:
        return ["txt", "md", "html"]

    def analyze_fact_consistency(self, text: str, context: Optional[str] = None) -> Dict[str, Any]:
        """
        외부 검색 증거(DuckDuckGo 키 불필요 / Naver / Google Fact Check)를 병렬 수집하여
        주장의 역사적 정합성을 평가한다. 증거 키워드 커버리지 + 상충 단서 기반 스코어링.
        """
        from truthhistory.text.evidence import build_query, gather_evidence, score_consistency, detect_anachronism, is_debunked
        from truthhistory.text.knowledge import verify_chronology

        query = context or build_query(text)
        fact_check_fn = self._search_fact_check_claims if self.fact_check_api_key else None
        evidence = gather_evidence(
            query=query,
            naver_client_id=self.naver_client_id,
            naver_client_secret=self.naver_client_secret,
            fact_check_fn=fact_check_fn,
        )
        result = score_consistency(text, evidence)
        # 한국사 사료 KB(국사편찬위원회 연표 기반) 연도·시대 교차 검증 — 오프라인 결정론 판정
        chrono = verify_chronology(text)
        result["chronology"] = chrono
        if chrono["contradiction_count"]:
            # 사건/인물 × 연도 상충 → 강한 할루시네이션 신호
            result["consistency_score"] = min(result["consistency_score"], 0.2)
            result["contradiction"] = True
        elif chrono["verified_count"]:
            result["consistency_score"] = min(1.0, result["consistency_score"] + 0.05)
        # 시대착오(Anachronism) — 현대 기기 + 역사 인물/시대 동시 등장
        ana = detect_anachronism(text)
        debunked = is_debunked(text) if ana["anachronism"] else False
        if ana["anachronism"]:
            if debunked:
                # 본문이 가짜/할루시네이션으로 정정 서술 → 과신 방지용 상한만
                result["consistency_score"] = min(result["consistency_score"], 0.6)
            else:
                # 정정 없이 시대착오 주장 → 강한 할루시네이션 신호
                result["consistency_score"] = min(result["consistency_score"], 0.25)
                result["contradiction"] = True
        result["anachronism"] = ana
        result["debunked"] = debunked
        sources_used = sorted({e.get("source", "?") for e in evidence})
        result["sources_used"] = sources_used
        result["evidence_count"] = len(evidence)
        result["evidence_sample"] = evidence[:5]
        # 권위 사료(커버리지 최고 증거)를 '참고 사료(수정된 진실 근거)'로 노출
        result["reference"] = result.get("best_evidence") or (evidence[0] if evidence else {})
        return result

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
        출처 신뢰도를 도메인 등급(tier) 기반으로 평가한다.

        기준(문헌 근거):
        - SIFT/횡적 읽기(Caulfield): '본문에 URL이 없다'는 것 자체는 비신뢰 신호가 아니다 —
          출처 평가는 명시된 링크의 도메인 등급과 외부 검증(횡적)으로 수행한다.
        - 자동 팩트체크(AFC) 연구: 도메인 신뢰 점수는 기관 유형(정부·교육·공공/공식 사료·
          주요 언론 vs 미지 도메인)의 등급화로 산출한다.

        산출:
        - Tier A(0.95): 정부·교육·공공기관·공식 사료(db.history.go.kr 등)·주요 언론 패턴
        - Tier B(0.60): 그 외 일반 URL (명시는 되었으나 평가 불가 도메인)
        - Tier C(0.50): URL 없음 — '부재'는 부정 증거가 아니므로 중립 처리(NEI는 별도 판정)
        """
        urls = [w for w in text.split() if w.startswith("http://") or w.startswith("https://")]
        if not urls:
            return {"source_tier": "C", "has_valid_source": False,
                    "credibility_score": 0.5, "urls": []}

        tier_a_domains = [
            ".gov", ".go.kr", ".edu", ".ac.kr", ".or.kr",
            "db.history.go.kr",  # 국사편찬위원회 한국사 DB(공식 사료)
            "history.go.kr", "contents.archives.go.kr",
            "wikipedia.org",  # 팩트체크 표준 참조 배경 출처(SIFT 'I' 단계)
            "news", "yonhap", "chosun", "joongang", "donga", "hankyung", "kbs", "mbc", "sbs",
            "factcheck", "snopes", "reuters",
        ]
        tier = "B"
        for url in urls:
            if any(d in url.lower() for d in tier_a_domains):
                tier = "A"
                break
        score = 0.95 if tier == "A" else 0.60
        return {"source_tier": tier, "has_valid_source": True,
                "credibility_score": score, "urls": urls}

    def detect_ai_generation(self, text: str) -> Dict[str, Any]:
        """
        지연 로딩을 활용하여 AI가 작성한 문맥인지 탐지합니다.
        가중치 패키지(transformers, torch) 부재 시 Lexical Diversity 룰셋으로 폴백합니다.
        """
        try:
            torch = LazyModuleImporter.import_module("torch", "text")
            transformers = LazyModuleImporter.import_module("transformers", "text")
            
            # transformers/torch 설치 시 GPT-2 기반 실제 Perplexity 산출
            # (미설치 시 하단 어휘 다양도 휴리스틱으로 폴백)
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
