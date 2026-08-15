# -*- coding: utf-8 -*-
import os
import shutil
import tempfile
from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional

import truthhistory
from truthhistory.explain.engine import ExplainEngine
from truthhistory.utils import fetch_url_text, load_env

load_env()  # 프로젝트 루트 .env → OS 환경 변수 (기존 환경 변수 우선)

app = FastAPI(
    title="Truth History REST API Gateway",
    description="한국사 텍스트 고증 검증·ELA 이미지 합성·딥페이크·AI 복제 음성 위변조를 검증하는 웹 게이트웨이"
)

# CORS 허용 (React 프론트엔드 연동)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

UPLOAD_DIR = os.path.join(tempfile.gettempdir(), "truthhistory_uploads")
os.makedirs(UPLOAD_DIR, exist_ok=True)

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
    transcript: Optional[str] = Form(None)
):
    """
    업로드된 미디어 파일을 저장하고, 적절한 Truth History 분석기를 로드하여 XAI 표준 JSON 규격을 반환합니다.
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
            result = truthhistory.detect_text(content)
        elif media_type == "image":
            result = truthhistory.detect_image(temp_path)
        elif media_type == "video":
            result = truthhistory.detect_video(temp_path)
        elif media_type == "audio":
            result = truthhistory.detect_audio(temp_path, transcript=transcript or "")

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

@app.post("/api/v1/scan/stream")
async def scan_stream(
    file: UploadFile = File(...),
    chunk_seconds: float = Form(2.0),
    max_chunks: Optional[int] = Form(None),
):
    """
    업로드된 스트리밍/장문 비디오를 시간 청크 단위로 실시간 분석하여
    청크별 타임라인 + 종합 판정(XAI 규격)을 반환합니다.
    """
    from truthhistory.video.streaming import StreamingVideoAnalyzer

    file_ext = file.filename.split(".")[-1]
    if file_ext.lower() not in ("mp4", "avi", "mov", "mkv"):
        raise HTTPException(status_code=400, detail="비디오 포맷만 지원됩니다 (mp4/avi/mov/mkv).")

    temp_path = os.path.join(UPLOAD_DIR, file.filename)
    with open(temp_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    try:
        analyzer = StreamingVideoAnalyzer({"chunk_seconds": chunk_seconds})
        raw_chunks = []
        chunks = []
        for chunk in analyzer.stream_analyze(temp_path, max_chunks=max_chunks):
            raw_chunks.append(chunk)
            r = chunk["result"]
            chunks.append({
                "chunk_index": chunk["chunk_index"],
                "time_start": chunk["time_start"],
                "time_end": chunk["time_end"],
                "frames": chunk["frames"],
                "credibility_score": r.credibility_score,
                "ai_probability": r.ai_probability,
                "risk_level": r.risk_level,
                "is_manipulated": r.is_manipulated,
                "reasons": r.reasons,
            })
        summary = analyzer.summarize(raw_chunks)

        anomalies = []
        for reason in summary.reasons:
            anomalies.append({
                "code": "VIDEO_STREAM_ANOMALY_DETECTED",
                "severity": "CRITICAL" if summary.risk_level in ["HIGH", "CRITICAL"] else "WARNING",
                "message": reason,
                "location": "global",
            })

        explain_report = ExplainEngine.format_explanations(
            target_file=file.filename,
            media_type="video",
            result=summary,
            anomalies=anomalies,
        )
        explain_report["stream"] = {
            "chunk_seconds": chunk_seconds,
            "chunk_count": len(chunks),
            "chunks": chunks,
        }
        return explain_report

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"스트리밍 분석 실패: {str(e)}")
    finally:
        if os.path.exists(temp_path):
            os.remove(temp_path)

class ScanURLPayload(BaseModel):
    url: str

@app.post("/api/v1/scan/url")
async def scan_url(
    payload: ScanURLPayload
):
    """
    지정된 URL 주소의 웹페이지 본문 텍스트를 크롤링하여 Truth History로 스캐닝한 후 XAI JSON 결과를 반환합니다.
    """
    url = str(payload.url)
    try:
        # 1. URL로부터 본문 텍스트 추출
        content = fetch_url_text(url)
        if not content.strip():
            raise HTTPException(status_code=400, detail="웹페이지에서 텍스트 콘텐츠를 읽어올 수 없습니다.")
            
        # 2. 텍스트 분석 실행
        result = truthhistory.detect_text(content)
        
        # 3. XAI 레포트 포맷팅
        anomalies = []
        for reason in result.reasons:
            anomalies.append({
                "code": "TEXT_ANOMALY_DETECTED",
                "severity": "CRITICAL" if result.risk_level in ["HIGH", "CRITICAL"] else "WARNING",
                "message": reason,
                "location": "global"
            })

        explain_report = ExplainEngine.format_explanations(
            target_file=url,
            media_type="text",
            result=result,
            anomalies=anomalies
        )
        
        return explain_report
        
    except HTTPException as he:
        raise he
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"웹사이트 분석 실패: {str(e)}")


class TextScanPayload(BaseModel):
    text: str


@app.post("/api/v1/scan/text")
async def scan_text(payload: TextScanPayload):
    """
    원시 텍스트 본문을 직접 받아 한국사 고증 검증(AI 생성·역사 정합성·선동성) 후
    XAI 표준 JSON 리포트를 반환합니다. (크롬 확장 프로그램 및 외부 API 연동용)
    """
    text = (payload.text or "").strip()
    if not text:
        raise HTTPException(status_code=400, detail="분석할 텍스트가 비어 있습니다.")
    try:
        result = truthhistory.detect_text(text)
        anomalies = []
        for reason in result.reasons:
            anomalies.append({
                "code": "TEXT_ANOMALY_DETECTED",
                "severity": "CRITICAL" if result.risk_level in ["HIGH", "CRITICAL"] else "WARNING",
                "message": reason,
                "location": "global"
            })
        return ExplainEngine.format_explanations(
            target_file="(inline-text)",
            media_type="text",
            result=result,
            anomalies=anomalies
        )
    except HTTPException as he:
        raise he
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"텍스트 분석 실패: {str(e)}")


