# -*- coding: utf-8 -*-
import os
import shutil
import json
from fastapi import FastAPI, UploadFile, File, Form, HTTPException, Security, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security.api_key import APIKeyHeader
from typing import Optional

import truthguard
from truthguard.explain.engine import ExplainEngine

app = FastAPI(
    title="TruthGuard REST API Gateway",
    description="텍스트, 이미지, 비디오, 오디오 신뢰성을 검증하는 웹 게이트웨이"
)

# CORS 허용 (React 프론트엔드 연동)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

UPLOAD_DIR = "uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)

# API Key 보안 스키마 정의
API_KEY_HEADER = APIKeyHeader(name="X-API-Key", auto_error=False)

def get_configured_api_key() -> Optional[str]:
    # 1. 환경 변수 우선 순위
    env_key = os.environ.get("TRUTHGUARD_API_KEY")
    if env_key:
        return env_key
    
    # 2. 설정 파일 fallback
    config_path = "truthguard.json"
    if os.path.exists(config_path):
        try:
            with open(config_path, "r", encoding="utf-8") as f:
                config = json.load(f)
                key = config.get("api_key")
                if key and key.strip():
                    return key
        except Exception:
            pass
    return None

async def verify_api_key(
    x_api_key: Optional[str] = Security(API_KEY_HEADER),
    api_key: Optional[str] = None
):
    configured_key = get_configured_api_key()
    if not configured_key:
        return
        
    provided_key = x_api_key or api_key
    if not provided_key or provided_key != configured_key:
        raise HTTPException(
            status_code=401,
            detail="유효하지 않은 API Key입니다. 인증되지 않은 접근입니다."
        )

def get_media_type_by_ext(ext: str) -> str:
    ext = ext.lower()
    if ext in ["txt", "md"]: return "text"
    if ext in ["jpg", "jpeg", "png", "webp"]: return "image"
    if ext in ["mp4", "avi", "mov", "mkv"]: return "video"
    if ext in ["wav", "mp3", "m4a", "flac"]: return "audio"
    return "unknown"

@app.post("/api/v1/scan/media")
async def scan_media(
    file: UploadFile = File(...),
    transcript: Optional[str] = Form(None),
    _ = Depends(verify_api_key)
):
    """
    업로드된 미디어 파일을 저장하고, 적절한 TruthGuard 분석기를 로드하여 XAI 표준 JSON 규격을 반환합니다.
    """
    file_ext = file.filename.split(".")[-1]
    media_type = get_media_type_by_ext(file_ext)
    
    if media_type == "unknown":
        raise HTTPException(status_code=400, detail="지원되지 않는 미디어 포맷입니다.")

    # 1. 파일 임시 저장
    temp_path = os.path.join(UPLOAD_DIR, file.filename)
    with open(temp_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    try:
        # 2. 미디어 타입별 검사 분기
        if media_type == "text":
            with open(temp_path, "r", encoding="utf-8") as f:
                content = f.read()
            result = truthguard.detect_text(content)
        elif media_type == "image":
            result = truthguard.detect_image(temp_path)
        elif media_type == "video":
            result = truthguard.detect_video(temp_path)
        elif media_type == "audio":
            result = truthguard.detect_audio(temp_path, transcript=transcript or "")

        # 3. 에러 분석 정보 수집 및 XAI 구조 가공
        anomalies = []
        for reason in result.reasons:
            anomalies.append({
                "code": f"{media_type.upper()}_ANOMALY_DETECTED",
                "severity": "CRITICAL" if result.risk_level in ["HIGH", "CRITICAL"] else "WARNING",
                "message": reason,
                "location": "global"
            })

        explain_report = ExplainEngine.format_explanations(
            target_file=file.filename,
            media_type=media_type,
            result=result,
            anomalies=anomalies
        )
        
        return explain_report

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"검사 엔진 실행 실패: {str(e)}")
        
    finally:
        # 임시 보관 파일 정리
        if os.path.exists(temp_path):
            os.remove(temp_path)

