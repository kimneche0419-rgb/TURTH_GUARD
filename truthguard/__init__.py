from truthguard.base import AnalysisResult

__version__ = "0.1.0"

def detect_text(content: str, **kwargs) -> AnalysisResult:
    """
    텍스트 데이터의 신뢰성을 스캔하고 분석 결과를 반환합니다.
    """
    from truthguard.text.analyzer import TextAnalyzer
    analyzer = TextAnalyzer()
    return analyzer.analyze(content, **kwargs)

def detect_image(image_path: str, **kwargs) -> AnalysisResult:
    """
    이미지 파일의 변조 여부 및 AI 생성을 판별하고 분석 결과를 반환합니다.
    """
    from truthguard.image.analyzer import ImageAnalyzer
    analyzer = ImageAnalyzer()
    return analyzer.analyze(image_path, **kwargs)

def detect_video(video_path: str, **kwargs) -> AnalysisResult:
    """
    비디오 파일의 변조 여부를 프레임 단위로 판별하고 분석 결과를 반환합니다.
    """
    from truthguard.video.analyzer import VideoAnalyzer
    analyzer = VideoAnalyzer()
    return analyzer.analyze(video_path, **kwargs)

def detect_audio(audio_path: str, **kwargs) -> AnalysisResult:
    """
    오디오 파일의 보이스 합성 여부를 판별하고 분석 결과를 반환합니다.
    """
    from truthguard.audio.analyzer import AudioAnalyzer
    analyzer = AudioAnalyzer()
    return analyzer.analyze(audio_path, **kwargs)
