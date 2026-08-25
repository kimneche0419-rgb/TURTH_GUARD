# 📡 스트리밍 실시간 청크 분석 모듈 구현 상세

> 모듈: `truthhistory/video/streaming.py` · CLI: `th stream` · API: `POST /api/v1/scan/stream` · 테스트: `tests/test_streaming.py`

## 1. 목적

기존 `VideoAnalyzer`는 전체 영상을 한 번에 분석합니다. 라이브 방송(RTSP/HTTP)·장문 영상·웹캠처럼 **길이를 알 수 없거나 즉시 판정이 필요한 소스**에는 맞지 않으므로, `StreamingVideoAnalyzer`는 **시간 청크(기본 2초) 단위 증분 분석**을 제공합니다.

## 2. 아키텍처

```
소스(파일/RTSP/HTTP/웹캠) → cv2.VideoCapture
    → 프레임 스트림 (sample_fps 샘플링)
    → 청크 버퍼 (chunk_seconds 충족 시 방출)
    → 청크별 분석: temporal jitter + 안면 비대칭 (VideoAnalyzer 로직 재사용)
    → yield {chunk_index, time_start, time_end, frames, result}
```

- **제너레이터(`stream_analyze`)**: 청크가 완성될 때마다 즉시 결과 방출 — 대기 시간 = 청크 길이.
- **조기 종료(early-stop)**: 청크가 `CRITICAL`이면 반복 중단(라이브 대응 지연 최소화). `--no-early-stop`으로 비활성화.
- **종합(`analyze`/`summarize`)**: 신뢰도는 **최악 청크 보수 기준**, AI 확률은 청크 최댓값, `analysis_details.chunks`에 전체 타임라인 포함.
- **캡처 소유권**: 분석기가 개방한 캡처는 종료 시 `release()`, 호출자가 주입한 캡처는 호출자 소유.

## 3. 사용 예

### CLI
```bash
th stream lecture_deepfake.mp4                 # 파일 청크 분석
th stream rtsp://cam.example.com/media.sdp     # 라이브 RTSP
th stream 0                                    # 웹캠 0번
th stream video.mp4 --chunk-seconds 5 -f json  # JSON 리포트
```

### SDK
```python
from truthhistory import detect_video_stream
result = detect_video_stream("rtsp://example/live", max_chunks=30)
result.analysis_details["chunks"]  # 청크 타임라인
```

### API
`POST /api/v1/scan/stream` — multipart 비디오 업로드(`chunk_seconds`, `max_chunks` 폼 옵션) → XAI 리포트 + `stream.chunks` 타임라인 반환.

## 4. 테스트

- 청크 타임라인 순서·커버리지, 청크별 결과 규격
- `max_chunks` 제한, 캡처 소유권/해제
- 종합 판정의 보수(최액) 신뢰도·최대 AI 확률
- 실제 mp4 파일 통합 분석(OpenCV 런타임), 열 수 없는 소스 `ValueError`
