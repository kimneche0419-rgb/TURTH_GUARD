# -*- coding: utf-8 -*-
"""
라이브 스트리밍/장문 영상 실시간 청크 분석기.
- RTSP/HTTP 스트림 URL, 비디오 파일, 웹캠 인덱스를 입력받아 시간 단위 청크로 프레임을
  적재하고 각 청크를 즉시 분석(제너레이터)하여 실시간 변조 탐지 결과를 스트리밍한다.
- 청크별 분석은 VideoAnalyzer의 시간 일관성(Jitter)·페이스 스왑(안면 비대칭) 로직을
  그대로 재사용하며, CRITICAL 청크 발견 시 조기 종료(early-stop)로 지연을 최소화한다.
"""
from typing import Any, Dict, Iterator, List, Optional

from truthhistory.base import BaseAnalyzer, AnalysisResult, LazyModuleImporter
from truthhistory.video.analyzer import VideoAnalyzer


class StreamingVideoAnalyzer(BaseAnalyzer):
    """
    스트리밍 소스를 청크 단위로 실시간 검증하는 분석기 (비동기 증분 처리).
    """

    def initialize_model(self) -> None:
        self.chunk_seconds = float(self.config.get("chunk_seconds", 2.0))
        self.sample_fps = int(self.config.get("sample_fps", 2))
        self.early_stop = bool(self.config.get("early_stop", True))
        self._core = VideoAnalyzer({
            "sample_fps": self.sample_fps,
            "weights": self.config.get("weights", {
                "jitter_weight": 0.5,
                "deepfake_weight": 0.5,
            }),
        })

    # ------------------------------------------------------------------
    # 스트리밍 분석 (제너레이터): 청크가 완성될 때마다 즉시 결과를 방출
    # ------------------------------------------------------------------
    def stream_analyze(
        self,
        source: Any,
        max_chunks: Optional[int] = None,
        capture: Any = None,
    ) -> Iterator[Dict[str, Any]]:
        """
        source: 비디오 파일 경로 / RTSP·HTTP 스트림 URL / 웹캠 인덱스(int)
        capture: 테스트 주입용 cv2.VideoCapture 호환 객체 (기본: source로 자동 개방)
        yield: {chunk_index, time_start, time_end, frames, result(AnalysisResult)}
        """
        owns_capture = capture is None
        if capture is None:
            capture = self._open_capture(source)
        chunk_index = 0
        try:
            for time_start, time_end, frames in self._iter_chunks(capture):
                result = self._analyze_chunk(frames)
                yield {
                    "chunk_index": chunk_index,
                    "time_start": round(time_start, 2),
                    "time_end": round(time_end, 2),
                    "frames": len(frames),
                    "result": result,
                }
                chunk_index += 1
                if self.early_stop and result.risk_level == "CRITICAL":
                    break
                if max_chunks is not None and chunk_index >= max_chunks:
                    break
        finally:
            if owns_capture:
                try:
                    capture.release()
                except Exception:
                    pass

    # ------------------------------------------------------------------
    # 전체 요약 분석 (청크 스트리밍을 소비해 종합 판정)
    # ------------------------------------------------------------------
    def analyze(self, data: Any, max_chunks: Optional[int] = None, **kwargs) -> AnalysisResult:
        chunks: List[Dict[str, Any]] = list(self.stream_analyze(data, max_chunks=max_chunks))
        return self.summarize(chunks)

    def summarize(self, chunks: List[Dict[str, Any]]) -> AnalysisResult:
        """청크 결과를 종합한다 — 신뢰도는 최악 청크(보수적), AI 확률은 최대값."""
        if not chunks:
            return AnalysisResult(
                is_manipulated=False,
                credibility_score=0.5,
                risk_level="LOW",
                ai_probability=0.0,
                analysis_details={"chunks": [], "chunk_count": 0},
                reasons=["스트림에서 분석 가능한 프레임이 없음 — 중립 처리"],
            )

        timeline = []
        worst = chunks[0]
        for ch in chunks:
            r: AnalysisResult = ch["result"]
            timeline.append({
                "chunk_index": ch["chunk_index"],
                "time_start": ch["time_start"],
                "time_end": ch["time_end"],
                "frames": ch["frames"],
                "credibility_score": r.credibility_score,
                "ai_probability": r.ai_probability,
                "risk_level": r.risk_level,
                "is_manipulated": r.is_manipulated,
            })
            if r.credibility_score < worst["result"].credibility_score:
                worst = ch

        worst_result: AnalysisResult = worst["result"]
        max_ai = max(c["result"].ai_probability for c in chunks)
        manipulated_count = sum(1 for c in chunks if c["result"].is_manipulated)
        credibility = worst_result.credibility_score
        risk_level = self._determine_risk_level(credibility, max_ai)

        reasons = []
        if manipulated_count:
            reasons.append(
                f"{len(chunks)}개 청크 중 {manipulated_count}개 청크에서 변조 의심 — "
                f"최초 이상 구간: {worst['time_start']}s~{worst['time_end']}s (청크 #{worst['chunk_index'] + 1})"
            )
        reasons.extend(worst_result.reasons)
        if not reasons:
            reasons.append(f"전체 {len(chunks)}개 청크에서 이상 징후 미검출")

        return AnalysisResult(
            is_manipulated=(manipulated_count > 0) or (max_ai > 0.8),
            credibility_score=credibility,
            risk_level=risk_level,
            ai_probability=round(max_ai, 4),
            analysis_details={
                "streaming": True,
                "chunk_count": len(chunks),
                "worst_chunk_index": worst["chunk_index"],
                "worst_chunk_range": [worst["time_start"], worst["time_end"]],
                "chunks": timeline,
            },
            reasons=reasons,
        )

    def supported_formats(self) -> List[str]:
        return ["mp4", "avi", "mov", "mkv", "rtsp", "http-stream", "webcam"]

    # ------------------------------------------------------------------ # 내부
    # ------------------------------------------------------------------
    def _open_capture(self, source: Any) -> Any:
        cv2 = LazyModuleImporter.import_module("cv2", "video")
        src = int(source) if isinstance(source, str) and source.isdigit() else source
        capture = cv2.VideoCapture(src)
        if not capture or not capture.isOpened():
            raise ValueError(f"스트림/비디오 소스를 열 수 없습니다: {source}")
        return capture

    def _iter_chunks(self, capture: Any) -> Iterator[tuple]:
        """프레임을 읽어 chunk_seconds 단위 청크로 자른다 (sample_fps 샘플링)."""
        cv2 = LazyModuleImporter.import_module("cv2", "video")
        fps = capture.get(cv2.CAP_PROP_FPS)
        if not fps or fps <= 0:
            fps = 30.0  # 라이브 스트림의 FPS 미보고 시 가정치
        frame_interval = max(int(fps / self.sample_fps), 1)
        chunk_frames = max(int(fps * self.chunk_seconds), 1)

        buffer: List[Any] = []
        chunk_first_idx: Optional[int] = None
        frame_idx = 0
        while True:
            ret, frame = capture.read()
            if not ret:
                break
            if frame_idx % frame_interval == 0:
                if chunk_first_idx is None:
                    chunk_first_idx = frame_idx
                buffer.append(frame)
            frame_idx += 1
            sampled = len(buffer) * frame_interval
            if sampled >= chunk_frames:
                yield (
                    chunk_first_idx / fps,
                    frame_idx / fps,
                    buffer,
                )
                buffer = []
                chunk_first_idx = None
        if buffer:  # 마지막 미완 청크 방출
            yield (chunk_first_idx / fps, frame_idx / fps, buffer)

    def _analyze_chunk(self, frames: List[Any]) -> AnalysisResult:
        temporal = self._core.analyze_temporal_consistency(frames)
        deepfake = self._core.analyze_deepfake_in_video(frames)
        jitter = temporal.get("jitter_index", 0.0)
        deepfake_score = deepfake.get("max_manipulation_probability", 0.0)
        credibility = 1.0 - (
            self._core.weights["jitter_weight"] * jitter +
            self._core.weights["deepfake_weight"] * deepfake_score
        )
        reasons = []
        if temporal.get("has_temporal_jitter", False):
            reasons.append(f"청크 내 프레임 연속성 파괴 (Jitter 지수: {jitter:.2f})")
        if deepfake_score > 0.8:
            reasons.append(f"안면 영역 합성 패턴 감지 (신뢰도: {deepfake_score * 100:.1f}%)")
        return AnalysisResult(
            is_manipulated=(credibility < 0.65) or (deepfake_score > 0.8),
            credibility_score=round(max(credibility, 0.0), 4),
            risk_level=self._determine_risk_level(credibility, deepfake_score),
            ai_probability=round(deepfake_score, 4),
            analysis_details={
                "temporal_consistency": temporal,
                "deepfake_results": deepfake,
            },
            reasons=reasons,
        )
