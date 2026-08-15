# -*- coding: utf-8 -*-
import os
import tempfile
import unittest

import numpy as np

from truthhistory.video.streaming import StreamingVideoAnalyzer


def _make_capture(fps=30.0, total_frames=300, frame_shape=(240, 320)):
    """cv2.VideoCapture 호환 목업 — 움직이는 사각형 프레임을 미리 생성."""
    frames = []
    for i in range(total_frames):
        frame = np.zeros((*frame_shape, 3), dtype=np.uint8)
        x = (i * 4) % (frame_shape[1] - 40)
        frame[100:140, x:x + 40] = (0, 200, 255)
        frames.append(frame)

    class FakeCapture:
        def __init__(self):
            self._idx = 0
            self._released = False

        def get(self, prop):
            return fps  # CAP_PROP_FPS

        def read(self):
            if self._idx >= len(frames):
                return False, None
            f = frames[self._idx]
            self._idx += 1
            return True, f

        def isOpened(self):
            return not self._released

        def release(self):
            self._released = True

    return FakeCapture()


class TestStreamingVideoAnalyzer(unittest.TestCase):
    def test_chunks_cover_timeline_in_order(self):
        analyzer = StreamingVideoAnalyzer({"chunk_seconds": 2.0})
        chunks = list(analyzer.stream_analyze("fake", capture=_make_capture(total_frames=300)))
        self.assertGreaterEqual(len(chunks), 4)  # 10초 @ 2s 청크
        for prev, cur in zip(chunks, chunks[1:]):
            self.assertEqual(cur["chunk_index"], prev["chunk_index"] + 1)
            self.assertGreaterEqual(cur["time_start"], prev["time_start"])
        # 마지막 청크가 영상 끝(10s) 근처까지 커버
        self.assertGreater(chunks[-1]["time_end"], 8.0)

    def test_every_chunk_has_result(self):
        analyzer = StreamingVideoAnalyzer({"chunk_seconds": 2.0})
        for chunk in analyzer.stream_analyze("fake", capture=_make_capture(total_frames=120)):
            r = chunk["result"]
            self.assertTrue(0.0 <= r.credibility_score <= 1.0)
            self.assertIn(r.risk_level, ["LOW", "MEDIUM", "HIGH", "CRITICAL"])
            self.assertTrue(chunk["frames"] > 0)

    def test_max_chunks_limits_output(self):
        analyzer = StreamingVideoAnalyzer({"chunk_seconds": 2.0})
        chunks = list(analyzer.stream_analyze("fake", max_chunks=2, capture=_make_capture(total_frames=300)))
        self.assertEqual(len(chunks), 2)

    def test_owned_capture_released(self):
        # 분석기가 자체 개방한 캡처는 소비 후 해제된다
        from unittest.mock import patch
        analyzer = StreamingVideoAnalyzer({"chunk_seconds": 2.0})
        cap = _make_capture(total_frames=60)
        with patch.object(StreamingVideoAnalyzer, "_open_capture", return_value=cap):
            chunks = list(analyzer.stream_analyze("fake"))
        self.assertGreaterEqual(len(chunks), 1)
        self.assertFalse(cap.isOpened())

    def test_injected_capture_not_released(self):
        analyzer = StreamingVideoAnalyzer({"chunk_seconds": 2.0})
        cap = _make_capture(total_frames=60)
        for _ in analyzer.stream_analyze("fake", capture=cap):
            break  # 조기 소비 종료
        self.assertTrue(cap.isOpened())  # 주입된 캡처는 호출자 소유

    def test_summarize_empty_chunks_is_neutral(self):
        analyzer = StreamingVideoAnalyzer()
        summary = analyzer.summarize([])
        self.assertEqual(summary.credibility_score, 0.5)
        self.assertFalse(summary.is_manipulated)
        self.assertEqual(summary.analysis_details["chunk_count"], 0)

    def test_summarize_uses_worst_chunk(self):
        analyzer = StreamingVideoAnalyzer()
        from truthhistory.base import AnalysisResult
        good = {"chunk_index": 0, "time_start": 0.0, "time_end": 2.0, "frames": 4,
                "result": AnalysisResult(is_manipulated=False, credibility_score=0.95, ai_probability=0.0)}
        bad = {"chunk_index": 1, "time_start": 2.0, "time_end": 4.0, "frames": 4,
               "result": AnalysisResult(is_manipulated=True, credibility_score=0.3, ai_probability=0.2)}
        summary = analyzer.summarize([good, bad])
        self.assertEqual(summary.credibility_score, 0.3)  # 보수적(최악 청크) 신뢰도
        self.assertTrue(summary.is_manipulated)
        self.assertEqual(summary.ai_probability, 0.2)  # 최대 AI 확률
        self.assertEqual(summary.analysis_details["worst_chunk_index"], 1)

    def test_analyze_real_video_file(self):
        # 실제 mp4 생성 후 종합 분석 (OpenCV 런타임 통합)
        try:
            import cv2
        except ImportError:
            self.skipTest("opencv not installed")
        with tempfile.TemporaryDirectory() as td:
            path = os.path.join(td, "stream.mp4")
            writer = cv2.VideoWriter(path, cv2.VideoWriter_fourcc(*"mp4v"), 30, (320, 240))
            for i in range(150):
                frame = np.zeros((240, 320, 3), dtype=np.uint8)
                cv2.rectangle(frame, ((i * 3) % 280, 100), ((i * 3) % 280 + 40, 140), (0, 200, 255), -1)
                writer.write(frame)
            writer.release()

            analyzer = StreamingVideoAnalyzer({"chunk_seconds": 2.0})
            summary = analyzer.analyze(path)
            self.assertGreaterEqual(summary.analysis_details["chunk_count"], 2)
            self.assertTrue(0.0 <= summary.credibility_score <= 1.0)
            self.assertTrue(any("chunk" in k or "chunks" in k for k in summary.analysis_details))

    def test_unopenable_source_raises_value_error(self):
        analyzer = StreamingVideoAnalyzer()
        with self.assertRaises(ValueError):
            list(analyzer.stream_analyze("Z:/nonexistent/video.mp4"))


if __name__ == "__main__":
    unittest.main()
