# -*- coding: utf-8 -*-
"""Vercel serverless entry — Truth History FastAPI 게이트웨이를 ASGI 함수로 노출.

Vercel Python 런타임은 모듈 수준의 FastAPI(ASGI) `app` 객체를 감지해 서버리스 함수로 래핑한다.
`vercel.json` 의 rewrite 규칙이 `/api/v1/*` 요청을 이 함수로 보내고,
FastAPI는 원본 경로(/api/v1/scan/text 등)를 그대로 라우팅한다.
"""
import os
import sys

# 프로젝트 루트를 import 경로에 추가 → truthhistory 패키지 + truthhistory_server import 가능
_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

from truthhistory_server import app  # noqa: E402,F401  (FastAPI ASGI 인스턴스)
