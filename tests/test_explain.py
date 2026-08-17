# -*- coding: utf-8 -*-
"""역사 분석 리포트 확장 — 다각도 판별(perspectives)·지정학 왜곡 불허 사유(significance) 단위 테스트."""
import unittest
from unittest.mock import patch

from truthhistory.text.analyzer import TextAnalyzer
from truthhistory.explain.engine import ExplainEngine, SIGNIFICANCE


def _no_external_evidence():
    """외부 검색 증거 소스 전부 비활성(오프라인 결정론 경로) 패치 데코레이터 목록."""
    return [
        patch("truthhistory.text.evidence.search_wikipedia", return_value=[]),
        patch("truthhistory.text.evidence.search_duckduckgo", return_value=[]),
        patch("truthhistory.text.evidence.search_naver", return_value=[]),
    ]


class TestPerspectives(unittest.TestCase):
    """다각도 판별 — 각 독립 렌즈의 점수·판정·종합 집계 검증"""

    def test_text_result_produces_multi_angle_breakdown(self):
        analyzer = TextAnalyzer()
        for p in _no_external_evidence():
            p.start()
        try:
            result = analyzer.analyze("임진왜란은 1592년에 발발했다")
        finally:
            for p in _no_external_evidence():
                p.stop()

        perspectives = ExplainEngine.build_perspectives(result, "text")
        names = [a["name"] for a in perspectives["angles"]]
        # 텍스트 고증의 핵심 각도는 반드시 노출되어야 한다
        for required in ["사료 정합성", "한국사 연표 KB", "AI 생성 가능성", "선동성·과장 표현", "출처 신뢰도", "시대착오(Anachronism)"]:
            self.assertIn(required, names)
        # 정합 사례: 연표 KB 각도는 검증 일치로 정상 판정
        kb = next(a for a in perspectives["angles"] if a["name"] == "한국사 연표 KB")
        self.assertEqual(kb["verdict"], "정상")
        self.assertEqual(kb["score"], 1.0)
        # 모든 각도는 판정·근거 필드를 갖는다
        for angle in perspectives["angles"]:
            self.assertIn(angle["verdict"], ["정상", "주의", "의심", "미판정"])
            self.assertIn("basis", angle)
            self.assertTrue(angle["detail"])

    def test_kb_contradiction_marks_suspected_angle_and_hard_cap(self):
        analyzer = TextAnalyzer()
        for p in _no_external_evidence():
            p.start()
        try:
            result = analyzer.analyze("임진왜란은 1920년에 발발했으며 세종대왕이 직접 지휘했다")
        finally:
            for p in _no_external_evidence():
                p.stop()

        perspectives = ExplainEngine.build_perspectives(result, "text")
        kb = next(a for a in perspectives["angles"] if a["name"] == "한국사 연표 KB")
        self.assertEqual(kb["verdict"], "의심")
        self.assertGreaterEqual(perspectives["summary"]["suspected_angles"], 1)
        self.assertIn("의심", perspectives["summary"]["note"])
        # 결정론 사료 위반은 가중합 희석 없이 상한 적용 → 위조 의심 판정
        self.assertLessEqual(result.credibility_score, 0.35)
        self.assertTrue(result.is_manipulated)

    def test_summary_counts_only_engaged_angles(self):
        analyzer = TextAnalyzer()
        for p in _no_external_evidence():
            p.start()
        try:
            result = analyzer.analyze("밥을 먹었다")  # 역사 주장 없음 → 연표 KB 미판정
        finally:
            for p in _no_external_evidence():
                p.stop()

        perspectives = ExplainEngine.build_perspectives(result, "text")
        kb = next(a for a in perspectives["angles"] if a["name"] == "한국사 연표 KB")
        self.assertEqual(kb["score"], None)
        self.assertEqual(kb["verdict"], "미판정")
        self.assertEqual(
            perspectives["summary"]["total_angles"] - perspectives["summary"]["engaged_angles"] >= 1,
            True,
        )

    def test_media_result_produces_signal_angles(self):
        # 이미지 결과 규격(의존성 부재 중립 경로 포함)에서도 각도 분해가 동작해야 한다
        result = type("R", (), {})()  # AnalysisResult 대체 최소 객체
        result.analysis_details = {
            "error_level_analysis": {"module_available": False, "manipulation_score": 0.0, "mean_difference": 0.0},
            "frequency_analysis": {"ai_probability": 0.1, "spike_count": 0, "module_available": False},
            "deepfake_analysis": {"detected_faces": 0, "asymmetry_score": 0.0},
        }
        perspectives = ExplainEngine.build_perspectives(result, "image")
        names = [a["name"] for a in perspectives["angles"]]
        self.assertIn("ELA 압축 왜곡", names)
        self.assertIn("FFT 주파수 노이즈", names)
        ela = next(a for a in perspectives["angles"] if a["name"] == "ELA 압축 왜곡")
        self.assertEqual(ela["score"], None)  # 모듈 미설치 → 미판정(의심 집계 제외)
        face = next(a for a in perspectives["angles"] if a["name"].startswith("안면 비대칭"))
        self.assertEqual(face["verdict"], "미판정")
        self.assertEqual(perspectives["summary"]["suspected_angles"], 0)

    def test_media_missing_modules_keep_all_angles_undecided(self):
        # 의존성 부재(서버리스 등)에서는 어느 각도도 '정상'으로 집계하지 않고 판정 보류해야 한다 —
        # "97%·LOW·정상" 판정과 "중립 결과 반환" 경고가 공존하던 모순 재발 방지
        result = type("R", (), {})()
        result.analysis_details = {
            "error_level_analysis": {"module_available": False, "manipulation_score": 0.0, "mean_difference": 0.0},
            "frequency_analysis": {"ai_probability": 0.1, "spike_count": 0, "module_available": False},
            "deepfake_analysis": {"detected_faces": 0, "asymmetry_score": 0.0},
        }
        perspectives = ExplainEngine.build_perspectives(result, "image")
        for angle in perspectives["angles"]:
            self.assertEqual(angle["score"], None, angle["name"])
            self.assertEqual(angle["verdict"], "미판정", angle["name"])
        self.assertEqual(perspectives["summary"]["engaged_angles"], 0)
        self.assertEqual(perspectives["summary"]["suspected_angles"], 0)
        self.assertIn("검증 재료 부족", perspectives["summary"]["note"])

    def test_image_with_modules_scores_angles(self):
        # 모듈 정상 설치 환경에서는 신호 각도가 실제 점수로 판별에 참여한다
        result = type("R", (), {})()
        result.analysis_details = {
            "error_level_analysis": {"module_available": True, "manipulation_score": 0.05, "mean_difference": 3.2},
            "frequency_analysis": {"ai_probability": 0.08, "spike_count": 12, "module_available": True},
            "deepfake_analysis": {"detected_faces": 1, "asymmetry_score": 0.12},
        }
        perspectives = ExplainEngine.build_perspectives(result, "image")
        self.assertEqual(perspectives["summary"]["engaged_angles"], 3)
        self.assertTrue(all(a["score"] is not None for a in perspectives["angles"]))
        self.assertEqual(perspectives["summary"]["suspected_angles"], 0)


class TestSignificance(unittest.TestCase):
    """지정학적 역사 왜곡 불허 사유 — 리포트 공통 콘텐츠 구조 검증"""

    def test_significance_content_structure(self):
        self.assertIn("지정학", SIGNIFICANCE["title"])
        self.assertTrue(SIGNIFICANCE["summary"])
        tags = [r["tag"] for r in SIGNIFICANCE["reasons"]]
        self.assertGreaterEqual(len(tags), 5)  # 영토·집단기억·외교신뢰·가해피해·AI증폭
        for reason in SIGNIFICANCE["reasons"]:
            self.assertTrue(reason["tag"])
            self.assertGreater(len(reason["detail"]), 40)

    def test_report_includes_perspectives_and_significance(self):
        analyzer = TextAnalyzer()
        for p in _no_external_evidence():
            p.start()
        try:
            result = analyzer.analyze("세종대왕은 1397년에 태어났다")
        finally:
            for p in _no_external_evidence():
                p.stop()

        report = ExplainEngine.format_explanations(
            target_file="(inline-text)", media_type="text",
            result=result, anomalies=[],
        )
        self.assertIn("perspectives", report)
        self.assertIn("significance", report)
        self.assertEqual(report["significance"]["title"], SIGNIFICANCE["title"])
        self.assertGreaterEqual(len(report["perspectives"]["angles"]), 5)
        # 기존 소비자(확장·대시보드) 호환 필드 유지
        for key in ["target_file", "media_type", "decision", "metrics", "explanations"]:
            self.assertIn(key, report)

    def test_significance_only_for_history_domain_text(self):
        # 지정학 섹션은 역사 영역 콘텐츠에만 — 일반 텍스트(요리·일상)에는 미표시
        analyzer = TextAnalyzer()
        for p in _no_external_evidence():
            p.start()
        try:
            history = analyzer.analyze("임진왜란은 1592년에 발발했다")
            daily = analyzer.analyze("오늘 저녁 메뉴는 크림 파스타이고 맛있었다")
        finally:
            for p in _no_external_evidence():
                p.stop()

        self.assertTrue(history.analysis_details["history_relevant"])
        self.assertFalse(daily.analysis_details["history_relevant"])

        hist_report = ExplainEngine.format_explanations("(t)", "text", history, [])
        daily_report = ExplainEngine.format_explanations("(t)", "text", daily, [])
        self.assertIsNotNone(hist_report["significance"])
        self.assertIsNone(daily_report["significance"])

    def test_significance_media_reports_have_no_geopolitics(self):
        # 이미지·영상·오디오는 위변조 판별 리포트 — 지정학 섹션 없음
        result = type("R", (), {})()
        result.analysis_details = {}
        result.is_manipulated = False
        result.credibility_score = 0.5
        result.risk_level = "MEDIUM"
        result.ai_probability = 0.0
        self.assertFalse(ExplainEngine.should_include_significance(result, "image"))
        self.assertFalse(ExplainEngine.should_include_significance(result, "video"))
        self.assertFalse(ExplainEngine.should_include_significance(result, "audio"))
        report = ExplainEngine.format_explanations("(img)", "image", result, [])
        self.assertIsNone(report["significance"])

    def test_significance_covers_multiple_disputes_with_map(self):
        # 쟁점 다각화 — 독도 편중 금지(간도·사할린·동북공정·강제동원·6·25 포함) + 지도 제시
        joined = " ".join(r["tag"] + r["detail"] for r in SIGNIFICANCE["reasons"])
        for case in ["독도", "간도", "사할린", "동북공정", "강제동원", "위안부", "6·25"]:
            self.assertIn(case, joined, case)
        map_info = SIGNIFICANCE["map"]
        self.assertTrue(map_info["svg"].startswith("<svg"))
        self.assertIn("독도", map_info["svg"])
        self.assertGreaterEqual(len(map_info["sources"]), 3)
        for src in map_info["sources"]:
            self.assertTrue(src["url"].startswith("https://"))

    def test_gauge_rendering_bounds(self):
        self.assertEqual(ExplainEngine.render_gauge(1.0), "█" * 20)
        self.assertEqual(ExplainEngine.render_gauge(0.0), "░" * 20)
        self.assertEqual(len(ExplainEngine.render_gauge(0.53, 10)), 10)
        # 경계 밖 값도 안전 클램프
        self.assertEqual(len(ExplainEngine.render_gauge(2.0, 5)), 5)


if __name__ == "__main__":
    unittest.main()
