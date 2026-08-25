# -*- coding: utf-8 -*-
"""
한국사 사료 지식베이스(오프라인 고증 계층).
- 국사편찬위원회 「한국사연표」·교과서 서술을 근거로 큐레이션한 주요 사건 연표와
  인물 생존/활동 연도를 SDK에 내장한다 (API 키·네트워크 불필요).
- LLM 할루시네이션이 가장 흔하게 발생하는 '사건/인물 × 연도' 조합을 결정론적으로
  교차 검증하여, 외부 검색 증거와 무관하게 오프라인에서도 즉시 판정한다.

제공 기능:
- search_knowledge_base(query): 키워드 겹침 기반 KB 검색 → 증거(evidence) 목록 반환
- verify_chronology(text): 문장 단위 '역사 대상 × 연도(세기)' 주장 추출·정합성 판정
"""
import re
from typing import Any, Dict, List, Optional, Tuple

# ---------------------------------------------------------------------------
# 큐레이션 데이터 — 국사편찬위원회 한국사연표/우리역사 기준 주요 사건
# start/end: 사건 지속(또는 발생) 연도. 단년 사건은 start == end.
# ---------------------------------------------------------------------------
_TIMELINE: List[Dict[str, Any]] = [
    {"event": "고구려 건국", "start": -37, "end": -37, "aliases": ["고구려건국"]},
    {"event": "백제 건국", "start": -18, "end": -18, "aliases": []},
    {"event": "신라 건국", "start": -57, "end": -57, "aliases": []},
    {"event": "광개토대왕 즉위", "start": 391, "end": 413, "aliases": ["광개토왕"]},
    {"event": "장보고 청해진 설치", "start": 828, "end": 828, "aliases": ["청해진"]},
    {"event": "후백제 건국", "start": 900, "end": 900, "aliases": []},
    {"event": "후고구려(태봉) 건국", "start": 901, "end": 901, "aliases": ["태봉"]},
    {"event": "고려 건국", "start": 918, "end": 918, "aliases": ["고려건국", "후삼국 통일"]},
    {"event": "거란 1차 침입(서희 답판)", "start": 993, "end": 993, "aliases": []},
    {"event": "거란 2차 침입", "start": 1010, "end": 1010, "aliases": []},
    {"event": "귀주대첩", "start": 1019, "end": 1019, "aliases": []},
    {"event": "무신정변", "start": 1170, "end": 1170, "aliases": []},
    {"event": "몽골 1차 침입", "start": 1231, "end": 1231, "aliases": []},
    {"event": "삼별초 항쟁", "start": 1270, "end": 1273, "aliases": []},
    {"event": "고려 멸망", "start": 1392, "end": 1392, "aliases": []},
    {"event": "조선 건국", "start": 1392, "end": 1392, "aliases": ["조선건국", "조선 개국"]},
    {"event": "훈민정음 창제", "start": 1443, "end": 1446, "aliases": ["훈민정음", "훈민정음 반포", "한글 창제", "한글"]},
    {"event": "계유정난", "start": 1453, "end": 1453, "aliases": []},
    {"event": "세조 반정", "start": 1455, "end": 1455, "aliases": []},
    {"event": "임진왜란", "start": 1592, "end": 1598, "aliases": []},
    {"event": "정묘호란", "start": 1627, "end": 1627, "aliases": []},
    {"event": "병자호란", "start": 1636, "end": 1637, "aliases": []},
    {"event": "동학농민운동", "start": 1894, "end": 1894, "aliases": ["동학농민운동", "갑오농민전쟁"]},
    {"event": "갑오개혁", "start": 1894, "end": 1894, "aliases": ["갑오경장"]},
    {"event": "을미개혁", "start": 1895, "end": 1895, "aliases": ["을미경장"]},
    {"event": "대한제국 선포", "start": 1897, "end": 1897, "aliases": []},
    {"event": "을사늑약", "start": 1905, "end": 1905, "aliases": ["을사조약"]},
    {"event": "국채보상운동", "start": 1907, "end": 1907, "aliases": []},
    {"event": "경술국치(한일병합)", "start": 1910, "end": 1910, "aliases": ["한일병합", "경술국치"]},
    {"event": "3·1운동", "start": 1919, "end": 1919, "aliases": ["3.1운동", "삼일운동", "3·1 독립선언"]},
    {"event": "대한민국 임시정부 수립", "start": 1919, "end": 1919, "aliases": ["임시정부 수립"]},
    {"event": "8·15 광복", "start": 1945, "end": 1945, "aliases": ["광복", "8.15 광복"]},
    {"event": "대한민국 정부 수립", "start": 1948, "end": 1948, "aliases": ["정부 수립"]},
    {"event": "한국전쟁", "start": 1950, "end": 1953, "aliases": ["6·25 전쟁", "6.25", "한국 동란"]},
    {"event": "4·19 혁명", "start": 1960, "end": 1960, "aliases": ["4.19 혁명", "사일혁명"]},
    {"event": "5·16 군사정변", "start": 1961, "end": 1961, "aliases": ["5.16"]},
    {"event": "5·18 민주화운동", "start": 1980, "end": 1980, "aliases": ["5.18", "광주민주화운동"]},
    {"event": "6월 민주항쟁", "start": 1987, "end": 1987, "aliases": ["6월 항쟁", "6·10 민주항쟁"]},
    {"event": "남북정상회담", "start": 2000, "end": 2018, "aliases": []},
]

# 인물: birth/death는 생몰 연도. 활동 시기만 확정된 인물은 active_start/active_end 사용.
_FIGURES: List[Dict[str, Any]] = [
    {"name": "광개토대왕", "birth": 374, "death": 412, "aliases": ["광개토왕"]},
    {"name": "김유신", "birth": 595, "death": 673, "aliases": []},
    {"name": "왕건", "birth": 877, "death": 943, "aliases": ["태조왕건"]},
    {"name": "서희", "birth": 942, "death": 998, "aliases": []},
    {"name": "강감찬", "birth": 948, "death": 1031, "aliases": []},
    {"name": "이성계", "birth": 1335, "death": 1408, "aliases": ["태조이성계"]},
    {"name": "세종", "birth": 1397, "death": 1450, "aliases": ["세종대왕"]},
    {"name": "신사임당", "birth": 1504, "death": 1551, "aliases": []},
    {"name": "이순신", "birth": 1545, "death": 1598, "aliases": ["충무공"]},
    {"name": "허준", "birth": 1539, "death": 1615, "aliases": []},
    {"name": "정약용", "birth": 1762, "death": 1836, "aliases": ["다산"]},
    {"name": "김구", "birth": 1876, "death": 1949, "aliases": ["백범"]},
    {"name": "안중근", "birth": 1879, "death": 1910, "aliases": []},
    {"name": "유관순", "birth": 1902, "death": 1920, "aliases": []},
]

_SENTENCE_SPLIT = re.compile(r"[.!?\n；;]+")
_YEAR_RE = re.compile(r"(?:기원전\s*)?(\d{1,4})\s*년")
_BC_RE = re.compile(r"기원전\s*(\d{1,4})\s*년")
_CENTURY_RE = re.compile(r"(\d{1,2})\s*세기")


def _event_names(entry: Dict[str, Any]) -> List[str]:
    return [entry["event"]] + [a for a in entry.get("aliases", []) if a]


def _figure_names(entry: Dict[str, Any]) -> List[str]:
    return [entry["name"]] + [a for a in entry.get("aliases", []) if a]


def _figure_span(entry: Dict[str, Any]) -> Tuple[int, int]:
    if "birth" in entry:
        return entry["birth"], entry["death"]
    return entry["active_start"], entry["active_end"]


def _format_year(year: int) -> str:
    return f"기원전 {abs(year)}년" if year < 0 else f"{year}년"


def extract_year_mentions(sentence: str) -> List[int]:
    """문장에서 'N년'(기원전 포함) 연도 언급을 정수 목록으로 추출."""
    years: List[int] = []
    for m in _BC_RE.finditer(sentence):
        years.append(-int(m.group(1)))
    bc_spans = [m.span() for m in _BC_RE.finditer(sentence)]
    for m in _YEAR_RE.finditer(sentence):
        if any(s <= m.start() < e for s, e in bc_spans):
            continue  # 기원전 연도로 이미 처리
        y = int(m.group(1))
        if 1 <= y <= 2100:
            years.append(y)
    return years


def extract_century_mentions(sentence: str) -> List[Tuple[int, int]]:
    """문장에서 'N세기' 언급을 (시작연도, 끝연도) 구간으로 추출 (15세기 → (1400, 1499))."""
    out: List[Tuple[int, int]] = []
    for m in _CENTURY_RE.finditer(sentence):
        c = int(m.group(1))
        if 1 <= c <= 21:
            out.append(((c - 1) * 100, (c - 1) * 100 + 99))
    return out


def _name_tokens(name: str) -> List[str]:
    return [t for t in re.split(r"\s+", name) if t]


def _matched_events(sentence: str) -> List[Dict[str, Any]]:
    # 복합 사건명("고구려 건국")은 조사 개입("고구려가 건국되었다")에도
    # 모든 구성 토큰이 문장에 있으면 매칭된 것으로 본다.
    matched = []
    for e in _TIMELINE:
        for n in _event_names(e):
            if n in sentence or all(t in sentence for t in _name_tokens(n)):
                matched.append(e)
                break
    return matched


def _matched_figures(sentence: str) -> List[Dict[str, Any]]:
    return [f for f in _FIGURES if any(n in sentence for n in _figure_names(f))]


def verify_chronology(text: str) -> Dict[str, Any]:
    """
    문장 단위로 '역사 사건/인물 × 연도(세기)' 주장을 추출해 KB와 교차 검증.

    반환:
    - verified: KB와 일치하는 주장 (사건 기간 내 연도, 인물 생존/활동기 내 연도)
    - contradictions: KB와 상충 (예: '임진왜란은 1920년' → expected 1592~1598)
    - 연도 언급이 없거나 KB 미등록 대상이면 해당 문장은 판정하지 않는다(과신 방지).
    """
    verified: List[Dict[str, Any]] = []
    contradictions: List[Dict[str, Any]] = []

    for raw_sentence in _SENTENCE_SPLIT.split(text or ""):
        sentence = raw_sentence.strip()
        if not sentence:
            continue
        years = extract_year_mentions(sentence)
        centuries = extract_century_mentions(sentence)

        for ev in _matched_events(sentence):
            span = (ev["start"], ev["end"])
            label = ev["event"]
            if not years and not centuries:
                continue
            for y in years:
                claim = {"sentence": sentence, "subject": label, "claim_year": y}
                if span[0] - 1 <= y <= span[1] + 1:
                    verified.append({**claim, "expected": list(span)})
                else:
                    contradictions.append({
                        **claim, "expected": list(span),
                        "detail": f"『{label}』 {_format_year(span[0])}~{_format_year(span[1])} 사이 — {_format_year(y)} 주장은 시대와 상충",
                    })
            for cs, ce in centuries:
                claim = {"sentence": sentence, "subject": label, "claim_century": (cs, ce)}
                if not (ce < span[0] - 1 or cs > span[1] + 1):
                    verified.append({**claim, "expected": list(span)})
                else:
                    contradictions.append({
                        **claim, "expected": list(span),
                        "detail": f"『{label}』 {_format_year(span[0])}~{_format_year(span[1])} 사이 — {cs//100 + 1}세기 주장은 시대와 상충",
                    })

        for fig in _matched_figures(sentence):
            span = _figure_span(fig)
            label = fig["name"]
            if not years:
                continue
            for y in years:
                claim = {"sentence": sentence, "subject": label, "claim_year": y}
                if span[0] - 1 <= y <= span[1] + 1:
                    verified.append({**claim, "expected": list(span)})
                else:
                    contradictions.append({
                        **claim, "expected": list(span),
                        "detail": f"{label} 활동기({_format_year(span[0])}~{_format_year(span[1])})에 {_format_year(y)}이(가) 포함되지 않음 — 시대착오",
                    })

    return {
        "verified": verified,
        "contradictions": contradictions,
        "verified_count": len(verified),
        "contradiction_count": len(contradictions),
        "kb_entries": len(_TIMELINE) + len(_FIGURES),
    }


def search_knowledge_base(query: str, max_results: int = 5) -> List[Dict[str, str]]:
    """
    쿼리 키워드와 KB 항목(사건명/인물명/별칭)의 겹침으로 증거를 생성한다.
    네트워크·API 키가 없어도 동작하는 1순위 로컬 권위 증거 소스.
    """
    if not query:
        return []
    tokens = {t for t in re.split(r"\s+", query.strip()) if len(t) >= 2}
    if not tokens:
        return []

    scored: List[Tuple[float, Dict[str, str]]] = []
    for ev in _TIMELINE:
        names = set(_event_names(ev))
        hit = tokens & names
        if not hit:
            continue
        desc = (f"{ev['event']} — 국사편찬위원회 한국사연표 기준 "
                f"{_format_year(ev['start'])}" + (f"~{_format_year(ev['end'])}" if ev["end"] != ev["start"] else ""))
        scored.append((len(hit) / len(tokens), {
            "source": "truthhistory-kb",
            "title": ev["event"],
            "snippet": desc,
            "url": "https://db.history.go.kr/",
        }))
    for fig in _FIGURES:
        names = set(_figure_names(fig))
        hit = tokens & names
        if not hit:
            continue
        span = _figure_span(fig)
        span_label = "활동" if "birth" not in fig else "생존"
        desc = f"{fig['name']} — {span_label}기 {_format_year(span[0])}~{_format_year(span[1])} (국사편찬위원회 인물사전 기준)"
        scored.append((len(hit) / len(tokens), {
            "source": "truthhistory-kb",
            "title": fig["name"],
            "snippet": desc,
            "url": "https://db.history.go.kr/",
        }))

    scored.sort(key=lambda x: -x[0])
    return [item for _, item in scored[:max_results]]

# ---------------------------------------------------------------------------
# 역사 영역 관련성 — 지정학 리포트(왜곡 불허 사유·지도) 표시 여부 판정용.
# 일반 콘텐츠(광고·요리·스포츠 등)에는 지정학 섹션을 붙이지 않는다.
# ("고려"/"조선" 단독 어휘는 일상어(고려하다/조선소) 충돌로 제외)
# ---------------------------------------------------------------------------
_HISTORY_KEYWORDS = [
    "고조선", "고구려", "백제", "신라", "발해", "통일신라", "삼국시대",
    "고려시대", "고려왕조", "조선시대", "조선왕조", "조선왕조실록",
    "대한제국", "임진왜란", "정묘호란", "병자호란", "동학농민",
    "을사늑약", "한일병합", "일제강점", "강제동원", "정신대", "위안부",
    "독립운동", "3·1운동", "3.1운동", "광복", "한국전쟁", "6·25", "6.25",
    "독도", "동해", "서해", "황해", "간도", "사할린", "백두산", "동북공정",
    "역사", "사료", "왕조", "대왕", "반정", "정변", "호란",
]


def is_history_related(text: str) -> bool:
    """텍스트가 한국사 영역 관련인지 판정 — KB 사건/인물명 또는 역사 키워드 포함 여부."""
    if not text:
        return False
    if _matched_events(text) or _matched_figures(text):
        return True
    return any(k in text for k in _HISTORY_KEYWORDS)
