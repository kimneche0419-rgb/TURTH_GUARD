# -*- coding: utf-8 -*-
import os
import tempfile
import unittest
from unittest.mock import patch
from PIL import Image
import numpy as np

from truthhistory.text.analyzer import TextAnalyzer
from truthhistory.image.analyzer import ImageAnalyzer
from truthhistory.video.analyzer import VideoAnalyzer
from truthhistory.audio.analyzer import AudioAnalyzer

class TestTruthHistoryAnalyzers(unittest.TestCase):
    
    def setUp(self):
        # 공통 임시 디렉터리 및 임시 파일 설정
        self.test_dir = tempfile.TemporaryDirectory()
        
        # 1. 텍스트 임시 파일 생성
        self.text_path = os.path.join(self.test_dir.name, "test_news.txt")
        with open(self.text_path, "w", encoding="utf-8") as f:
            f.write("이것은 정상적인 가짜뉴스가 아닌 공인된 정합성이 높은 뉴스 기사 본문입니다. 출처는 https://news.or.kr 입니다.")
            
        # 2. 이미지 임시 파일 생성 (실제 ELA 연산 테스트 가능)
        self.image_path = os.path.join(self.test_dir.name, "test_photo.jpg")
        img = Image.new("RGB", (100, 100), color="blue")
        img.save(self.image_path, "JPEG")
        
        # 3. 비디오 임시 파일 생성 (더미)
        self.video_path = os.path.join(self.test_dir.name, "test_video.mp4")
        with open(self.video_path, "wb") as f:
            f.write(b"dummy_video_stream_bytes")
            
        # 4. 오디오 임시 파일 생성 (더미)
        self.audio_path = os.path.join(self.test_dir.name, "test_audio.wav")
        with open(self.audio_path, "wb") as f:
            f.write(b"dummy_audio_stream_bytes")

    def tearDown(self):
        self.test_dir.cleanup()

    @patch("truthhistory.text.evidence.search_wikipedia", return_value=[])
    @patch("truthhistory.text.evidence.search_duckduckgo", return_value=[])
    @patch("truthhistory.text.evidence.search_naver", return_value=[])
    def test_text_analyzer(self, _wiki, _ddg, _naver):
        analyzer = TextAnalyzer()
        with open(self.text_path, "r", encoding="utf-8") as f:
            text_content = f.read()
            
        result = analyzer.analyze(text_content)
        
        self.assertIsNotNone(result.credibility_score)
        self.assertIsInstance(result.is_manipulated, bool)
        self.assertIn("ai_generation", result.analysis_details)
        self.assertIn("source_credibility", result.analysis_details)

    def test_image_analyzer(self):
        analyzer = ImageAnalyzer()
        result = analyzer.analyze(self.image_path)
        
        self.assertIsNotNone(result.credibility_score)
        self.assertIsInstance(result.is_manipulated, bool)
        self.assertIn("error_level_analysis", result.analysis_details)
        self.assertIn("frequency_analysis", result.analysis_details)
        
        # ELA 정상 파일이므로 변조 점수가 비교적 낮아야 함
        # 피드백 보장 — 정상 컨텐츠여도 판정 근거가 항상 제공되어야 함
        self.assertTrue(result.reasons)

    def test_video_analyzer(self):
        analyzer = VideoAnalyzer()
        result = analyzer.analyze(self.video_path)
        
        self.assertIsNotNone(result.credibility_score)
        self.assertIsInstance(result.is_manipulated, bool)
        # 피드백 보장 — 정상 컨텐츠여도 판정 근거가 항상 제공되어야 함
        self.assertTrue(result.reasons)

    def test_audio_analyzer(self):
        analyzer = AudioAnalyzer()
        result = analyzer.analyze(self.audio_path, transcript="긴급 송금 이체 해주세요. 검찰 금융감독원 수사 대출 계좌입니다.")
        
        self.assertIsNotNone(result.credibility_score)
        # 보이스피싱 키워드가 다수 매칭되었으므로 조작 의심(is_manipulated=True)으로 나와야 함
        self.assertTrue(result.is_manipulated)
        self.assertIn("phishing_analysis", result.analysis_details)
        self.assertTrue(result.reasons)

    def test_media_analyzers_warn_when_dependencies_missing(self):
        # 의존성 부재 폴백 시 '분석 미수행' 경고가 사용자에게 명시되어야 함 (Vercel 서버리스 등)
        def _raise(module_name, extra_group):
            raise ImportError(f"Missing dependency for extra group: {extra_group}")

        for analyzer_cls, path in [
            (ImageAnalyzer, self.image_path),
            (VideoAnalyzer, self.video_path),
            (AudioAnalyzer, self.audio_path),
        ]:
            with patch("truthhistory.base.LazyModuleImporter.import_module", side_effect=_raise), \
                 patch("builtins.print"):
                result = analyzer_cls().analyze(path, transcript="")
            self.assertTrue(any("미설치" in r or "설치되지 않은" in r for r in result.reasons),
                            msg=f"{analyzer_cls.__name__} 의존성 부재 경고 없음: {result.reasons}")

if __name__ == "__main__":
    unittest.main()
