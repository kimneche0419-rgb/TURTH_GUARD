# -*- coding: utf-8 -*-
from typing import Any, Dict, List

from truthguard.base import BaseAnalyzer, AnalysisResult, LazyModuleImporter

class AudioAnalyzer(BaseAnalyzer):
    """
    합성 음성 및 보이스피싱 범죄 의심 오디오를 판별하는 분석기 클래스
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

        # 2. 보이스피싱 텍스트 문맥 분석 (스텁 데이터 또는 텍스트 기반)
        transcript = kwargs.get("transcript", "더미 텍스트")
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
            reasons.append("대화 문맥에서 수사기관 사칭 또는 송금 강요 위험 어휘 패턴 검출")

        return AnalysisResult(
            is_manipulated=(credibility_score < 0.6) or (ai_prob > 0.8),
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
                "mfcc_vectors": mfcc_mean.tolist()[:5]
            }
        except (ImportError, Exception):
            # 라이브러리 부재 시 기본 모킹값 반환
            return {
                "synthetic_voice_probability": 0.2,
                "hnr_decibels": 15.0,
                "mfcc_vectors": [0.0, 0.0, 0.0, 0.0, 0.0]
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
