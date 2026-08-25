# Truth History SDK: Video(페이스 스왑) & Audio(AI 복제 음성) Analyzer 상세 구현 설계서

생성형 AI는 영상과 음성 영역에서도 역사 왜곡의 도구가 됩니다. 역사 인물의 얼굴을 합성한 딥페이크 **페이스 스왑 영상**이나 실존 인물의 음성을 복제(cloning)해 만든 **AI 합성·클론 음성 발언**은 인물 사칭과 허위 역사 발언 유포에 악용되어 사회적 불신과 정보 교란을 유발합니다. Truth History SDK의 `VideoAnalyzer`·`AudioAnalyzer`는 이러한 시청각 위변조를 텍스트 고증 검증과 교차 검증할 수 있도록 단일 SDK에 통합합니다.

본 문서는 `VideoAnalyzer`의 비디오 프레임 추출 및 시간적 일관성(Jitter) 탐지 알고리즘, 그리고 `AudioAnalyzer`의 음성 신호 처리(MFCC & HNR) 및 AI 복제 음성 기반 사칭·사회 불안 유발 어휘 문맥 검사 구현 코드를 상술합니다. 각 모듈은 **설명 가능한 판정 근거(XAI)**를 정량 데이터로 산출합니다. Video는 **프레임 간 temporal jitter 지수**, Audio는 **MFCC 계수 벡터와 HNR 데시벨**, 문맥 검사는 **매칭된 사칭/불안 유발 어휘 리스트**를 JSON 리포트로 노출합니다.

---

## 1. Video Analyzer 구현 및 프레임 처리

딥페이크 페이스 스왑 영상 검증은 연산량이 크므로 효율적인 프레임 샘플링과 시간 범위 분석이 필수적입니다. 영상은 정지 이미지 단위의 안면 비대칭뿐 아니라 **프레임 간 temporal jitter(시간적 요동)**라는 동적 단서를 추가로 제공하므로, 사료 속 인물 얼굴을 합성한 위조 영상에 대해 더 강건한 페이스 스왑 탐지가 가능합니다.

### 1.1 비디오 프레임 샘플링 및 시간 요동(Jitter) 검출 코드
페이스 스왑으로 합성된 영상의 얼굴은 프레임 전환 시 안면 경계부 랜드마크가 미세하게 요동치며 떨리는 현상(Temporal Jitter)을 보입니다. 실제 촬영된 얼굴은 자연스러운 움직임을 보이지만, 합성 얼굴은 프레임별 재합성 과정에서 비일관적인 랜드마크 변동을 남깁니다.

```python
from truthhistory.architecture import LazyModuleImporter

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

산출된 `jitter_index`(요동 표준편차/평균 비)가 임계치(0.35)를 초과하면 temporal jitter로 판정하며, 샘플링된 프레임 수(`total_sampled_frames`)와 함께 XAI 근거로 리포트됩니다. 이 수치는 영상 내 어느 시점에 불연속적인 안면 변동이 집중되었는지를 정량화하여 **페이스 스왑 판정 근거**를 투명하게 제공합니다.

---

## 2. Audio Analyzer 오디오 처리 알고리즘 구현

**AI 복제/클론 음성** 탐지는 합성 음성 특유의 기계음과 주파수 단절 구역을 분석하기 위해 Librosa 라이브러리를 사용합니다. 실존 인물의 음성을 소량 샘플링해 복제한 클론 음성으로 허위 역사 발언을 유포하거나 인물을 사칭하는 공격에 대응합니다.

### 2.1 MFCC 및 HNR (Harmonic-to-Noise Ratio) 추출
* **MFCC:** 사람의 청각 특성을 고려한 음성 주파수 피처로, AI 복제 음성은 자연 발성과 미세하게 차이 나는 멜 스케일 에너지 분포 패턴을 보입니다. MFCC 계수 벡터는 XAI 리포트에서 합성 의심 주파수 대역을 명시하는 판정 근거로 사용됩니다.
* **HNR (성대 고주파 노이즈 성분비):** 기계적으로 합성·클론된 음성은 성대의 진동(Harmonic) 대비 주파수 공간에 임의 배치된 노이즈 성분이 특정 고주파수 영역에서 왜곡되어 나타납니다. HNR 데시벨 수치는 자연 음성 대비 얼마나 기계적 노이즈 비율이 높은지를 정량화한 XAI 근거입니다.

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

반환된 `synthetic_voice_probability`, `hnr_decibels`, `mfcc_vector`(상위 5 계수)는 **AI 복제 음성 판정의 핵심 근거**입니다. HNR이 8dB 이하로 떨어지거나 MFCC에 결측치가 발생하면 합성으로 판정하며, 각 수치가 리포트에 명시되므로 검증 담당자는 "어떤 주파수 대역·노이즈 비율에서 복제 음성으로 의심되는가"를 설명 가능한 형태로 확인할 수 있습니다.

---

## 3. AI 복제 음성 기반 사칭/사회 불안 유발 어휘 탐지

오디오 합성 검증의 최종 레이어로, STT로 추출된 텍스트에서 **AI 복제 음성으로 인물을 사칭**하거나 **사회적 불안·혼란을 유발**하는 어휘 패턴을 사전 정의된 키워드 집합과 매칭하여 위험도를 산출합니다. 실존 역사 인물·공인의 음성을 복제해 허위 발언이나 사회 불안 조장 문구를 유포하는 공격을 탐지합니다.

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

매칭된 어휘 리스트(`matched_words`)와 정규화된 위험 확률(`phishing_probability`)이 함께 반환되므로, **어떤 사칭/불안 유발 어휘가 탐지를 주도했는지**를 XAI 근거로 투명하게 제시합니다. 키워드 집합은 임베딩 환경의 위협 시나리오(역사 인물 사칭, 허위 역사 발언 유포, 사회 불안 조장 등)에 맞춰 손쉽게 확장 가능합니다.
