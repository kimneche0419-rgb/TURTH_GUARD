# -*- coding: utf-8 -*-
"""
OpenRouter 무료 LLM 기반 한국사 고증 판정 계층.
- OpenRouter(https://openrouter.ai)의 `:free` 접미 무료 모델로 한국사 텍스트의
  할루시네이션 여부를 LLM 심사(judge)하여 구조화된 JSON 판정을 반환한다.
- OPENROUTER_API_KEY 환경 변수가 있을 때만 활성화(선택 사항) — 키가 없으면
  기존 로컬 분석(연표 KB·외부 검색 증거) 경로가 그대로 동작한다.
- 기본 모델은 무료 라인(meta-llama/llama-3.3-70b-instruct:free)이며
  OPENROUTER_MODEL 환경 변수로 교체 가능하다.
"""
import json
import os
import re
from typing import Any, Dict, Optional

import requests

OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"
DEFAULT_MODEL = "meta-llama/llama-3.3-70b-instruct:free"

_SYSTEM_PROMPT = (
    "너는 한국사 고증 심사관이다. 입력된 한국사 관련 텍스트를 사료 정합성 관점에서 검증하고 "
    "다음 JSON 형식으로만 답하라(코드펜스·부가 설명 금지): "
    '{"is_hallucination": true|false, "confidence": 0.0~1.0, '
    '"errors": [{"claim": "문장 속 주장", "problem": "사료와 상충하는 내용"}], '
    '"summary": "한 줄 판정 요약"}'
)


def _extract_json(content: str) -> Optional[Dict[str, Any]]:
    """응답 본문에서 JSON 객체를 관대하게 추출(코드펜스/전후 텍스트 허용)."""
    if not content:
        return None
    fence = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", content, re.S)
    if fence:
        content = fence.group(1)
    else:
        brace = re.search(r"\{.*\}", content, re.S)
        if brace:
            content = brace.group(0)
    try:
        data = json.loads(content)
        return data if isinstance(data, dict) else None
    except (json.JSONDecodeError, ValueError):
        return None


def verify_with_openrouter(
    text: str,
    api_key: Optional[str] = None,
    model: Optional[str] = None,
    timeout: int = 25,
) -> Dict[str, Any]:
    """
    한국사 텍스트를 OpenRouter 무료 LLM으로 고증 심사한다.

    반환:
    - 성공: {"available": True, "model": ..., "is_hallucination": ..., "confidence": ...,
             "errors": [...], "summary": ...}
    - 키 없음/호출 실패/파싱 실패: {"available": False, "error": ...} (분석 파이프라인은 계속 동작)
    """
    api_key = api_key or os.environ.get("OPENROUTER_API_KEY")
    if not api_key:
        return {"available": False, "error": "OPENROUTER_API_KEY 미설정 — LLM 심사 비활성"}
    if not text or not text.strip():
        return {"available": False, "error": "빈 텍스트"}

    model = model or os.environ.get("OPENROUTER_MODEL") or DEFAULT_MODEL
    try:
        resp = requests.post(
            OPENROUTER_URL,
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
                "X-Title": "Truth History SDK",
            },
            json={
                "model": model,
                "messages": [
                    {"role": "system", "content": _SYSTEM_PROMPT},
                    {"role": "user", "content": text[:4000]},
                ],
                "temperature": 0.0,
            },
            timeout=timeout,
        )
        if not resp.ok:
            return {"available": False, "error": f"OpenRouter HTTP {resp.status_code}"}
        content = resp.json().get("choices", [{}])[0].get("message", {}).get("content", "")
    except requests.RequestException as e:
        return {"available": False, "error": f"OpenRouter 요청 실패: {e}"}

    data = _extract_json(content)
    if data is None or "is_hallucination" not in data:
        return {"available": False, "error": "LLM 응답 JSON 파싱 실패"}

    return {
        "available": True,
        "model": model,
        "is_hallucination": bool(data.get("is_hallucination", False)),
        "confidence": max(0.0, min(1.0, float(data.get("confidence", 0.0)))),
        "errors": data.get("errors", []) or [],
        "summary": str(data.get("summary", "")),
    }
