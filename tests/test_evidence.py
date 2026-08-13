# -*- coding: utf-8 -*-
import unittest
from unittest.mock import patch, MagicMock

import truthhistory.text.evidence as ev
from truthhistory.text.analyzer import TextAnalyzer


class _Resp:
    def __init__(self, ok=True, payload=None, text=""):
        self.ok = ok
        self._p = payload
        self.text = text

    def json(self):
        return self._p


def _fake_ddg_get(url, params=None, headers=None, timeout=None, **kw):
    if "api.duckduckgo.com" in url:
        return _Resp(payload={
            "AbstractText": "이순신은 조선 중기의 무신으로 거북선을 지휘하였다.",
            "Heading": "이순신",
            "RelatedTopics": [{"text": "임진왜란 한산도 대첩에서 승리"}],
        })
    if "html.duckduckgo.com" in url:
        return _Resp(text=(
            '<a class="result__a">이순신</a>'
            '<a class="result__snippet">이순신 장군은 임진왜란 때 거북선으로 일본 수군을 격파</a>'
        ))
    return _Resp(ok=False)


class TestEvidence(unittest.TestCase):
    def test_extract_keywords_strips_particles(self):
        kw = ev.extract_keywords("이순신은 임진왜란 때 거북선으로 승리했다")
        self.assertIn("이순신", kw)
        self.assertIn("임진왜란", kw)
        self.assertIn("거북선", kw)
        self.assertNotIn("이순신은", kw)

    def test_score_no_evidence_is_neutral(self):
        r = ev.score_consistency("이순신 임진왜란 거북선", [])
        self.assertEqual(r["consistency_score"], 0.5)
        self.assertFalse(r["contradiction"])

    def test_score_high_coverage(self):
        evidence = [{"source": "x", "snippet": "이순신은 임진왜란 때 거북선으로 승리했다", "title": ""}]
        r = ev.score_consistency("이순신 임진왜란 거북선 승리", evidence)
        self.assertGreater(r["consistency_score"], 0.6)
        self.assertGreater(r["best_coverage"], 0.5)
        self.assertFalse(r["contradiction"])

    def test_score_contradiction_lowers(self):
        evidence = [{"source": "x", "snippet": "이순신이 임진왜란 거북선 승리라는 주장은 거짓이다", "title": ""}]
        r = ev.score_consistency("이순신 임진왜란 거북선 승리", evidence)
        self.assertTrue(r["contradiction"])
        self.assertLess(r["consistency_score"], 0.5)

    @patch("truthhistory.text.evidence.requests.get", side_effect=_fake_ddg_get)
    def test_search_duckduckgo_mocked(self, _mock_get):
        evi = ev.search_duckduckgo("이순신 거북선")
        self.assertTrue(evi)
        self.assertTrue(all(e["source"] == "duckduckgo" for e in evi))

    @patch("truthhistory.text.evidence.requests.get", side_effect=_fake_ddg_get)
    def test_analyzer_fact_consistency_uses_evidence(self, _mock_get):
        analyzer = TextAnalyzer()
        res = analyzer.analyze_fact_consistency("이순신은 임진왜란 때 거북선으로 승리했다")
        self.assertIn("sources_used", res)
        self.assertIn("duckduckgo", res["sources_used"])
        self.assertGreaterEqual(res["evidence_count"], 1)
        self.assertGreaterEqual(res["consistency_score"], 0.0)
        self.assertLessEqual(res["consistency_score"], 1.0)


if __name__ == "__main__":
    unittest.main()
