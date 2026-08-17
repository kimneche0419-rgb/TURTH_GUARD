# -*- coding: utf-8 -*-
from typing import Any, Dict, List, Optional
from truthhistory.base import AnalysisResult

# 지정학적 역사 왜곡이 허용될 수 없는 이유 — 모든 분석 리포트에 공통 포함되는 콘텐츠.
# 생성형 AI 시대의 역사 왜곡은 단순 오류가 아니라 영토·외교·교육에 직결되는
# 국가적 이해관계 침해이므로, 탐지 결과와 함께 그 '왜(Why)'를 반드시 함께 전달한다.
SIGNIFICANCE: Dict[str, Any] = {
    "title": "지정학적으로 역사가 왜곡되어서는 안 되는 이유",
    "summary": (
        "역사 서술은 영토·주권·외교·교육의 판단 근거가 되는 공적 자산이다. "
        "왜곡된 역사가 유통되면 사료가 아니라 정치적 의도가 '사실'로 둔갑해 "
        "국제 사회의 합의 기반 자체가 침식된다."
    ),
    "reasons": [
        {
            "tag": "영토·주권 분쟁의 근거 오염",
            "detail": "독도·동해 표기 등 영토·해양 권리 주장은 사료와 역사적 사실관계를 국제법적 근거로 삼는다. "
                      "왜곡된 서술이 반복·정착되면 외교 협상과 국제 심판에서 실질적 손해로 직결된다.",
        },
        {
            "tag": "집단 기억·정체성의 세대 오염",
            "detail": "역사 인식은 교육과 세대 전달을 통해 복리로 누적된다. 한 번 굳어진 왜곡은 이후 수십 년간 "
                      "수정에 막대한 사회적 비용을 요구하며, 세대 간 사실 인식의 단절을 낳는다.",
        },
        {
            "tag": "국제 신뢰·외교 협상 기반 붕괴",
            "detail": "검증 가능한 사료는 국가 간 대화의 공통 출발점이다. 상대국이 사료 조작을 감지하는 순간 "
                      "협상 채널 전반이 불신에 잠기며, 정상 외교 안건까지 함께 결린다.",
        },
        {
            "tag": "가해·피해 관계의 전도 위험",
            "detail": "침략·점령·식민지배 등 가해 사실의 은폐·축소·전도는 피해자의 명예와 인류 공통의 "
                      "역사 교훈을 훼손한다. 이는 과거사 부인이 다시 범죄의 문턱을 낮추는 근거로 악용되는 경로이기도 하다.",
        },
        {
            "tag": "생성형 AI에 의한 왜곡 증폭",
            "detail": "LLM은 그럴듯한 위조 역사를 출처까지 지어내 대량 생산한다. 왜곡이 '평균적인 답변'으로 "
                      "표준화되면 원본 사료와의 구별이 사실상 불가능해지므로, 유통 단계의 검증 가드레일이 필수다.",
        },
    ],
}

# 다각도 판별 기준 — 신뢰도 관점 점수(높을수록 정상)에 대한 판정 문구
_VERDICTS = ((0.7, "정상", "ok"), (0.4, "주의", "warn"), (-1.0, "의심", "bad"))


def _verdict(score: Optional[float]) -> Dict[str, Any]:
    """신뢰도 관점 점수 → 3단계 판정 + 시각화용 토큰."""
    if score is None:
        return {"verdict": "미판정", "tone": "neutral"}
    for threshold, label, tone in _VERDICTS:
        if score >= threshold:
            return {"verdict": label, "tone": tone}
    return {"verdict": "의심", "tone": "bad"}


def _perspective(name: str, basis: str, score: Optional[float], detail: str) -> Dict[str, Any]:
    p = {
        "name": name,
        "basis": basis,
        "score": None if score is None else round(max(0.0, min(score, 1.0)), 4),
        "detail": detail,
    }
    p.update(_verdict(p["score"]))
    return p


def _f(value: Optional[float]) -> str:
    return "—" if value is None else f"{value:.2f}"


class ExplainEngine:
    """
    모듈별 분석 리포트를 기반으로 최종 설명 JSON 데이터 포맷팅 및 검증 수행
    """

    @staticmethod
    def build_perspectives(result: AnalysisResult, media_type: str) -> Dict[str, Any]:
        """
        분석 결과를 매체 유형별 '판별 각도'로 분해 — 한 콘텐츠를 독립된 복수 렌즈로
        교차 판별(다각도 분석)하고 각도별 판정·점수·근거를 제공한다.

        - score: 신뢰도 관점 점수(1.0=정상, 0.0=강한 의심), None=판정 재료 부족(미판정)
        - verdict: 정상 / 주의 / 의심 / 미판정 (미분석·미판정은 종합 의심 각도에서 제외)
        """
        d = result.analysis_details or {}
        perspectives: List[Dict[str, Any]] = []

        if media_type == "text":
            fact = d.get("fact_consistency", {}) or {}
            chrono = fact.get("chronology", {}) or {}
            ana = fact.get("anachronism", {}) or {}
            ai = d.get("ai_generation", {}) or {}
            sens = d.get("sensationalism", {}) or {}
            src = d.get("source_credibility", {}) or {}
            llm = d.get("llm_judge", {}) or {}

            consistency = fact.get("consistency_score", 1.0)
            n_ev = fact.get("evidence_count", 0)
            if fact.get("contradiction"):
                consistency = min(consistency, 0.2)
            ev_detail = (f"외부 증거 {n_ev}건 교차 검증"
                         + (f" · 출처: {', '.join(fact.get('sources_used', [])[:3])}" if fact.get("sources_used") else "")
                         + (" · 증거-주장 상충 발견" if fact.get("contradiction") else ""))
            if n_ev == 0:
                ev_detail = "검증 가능한 외부 증거 미확보(NEI) — 중립 처리"
            perspectives.append(_perspective(
                "사료 정합성", "외부 검색 증거 교차 검증(위키백과·DuckDuckGo·Naver·Google Fact Check)",
                consistency, ev_detail))

            kb_hit = (chrono.get("verified_count", 0) or 0) + (chrono.get("contradiction_count", 0) or 0)
            if kb_hit == 0:
                perspectives.append(_perspective(
                    "한국사 연표 KB", "내장 사료 지식베이스(국사편찬위원회 「한국사연표」 기반) 오프라인 교차 검증",
                    None, "본문에서 연표 검증 가능한 '사건/인물 × 연도' 주장 미검출"))
            else:
                kb_score = 0.0 if chrono.get("contradiction_count", 0) else 1.0
                kb_detail = (f"연표 검증 일치 {chrono.get('verified_count', 0)}건"
                             if kb_score else
                             "연표 상충 " + "; ".join(
                                 c.get("detail", "") for c in (chrono.get("contradictions") or [])[:2]))
                perspectives.append(_perspective(
                    "한국사 연표 KB", "내장 사료 지식베이스(국사편찬위원회 「한국사연표」 기반) 오프라인 교차 검증",
                    kb_score, kb_detail))

            ai_prob = ai.get("ai_probability", result.ai_probability)
            method = {"perplexity": "GPT-2 Perplexity/Burstiness 로컬 추론",
                      "fallback_lexical": "어휘 다양도 휴리스틱(GPT-2 미설치 폴백)"}.get(ai.get("method", ""), ai.get("method", ""))
            perspectives.append(_perspective(
                "AI 생성 가능성", f"생성형 AI 작성 패턴 탐지({method})",
                1.0 - ai_prob, f"AI 생성 확률 {_f(ai_prob)}"))

            sens_idx = sens.get("sensationalism_index", 0.0)
            perspectives.append(_perspective(
                "선동성·과장 표현", "감정·선동 어휘 밀도 기반 선동성 지수",
                1.0 - sens_idx, f"선동성 지수 {_f(sens_idx)}"))

            src_score = src.get("credibility_score", 0.5)
            perspectives.append(_perspective(
                "출처 신뢰도", "인용 URL 도메인 3-tier(공공기관·언론·일반) 평가",
                src_score, ("인용 URL 미포함(NEI) — 중립 처리" if not src.get("urls")
                            else f"출처 등급 {src.get('source_tier', '?')} ({len(src.get('urls', []))}건 인용)")))

            if ana:
                if ana.get("anachronism"):
                    a_score = 0.5 if fact.get("debunked") else 0.0
                    a_detail = ("현대 대상×역사 시대 동시 등장 — 본문이 가짜로 정정 서술" if fact.get("debunked")
                                else f"현대 대상({', '.join(ana.get('modern_terms', [])[:3])})이 역사 시대와 동시 등장")
                else:
                    a_score, a_detail = 1.0, "시대착오 조합 미검출"
                perspectives.append(_perspective(
                    "시대착오(Anachronism)", "현대 기기·대상 × 역사 인물·시대 동시 등장 패턴 탐지",
                    a_score, a_detail))

            if llm.get("available"):
                perspectives.append(_perspective(
                    "LLM 고증 심사", f"OpenRouter 오픈웨이트 모델 심사(신뢰도 {_f(llm.get('confidence'))})",
                    (0.9 if not llm.get("is_hallucination") else 0.1),
                    (llm.get("summary") or ("할루시네이션 판정" if llm.get("is_hallucination") else "정합 판정"))[:120]))

        elif media_type == "image":
            ela = d.get("error_level_analysis", {}) or {}
            fft = d.get("frequency_analysis", {}) or {}
            face = d.get("deepfake_analysis", {}) or {}

            perspectives.append(_perspective(
                "ELA 압축 왜곡", "재인코딩 오차율(Error Level Analysis) 기반 합성 흔적 탐지",
                None if not ela.get("module_available", False) else 1.0 - ela.get("manipulation_score", 0.0),
                "분석 모듈 미설치 — 판정 보류" if not ela.get("module_available", False)
                else f"ELA 편차 {ela.get('mean_difference', 0.0):.2f} · 조작 점수 {_f(ela.get('manipulation_score'))}"))

            perspectives.append(_perspective(
                "FFT 주파수 노이즈", "GAN/Diffusion 격자 아티팩트 주파수 스파이크 탐지",
                1.0 - fft.get("ai_probability", 0.0),
                (f"주파수 스파이크 {fft.get('spike_count', 0)}개 · AI 생성 확률 {_f(fft.get('ai_probability'))}"
                 if fft.get("module_available", False) else "정밀 FFT 미수행(의존성 부재 폴백) — 참고용")))

            if face.get("detected_faces", 0) > 0:
                perspectives.append(_perspective(
                    "안면 비대칭(페이스 스왑)", "Haar Cascade 안면 랜드마크 좌우 대칭 편차 분석",
                    1.0 - face.get("asymmetry_score", 0.0),
                    f"검출 안면 {face.get('detected_faces')}개 · 비대칭 점수 {_f(face.get('asymmetry_score'))}"))
            else:
                perspectives.append(_perspective(
                    "안면 비대칭(페이스 스왑)", "Haar Cascade 안면 랜드마크 좌우 대칭 편차 분석",
                    None, "검출 안면 없음 — 인물 사진 아님(판정 대상 아님)"))

        elif media_type in ("video", "audio"):
            if media_type == "video":
                temporal = d.get("temporal_consistency", {}) or {}
                deepfake = d.get("deepfake_results", {}) or {}
                perspectives.append(_perspective(
                    "프레임 연속성(Jitter)", "샘플 프레임 간 히스토그램 차이 기반 temporal jitter 지수",
                    1.0 - temporal.get("jitter_index", 0.0),
                    f"Jitter 지수 {_f(temporal.get('jitter_index'))}"
                    + ("" if temporal.get("module_available", True) else " (모듈 미설치 — 기본값)")))
                perspectives.append(_perspective(
                    "안면 합성(딥페이크)", "프레임 샘플 안면 비대칭 최댓값 기반 페이스 스왑 탐지",
                    1.0 - deepfake.get("max_manipulation_probability", 0.0),
                    f"검출 안면 {deepfake.get('detected_faces_total', 0)}개 · 최대 합성 확률 {_f(deepfake.get('max_manipulation_probability'))}"))
            else:
                spectral = d.get("spectral_analysis", {}) or {}
                phishing = d.get("phishing_analysis", {}) or {}
                perspectives.append(_perspective(
                    "음향 스펙트럼(MFCC/HNR)", "MFCC 유사도·조화-비조화 비율 기반 합성 음성 탐지",
                    1.0 - spectral.get("synthetic_voice_probability", 0.0),
                    f"합성 음성 확률 {_f(spectral.get('synthetic_voice_probability'))}"
                    + ("" if spectral.get("module_available", True) else " (모듈 미설치 — 중립 처리)")))
                perspectives.append(_perspective(
                    "사칭·유도 어휘", "STT 전사 텍스트의 금전·허위정보 유도 패턴 탐지",
                    1.0 - phishing.get("phishing_probability", 0.0),
                    f"유도 위험 확률 {_f(phishing.get('phishing_probability'))}"))

        # 다각도 종합 — 실제 판별에 참여한 각도만 집계(미판정·미분석 제외)
        engaged = [p for p in perspectives if p["score"] is not None]
        suspected = [p for p in engaged if p["verdict"] == "의심"]
        caution = [p for p in engaged if p["verdict"] == "주의"]
        if suspected:
            note = f"{len(suspected)}개 각도에서 왜곡·위변조 의심 — {', '.join(p['name'] for p in suspected[:3])}"
        elif caution:
            note = f"의심 각도 0개 · 주의 {len(caution)}개 — 단정적 판정 보류(중립 권장)"
        elif engaged:
            note = f"전체 {len(engaged)}개 각도 정상 — 다각도 교차 검증 양호"
        else:
            note = "판별 가능한 각도 없음 — 검증 재료 부족"

        return {
            "summary": {
                "total_angles": len(perspectives),
                "engaged_angles": len(engaged),
                "suspected_angles": len(suspected),
                "caution_angles": len(caution),
                "note": note,
            },
            "angles": perspectives,
        }

    @staticmethod
    def render_gauge(score: float, width: int = 20) -> str:
        """CLI 텍스트 리포트용 신뢰도 게이지(█/░ 블록) — 시각 자료."""
        filled = max(0, min(width, round(score * width)))
        return "█" * filled + "░" * (width - filled)

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
            "perspectives": ExplainEngine.build_perspectives(result, media_type),
            "significance": SIGNIFICANCE,
            "explanations": [],
            "evidence": (result.analysis_details.get("fact_consistency", {}) or {}).get("evidence_sample", []),
            "reference": (result.analysis_details.get("fact_consistency", {}) or {}).get("reference") or {},
        }

        for anomaly in anomalies:
            response_data["explanations"].append({
                "code": anomaly.get("code", "UNKNOWN_ERR"),
                "severity": anomaly.get("severity", "INFO"),
                "message": anomaly.get("message", ""),
                "location": anomaly.get("location", "global")
            })

        return response_data
