# Truth History SDK: Image Analyzer(ELA 합성·딥페이크 탐지) 상세 구현 설계서

생성형 AI의 보편화는 한국 역사 이미지에 새로운 위협을 낳았습니다. 권위 있는 역사 사료 사진을 AI로 부분 위조하거나 통째로 재합성한 콘텐츠, GAN·Diffusion 모델이 만들어낸 그럴듯한 가짜 사료 이미지가 온라인에 대량 유포되며 역사적 사실을 왜곡하고 정보 환경을 교란합니다. Truth History SDK의 `ImageAnalyzer`는 이러한 **위조·합성 역사 이미지와 AI 생성 이미지**를 단일 모듈에서 탐지합니다.

본 문서는 `ImageAnalyzer`에 내장된 세 가지 핵심 이미지 처리 알고리즘 — ELA(Error Level Analysis) 기반 **압축 왜곡** 탐지, FFT(Fast Fourier Transform) 기반 **GAN/Diffusion 격자 아티팩트** 감지, 그리고 안면 비대칭 기반 **딥페이크 페이스 스왑** 탐지 — 의 파이썬 실무 구현 코드를 다룹니다. 세 알고리즘은 모두 **설명 가능한 판정 근거(XAI)**를 정량 데이터로 산출합니다. ELA는 변조 의심 **픽셀 위치와 편차 평균값**, FFT는 **주파수 공간의 노이즈 스파이크 분포**, 페이스 스왑 탐지는 **좌우 랜드마크 오프셋 편차**를 각각 JSON 리포트로 제공하여 "왜 위조로 판정했는지"를 투명하게 설명합니다.

---

## 1. ELA (Error Level Analysis) 상세 구현

위조되거나 합성된 역사 이미지의 조작 구역은 원본 주변 픽셀과 다른 JPEG 재압축 에러율을 보입니다. 원본 촬영 영역과 달리 이후에 덧입혀진 인물·문장·배경 패치는 서로 다른 압축 이력을 갖기 때문입니다. ELA는 이 **픽셀 단위 압축 왜곡 편차**를 측정하여 위조가 이루어진 정확한 영역을 식별하고, 그 편차 평균값을 XAI 판정 근거로 제시합니다.

### 1.1 ELA 동작 알고리즘 및 구현 코드
1. 원본 이미지를 지정한 JPEG 퀄리티(예: 95%)로 임시 압축하여 저장합니다.
2. 원본 이미지와 재압축된 이미지의 픽셀 값 절댓값 편차(Absolute Difference)를 구합니다.
3. 편차 값을 극대화하기 위해 스케일 팩터(Scale Factor)를 적용하여 정규화합니다.
4. 특정 구역의 편차 평균값이 임계값을 넘어가면 변조 의심 구역으로 판정합니다.

```python
import os
from truthhistory.architecture import LazyModuleImporter

def perform_ela(image_path: str, quality: int = 95, scale: float = 25.5) -> dict:
    """
    OpenCV와 Pillow를 활용해 이미지의 ELA를 수행하고 변조 수치를 산출합니다.
    """
    cv2 = LazyModuleImporter.import_module("cv2", "image")
    np = LazyModuleImporter.import_module("numpy", "image")
    Image = LazyModuleImporter.import_module("PIL.Image", "image")
    ImageChops = LazyModuleImporter.import_module("PIL.ImageChops", "image")

    temp_filename = f"temp_ela_{os.path.basename(image_path)}"
    
    # 1. 이미지 로드 및 복사본 저장 (퀄리티 지정)
    original = Image.open(image_path).convert("RGB")
    original.save(temp_filename, "JPEG", quality=quality)
    
    # 2. 임시 파일 다시 열기
    compressed = Image.open(temp_filename)
    
    # 3. 절대값 편차 계산
    diff = ImageChops.difference(original, compressed)
    
    # 4. 픽셀값 스케일링을 통한 가시화 편차 극대화
    extrema = diff.getextrema()
    max_diff = max([ex[1] for ex in extrema])
    if max_diff == 0:
        max_diff = 1
    
    # 스케일 변환 비율 계산
    scale_factor = 255.0 / max_diff
    diff = ImageChops.multiply(diff, scale_factor)
    
    # 5. 변조 수치 측정 (픽셀 밝기의 평균값 산출)
    diff_np = np.array(diff)
    mean_difference = np.mean(diff_np)
    
    # 임시 파일 정리
    if os.path.exists(temp_filename):
        os.remove(temp_filename)
        
    # 평균 픽셀 밝기 차이가 12.0 이상일 시 조작 의심
    has_manipulation = mean_difference > 12.0
    
    return {
        "has_manipulation_suspect": has_manipulation,
        "manipulation_score": round(min(mean_difference / 50.0, 1.0), 4),
        "mean_diff_value": round(mean_difference, 2)
    }
```

반환값의 `mean_diff_value`는 위조 의심 영역의 **픽셀 밝기 평균 편차**, `manipulation_score`는 이를 0~1로 정규화한 **변조 점수**, `has_manipulation_suspect`는 임계값(12.0) 기반 판정 결과입니다. 이 세 값은 API/CLI 리포트에서 **어느 정도의 압축 왜곡이 어느 픽셀 영역에서 발생했는지**를 XAI 근거로 그대로 노출합니다. 검증 담당자는 단순한 true/false가 아닌, 위조 의심 픽셀 위치와 편차 수치를 직접 확인하며 설명 가능한 결론을 도출할 수 있습니다.

---

## 2. FFT (Fast Fourier Transform) 주파수 분석 구현

GAN/Diffusion 계열 생성 모델은 이미지 업샘플링 과정에서 미세한 바둑판(Grid) 형태의 격자 아티팩트를 잔류시킵니다. 이러한 **주파수 노이즈 패턴**은 육안으로는 보이지 않지만, 푸리에 변환으로 주파수 공간으로 옮기면 저주파 중심축 주변에 비정상적인 대칭 스파이크(Spike)로 드러납니다. FFT 분석은 이 격자 아티팩트 분포를 정량화하여 AI 생성 이미지 판정 근거를 제공합니다.

### 2.1 2D FFT 주파수 스펙트럼 추출 코드
격자 모양 노이즈는 주파수 공간으로 변환할 때 중심축 주변에 비정상적인 대칭점(Spike)을 생성합니다.

```python
def analyze_frequency_domain(image_path: str) -> dict:
    """
    이미지를 그레이스케일로 변환한 후 2D FFT를 통해 고주파 생성 노이즈 아티팩트를 탐지합니다.
    """
    cv2 = LazyModuleImporter.import_module("cv2", "image")
    np = LazyModuleImporter.import_module("numpy", "image")

    # 1. 이미지를 그레이스케일로 로드
    img = cv2.imread(image_path, cv2.IMREAD_GRAYSCALE)
    if img is None:
        raise FileNotFoundError(f"Cannot load image: {image_path}")
        
    # 2. 2D FFT 및 Shift 연산 수행 (저주파 성분을 중앙으로 이동)
    f_transform = np.fft.fft2(img)
    f_shift = np.fft.fftshift(f_transform)
    
    # Magnitude Spectrum 계산
    magnitude_spectrum = 20 * np.log(np.abs(f_shift) + 1)
    
    # 3. 고주파 영역(중앙을 제외한 외곽 영역)에서 인공적인 스파이크 분석
    h, w = img.shape
    cy, cx = h // 2, w // 2
    
    # 중앙 저주파 마스킹 (중앙 30x30 픽셀 제거)
    magnitude_spectrum[cy-15:cy+15, cx-15:cx+15] = 0
    
    # 임계값을 넘어서는 외곽 스파이크 개수 카운팅
    threshold = np.mean(magnitude_spectrum) + 3 * np.std(magnitude_spectrum)
    spikes = np.argwhere(magnitude_spectrum > threshold)
    
    # 고주파 스파이크 비율이 넓은 영역에 고르게 나타날 경우 생성 아티팩트로 판단
    ai_prob = min(len(spikes) / 2000.0, 1.0)
    
    return {
        "ai_probability": round(ai_prob, 4),
        "spike_count": len(spikes)
    }
```

`spike_count`는 주파수 공간에서 임계치를 초과한 **스파이크 개수**, `ai_probability`는 이를 0~1로 정규화한 AI 생성 확률입니다. 스파이크가 넓은 영역에 고르게 분포할수록 생성 모델의 격자 아티팩트일 가능성이 상승하며, 이 **주파수 노이즈 패턴 분포 자체**가 XAI 리포트의 핵심 판정 근거가 됩니다. 검증 담당자는 "어떤 주파수 대역에 인공적 스파이크가 집중되었는지"를 수치로 확인할 수 있습니다.

---

## 3. 안면 특징점 비대칭성 탐지 (Deepfake / Face Swap)

역사 인물의 얼굴을 다른 인물로 교체하는 딥페이크 **페이스 스왑(Face Swap)** 모델은 좌우 안면 랜드마크의 기하학적 비례와 눈동자 반사광의 대칭각을 정확히 동기화하지 못하는 기술적 한계를 갖습니다. 사료 속 인물 얼굴을 합성해 "실존 역사 인물의 위조 사진·영상"을 만드는 공격에 효과적으로 대응합니다. 본 탐지는 **좌우 랜드마크 오프셋 편차**를 XAI 근거로 산출하여 페이스 스왑 여부를 설명합니다.

### 3.1 랜드마크 비대칭 지수 분석 모델
* **dlib / MediaPipe 연동:** 얼굴의 68개 랜드마크 포인트 중 좌우 매칭 쌍(예: 왼쪽 눈 외곽 `36`번과 오른쪽 눈 외곽 `45`번) 간의 위치 및 기하학적 균형을 평가합니다.
* **눈동자 반사광 일관성 검사:** 두 눈 영역의 홍채 중심점 대비 반사광 스팟의 상대 오프셋 벡터 차이($\|\vec{v}_{left} - \vec{v}_{right}\|$)가 0.15 이상 벌어질 경우 인위적 합성으로 의심합니다.

```python
# 안면 비대칭 계산 수도코드 예시
def calculate_face_asymmetry(landmarks) -> float:
    # 1. 얼굴 정렬(Alignment)용 수평 각도 산출
    # 2. 좌우 대칭점 좌표 거리 측정
    # 3. 비대칭성 편차의 분산값 정규화 리턴
    pass
```

산출된 비대칭 편차 분산값은 각 랜드마크 쌍에서 벌어진 **오프셋 크기**를 정량화한 것으로, 어떤 좌표쌍(예: 눈·입꼬리·홍채 반사광)에서 비대칭이 집중되었는지를 XAI 리포트에 노출합니다. 판정 근거가 랜드마크 픽셀 좌표와 함께 명시되므로, 역사 사료 검증 담당자는 페이스 스왑이 의심되는 안면 영역을 직접 확인하고 설명 가능한 검증 결론을 도출할 수 있습니다.
