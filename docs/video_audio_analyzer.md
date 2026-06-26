# TruthGuard SDK: Video & Audio Analyzer 상세 구현 설계서

본 문서는 `VideoAnalyzer`의 비디오 프레임 추출 및 시간적 일관성(Jitter) 탐지 알고리즘, 그리고 `AudioAnalyzer`의 음성 신호 처리(MFCC & HNR) 구현 코드를 상술합니다.

---

## 1. Video Analyzer 구현 및 프레임 처리

동영상 파일 검증은 연산량이 크므로 효율적인 프레임 샘플링과 시간 범위 분석이 필수적입니다.

### 1.1 비디오 프레임 샘플링 및 시간 요동(Jitter) 검출 코드
비디오 내 합성된 인물의 얼굴은 프레임 전환 시 안면 경계부 랜드마크가 미세하게 요동치며 떨리는 현상(Temporal Jitter)이 발생합니다.

```python
from truthguard.architecture import LazyModuleImporter

def analyze_video_temporal_jitter(video_path: str, target_fps: int = 2) -> dict:
    """
    OpenCV를 사용해 비디오 프레임을 초당 target_fps 비율로 추출하고,
    인접 프레임 간 안면 랜드마크 변화의 표준편차를 구해 Jitter 지수를 도출합니다.
    """
    cv2 = LazyModuleImporter.import_module("cv2", "video")
    np = LazyModuleImporter.import_module("numpy", "video")

    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        raise FileNotFoundError(f"Cannot open video: {video_path}")

    fps = cap.get(cv2.CAP_PROP_FPS)
    frame_interval = max(int(fps / target_fps), 1)

    frame_count = 0
    sampled_frames = []
    
    # 1. 비디오 프레임 샘플링
    while True:
        ret, frame = cap.read()
        if not ret:
            break
        if frame_count % frame_interval == 0:
            sampled_frames.append(frame)
        frame_count += 1
    
    cap.release()

    # 2. 인접 프레임 안면 변화량 측정 시뮬레이션
    # (실제 구현에서는 dlib/MediaPipe로 검출된 랜드마크 좌표 리스트를 이용)
    # 여기서는 샘플링 프레임의 히스토그램 밝기 변화량을 모사 연산함
    diffs = []
    prev_hist = None
    
    for frame in sampled_frames:
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        hist = cv2.calcHist([gray], [0], None, [256], [0, 256])
        cv2.normalize(hist, hist, 0, 1, cv2.NORM_MINMAX)
        
        if prev_hist is not None:
            # 바타차랴(Bhattacharyya) 거리를 이용한 두 프레임 간 유사성 검증
            distance = cv2.compareHist(prev_hist, hist, cv2.HISTCMP_BHATTACHARYYA)
            diffs.append(distance)
        prev_hist = hist

    if not diffs:
        return {"has_temporal_jitter": False, "jitter_index": 0.0}

    # 연속성 변화량의 표준편차가 임계치를 초과할 경우 떨림으로 감지
    std_diff = float(np.std(diffs))
    mean_diff = float(np.mean(diffs))
    
    jitter_index = std_diff / mean_diff if mean_diff > 0 else 0
    has_jitter = jitter_index > 0.35  # Jitter 임계치 설정

    return {
        "has_temporal_jitter": has_jitter,
        "jitter_index": round(jitter_index, 4),
        "total_sampled_frames": len(sampled_frames)
    }
```

---

## 2. Audio Analyzer 오디오 처리 알고리즘 구현

합성 음성(AI Voice) 탐지는 발성에 포함되는 특유의 기계음과 주파수 단절 구역을 분석하기 위해 Librosa 라이브러리를 사용합니다.

### 2.1 MFCC 및 HNR (Harmonic-to-Noise Ratio) 추출
* **MFCC:** 사람의 청각 특성을 고려한 음성 주파수 피처로, 인공 합성 시 미세하게 차이 나는 멜 스케일 에너지 분포 패턴을 잡아냅니다.
* **HNR (성대 고주파 노이즈 성분비):** 기계적으로 합성된 소리는 성대의 진동(Harmonic) 대비 주파수 공간에 임의 배치된 노이즈 성분이 특정 고주파수 영역에서 왜곡되어 나타납니다.

```python
def extract_audio_spectral_features(audio_path: str) -> dict:
    """
    librosa를 활용하여 오디오 신호의 MFCC 특징점과 HNR 비율을 추출합니다.
    """
    librosa = LazyModuleImporter.import_module("librosa", "audio")
    np = LazyModuleImporter.import_module("numpy", "audio")

    # 1. 오디오 신호 로드
    y, sr = librosa.load(audio_path, sr=16000)

    # 2. MFCC 추출 (20개 계수 추출)
    mfccs = librosa.feature.mfcc(y=y, sr=sr, n_mfcc=20)
    mfcc_mean = np.mean(mfccs, axis=1)

    # 3. Harmonic-to-Noise Ratio (HNR) 산출
    # librosa의 harmonic, percussive 분리 기능을 사용하여 성대 고조파 대 노이즈 에너지 비율 산출
    y_harmonic, y_noise = librosa.effects.hpss(y)
    
    harmonic_energy = np.sum(y_harmonic ** 2)
    noise_energy = np.sum(y_noise ** 2)
    
    if noise_energy == 0:
        hnr = 100.0  # 노이즈가 없는 이상적 경우
    else:
        hnr = 10 * np.log10(harmonic_energy / noise_energy)

    # 합성 오디오일수록 HNR 지수가 부자연스럽게 비정상 범위(예: 8dB 이하)로 나타남
    is_synthetic = hnr < 8.0 or np.any(np.isnan(mfcc_mean))
    synthetic_prob = 0.95 if hnr < 6.0 else (0.75 if hnr < 8.0 else 0.1)

    return {
        "synthetic_voice_probability": synthetic_prob,
        "hnr_decibels": round(float(hnr), 2),
        "mfcc_vector": mfcc_mean.tolist()[:5]  # 시각화용 상위 5개 계수
    }
```

---

## 3. 보이스피싱 텍스트 문맥 검사

오디오 합성 검증의 최종 레이어로, 추출된 STT 텍스트 데이터의 긴급도/위협도 등 패턴을 사전에 정의된 특정 키워드 집합과 매핑하여 피싱 확률을 구합니다.

```python
def detect_phishing_keywords(transcript: str) -> dict:
    """
    텍스트 내 수사기관 사칭, 금융 결제 긴급 유도 어휘를 검색하여 피싱 신뢰도를 반환합니다.
    """
    danger_keywords = ["송금", "검찰", "계좌 안전", "대출", "카드 연체", "수사"]
    matched = [word for word in danger_keywords if word in transcript]
    
    phishing_prob = len(matched) / len(danger_keywords)
    
    return {
        "phishing_probability": round(phishing_prob, 4),
        "matched_words": matched
    }
```
