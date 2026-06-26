# -*- coding: utf-8 -*-
import os
import tempfile
import unittest
from click.testing import CliRunner
from PIL import Image

from truthguard.cli.main import scan

class TestTruthGuardCLI(unittest.TestCase):
    def setUp(self):
        self.runner = CliRunner()
        self.test_dir = tempfile.TemporaryDirectory()
        
        # 1. 정상 텍스트 파일 생성
        self.text_path = os.path.join(self.test_dir.name, "news.txt")
        with open(self.text_path, "w", encoding="utf-8") as f:
            f.write("이것은 정상적인 공인 기사입니다. 출처는 https://news.or.kr 입니다.")
            
        # 2. ELA 정상 이미지 생성
        self.image_path = os.path.join(self.test_dir.name, "photo.jpg")
        img = Image.new("RGB", (80, 80), color="green")
        img.save(self.image_path, "JPEG")

    def tearDown(self):
        self.test_dir.cleanup()

    def test_cli_scan_text_success(self):
        # 정상 파일은 exit_code가 0이어야 함
        result = self.runner.invoke(scan, [self.text_path])
        self.assertEqual(result.exit_code, 0)
        self.assertIn("대상 파일", result.output)
        self.assertIn("정상 콘텐츠", result.output)

    def test_cli_scan_image_json_format(self):
        # JSON 포맷 출력 검증
        result = self.runner.invoke(scan, [self.image_path, "-f", "json"])
        self.assertEqual(result.exit_code, 0)
        # JSON 파싱성 확인
        import json
        output = result.output
        start_idx = output.find("{")
        end_idx = output.rfind("}") + 1
        data = json.loads(output[start_idx:end_idx])
        self.assertEqual(data["media_type"], "image")
        self.assertIn("decision", data)

    def test_cli_scan_table_format(self):
        # 테이블 포맷 출력 검증
        result = self.runner.invoke(scan, [self.image_path, "-f", "table"])
        self.assertEqual(result.exit_code, 0)
        self.assertIn("TruthGuard Scan Summary", result.output)

if __name__ == "__main__":
    unittest.main()
