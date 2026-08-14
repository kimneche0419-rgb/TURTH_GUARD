# -*- coding: utf-8 -*-
"""MCP stdio 서버 도구 계약 테스트 (확장 프로그램 모티브 정렬 검증)."""
import json
import unittest

from truthhistory_mcp import handle_list_tools, handle_call_tool


class TestMCPTools(unittest.TestCase):
    def test_list_tools_scan_text_is_primary(self):
        # scan_text(확장 프로그램 모티브 = LLM 답변 텍스트 즉시 검증)가 첫 번째 도구여야 함
        response = handle_list_tools(1)
        tools = response["result"]["tools"]
        self.assertEqual(tools[0]["name"], "scan_text")
        self.assertEqual(tools[1]["name"], "scan_file")
        required = tools[0]["inputSchema"]["required"]
        self.assertEqual(required, ["text"])

    def test_call_scan_text_returns_hallucination_report(self):
        response = handle_call_tool(2, "scan_text", {
            "text": "이것은 정상적인 공인 뉴스 기사 내용입니다. 출처는 https://news.or.kr 입니다."
        })
        content = response["result"]["content"][0]["text"]
        report = json.loads(content)
        # 확장 프로그램 판정 리포트와 동일한 필드 노출
        for key in ("is_manipulated", "credibility_score", "risk_level", "ai_probability", "reasons", "analysis_details"):
            self.assertIn(key, report)
        self.assertIsInstance(report["reasons"], list)

    def test_call_scan_text_rejects_empty(self):
        response = handle_call_tool(3, "scan_text", {"text": ""})
        self.assertIn("error", response)

    def test_call_unknown_tool_errors(self):
        response = handle_call_tool(4, "no_such_tool", {})
        self.assertIn("error", response)


if __name__ == "__main__":
    unittest.main()
