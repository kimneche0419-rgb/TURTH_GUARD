# TruthGuard SDK: 개발자 환경 설정 및 시작 가이드

본 문서는 TruthGuard SDK 오픈소스 기여자와 개발자를 위한 개발 환경 셋업, 의존성 패키지 관리, 테스트 실행 및 PyPI 배포 프로세스를 다룹니다.

---

## 1. 개발 환경 요구사항

* **Python Version:** Python 3.9 이상 (3.10 ~ 3.12 권장)
* **OS:** Windows / macOS / Linux 지원
* **의존성 도구:** `pip` 및 `venv` (또는 현대적인 의존성 관리 도구인 `Poetry`)

---

## 2. 프로젝트 초기 의존성 관리 스펙 (`pyproject.toml`)

TruthGuard SDK는 패키지 빌드 및 배포 표준 규격인 `pyproject.toml`을 사용하여 의존성을 정의합니다. 아래 스펙을 프로젝트 루트에 작성합니다.

```toml
[build-system]
requires = ["poetry-core>=1.0.0"]
build-backend = "poetry.core.masonry.api"

[tool.poetry]
name = "truthguard-sdk"
version = "0.1.0"
description = "AI-generated content and misinformation detection SDK & CLI framework."
authors = ["TruthGuard Contributors <contact@truthguard.org>"]
license = "MIT"
readme = "README.md"
repository = "https://github.com/truthguard/truthguard"
packages = [{include = "truthguard"}]

[tool.poetry.dependencies]
python = "^3.9"
pydantic = "^2.0.0"
requests = "^2.31.0"
rich = "^13.7.0"
click = "^8.1.0"

# 선택적 의존성 (Extras) - 대용량 라이브러리 최소화 목적
transformers = { version = "^4.35.0", optional = true }
torch = { version = "^2.1.0", optional = true }
opencv-python = { version = "^4.8.0", optional = true }
pillow = { version = "^10.0.0", optional = true }
librosa = { version = "^0.10.0", optional = true }

[tool.poetry.extras]
text = ["transformers", "torch"]
image = ["opencv-python", "pillow", "torch"]
video = ["opencv-python", "pillow", "torch"]
audio = ["librosa", "torch"]
all = ["transformers", "torch", "opencv-python", "pillow", "librosa"]

[tool.poetry.scripts]
truthguard = "truthguard.cli.main:main"

[tool.poetry.group.dev.dependencies]
pytest = "^7.4.0"
black = "^23.7.0"
flake8 = "^6.1.0"
mypy = "^1.5.0"
```

---

## 3. 개발 가상환경 구축 단계 (CLI Commands)

### 3.1 venv와 pip를 사용하는 경우
```bash
# 1. 저장소 클론 및 이동
git clone https://github.com/truthguard/truthguard.git
cd truthguard

# 2. 가상환경 생성 및 활성화 (Windows 기준)
python -m venv .venv
.venv\Scripts\activate

# 3. 개발 및 테스트 의존성 패키지 설치 (기본 모듈)
pip install -e .[all]
pip install -r requirements-dev.txt
```

### 3.2 Poetry를 사용하는 경우 (권장)
```bash
# 1. 의존성 설치 및 가상환경 구성 (모든 Extra 활성화)
poetry install --all-extras

# 2. 가상환경 셸 진입
poetry shell
```

---

## 4. 파이썬 패키지 내부 패키징 구조
Python 모듈로서 정상 임포트가 가능하게 하려면, 모든 디렉터리에 `__init__.py`가 알맞게 배치되어야 합니다.

```plaintext
truthguard/
 ├── __init__.py             # 버전 및 주요 detect_xxx 함수 노출
 ├── base.py                 # BaseAnalyzer 및 AnalysisResult 정의
 ├── text/
 │    ├── __init__.py
 │    └── analyzer.py
 ├── image/
 │    ├── __init__.py
 │    └── analyzer.py
 ├── video/
 │    ├── __init__.py
 │    └── analyzer.py
 ├── audio/
 │    ├── __init__.py
 │    └── analyzer.py
 ├── explain/
 │    ├── __init__.py
 │    └── engine.py
 └── cli/
      ├── __init__.py
      └── main.py            # click/argparse CLI 엔트리 포인트
```

`truthguard/__init__.py` 예시:
```python
from truthguard.base import AnalysisResult
from truthguard.text.analyzer import TextAnalyzer
from truthguard.image.analyzer import ImageAnalyzer

__version__ = "0.1.0"

def detect_text(content: str, **kwargs) -> AnalysisResult:
    analyzer = TextAnalyzer()
    return analyzer.analyze(content, **kwargs)

def detect_image(image_path: str, **kwargs) -> AnalysisResult:
    analyzer = ImageAnalyzer()
    return analyzer.analyze(image_path, **kwargs)
```

---

## 5. 정적 테스트 및 포맷팅 수행

품질 높은 오픈소스 소스코드를 위해 PR 제출 전 반드시 다음 포맷팅 체크를 통과해야 합니다.

```bash
# 코드 포맷 자동 교정
black truthguard/ tests/

# 정적 분석 및 네이밍 스타일 검사
flake8 truthguard/

# 타입 힌트 오류 체크
mypy truthguard/
```

---

## 6. 테스트 수행 가이드 (Testing)

모든 분석기의 기본 구현은 `tests/` 폴더 내에 단위 테스트를 정의하여 입증합니다.

```bash
# 모든 단위 테스트 검증
pytest tests/ -v
```

---

## 7. PyPI 배포 가이드 (Publishing)

새로운 버전을 릴리즈할 때는 아래 명령어를 사용하여 패키지를 빌드하고 PyPI 저장소에 배포합니다.

```bash
# 1. 소스 배포(sdist) 및 바이너리 휠(wheel) 빌드
poetry build

# 2. PyPI 테스트 환경에 먼저 배포 검증
poetry publish -r testpypi

# 3. 본 환경에 배포
poetry publish
```
