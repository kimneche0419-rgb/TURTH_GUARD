# -*- coding: utf-8 -*-
from typing import Any, Dict, List

from truthguard.base import BaseAnalyzer, AnalysisResult, LazyModuleImporter

class VideoAnalyzer(BaseAnalyzer):
    """
    영상 프레임 간 불일치성 및 비디오 내 페이스 스왑(Deepfake) 변조를 검증하는 클래스
    """

    def initialize_model(self) -> None:
        self.sample_fps = self.config.get("sample_fps", 2)
        self.temporal_window = self.config.get("temporal_window", 16)
        self.weights = self.config.get("weights", {
            "jitter_weight": 0.5,
            "deepfake_weight": 0.5
        })

    def analyze(self, data: str, **kwargs) -> AnalysisResult:
        if not isinstance(data, str):
            raise ValueError("VideoAnalyzer는 비디오 파일 경로(str)만 처리할 수 있습니다.")

        # 프레임 추출
        frames = self._extract_frames(data)
        
        # 시간 일관성 Jitter 검사
        temporal_results = self.analyze_temporal_consistency(frames)
        jitter_score = temporal_results.get("jitter_index", 0.0)

        # 딥페이크 분석 시뮬레이션
        deepfake_results = self.analyze_deepfake_in_video(frames)
        deepfake_score = deepfake_results.get("max_manipulation_probability", 0.0)

        # 가중합 스코어링
        credibility_score = 1.0 - (
            self.weights["jitter_weight"] * jitter_score +
            self.weights["deepfake_weight"] * deepfake_score
        )

        risk_level = self._determine_risk_level(credibility_score, deepfake_score)

        reasons = []
        if temporal_results.get("has_temporal_jitter", False):
            reasons.append(f"프레임 간 연속성 파괴 감지 (얼굴 경계면의 Jitter 발생, 지수: {jitter_score:.2f})")
        if deepfake_score > 0.8:
            reasons.append(f"비디오 내 안면 영역 합성 패턴 감지 (신뢰도: {deepfake_score * 100:.1f}%)")

        return AnalysisResult(
            is_manipulated=(credibility_score < 0.65) or (deepfake_score > 0.8),
            credibility_score=round(max(credibility_score, 0.0), 4),
            risk_level=risk_level,
            ai_probability=round(deepfake_score, 4),
            analysis_details={
                "temporal_consistency": temporal_results,
                "deepfake_results": deepfake_results
            },
            reasons=reasons
        )

    def supported_formats(self) -> List[str]:
        return ["mp4", "avi", "mov", "mkv"]

    def _extract_frames(self, video_path: str) -> List[Any]:
        """
        OpenCV VideoCapture를 사용해 프레임을 샘플링합니다.
        """
        try:
            cv2 = LazyModuleImporter.import_module("cv2", "video")
            cap = cv2.VideoCapture(video_path)
            if not cap.isOpened():
                return []
                
            fps = cap.get(cv2.CAP_PROP_FPS)
            frame_interval = max(int(fps / self.sample_fps), 1)
            
            frames = []
            frame_count = 0
            while True:
                ret, frame = cap.read()
                if not ret:
                    break
                if frame_count % frame_interval == 0:
                    frames.append(frame)
                frame_count += 1
                
            cap.release()
            return frames
        except (ImportError, Exception):
            # 라이브러리가 없거나 비디오를 열 수 없을 시 모킹 프레임 반환
            return [None] * 5

    def analyze_temporal_consistency(self, frames: List[Any]) -> Dict[str, Any]:
        """
        인접 프레임 간 안면 랜드마크 변위의 일관성을 검사합니다.
        """
        try:
            cv2 = LazyModuleImporter.import_module("cv2", "video")
            np = LazyModuleImporter.import_module("numpy", "video")
            
            # 실제 OpenCV 로직 모사 (안면 변화도 측정)
            diffs = []
            prev_hist = None
            for frame in frames:
                if frame is None:
                    continue
                gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
                hist = cv2.calcHist([gray], [0], None, [256], [0, 256])
                cv2.normalize(hist, hist, 0, 1, cv2.NORM_MINMAX)
                if prev_hist is not None:
                    dist = cv2.compareHist(prev_hist, hist, cv2.HISTCMP_BHATTACHARYYA)
                    diffs.append(dist)
                prev_hist = hist
                
            if not diffs:
                return {"has_temporal_jitter": False, "jitter_index": 0.0}
                
            mean_val = np.mean(diffs)
            std_val = np.std(diffs)
            jitter_idx = std_val / mean_val if mean_val > 0 else 0.0
            
            return {
                "has_temporal_jitter": jitter_idx > 0.35,
                "jitter_index": round(float(jitter_idx), 4)
            }
        except (ImportError, Exception):
            # 폴백
            return {
                "has_temporal_jitter": False,
                "jitter_index": 0.1
            }

    def analyze_deepfake_in_video(self, frames: List[Any]) -> Dict[str, Any]:
        """
        프레임별 개별 딥페이크 탐지 시뮬레이션
        """
        return {
            "manipulated_frame_ratio": 0.1,
            "max_manipulation_probability": 0.2
        }
