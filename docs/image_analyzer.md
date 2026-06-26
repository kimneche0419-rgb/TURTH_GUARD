# TruthGuard SDK: Image Analyzer 상세 구현 설계서

본 문서는 `ImageAnalyzer`에 내장되는 핵심 이미지 처리 알고리즘인 ELA(Error Level Analysis), FFT(Fast Fourier Transform) 기반 아티팩트 감지, 그리고 안면 비대칭 탐지의 파이썬 실무 구현 코드를 다룹니다.

---

## 1. ELA (Error Level Analysis) 상세 구현

합성되거나 가공된 구역은 재압축될 때 원래 주변 픽셀들과는 다른 에러 오차율을 갖습니다. 

### 1.1 ELA 동작 알고리즘 및 구현 코드
1. 원본 이미지를 지정한 JPEG 퀄리티(예: 95%)로 임시 압축하여 저장합니다.
2. 원본 이미지와 재압축된 이미지의 픽셀 값 절댓값 편차(Absolute Difference)를 구합니다.
3. 편차 값을 극대화하기 위해 스케일 팩터(Scale Factor)를 적용하여 정규화합니다.
4. 특정 구역의 편차 평균값이 임계값을 넘어가면 변조 의심 구역으로 판정합니다.

```python
import os
from truthguard.architecture import LazyModuleImporter

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

---

## 2. FFT (Fast Fourier Transform) 주파수 분석 구현

생성형 AI 모델(특히 GAN 계열)은 이미지 업샘플링 과정에서 미세한 바둑판(Grid) 노이즈 아티팩트를 격자 형태로 남깁니다.

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

---

## 3. 안면 특징점 비대칭성 탐지 (Deepfake)

얼굴 교체(Face Swap) 모델은 사람의 눈동자에 투영되는 광원의 대칭각 및 안면 좌우 랜드마크 비례를 정확하게 동기화하지 못하는 기술적 한계가 있습니다.

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
