# -*- coding: utf-8 -*-
from typing import Any, Dict, List

from truthhistory.base import BaseAnalyzer, AnalysisResult, LazyModuleImporter

class AudioAnalyzer(BaseAnalyzer):
    """
    AI 복제(클론)·합성 음성을 판별하고 사칭·허위정보 유도 어휘를 탐지하는 분석기 클래스
    """

    def initialize_model(self) -> None:
        self.sample_rate = self.config.get("sample_rate", 16000)
        self.weights = self.config.get("weights", {
            "spectral_weight": 0.6,
            "phishing_weight": 0.4
        })

    def analyze(self, data: str, **kwargs) -> AnalysisResult:
        if not isinstance(data, str):
            raise ValueError("AudioAnalyzer는 오디오 파일 경로(str)만 처리할 수 있습니다.")

        # 1. 스펙트럼 분석
        spectral_results = self.analyze_spectral_features(data)
        ai_prob = spectral_results.get("synthetic_voice_probability", 0.0)

        # 2. AI 복제 음성 기반 사칭·위험 어휘 문맥 분석 (STT 전사 텍스트)
        transcript = kwargs.get("transcript", "")
        phishing_results = self.detect_voice_phishing(transcript)
        phishing_prob = phishing_results.get("phishing_probability", 0.0)

        # 가중치 계산
        credibility_score = 1.0 - (
            self.weights["spectral_weight"] * ai_prob +
            self.weights["phishing_weight"] * phishing_prob
        )

        risk_level = self._determine_risk_level(credibility_score, ai_prob)

        reasons = []
        if ai_prob > 0.8:
            reasons.append(f"음향 주파수 왜곡 및 기계 합성 음성 감지 (확률: {ai_prob * 100:.1f}%)")
        if phishing_prob > 0.7:
            reasons.append("AI 복제 음성 기반 인물 사칭 및 금전·허위정보 유도 위험 어휘 패턴 검출")

        # 피드백 보장: 의존성 부재 경고 또는 정상 판정 근거를 항상 제공
        modules_available = spectral_results.get("module_available", True)
        if not modules_available:
            credibility_score = 0.50
            risk_level = "MEDIUM"
            is_manipulated = phishing_prob > 0.7
            reasons.append("⚠ 오디오 정밀 분석 모듈(librosa)이 설치되지 않은 환경 — 중립(50%) 결과 반환됨. "
                           "정밀 MFCC/HNR 분석은 로컬 CLI(`th scan 음성경로`) 또는 `pip install -e .[audio]` 후 이용")
        else:
            is_manipulated = (credibility_score < 0.6) or (ai_prob > 0.8)
            if not reasons:
                reasons.append(f"이상 징후 미검출 — HNR {spectral_results.get('hnr_decibels', 0.0):.1f}dB"
                               "(자연 음성 범위) · 사칭·유도 어휘 패턴 미검출"
                               + ("" if transcript else " (STT 전사 텍스트 미제공 — 어휘 문맥 분석 생략)"))

        return AnalysisResult(
            is_manipulated=is_manipulated,
            credibility_score=round(max(credibility_score, 0.0), 4),
            risk_level=risk_level,
            ai_probability=round(ai_prob, 4),
            analysis_details={
                "spectral_analysis": spectral_results,
                "phishing_analysis": phishing_results
            },
            reasons=reasons
        )

    def supported_formats(self) -> List[str]:
        return ["wav", "mp3", "m4a", "flac"]

    def analyze_spectral_features(self, audio_path: str) -> Dict[str, Any]:
        """
        librosa 라이브러리를 활용해 MFCC 및 HNR 값을 계산합니다.
        """
        try:
            librosa = LazyModuleImporter.import_module("librosa", "audio")
            np = LazyModuleImporter.import_module("numpy", "audio")
            
            # 음성 로딩 및 계산
            y, sr = librosa.load(audio_path, sr=self.sample_rate)
            
            # MFCC 추출
            mfccs = librosa.feature.mfcc(y=y, sr=sr, n_mfcc=13)
            mfcc_mean = np.mean(mfccs, axis=1)
            
            # HNR 간이 연산 (Harmonic vs Noise 에너지)
            y_harm, y_noise = librosa.effects.hpss(y)
            harm_energy = np.sum(y_harm ** 2)
            noise_energy = np.sum(y_noise ** 2)
            
            hnr = 10.0 * np.log10(harm_energy / noise_energy) if noise_energy > 0 else 100.0
            
            # HNR이 8.0dB 이하면 기계 합성 비율 높음
            ai_prob = 0.95 if hnr < 6.0 else (0.75 if hnr < 8.0 else 0.1)
            
            return {
                "synthetic_voice_probability": ai_prob,
                "hnr_decibels": round(float(hnr), 2),
                "mfcc_vectors": mfcc_mean.tolist()[:5],
                "module_available": True
            }
        except (ImportError, Exception):
            # 라이브러리 부재 시 폴백 기본값 반환 — 분석 미수행을 명시해 사용자 피드백 보장
            return {
                "synthetic_voice_probability": 0.2,
                "hnr_decibels": 15.0,
                "mfcc_vectors": [0.0, 0.0, 0.0, 0.0, 0.0],
                "module_available": False
            }

    def detect_voice_phishing(self, transcript: str) -> Dict[str, Any]:
        """
        변환된 대화 텍스트의 키워드 분석을 수행합니다.
        """
        danger_keywords = ["송금", "이체", "검찰", "계좌", "금융감독원", "대출", "카드 연체", "수사"]
        matched = [word for word in danger_keywords if word in transcript]
        
        phishing_prob = len(matched) / len(danger_keywords)
        
        return {
            "phishing_probability": round(phishing_prob, 4),
            "matched_keywords": matched
        }
