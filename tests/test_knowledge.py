# -*- coding: utf-8 -*-
import unittest
from unittest.mock import patch

import truthhistory.text.knowledge as kb
from truthhistory.text.analyzer import TextAnalyzer


class TestKnowledgeBase(unittest.TestCase):
    def test_verified_event_year(self):
        r = kb.verify_chronology("임진왜란은 1592년에 발발했다")
        self.assertEqual(r["verified_count"], 1)
        self.assertEqual(r["contradiction_count"], 0)

    def test_event_year_duration_tolerance(self):
        # 임진왜란(1592~1598) 기간 내 연도는 정합
        r = kb.verify_chronology("1597년 명량해전에서 이순신이 승리했다")
        self.assertEqual(r["contradiction_count"], 0)

    def test_contradictory_event_year(self):
        r = kb.verify_chronology("임진왜란은 1920년에 일어났다")
        self.assertEqual(r["contradiction_count"], 1)
        c = r["contradictions"][0]
        self.assertEqual(c["subject"], "임진왜란")
        self.assertEqual(c["claim_year"], 1920)
        self.assertEqual(c["expected"], [1592, 1598])

    def test_figure_anachronism(self):
        # 세종(1397~1450)은 1592년에 존재하지 않음
        r = kb.verify_chronology("세종대왕은 1592년에 전쟁을 지휘했다")
        self.assertEqual(r["contradiction_count"], 1)
        self.assertIn("시대착오", r["contradictions"][0]["detail"])

    def test_figure_verified_year(self):
        r = kb.verify_chronology("이순신 장군은 1595년에 활동했다")
        self.assertEqual(r["verified_count"], 1)
        self.assertEqual(r["contradiction_count"], 0)

    def test_century_claim(self):
        r = kb.verify_chronology("훈민정음은 15세기에 창제되었다")
        self.assertEqual(r["verified_count"], 1)
        r2 = kb.verify_chronology("훈민정음은 20세기에 창제되었다")
        self.assertEqual(r2["contradiction_count"], 1)

    def test_bc_year(self):
        r = kb.verify_chronology("고구려는 기원전 37년에 건국되었다")
        self.assertEqual(r["verified_count"], 1)

    def test_particle_intervening_match(self):
        # 조사 개입("고구려가 건국") 형태도 매칭
        r = kb.verify_chronology("고구려가 기원전 37년에 건국되었다")
        self.assertGreaterEqual(r["verified_count"] + r["contradiction_count"], 1)

    def test_no_year_claim_is_silent(self):
        # 연도 언급이 없으면 과신 방지를 위해 판정하지 않음
        r = kb.verify_chronology("이순신은 거북선을 지휘했다")
        self.assertEqual(r["verified_count"], 0)
        self.assertEqual(r["contradiction_count"], 0)

    def test_search_knowledge_base_offline_evidence(self):
        evi = kb.search_knowledge_base("이순신 임진왜란 거북선")
        self.assertTrue(evi)
        self.assertEqual(evi[0]["source"], "truthhistory-kb")
        self.assertIn("임진왜란", evi[0]["snippet"])

    def test_search_knowledge_base_no_match(self):
        self.assertEqual(kb.search_knowledge_base("오늘 날씨"), [])


class TestAnalyzerKBIntegration(unittest.TestCase):
    @patch("truthhistory.text.evidence.search_wikipedia", return_value=[])
    @patch("truthhistory.text.evidence.search_duckduckgo", return_value=[])
    def test_offline_kb_contradiction_caps_score(self, _wiki, _ddg):
        analyzer = TextAnalyzer()
        r = analyzer.analyze_fact_consistency("임진왜란은 1920년에 발발했다")
        self.assertIn("truthhistory-kb", r["sources_used"])
        self.assertTrue(r["contradiction"])
        self.assertLessEqual(r["consistency_score"], 0.2)

    @patch("truthhistory.text.evidence.search_wikipedia", return_value=[])
    @patch("truthhistory.text.evidence.search_duckduckgo", return_value=[])
    def test_offline_kb_verified_boosts_score(self, _wiki, _ddg):
        analyzer = TextAnalyzer()
        r = analyzer.analyze_fact_consistency("임진왜란은 1592년에 발발했다")
        # 중립(0.5) + KB 검증 일치 보스팅
        self.assertGreaterEqual(r["consistency_score"], 0.55)
        self.assertFalse(r["contradiction"])

    @patch("truthhistory.text.evidence.search_wikipedia", return_value=[])
    @patch("truthhistory.text.evidence.search_duckduckgo", return_value=[])
    def test_chronology_reasons_surface(self, _wiki, _ddg):
        analyzer = TextAnalyzer()
        res = analyzer.analyze("임진왜란은 1920년에 발발했다")
        self.assertTrue(any("연표" in reason for reason in res.reasons))


if __name__ == "__main__":
    unittest.main()
