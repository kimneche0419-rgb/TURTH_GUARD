# TruthGuard SDK: 풀스택 및 다국어 확장 아키텍처 명세서

본 문서는 Python 백엔드(FastAPI)와 Node.js 프론트엔드(Vite, React, Chrome Extension), 그리고 Agentic AI 환경 연동을 위한 MCP(Model Context Protocol) 서버를 활용하여 TruthGuard SDK의 탐지 성능을 가장 효율적으로 사용하는 풀스택 확장 규격을 상술합니다.

---

## 1. Part 1: FastAPI REST Gateway (pip 기반 백엔드)

TruthGuard 라이브러리를 웹 서비스나 모바일 백엔드로 사용하기 위해, 비동기 처리가 가능한 FastAPI 게이트웨이를 구축합니다.

### 1.1 추가 패키지 요구사항 (`requirements.txt`)
```text
fastapi>=0.100.0
uvicorn>=0.22.0
python-multipart>=0.0.6
```

### 1.2 비동기 REST API 서버 구현 (`truthguard_server.py`)

```python
import os
import shutil
from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional

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
```

---

## 2. Part 2: React Web Dashboard & Browser Extension (npm 기반 프론트엔드)

사용자 편의성을 극대화하기 위해 웹 브라우저 및 대시보드를 구축합니다.

### 2.1 프론트엔드 프로젝트 명세 (`package.json`)
```json
{
  "name": "truthguard-dashboard",
  "private": true,
  "version": "0.1.0",
  "type": "module",
  "scripts": {
    "dev": "vite",
    "build": "tsc && vite build",
    "preview": "vite preview"
  },
  "dependencies": {
    "react": "^18.2.0",
    "react-dom": "^18.2.0",
    "axios": "^1.6.0",
    "lucide-react": "^0.290.0",
    "chart.js": "^4.4.0",
    "react-chartjs-2": "^5.2.0"
  },
  "devDependencies": {
    "vite": "^5.0.0",
    "typescript": "^5.0.0"
  }
}
```

### 2.2 React 시각화 대시보드 컴포넌트 (`Dashboard.tsx`)
FastAPI 백엔드가 리턴하는 `ExplainResponse` 객체를 차트와 히드맵으로 연동하여 신뢰도를 시각화합니다.

```tsx
import React, { useState } from 'react';
import axios from 'axios';
import { AlertTriangle, CheckCircle, FileText, BarChart2 } from 'lucide-react';

interface Decision {
  is_manipulated: boolean;
  credibility_score: number;
  risk_level: 'LOW' | 'MEDIUM' | 'HIGH' | 'CRITICAL';
}

interface Metric {
  ai_generation_probability: number;
  editing_artifact_score: number;
}

interface ScanResult {
  target_file: string;
  media_type: string;
  decision: Decision;
  metrics: Metric;
  explanations: Array<{ code: string; severity: string; message: string }>;
}

export default function Dashboard() {
  const [file, setFile] = useState<File | null>(null);
  const [result, setResult] = useState<ScanResult | null>(null);
  const [loading, setLoading] = useState(false);

  const handleUpload = async () => {
    if (!file) return;
    setLoading(true);
    const formData = new FormData();
    formData.append('file', file);

    try {
      const response = await axios.post<ScanResult>('http://localhost:8000/api/v1/scan/media', formData);
      setResult(response.data);
    } catch (err) {
      alert('분석에 실패하였습니다.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="p-8 max-w-4xl mx-auto font-sans">
      <h1 className="text-3xl font-bold mb-6 text-gray-800">TruthGuard AI 신뢰도 대시보드</h1>
      
      <div className="border-2 border-dashed border-gray-300 p-6 rounded-lg mb-6 text-center">
        <input type="file" onChange={(e) => setFile(e.target.files?.[0] || null)} className="mb-4 block mx-auto" />
        <button 
          onClick={handleUpload} 
          disabled={loading}
          className="bg-blue-600 text-white px-4 py-2 rounded hover:bg-blue-700 disabled:opacity-50"
        >
          {loading ? '검사 중...' : '콘텐츠 신뢰성 분석 시작'}
        </button>
      </div>

      {result && (
        <div className="bg-white shadow rounded-lg p-6">
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-xl font-bold">{result.target_file} 스캔 결과</h2>
            <span className={`px-3 py-1 rounded-full text-white font-bold ${
              result.decision.is_manipulated ? 'bg-red-500' : 'bg-green-500'
            }`}>
              {result.decision.is_manipulated ? '변조 의심' : '안전함'}
            </span>
          </div>

          <div className="grid grid-cols-2 gap-4 mb-6">
            <div className="border p-4 rounded bg-gray-50">
              <p className="text-sm text-gray-500">종합 신뢰도 점수</p>
              <p className="text-2xl font-bold text-blue-600">{result.decision.credibility_score * 100}%</p>
            </div>
            <div className="border p-4 rounded bg-gray-50">
              <p className="text-sm text-gray-500">AI 생성 확률</p>
              <p className="text-2xl font-bold text-purple-600">{result.metrics.ai_generation_probability * 100}%</p>
            </div>
          </div>

          <div>
            <h3 className="font-bold mb-2 flex items-center">
              <AlertTriangle className="mr-2 text-yellow-500" /> 탐지된 어노말리 목록
            </h3>
            <ul className="space-y-2">
              {result.explanations.map((exp, idx) => (
                <li key={idx} className="bg-yellow-50 border-l-4 border-yellow-500 p-2 text-sm">
                  <strong>[{exp.code}]</strong> {exp.message}
                </li>
              ))}
            </ul>
          </div>
        </div>
      )}
    </div>
  );
}
```

### 2.3 Chrome Extension Manifest Specification (`manifest.json`)
웹서핑 중 마우스 우클릭으로 이미지를 다운받지 않고 백엔드로 즉시 스캔 요청하는 크롬 브라우저 익스텐션 스펙입니다.

```json
{
  "manifest_version": 3,
  "name": "TruthGuard Web Scanner",
  "version": "0.1.0",
  "description": "우클릭 이미지 및 텍스트의 AI 위변조 실시간 검사",
  "permissions": [
    "contextMenus",
    "activeTab"
  ],
  "background": {
    "service_worker": "background.js"
  },
  "content_scripts": [
    {
      "matches": ["<all_urls>"],
      "js": ["content.js"]
    }
  ]
}
```

---

## 3. Part 3: Model Context Protocol (MCP) Server

에이전트 AI(Claude, Gemini 등)가 웹 서칭 중 만나는 미디어를 자율적으로 검증할 수 있도록 연동하는 JSON-RPC 기반 MCP 인터페이스 규격입니다.

### 3.1 MCP 도구 선언 규격 (`mcp_server.py`)
```python
# python-mcp-server 구현 가이드라인
import asyncio
from mcp.server.models import InitializationOptions
from mcp.server import Notification, Server
import mcp.types as types
import truthguard

server = Server("truthguard-mcp-server")

@server.list_tools()
async def handle_list_tools() -> list[types.Tool]:
    """
    LLM 에이전트에게 TruthGuard가 제공하는 분석 툴 리스트를 전달합니다.
    """
    return [
        types.Tool(
            name="truthguard_scan_text",
            description="텍스트의 허위 사실 및 AI 작성 확률 판별",
            inputSchema={
                "type": "object",
                "properties": {
                    "text": {"type": "string", "description": "분석할 뉴스/블로그 기사 본문"}
                },
                "required": ["text"],
            },
        ),
        types.Tool(
            name="truthguard_scan_image",
            description="이미지 ELA 및 주파수 노이즈 분석을 통한 합성 및 딥페이크 탐지",
            inputSchema={
                "type": "object",
                "properties": {
                    "image_path": {"type": "string", "description": "로컬 이미지 파일 경로"}
                },
                "required": ["image_path"],
            },
        )
    ]

@server.call_tool()
async def handle_call_tool(
    name: str, arguments: dict | None
) -> list[types.TextContent]:
    """
    에이전트가 툴을 트리거할 때 Python SDK를 기동하여 결과를 JSON 구조화 텍스트로 리턴합니다.
    """
    if not arguments:
        raise ValueError("인자가 제공되지 않았습니다.")

    if name == "truthguard_scan_text":
        text = arguments["text"]
        result = truthguard.detect_text(text)
        return [types.TextContent(type="text", text=result.model_dump_json())]
        
    elif name == "truthguard_scan_image":
        image_path = arguments["image_path"]
        result = truthguard.detect_image(image_path)
        return [types.TextContent(type="text", text=result.model_dump_json())]
        
    else:
        raise ValueError(f"지원되지 않는 MCP Tool 입니다: {name}")
```
