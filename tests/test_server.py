# -*- coding: utf-8 -*-
import unittest
from fastapi.testclient import TestClient

from truthhistory_server import app


class TestTruthHistoryServer(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app)

    def test_scan_text_endpoint_returns_xai_report(self):
        # 한국사 문장을 직접 전송해 XAI 리포트 구조가 반환되는지 검증
        r = self.client.post(
            "/api/v1/scan/text",
            json={"text": "이순신 장군은 임진왜란 때 거북선을 이끌고 한산도 대첩에서 승리했다."},
        )
        self.assertEqual(r.status_code, 200)
        data = r.json()
        self.assertIn("decision", data)
        self.assertIn("metrics", data)
        self.assertIn("explanations", data)
        self.assertIsInstance(data["decision"]["is_manipulated"], bool)
        self.assertIn("credibility_score", data["decision"])

    def test_scan_text_rejects_empty_body(self):
        r = self.client.post("/api/v1/scan/text", json={"text": "   "})
        self.assertEqual(r.status_code, 400)


if __name__ == "__main__":
    unittest.main()
