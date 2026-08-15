# -*- coding: utf-8 -*-
import unittest
from unittest.mock import patch, MagicMock

from truthhistory.text.llm import verify_with_openrouter, _extract_json
from truthhistory.text.analyzer import TextAnalyzer


def _resp(payload, ok=True, status=200):
    m = MagicMock()
    m.ok = ok
    m.status_code = status
    m.json.return_value = payload
    return m


class TestExtractJson(unittest.TestCase):
    def test_plain_json(self):
        d = _extract_json('{"is_hallucination": true}')
        self.assertEqual(d["is_hallucination"], True)

    def test_fenced_json(self):
        d = _extract_json('```json\n{"is_hallucination": false, "confidence": 0.9}\n```')
        self.assertEqual(d["confidence"], 0.9)

    def test_json_with_surrounding_text(self):
        d = _extract_json('판정 결과는 다음과 같습니다. {"is_hallucination": true} 감사합니다.')
        self.assertIsNotNone(d)

    def test_invalid_returns_none(self):
        self.assertIsNone(_extract_json("판정 불가"))
        self.assertIsNone(_extract_json("[1,2,3]"))


class TestVerifyWithOpenRouter(unittest.TestCase):
    def test_no_key_disables_gracefully(self):
        with patch.dict("os.environ", {}, clear=True):
            r = verify_with_openrouter("임진왜란은 1592년")
        self.assertFalse(r["available"])

    def test_success_response_parsed(self):
        payload = {"choices": [{"message": {"content":
            '{"is_hallucination": true, "confidence": 0.95, '
            '"errors": [{"claim": "1920년 발발", "problem": "1592년이 정확"}], '
            '"summary": "연도 왜곡"}'}}]}
        with patch.dict("os.environ", {"OPENROUTER_API_KEY": "test-key"}):
            with patch("truthhistory.text.llm.requests.post", return_value=_resp(payload)) as post:
                r = verify_with_openrouter("임진왜란은 1920년에 발발했다")
        self.assertTrue(r["available"])
        self.assertTrue(r["is_hallucination"])
        self.assertGreaterEqual(r["confidence"], 0.9)
        # 무료 모델 기본값 사용 확인
        self.assertIn(":free", post.call_args.kwargs["json"]["model"])
        self.assertEqual(post.call_args.kwargs["headers"]["Authorization"], "Bearer test-key")

    def test_http_error_graceful(self):
        with patch.dict("os.environ", {"OPENROUTER_API_KEY": "test-key"}):
            with patch("truthhistory.text.llm.requests.post", return_value=_resp({}, ok=False, status=429)):
                r = verify_with_openrouter("텍스트")
        self.assertFalse(r["available"])
        self.assertIn("429", r["error"])

    def test_unparseable_response_graceful(self):
        payload = {"choices": [{"message": {"content": "JSON이 아니에요"}}]}
        with patch.dict("os.environ", {"OPENROUTER_API_KEY": "test-key"}):
            with patch("truthhistory.text.llm.requests.post", return_value=_resp(payload)):
                r = verify_with_openrouter("텍스트")
        self.assertFalse(r["available"])
        self.assertIn("파싱 실패", r["error"])


class TestAnalyzerLLMIntegration(unittest.TestCase):
    @patch("truthhistory.text.evidence.search_wikipedia", return_value=[])
    @patch("truthhistory.text.evidence.search_duckduckgo", return_value=[])
    def test_disabled_key_does_not_affect_pipeline(self, _wiki, _ddg):
        analyzer = TextAnalyzer({"openrouter_api_key": None})
        res = analyzer.analyze("임진왜란은 1592년에 발발했다")
        self.assertFalse(res.analysis_details["llm_judge"]["available"])
        self.assertFalse(any("OpenRouter" in r for r in res.reasons))

    @patch("truthhistory.text.evidence.search_wikipedia", return_value=[])
    @patch("truthhistory.text.evidence.search_duckduckgo", return_value=[])
    def test_hallucination_verdict_caps_score(self, _wiki, _ddg):
        verdict = {"available": True, "model": "m:free", "is_hallucination": True,
                   "confidence": 0.95, "errors": [{"claim": "c", "problem": "1592년이 정확"}],
                   "summary": "연도 왜곡"}
        with patch("truthhistory.text.llm.verify_with_openrouter", return_value=verdict):
            analyzer = TextAnalyzer({"openrouter_api_key": "k"})
            res = analyzer.analyze("임진왜란은 1920년에 발발했다")
        self.assertLessEqual(res.credibility_score, 0.35)
        self.assertTrue(any("OpenRouter" in r and "할루시네이션" in r for r in res.reasons))

    @patch("truthhistory.text.evidence.search_wikipedia", return_value=[])
    @patch("truthhistory.text.evidence.search_duckduckgo", return_value=[])
    def test_consistent_verdict_adds_reason(self, _wiki, _ddg):
        verdict = {"available": True, "model": "m:free", "is_hallucination": False,
                   "confidence": 0.9, "errors": [], "summary": "정합"}
        with patch("truthhistory.text.llm.verify_with_openrouter", return_value=verdict):
            analyzer = TextAnalyzer({"openrouter_api_key": "k"})
            res = analyzer.analyze("임진왜란은 1592년에 발발했다")
        self.assertTrue(any("OpenRouter" in r and "정합" in r for r in res.reasons))


if __name__ == "__main__":
    unittest.main()
