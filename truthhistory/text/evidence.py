# -*- coding: utf-8 -*-
"""
외부 검색 증거 기반 정합성 검증 계층.
- 한국어 위키백과 검색 API — 키 불필요, 한국사 사료 정합성에 가장 효과적 (1순위 무료 소스)
- DuckDuckGo (Instant Answer API + HTML 결과 스크립트) — 키 불필요, 보조 소스
- Naver Search API — 한국어/한국사 특화 (NAVER_CLIENT_ID / NAVER_CLIENT_SECRET 필요)
- Google Fact Check API — 기존 (FACT_CHECK_API_KEY 필요)

각 소스를 병렬로 조회해 수집한 증거 스니펫으로부터 키워드 커버리지 + 상충 단서를
산출하여 정합성 점수(0.0~1.0)를 반환한다. 증거가 없으면 중립(0.5) 처리.
"""
import re
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any, Callable, Dict, List, Optional

import requests

from truthhistory.text.knowledge import search_knowledge_base

DDG_IA_URL = "https://api.duckduckgo.com/"
DDG_HTML_URL = "https://html.duckduckgo.com/html/"
NAVER_WEB_URL = "https://openapi.naver.com/v1/search/webkr.json"
UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")

_KO_STOPWORDS = set(
    "은 는 이 가 을 를 의 에 서 와 과 도 만 및 그 또한 매우 등 위해 통해 "
    "때문 그리고 하다 했다 한다 한다고 있다 있다고 대한 이런 저런 우리".split()
)

_CONTRADICTION_CUES = [
    "거짓", "허위", "틀린", "오류", "잘못", "실제로는", "정정", "사실이 아",
    "다르다", "상충", "왜곡", "조작", "검증되지 않", "루머",
    "가짜", "환각", "할루시네이션", "아니다", "아니야", "불가능", "없다", "없음",
    "없는", "허구", "날조", "밈", "사실무근",
]

# 현대 기술/대상 (역사 시대와 동시 등장 시 시대착오)
_MODERN_TERMS = [
    "맥북", "맥북프로", "맥북에어", "아이폰", "아이패드", "갤럭시", "갤럭시폰", "갤럭시탭",
    "스마트폰", "노트북", "태블릿", "컴퓨터", "피씨", "인터넷", "와이파이", "블루투스",
    "usb", "이어폰", "에어팟", "스마트워치", "카메라", "전기", "로봇", "드론",
    "비행기", "자동차", "라디오", "텔레비전", "티비", "유튜브", "트위터", "인스타그램",
    "틱톡", "ai", "인공지능", "챗gpt", "챗지피티", "gpt", "스마트", "앱",
]

# 역사 인물/시대/제도 (현대 대상과 동시 등장 시 시대착오)
_HISTORICAL_MARKERS = [
    "세종", "세종대왕", "이순신", "장영실", "광개토대왕", "태종", "정조", "영조", "선조",
    "숙종", "중종", "단종", "조선", "고려", "고구려", "백제", "신라", "발해",
    "삼국시대", "통일신라", "임진왜란", "병자호란", "한산도대첩", "거북선", "훈민정음",
    "조선왕조실록", "왕", "대왕", "왕조", "실록", "양반", "왕세자", "사관",
]


_PARTICLES = sorted(
    ["으로서", "에서는", "에서", "이며", "이라", "이고", "하고", "하는", "한다", "했다",
     "한", "으로", "의", "에", "와", "과", "도", "은", "는", "이", "가", "을", "를", "로"],
    key=len, reverse=True,
)


def _strip_particle(tok: str) -> str:
    """한국어 조사/어미를 떼어 명사 후보를 정규화 (이순신은→이순신, 거북선으로→거북선)."""
    for p in _PARTICLES:
        if len(tok) > len(p) + 1 and tok.endswith(p):
            return tok[: -len(p)]
    return tok


def extract_keywords(text: str, max_terms: int = 8) -> List[str]:
    """한글/영문/숫자 2자 이상 명사 후보 추출(조사 제거·불용어 제거·중복 제거·순서 유지)."""
    tokens = re.findall(r"[가-힣A-Za-z0-9]{2,}", text or "")
    seen, out = set(), []
    for t in tokens:
        t = _strip_particle(t)
        if len(t) < 2 or t in _KO_STOPWORDS or t in seen:
            continue
        seen.add(t)
        out.append(t)
    return out[:max_terms]


def build_query(text: str, max_terms: int = 6) -> str:
    return " ".join(extract_keywords(text, max_terms=max_terms))


def _strip_tags(s: str) -> str:
    return re.sub(r"<[^>]+>", "", s or "").strip()


def _ddg_html_snippets(html: str, limit: int = 5) -> List[Dict[str, str]]:
    snips = re.findall(r'class="result__snippet"[^>]*>(.*?)</a>', html, re.S)
    titles = re.findall(r'class="result__a"[^>]*>(.*?)</a>', html, re.S)
    out = []
    for i, raw in enumerate(snips[:limit]):
        text = _strip_tags(raw)
        if text:
            title = _strip_tags(titles[i]) if i < len(titles) else ""
            out.append({"source": "duckduckgo", "title": title, "snippet": text})
    return out


def search_duckduckgo(query: str, timeout: int = 6) -> List[Dict[str, str]]:
    """DuckDuckGo: Instant Answer API(키 불필요) + HTML 결과 스크립트(키 불필요)."""
    if not query:
        return []
    evidence: List[Dict[str, str]] = []
    # 1) Instant Answer API (공식, 키 불필요)
    try:
        r = requests.get(
            DDG_IA_URL,
            params={"q": query, "format": "json", "no_html": 1, "skip_disambig": 1, "kl": "kr-kr"},
            headers={"User-Agent": UA}, timeout=timeout,
        )
        if r.ok:
            d = r.json()
            if d.get("AbstractText"):
                evidence.append({"source": "duckduckgo", "title": d.get("Heading", ""),
                                 "snippet": d["AbstractText"]})
            for t in (d.get("RelatedTopics") or [])[:5]:
                if isinstance(t, dict) and t.get("text"):
                    evidence.append({"source": "duckduckgo", "title": "", "snippet": t["text"]})
    except Exception:
        pass
    # 2) HTML 결과 스크립트 — IA 결과가 부족할 때만 보완
    if len(evidence) < 3:
        try:
            r = requests.get(DDG_HTML_URL, params={"q": query},
                             headers={"User-Agent": UA}, timeout=timeout)
            if r.ok:
                evidence.extend(_ddg_html_snippets(r.text, limit=5))
        except Exception:
            pass
    # 중복 스니펫 제거
    seen, uniq = set(), []
    for e in evidence:
        key = e["snippet"][:60]
        if key and key not in seen:
            seen.add(key)
            uniq.append(e)
    return uniq[:8]


def search_naver(query: str, client_id: str, client_secret: str, timeout: int = 6) -> List[Dict[str, str]]:
    """Naver 통합 웹검색 API (한국어/한국사 특화). 키 필수."""
    if not (client_id and client_secret and query):
        return []
    try:
        r = requests.get(
            NAVER_WEB_URL,
            params={"query": query, "display": 5, "sort": "sim"},
            headers={"X-Naver-Client-Id": client_id,
                     "X-Naver-Client-Secret": client_secret, "User-Agent": UA},
            timeout=timeout,
        )
        if not r.ok:
            return []
        out = []
        for item in r.json().get("items", [])[:5]:
            desc = _strip_tags(item.get("description", ""))
            if desc:
                out.append({"source": "naver", "title": _strip_tags(item.get("title", "")), "snippet": desc, "url": item.get("link", "")})
        return out
    except Exception:
        return []
WIKI_API = "https://ko.wikipedia.org/w/api.php"


def search_wikipedia(query: str, timeout: int = 6) -> List[Dict[str, str]]:
    """한국어 위키백과 검색 API (키 불필요, 한국사 사료 정합성에 가장 효과적)."""
    if not query:
        return []
    try:
        r = requests.get(
            WIKI_API,
            params={"action": "query", "list": "search", "srsearch": query,
                    "srlimit": 5, "format": "json", "utf8": 1, "srsort": "relevance"},
            headers={"User-Agent": UA},
            timeout=timeout,
        )
        if not r.ok:
            return []
        out = []
        for it in r.json().get("query", {}).get("search", [])[:5]:
            snip = _strip_tags(it.get("snippet", ""))
            if snip:
                pageid = it.get("pageid")
                url = f"https://ko.wikipedia.org/?curid={pageid}" if pageid else ""
                out.append({"source": "wikipedia", "title": it.get("title", ""), "snippet": snip, "url": url})
        return out
    except Exception:
        return []


def gather_evidence(
    query: str,
    naver_client_id: Optional[str] = None,
    naver_client_secret: Optional[str] = None,
    fact_check_fn: Optional[Callable] = None,
    per_call_timeout: int = 6,
) -> List[Dict[str, str]]:
    """활성화된 검색 소스를 병렬로 조회해 증거를 병합(지연 최소화)."""
    tasks: List[Callable[[], List[Dict[str, str]]]] = [
        lambda: search_knowledge_base(query),  # 오프라인 권위 KB(국사편찬위원회 연표 기반)
        lambda: search_wikipedia(query, per_call_timeout),
        lambda: search_duckduckgo(query, per_call_timeout),
    ]
    if naver_client_id and naver_client_secret:
        tasks.append(lambda: search_naver(query, naver_client_id, naver_client_secret, per_call_timeout))
    if fact_check_fn:
        tasks.append(lambda: _normalize_factcheck(fact_check_fn(query)))

    merged: List[Dict[str, str]] = []
    with ThreadPoolExecutor(max_workers=4) as ex:
        futs = [ex.submit(t) for t in tasks]
        for fut in as_completed(futs, timeout=per_call_timeout + 3):
            try:
                merged.extend(fut.result() or [])
            except Exception:
                pass
    return merged


def _normalize_factcheck(claims: List[Dict[str, str]]) -> List[Dict[str, str]]:
    out = []
    for c in claims or []:
        out.append({
            "source": "google-factcheck",
            "title": c.get("text", ""),
            "snippet": c.get("review", "") or c.get("text", ""),
        })
    return out



def detect_anachronism(text: str) -> Dict[str, Any]:
    """현대 기술/대상이 역사 인물·시대와 동시에 등장하면 시대착오(할루시네이션)로 판정."""
    lower = (text or "").lower()
    modern = [m for m in _MODERN_TERMS if m in lower]
    hist = [h for h in _HISTORICAL_MARKERS if h in (text or "")]
    if modern and hist:
        return {
            "anachronism": True,
            "modern_terms": modern[:3],
            "historical_markers": hist[:3],
        }
    return {"anachronism": False, "modern_terms": [], "historical_markers": []}


def is_debunked(text: str) -> bool:
    """본문이 해당 내용을 가짜/할루시네이션으로 정정(정정 서술)하는지 검사."""
    t = text or ""
    return any(c in t for c in _CONTRADICTION_CUES)

def score_consistency(text: str, evidence: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    수집된 증거 대비 주장 키워드 커버리지 + 상충 단서로 정합성 점수 산출.
    - 증거/키워드 없으면 중립 0.5
    - 커버리지 높을수록(증거가 주장을 뒷받침) 상승
    - 상충 단서 발견 시 감점
    """
    keywords = extract_keywords(text)
    if not evidence or not keywords:
        return {
            "consistency_score": 0.5,
            "best_coverage": 0.0,
            "matched_keywords": [],
            "contradiction": False,
            "best_evidence": {},
        }
    best_cov, best_snip, matched_best, best_ev = 0.0, "", [], None
    for ev in evidence:
        snip = f"{ev.get('snippet', '')} {ev.get('title', '')}"
        matched = [k for k in keywords if k in snip]
        cov = len(matched) / len(keywords)
        if cov > best_cov:
            best_cov, best_snip, matched_best, best_ev = cov, snip, matched, ev
    contradiction = best_cov > 0 and any(c in best_snip for c in _CONTRADICTION_CUES)
    score = 0.4 + 0.5 * best_cov
    if contradiction:
        score = min(score, 0.4)  # 상충 단서 발견 시 정합성 낮게 상한
    score = max(0.0, min(1.0, score))
    return {
        "consistency_score": round(score, 4),
        "best_coverage": round(best_cov, 4),
        "matched_keywords": matched_best,
        "contradiction": contradiction,
        "best_evidence": best_ev or {},
    }
