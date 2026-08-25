from typing import Any, Optional

from truthhistory.base import AnalysisResult

__version__ = "0.1.0"

def detect_text(content: str, **kwargs) -> AnalysisResult:
    """
    텍스트 데이터의 신뢰성을 스캔하고 분석 결과를 반환합니다.
    """
    from truthhistory.text.analyzer import TextAnalyzer
    analyzer = TextAnalyzer()
    return analyzer.analyze(content, **kwargs)

def detect_image(image_path: str, **kwargs) -> AnalysisResult:
    """
    이미지 파일의 변조 여부 및 AI 생성을 판별하고 분석 결과를 반환합니다.
    """
    from truthhistory.image.analyzer import ImageAnalyzer
    analyzer = ImageAnalyzer()
    return analyzer.analyze(image_path, **kwargs)

def detect_video(video_path: str, **kwargs) -> AnalysisResult:
    """
    비디오 파일의 변조 여부를 프레임 단위로 판별하고 분석 결과를 반환합니다.
    """
    from truthhistory.video.analyzer import VideoAnalyzer
    analyzer = VideoAnalyzer()
    return analyzer.analyze(video_path, **kwargs)

def detect_video_stream(source: Any, max_chunks: Optional[int] = None, **kwargs) -> AnalysisResult:
    """
    라이브 스트리밍/장문 영상을 시간 청크 단위로 실시간 분석하고 종합 결과를 반환합니다.
    source: 비디오 파일 경로, RTSP/HTTP 스트림 URL 또는 웹캠 인덱스(int)
    """
    from truthhistory.video.streaming import StreamingVideoAnalyzer
    analyzer = StreamingVideoAnalyzer()
    return analyzer.analyze(source, max_chunks=max_chunks, **kwargs)

def detect_audio(audio_path: str, **kwargs) -> AnalysisResult:
    """
    오디오 파일의 보이스 합성 여부를 판별하고 분석 결과를 반환합니다.
    """
    from truthhistory.audio.analyzer import AudioAnalyzer
    analyzer = AudioAnalyzer()
    return analyzer.analyze(audio_path, **kwargs)
