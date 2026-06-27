# -*- coding: utf-8 -*-
import sys
import os
import json
import traceback

# Ensure we can import truthguard
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))
import truthguard

def log_debug(msg):
    # Log to stderr since stdout is used for JSON-RPC messages
    sys.stderr.write(f"[DEBUG] {msg}\n")
    sys.stderr.flush()

def handle_initialize(request_id):
    response = {
        "jsonrpc": "2.0",
        "id": request_id,
        "result": {
            "protocolVersion": "2024-11-05",
            "capabilities": {
                "tools": {}
            },
            "serverInfo": {
                "name": "truthguard-mcp",
                "version": "0.1.0"
            }
        }
    }
    return response

def handle_list_tools(request_id):
    tools = [
        {
          "name": "scan_file",
          "description": "지정된 경로의 파일(텍스트, 이미지, 비디오, 오디오)의 위조 및 변조 신뢰도를 스캔하여 종합 보고서를 반환합니다.",
          "inputSchema": {
            "type": "object",
            "properties": {
              "path": {
                "type": "string",
                "description": "분석할 미디어 파일의 절대 경로 또는 상대 경로"
              }
            },
            "required": ["path"]
          }
        },
        {
          "name": "scan_text",
          "description": "텍스트 본문의 신뢰성, AI 생성 확률, 선동성 지수 및 이상 징후를 직접 실시간 분석합니다.",
          "inputSchema": {
            "type": "object",
            "properties": {
              "text": {
                "type": "string",
                "description": "분석할 텍스트 문자열 내용"
              }
            },
            "required": ["text"]
          }
        }
    ]
    return {
        "jsonrpc": "2.0",
        "id": request_id,
        "result": {
            "tools": tools
        }
    }

def handle_call_tool(request_id, name, arguments):
    try:
        if name == "scan_text":
            text = arguments.get("text", "")
            if not text:
                return make_error_response(request_id, -32602, "text argument is required")
            
            result = truthguard.detect_text(text)
            
            # Format output
            report = {
                "is_manipulated": result.is_manipulated,
                "credibility_score": result.credibility_score,
                "risk_level": result.risk_level,
                "ai_probability": result.ai_probability,
                "reasons": result.reasons,
                "analysis_details": result.analysis_details
            }
            
            return make_success_tool_response(request_id, report)
            
        elif name == "scan_file":
            path = arguments.get("path", "")
            if not path or not os.path.exists(path):
                return make_error_response(request_id, -32602, f"file not found: {path}")
                
            ext = path.split(".")[-1].lower()
            if ext in ["txt", "md"]:
                with open(path, "r", encoding="utf-8") as f:
                    content = f.read()
                result = truthguard.detect_text(content)
            elif ext in ["jpg", "jpeg", "png", "webp"]:
                result = truthguard.detect_image(path)
            elif ext in ["mp4", "avi", "mov", "mkv"]:
                result = truthguard.detect_video(path)
            elif ext in ["wav", "mp3", "m4a", "flac"]:
                result = truthguard.detect_audio(path)
            else:
                return make_error_response(request_id, -32602, f"unsupported media type: {ext}")
                
            report = {
                "target_file": os.path.basename(path),
                "media_type": ext,
                "is_manipulated": result.is_manipulated,
                "credibility_score": result.credibility_score,
                "risk_level": result.risk_level,
                "ai_probability": result.ai_probability,
                "reasons": result.reasons
            }
            return make_success_tool_response(request_id, report)
            
        else:
            return make_error_response(request_id, -32601, f"Tool not found: {name}")
            
    except Exception as e:
        return make_error_response(request_id, -32603, f"Internal error: {str(e)}\n{traceback.format_exc()}")

def make_success_tool_response(request_id, data):
    return {
        "jsonrpc": "2.0",
        "id": request_id,
        "result": {
            "content": [
                {
                    "type": "text",
                    "text": json.dumps(data, indent=2, ensure_ascii=False)
                }
            ]
        }
    }

def make_error_response(request_id, code, message):
    return {
        "jsonrpc": "2.0",
        "id": request_id,
        "error": {
            "code": code,
            "message": message
        }
    }

def main():
    log_debug("TruthGuard MCP Server started")
    sys.stdout.reconfigure(encoding="utf-8") if hasattr(sys.stdout, "reconfigure") else None
    
    while True:
        try:
            line = sys.stdin.readline()
            if not line:
                break
                
            line = line.strip()
            if not line:
                continue
                
            log_debug(f"Received: {line}")
            request = json.loads(line)
            
            method = request.get("method")
            request_id = request.get("id")
            
            if method == "initialize":
                response = handle_initialize(request_id)
            elif method == "notifications/initialized":
                continue # No response needed
            elif method == "tools/list":
                response = handle_list_tools(request_id)
            elif method == "tools/call":
                params = request.get("params", {})
                name = params.get("name")
                arguments = params.get("arguments", {})
                response = handle_call_tool(request_id, name, arguments)
            elif method == "ping":
                response = {"jsonrpc": "2.0", "id": request_id, "result": {}}
            else:
                if request_id is not None:
                    response = make_error_response(request_id, -32601, f"Method not found: {method}")
                else:
                    continue
            
            response_str = json.dumps(response, ensure_ascii=False)
            log_debug(f"Sending: {response_str}")
            sys.stdout.write(response_str + "\n")
            sys.stdout.flush()
            
        except Exception as e:
            log_debug(f"Error in main loop: {str(e)}\n{traceback.format_exc()}")

if __name__ == "__main__":
    main()
