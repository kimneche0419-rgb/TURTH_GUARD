# -*- coding: utf-8 -*-
from typing import Any, Dict, List, Optional
from truthhistory.base import AnalysisResult

# 지정학적 역사 왜곡이 허용될 수 없는 이유 — 역사 영역 콘텐츠 리포트에만 포함.
# 쟁점은 단일 사례(독도)에 치우치지 않게 영토(독도·동해·간도·사할린),
# 고대사 귀속(동북공정), 식민 지배(강제동원·위안부), 전쟁 발발 주체(6·25)로 다각화.
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
            "detail": "독도와 동해 표기, 간도 영토, 사할린 강제이주 동포 문제 등은 사료와 역사적 사실관계를 "
                      "국제법적 근거로 삼는다. 왜곡된 서술이 반복·정착되면 외교 협상과 국제 심판에서 실질적 손해로 직결된다.",
        },
        {
            "tag": "고대사 귀속 왜곡(동북공정)",
            "detail": "고구려·발해사를 중국 지방사로 편입하려는 동북공정류 서술은 한반도 고대사의 연속성을 단절시키고 "
                      "국제 학계·교과서 서술의 근거를 흔든다. 고대사 귀속은 민족사 정체성의 출발점 문제다.",
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
            "detail": "일제강점기 강제동원·위안부 등 피해 사실의 은폐·축소, 6·25 전쟁 발발 주체 왜곡 등은 피해자의 명예와 "
                      "인류 공통의 역사 교훈을 훼손한다. 과거사 부인은 다시 범죄의 문턱을 낮추는 근거로 악용된다.",
        },
        {
            "tag": "생성형 AI에 의한 왜곡 증폭",
            "detail": "LLM은 그럴듯한 위조 역사를 출처까지 지어내 대량 생산한다. 왜곡이 '평균적인 답변'으로 "
                      "표준화되면 원본 사료와의 구별이 사실상 불가능해지므로, 유통 단계의 검증 가드레일이 필수다.",
        },
    ],
    "map": {
        "title": "역사·영토 쟁점 지도",
        "note": "개념도 — 실제 국경·영역과 다를 수 있음. 공식 지도는 아래 출처 확인.",
        "svg": (
            '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 360 260" '
            'style="max-width:100%;height:auto;font-family:sans-serif">'
            '<rect width="360" height="260" fill="#dceaf5"/>'
            # 아시아 대륙(만주·중국)
            '<path d="M0 0h360v56c-26 4-46 16-64 32l-14 24c-30 14-58 24-90 28L104 92C68 84 30 66 0 40Z" '
            'fill="#efe8d5" stroke="#b8a878" stroke-width="1"/>'
            # 사할린
            '<path d="M306 10c10 20 14 42 11 64l-9 1c2-23-1-44-10-61Z" fill="#efe8d5" stroke="#b8a878" stroke-width="1"/>'
            # 일본 열도
            '<path d="M318 130c10 16 15 36 13 56s-8 36-15 48c3-18-1-36-9-52s-11-32-5-46Z" '
            'fill="#efe8d5" stroke="#b8a878" stroke-width="1"/>'
            # 한반도
            '<path d="M186 96c11 12 13 30 9 49-4 20-10 38-19 56-6 12-14 25-22 23-8-2-8-15-6-27 4-20 0-37-4-54-4-16-2-32 6-43 12-14 26-15 36-4Z" '
            'fill="#f7f2e3" stroke="#8d7f57" stroke-width="1.2"/>'
            # 국경(백두산 부근) 점선
            '<path d="M177 108c6-8 17-13 28-10" fill="none" stroke="#7c6f4d" stroke-width="1.4" stroke-dasharray="4 3"/>'
            # 해역명
            '<text x="96" y="178" font-size="11" fill="#44688a">서해(황해)</text>'
            '<text x="224" y="152" font-size="11" fill="#44688a">동해</text>'
            '<text x="168" y="238" font-size="11" fill="#44688a">남해</text>'
            # 쟁점 마커
            '<circle cx="190" cy="102" r="4" fill="#b91c1c"/>'
            '<text x="150" y="90" font-size="10" fill="#7f1d1d">백두산·국경(고구려·발해)</text>'
            '<circle cx="213" cy="70" r="4" fill="#b91c1c"/>'
            '<text x="200" y="60" font-size="10" fill="#7f1d1d">간도</text>'
            '<circle cx="258" cy="170" r="4" fill="#b91c1c"/>'
            '<text x="248" y="186" font-size="10" fill="#7f1d1d">독도</text>'
            '<circle cx="312" cy="42" r="4" fill="#b91c1c"/>'
            '<text x="292" y="30" font-size="10" fill="#7f1d1d">사할린</text>'
            '<text x="318" y="200" font-size="10" fill="#6b7280">일본</text>'
            '<text x="30" y="30" font-size="10" fill="#6b7280">만주·중국</text>'
            '<text x="12" y="252" font-size="9" fill="#64748b">개념도 — 실제 국경·영역과 다름</text>'
            '</svg>'
        ),
        "sources": [
            {"label": "독도 (해양수산부 독도 종합정보)", "url": "https://www.dokdo.go.kr"},
            {"label": "동해 표기·고구려사 자료 (동북아역사재단)", "url": "https://www.nahf.or.kr"},
            {"label": "한국사연표 (국사편찬위원회)", "url": "https://www.history.go.kr"},
        ],
    },
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

# 쟁점 주제별 지도 선택 — '아무 때나 항상 같은 지도'가 아니라
# ① 영토 쟁점 언급 시에만 첨부 ② 언급된 쟁점 위치를 하이라이트한 주제별 지도.
_MAP_FOCUS = {
    "독도·동해 표기": {"markers": [("독도", 258, 170)], "title": "독도·동해 쟁점 지도"},
    "간도·백두산 국경": {"markers": [("간도", 213, 70), ("백두산·국경", 190, 102)], "title": "간도·백두산 국경 쟁점 지도"},
    "사할린 강제이주": {"markers": [("사할린", 312, 42)], "title": "사할린 강제이주 쟁점 지도"},
    "동북공정(고구려·발해 귀속)": {"markers": [("백두산·국경", 190, 102)], "title": "동북공정·고구려발해 귀속 쟁점 지도"},
}
_BASE_MAP_MARKERS = [("백두산·국경", 190, 102), ("간도", 213, 70), ("독도", 258, 170), ("사할린", 312, 42)]


def _territory_svg(focus: Optional[List[tuple]]) -> str:
    """기본 개념도 SVG — focus에 지정된 쟁점 마커만 강조 링으로 하이라이트."""
    markers = ""
    for name, cx, cy in _BASE_MAP_MARKERS:
        markers += f'<circle cx="{cx}" cy="{cy}" r="4" fill="#b91c1c"/>'
        label_x = cx - 12 if cx > 240 else cx - 40
        label_y = cy - 12 if cy > 100 else cy - 12
        markers += f'<text x="{label_x}" y="{label_y}" font-size="10" fill="#7f1d1d">{name}</text>'
    for name, cx, cy in (focus or []):
        markers += (f'<circle cx="{cx}" cy="{cy}" r="9" fill="none" stroke="#dc2626" '
                    f'stroke-width="2.5"><animate attributeName="r" values="7;11;7" dur="2s" '
                    f'repeatCount="indefinite"/></circle>')
    return (
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 360 260" '
        'style="max-width:100%;height:auto;font-family:sans-serif">'
        '<rect width="360" height="260" fill="#dceaf5"/>'
        '<path d="M0 0h360v56c-26 4-46 16-64 32l-14 24c-30 14-58 24-90 28L104 92C68 84 30 66 0 40Z" '
        'fill="#efe8d5" stroke="#b8a878" stroke-width="1"/>'
        '<path d="M306 10c10 20 14 42 11 64l-9 1c2-23-1-44-10-61Z" fill="#efe8d5" stroke="#b8a878" stroke-width="1"/>'
        '<path d="M318 130c10 16 15 36 13 56s-8 36-15 48c3-18-1-36-9-52s-11-32-5-46Z" '
        'fill="#efe8d5" stroke="#b8a878" stroke-width="1"/>'
        '<path d="M186 96c11 12 13 30 9 49-4 20-10 38-19 56-6 12-14 25-22 23-8-2-8-15-6-27 4-20 0-37-4-54-4-16-2-32 6-43 12-14 26-15 36-4Z" '
        'fill="#f7f2e3" stroke="#8d7f57" stroke-width="1.2"/>'
        '<path d="M177 108c6-8 17-13 28-10" fill="none" stroke="#7c6f4d" stroke-width="1.4" stroke-dasharray="4 3"/>'
        '<text x="96" y="178" font-size="11" fill="#44688a">서해(황해)</text>'
        '<text x="224" y="152" font-size="11" fill="#44688a">동해</text>'
        '<text x="168" y="238" font-size="11" fill="#44688a">남해</text>'
        + markers +
        '<text x="318" y="200" font-size="10" fill="#6b7280">일본</text>'
        '<text x="30" y="30" font-size="10" fill="#6b7280">만주·중국</text>'
        '<text x="12" y="252" font-size="9" fill="#64748b">개념도 — 실제 국경·영역과 다름</text>'
        '</svg>'
    )


def _significance_for(result: AnalysisResult) -> Optional[Dict[str, Any]]:
    """SIGNIFICANCE 사본 + 쟁점 주제에 맞는 지도. 영토 쟁점 미언급 시 지도 미첨부."""
    import copy
    sig = copy.deepcopy(SIGNIFICANCE)
    topics = (result.analysis_details or {}).get("dispute_topics") or []
    territorial = [t for t in topics if t in _MAP_FOCUS]
    if not territorial:
        sig["map"] = None  # 식민·전쟁 쟁점만 언급됐거나 쟁점 없음 — 지도 없음
        return sig
    focus_meta = _MAP_FOCUS[territorial[0]]
    focus = focus_meta["markers"] if len(territorial) == 1 else [m for t in territorial for m in _MAP_FOCUS[t]["markers"]]
    sig["map"] = {
        "title": focus_meta["title"] if len(territorial) == 1 else "역사·영토 쟁점 지도",
        "note": SIGNIFICANCE["map"]["note"] + f" 하이라이트: {', '.join(territorial)}.",
        "svg": _territory_svg(focus),
        "sources": SIGNIFICANCE["map"]["sources"],
    }
    return sig


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
                None if not fft.get("module_available", False) else 1.0 - fft.get("ai_probability", 0.0),
                "정밀 FFT 미수행(의존성 부재 폴백) — 판정 보류" if not fft.get("module_available", False)
                else f"주파수 스파이크 {fft.get('spike_count', 0)}개 · AI 생성 확률 {_f(fft.get('ai_probability'))}"))

            if face.get("detected_faces", 0) > 0:
                if face.get("synthetic_symmetry"):
                    perspectives.append(_perspective(
                        "안면 비대칭(페이스 스왑)", "Haar Cascade 안면 랜드마크 좌우 대칭 편차 분석",
                        0.15,
                        f"검출 안면 {face.get('detected_faces')}개 · 과대칭(전체 {_f(face.get('raw_asymmetry'))} · "
                        f"내부 {_f(face.get('inner_asymmetry'))}) — 실존 인물 최소값(0.107) 미달, AI 완전 합성 의심"))
                else:
                    perspectives.append(_perspective(
                        "안면 비대칭(페이스 스왑)", "Haar Cascade 안면 랜드마크 좌우 대칭 편차 분석",
                        1.0 - face.get("asymmetry_score", 0.0),
                        f"검출 안면 {face.get('detected_faces')}개 · 비대칭 점수 {_f(face.get('asymmetry_score'))}"))
            elif not face.get("module_available", True):
                # cv2 미설치 환경(서버리스 등) — '얼굴 없음'이 아닌 '분석 불가'로 표시
                perspectives.append(_perspective(
                    "안면 비대칭(페이스 스왑)", "Haar Cascade 안면 랜드마크 좌우 대칭 편차 분석",
                    None, "안면 분석 모듈(OpenCV) 미설치 — 판정 보류(로컬 CLI `th scan`으로 정밀 분석)"))
            else:
                perspectives.append(_perspective(
                    "안면 비대칭(페이스 스왑)", "Haar Cascade 안면 랜드마크 좌우 대칭 편차 분석",
                    None, "검출 안면 없음 — 정면 얼굴이 아니거나 너무 작음(판정 대상 아님)"))

        elif media_type in ("video", "audio"):
            if media_type == "video":
                temporal = d.get("temporal_consistency", {}) or {}
                deepfake = d.get("deepfake_results", {}) or {}
                perspectives.append(_perspective(
                    "프레임 연속성(Jitter)", "샘플 프레임 간 히스토그램 차이 기반 temporal jitter 지수",
                    None if not temporal.get("module_available", True) else 1.0 - temporal.get("jitter_index", 0.0),
                    "모듈 미설치 — 판정 보류" if not temporal.get("module_available", True)
                    else f"Jitter 지수 {_f(temporal.get('jitter_index'))}"))
                perspectives.append(_perspective(
                    "안면 합성(딥페이크)", "프레임 샘플 안면 비대칭 최댓값 기반 페이스 스왑 탐지",
                    None if not deepfake.get("module_available", True) else 1.0 - deepfake.get("max_manipulation_probability", 0.0),
                    "모듈 미설치 — 판정 보류" if not deepfake.get("module_available", True)
                    else f"검출 안면 {deepfake.get('detected_faces_total', 0)}개 · 최대 합성 확률 {_f(deepfake.get('max_manipulation_probability'))}"))
            else:
                spectral = d.get("spectral_analysis", {}) or {}
                phishing = d.get("phishing_analysis", {}) or {}
                perspectives.append(_perspective(
                    "음향 스펙트럼(MFCC/HNR)", "MFCC 유사도·조화-비조화 비율 기반 합성 음성 탐지",
                    None if not spectral.get("module_available", True) else 1.0 - spectral.get("synthetic_voice_probability", 0.0),
                    "모듈 미설치 — 판정 보류" if not spectral.get("module_available", True)
                    else f"합성 음성 확률 {_f(spectral.get('synthetic_voice_probability'))}"))
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
    def should_include_significance(result: AnalysisResult, media_type: str) -> bool:
        """지정학 왜곡 불허 사유는 '역사 영역' 콘텐츠에만 표시한다.

        - 이미지·영상·오디오는 위변조 판별 리포트이므로 미표시
        - 텍스트는 분석기가 산출한 history_relevant(KB 교차 검증·시대착오·역사 키워드) 기준
        """
        if media_type != "text":
            return False
        return bool((result.analysis_details or {}).get("history_relevant", False))

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
            # 역사 이미지 분류 결과 — 확장 프로그램 배지 부착 여부 판정에 사용
            "history_relevance": (result.analysis_details.get("history_relevance")
                                  if media_type == "image" else None),
            "perspectives": ExplainEngine.build_perspectives(result, media_type),
            "significance": (_significance_for(result)
                             if ExplainEngine.should_include_significance(result, "text") else None),
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
