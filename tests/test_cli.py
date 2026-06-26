# -*- coding: utf-8 -*-
import os
import tempfile
import unittest
import unittest.mock
from click.testing import CliRunner
from PIL import Image

from truthguard.cli.main import scan, init, dev

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

    def test_cli_init_command_creates_config(self):
        # 격리된 임시 파일시스템 내에서 테스트 실행
        with self.runner.isolated_filesystem():
            # 1. 첫 실행: 설정 파일 및 uploads 폴더가 정상 생성되는지 검증
            result = self.runner.invoke(init)
            self.assertEqual(result.exit_code, 0)
            self.assertTrue(os.path.exists("truthguard.json"))
            self.assertTrue(os.path.exists("uploads"))
            
            # 2. 두 번째 실행: 덮어쓰기 옵션(force) 없이 실행 시 예외 발생 검증
            result2 = self.runner.invoke(init)
            self.assertNotEqual(result2.exit_code, 0)
            self.assertIn("Config file already exists", result2.output)
            
            # 3. 세 번째 실행: --force 옵션 적용 시 정상 재작성 완료 검증
            result3 = self.runner.invoke(init, ["--force"])
            self.assertEqual(result3.exit_code, 0)

    @unittest.mock.patch("subprocess.Popen")
    def test_cli_dev_command_starts_servers(self, mock_popen):
        # dev 명령어 실행 시 uvicorn 및 npm run dev 서브프로세스가 기동되는지 검증
        result = self.runner.invoke(dev)
        self.assertEqual(result.exit_code, 0)
        self.assertIn("Starting TruthGuard Development Servers", result.output)
        self.assertEqual(mock_popen.call_count, 2)

if __name__ == "__main__":
    unittest.main()


