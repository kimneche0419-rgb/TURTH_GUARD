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
        self._assert_image_result(result)

    def test_fft_runs_with_pillow_when_cv2_missing(self):
        # 서버리스(Vercel) 시나리오 — cv2 없이 Pillow+numpy만으로 정밀 FFT 동작 검증
        from unittest.mock import patch as _patch
        from truthhistory.base import LazyModuleImporter as LMI

        real_import = LMI.import_module

        def _no_cv2(module_name, extra_group):
            if module_name == "cv2":
                raise ImportError("No module named 'cv2' (serverless)")
            return real_import(module_name, extra_group)

        analyzer = ImageAnalyzer()
        with _patch.object(LMI, "import_module", staticmethod(_no_cv2)):
            fft = analyzer.analyze_frequency_domain(self.image_path)
        self.assertTrue(fft["module_available"])
        self.assertEqual(fft["loader"], "pillow")
        self.assertIsInstance(fft["ai_probability"], float)
        self.assertGreaterEqual(fft["spike_count"], 0)

        # 전체 분석도 중립 폴백이 아닌 정밀 점수로 판정해야 함
        with _patch.object(LMI, "import_module", staticmethod(_no_cv2)):
            result = analyzer.analyze(self.image_path)
        self.assertNotIn("중립(50%) 결과 반환됨", " ".join(result.reasons))
        self.assertNotEqual(result.credibility_score, 0.50)

    def _assert_image_result(self, result):
        self.assertIsNotNone(result.credibility_score)
        self.assertIsInstance(result.is_manipulated, bool)
        self.assertIn("error_level_analysis", result.analysis_details)
        self.assertIn("frequency_analysis", result.analysis_details)
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

class TestSourceCredibilityCriteria(unittest.TestCase):
    """출처 신뢰도 기준 — SIFT(횡적 읽기)/FEVER(NEI) 문헌 근거 재설계 검증"""

    def test_tier_a_official_sources(self):
        analyzer = TextAnalyzer()
        r = analyzer.verify_source_credibility("출처: https://db.history.go.kr/item.do?levelId=imjin")
        self.assertEqual(r["source_tier"], "A")
        self.assertEqual(r["credibility_score"], 0.95)

    def test_tier_b_unknown_url(self):
        analyzer = TextAnalyzer()
        r = analyzer.verify_source_credibility("보러가기 https://blog.example.xyz/post/1")
        self.assertEqual(r["source_tier"], "B")
        self.assertEqual(r["credibility_score"], 0.60)

    def test_tier_c_no_url_is_neutral_not_negative(self):
        # 'URL 부재'는 부정 증거가 아님 — 중립 0.5 (기존 0.3 감점 제거)
        analyzer = TextAnalyzer()
        r = analyzer.verify_source_credibility("임진왜란은 1592년에 발발했다")
        self.assertEqual(r["source_tier"], "C")
        self.assertEqual(r["credibility_score"], 0.5)

    @patch("truthhistory.text.evidence.search_wikipedia", return_value=[])
    @patch("truthhistory.text.evidence.search_duckduckgo", return_value=[])
    def test_nei_reason_only_when_unverifiable(self, _wiki, _ddg):
        # NEI(NotEnoughInfo): 증거·KB 어느 것도 작동하지 않은 경우에만 표시
        analyzer = TextAnalyzer()
        res = analyzer.analyze("어느 역사학자가 새로운 해석을 제기했다는 이야기가 있다")
        self.assertTrue(any("NEI" in r for r in res.reasons))

    @patch("truthhistory.text.evidence.search_wikipedia", return_value=[])
    @patch("truthhistory.text.evidence.search_duckduckgo", return_value=[])
    def test_no_nei_when_kb_engaged(self, _wiki, _ddg):
        # KB 연표 검증이 작동한 텍스트에는 '출처 식별 불가' 류 경고가 붙지 않아야 함
        analyzer = TextAnalyzer()
        res = analyzer.analyze("임진왜란은 1920년에 발발했다")
        self.assertFalse(any("NEI" in r or "식별 불가" in r for r in res.reasons))
        self.assertTrue(any("연표" in r for r in res.reasons))

    def test_no_nei_when_url_present(self):
        analyzer = TextAnalyzer()
        res = analyzer.analyze("기사 본문입니다. 출처 https://news.or.kr/article/1")
        self.assertFalse(any("NEI" in r for r in res.reasons))

if __name__ == "__main__":
    unittest.main()
