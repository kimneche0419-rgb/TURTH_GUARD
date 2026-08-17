# -*- coding: utf-8 -*-
import unittest
from unittest.mock import patch
from fastapi.testclient import TestClient

from truthhistory_server import app


class TestTruthHistoryServer(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app)
    @patch("truthhistory.text.evidence.search_wikipedia", return_value=[])
    @patch("truthhistory.text.evidence.search_duckduckgo", return_value=[])
    @patch("truthhistory.text.evidence.search_naver", return_value=[])
    def test_scan_text_endpoint_returns_xai_report(self, _wiki, _ddg, _naver):
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
        # 다각도 판별 + 지정학 왜곡 불허 사유 — 리포트 확장 필드 검증
        self.assertIn("perspectives", data)
        self.assertIn("significance", data)
        self.assertGreaterEqual(len(data["perspectives"]["angles"]), 5)
        self.assertIn("note", data["perspectives"]["summary"])
        self.assertIn("지정학", data["significance"]["title"])
        self.assertGreaterEqual(len(data["significance"]["reasons"]), 5)
        self.assertIsInstance(data["decision"]["is_manipulated"], bool)
        self.assertIn("credibility_score", data["decision"])

    def test_scan_text_rejects_empty_body(self):
        r = self.client.post("/api/v1/scan/text", json={"text": "   "})
        self.assertEqual(r.status_code, 400)

    def test_health_check_endpoint(self):
        # 헬스체크 엔드포인트 정상 동작 및 기능 가용성 메타데이터 반환 검증
        r = self.client.get("/health")
        self.assertEqual(r.status_code, 200)
        data = r.json()
        self.assertEqual(data["status"], "ok")
        self.assertIn("features", data)
        self.assertTrue(data["features"]["text"])

    def test_scan_media_image_upload(self):
        # 이미지 업로드 스캔 200 OK 및 XAI 리포트 반환 검증
        import io
        from PIL import Image
        img_bytes = io.BytesIO()
        Image.new("RGB", (64, 64), color="blue").save(img_bytes, format="JPEG")
        img_bytes.seek(0)
        r = self.client.post(
            "/api/v1/scan/media",
            files={"file": ("test.jpg", img_bytes, "image/jpeg")},
        )
        self.assertEqual(r.status_code, 200)
        data = r.json()
        self.assertEqual(data["media_type"], "image")
        self.assertIn("decision", data)
        self.assertIn("explanations", data)

if __name__ == "__main__":
    unittest.main()
