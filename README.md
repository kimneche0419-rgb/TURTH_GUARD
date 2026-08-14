# Truth History SDK: 생성형 AI 한국사 왜곡·멀티미디어 위변조 통합 탐지 오픈소스 프레임워크

[![프로젝트 파이프라인 및 분석 보기](https://img.shields.io/badge/%F0%9F%93%8A%20%ED%94%84%EB%A1%9C%EC%A0%9D%ED%8A%B8%20%ED%8C%8C%EC%9D%B4%ED%94%84%EB%9D%BC%EC%9D%B8%20%EB%B0%8F%20%EB%B6%84%EC%84%9D%20%EB%B3%B4%EA%B8%B0-0052FF?style=for-the-badge&logo=markdown&logoColor=white)](./PROJECT_PIPELINE.md) [![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg?style=for-the-badge)](./LICENSE)

> **Truth History SDK**는 생성형 AI로 인해 급증하는 **한국 역사 할루시네이션(그럴듯하지만 거짓인 역사 정보 대량 생성)**과 **멀티미디어 위변조(역사 사진 합성, 딥페이크 페이스 스왑, AI 복제 음성)** 리스크에 대응하기 위해, 텍스트·시청각 교차 검증 모델을 **단일 SDK**로 통합한 오픈소스 프레임워크입니다. 누구나 자사 인프라에 역사 콘텐츠 신뢰성을 확보하고 오염된 거짓 정보의 확산을 차단할 수 있습니다. 본 문서는 시스템 아키텍처, 상세 기능 사양, 코드 레벨의 API 활용 예시를 포함한 프로젝트 명세서입니다.

---

## 1. 프로젝트 개요

### 1.1 프로젝트 소개
생성형 AI(Generative AI)의 대중화로 짧은 시간 안에 정교한 텍스트·이미지·영상·음성이 대량으로 자동 생성되는 시대가 되었습니다. 이와 동시에 (a) 한국 역사를 왜곡하는 **할루시네이션** — 문장은 매끄럽고 출처까지 그럴듯하게 꾸며냈으나 사료와 일치하지 않는 거짓 역사 정보 — 이 LLM을 통해 대량 생산·유포되고 있으며, (b) 역사적 사진의 **합성·위조**, 인물의 **딥페이크 페이스 스왑**, 사칭 인물의 **AI 복제 음성** 등 **멀티미디어 위변조**가 역사적 사실관계를 교란하고 있습니다.

**Truth History SDK**는 일반 사용자를 위한 단일 서비스가 아닙니다. 뉴스 플랫폼, SNS, 교육 시스템, 공공기관 등의 개발자가 자사 인프라와 서비스에 **한국 역사 콘텐츠 신뢰성 검증 레이어**를 손쉽게 임베딩할 수 있도록 지원하는 **오픈소스 SDK 및 CLI 도구**입니다. 텍스트 고증 검증과 이미지·영상·오디오 교차 검증을 하나의 규격으로 묶어, 디지털 역사 주권을 스스로 방어할 수 있는 가드레일을 제공합니다.

### 1.2 핵심 아키텍처 원칙
* **Modular & Pluggable (지연 로딩):** 텍스트 고증, 이미지 합성, 딥페이크 페이스 스왑, AI 복제 음성 모듈이 완전히 분리되어, 필요한 모듈만 지연 로딩(Lazy Loading)으로 선택적으로 사용할 수 있습니다.
* **Model Agnostic (경량 로컬 추론 + 외부 API 연동 혼합):** 경량 로컬 추론 모델과 외부 API 연동을 혼합 설계하여 비용과 정확도를 모두 잡았으며, 백엔드는 자체 경량 모델부터 외부 거대 모델(Hugging Face, 외부 API 등)까지 유연하게 교체할 수 있습니다.
* **Explainable AI (XAI):** 단순 결과 수치(Pass/Fail) 제공을 넘어, 픽셀 위치(ELA 편차·바운딩 박스), 주파수 노이즈 패턴(FFT 스파이크), 안면 랜드마크 오프셋 등 **판정 근거**를 구조화된 JSON 리포트로 반환합니다.

---

## 2. 개발 배경 및 목적

### 2.1 사회적 및 기술적 문제점
1. **한국사 할루시네이션 확산:** LLM이 사료와 일치하지 않는 그럴듯한 거짓 역사 정보(Hallucination)를 출처까지 꾸며 대량으로 생성·유포하며, 이것이 교육·언론·SNS를 통해 사실처럼 재생산되는 사례 폭증.
2. **역사 멀티미디어 위변조 악용:** 역사적 사진 합성(GAN/Diffusion), 딥페이크 페이스 스왑(역사 인물 사칭), AI 복제 음성(인물 사칭·허위 역사 발언 유포)을 통한 역사적 사실관계 교란 및 사회적 사기 증가.
3. **통합 교차 검증 프레임워크의 부재:** 기존 공개 오픈소스는 단일 기능(텍스트 분류, 단일 딥페이크 탐지 등)에 파편화되어 있어, 하나의 역사 콘텐츠를 텍스트·이미지·영상·오디오에 걸쳐 **교차 검증**할 수 있는 통합 규격이 부재했고 상용 플랫폼 접근성도 낮았음.

### 2.2 개발 목적
Truth History SDK는 텍스트 고증 검증과 시청각(이미지·영상·오디오) 교차 검증을 표준화된 단일 API로 묶어, 누구나 자사 인프라에 **역사 콘텐츠 신뢰성 가드레일**을 최소한의 비용으로 신속하게 구축하고, 오염된 거짓 정보의 확산을 차단할 수 있도록 돕는 것을 목적으로 합니다.

---

## 3. 핵심 목표
* **4대 탐지 모듈 통합 SDK:** 아래 모듈을 단일 규격으로 통합 제공.
  * **📝 텍스트 고증 검증** — 한국사 텍스트의 AI 생성(Perplexity/Burstiness) 탐지 + 한국어 위키백과·DuckDuckGo·Naver Search·Google Fact Check **외부 검색 증거 병렬 교차 검증** 기반 **역사적 정합성 검증** + 현대 기기·대상이 역사 인물·시대와 동시 등장하는 **시대착오(Anachronism) 할루시네이션 탐지**.
  * **🖼️ ELA 이미지 합성 탐지** — Error Level Analysis 압축 왜곡 + FFT 주파수 노이즈(GAN/Diffusion 격자 아티팩트)로 위조·합성 역사 이미지 탐지.
  * **🎬 딥페이크 페이스 스왑 탐지(영상/정지영상)** — 안면 랜드마크 비대칭 + 프레임 간 temporal jitter로 페이스 스왑 탐지.
  * **🎙️ AI 복제 음성 탐지(오디오)** — MFCC + HNR 주파수 분석으로 합성/클론 음성 탐지(인물 사칭·허위 역사 발언 유포 대응).
* **다차원 정량 스코어링:** 각 모듈의 탐지 결과를 신뢰도 점수 및 위조 위험도로 수치화하고, 모듈 간 교차 검증 점수를 종합 제공.
* **설명 가능성(XAI) 확보:** 탐지 결과의 원인이 되는 근거(ELA 편차/바운딩, FFT 주파수 스파이크, 안면 랜드마크 오프셋, 문맥적 고증 오류 지점 등)를 API/CLI 리포트(JSON)로 명확히 제공.
* **개발자 친화적 API & 플러그인 구조:** 자체 모델·최신 가중치·외부 팩트체크 API를 쉽게 주입·확장할 수 있는 구조.

---

## 4. Quick Start (빠른 시작)

Truth History SDK 및 대시보드를 신속하게 실행하는 방법입니다.

> **라이브 데모:** [https://platy-rho.vercel.app](https://platy-rho.vercel.app) — React 대시보드와 FastAPI 서버리스 백엔드가 단일 도메인에 통합 배포되어 있습니다. 텍스트 고증 검증/URL 스캔은 라이브에서 즉시 사용 가능하며, 이미지·영상·오디오 분석은 서버리스 의존성 제약상 로컬 실행을 권장합니다 ([DEPLOY.md](DEPLOY.md) 참고).

### 4.1 설치 및 환경 설정 (Installation & Setup)

프로젝트 저장소를 로컬에 복제하고 필요한 백엔드(Python) 및 프론트엔드(Node.js) 의존성을 구성합니다:

**Step 1. 저장소 복제 및 디렉터리 이동**
```bash
git clone https://github.com/kimneche0419-rgb/TURTH_GUARD.git
cd TURTH_GUARD
```

**Step 2. 파이썬 가상환경 생성**
```bash
python -m venv .venv
```

**Step 3. 백엔드 의존성 및 패키지 개발자 모드 설치 (기본/AI 텍스트 고증 분석 포함)**
```bash
# Windows
.venv\Scripts\pip install -e .[text]

# macOS / Linux
.venv/bin/pip install -e .[text]
```

**Step 4. 프론트엔드 대시보드 라이브러리 설치**
```bash
npm install
```


### 4.2 기본 환경 초기화
작업 공간 내에 설정 파일(`truthhistory.json`), 미디어 수집 폴더(`uploads/`), 시크릿 보관용 `.env` 파일을 준비합니다:
* **PowerShell:** `.\th init`
* **CMD:** `th init`

### 4.3 개별 및 통합 실행 명령어
가상환경 활성화 없이 루트 경로에서 즉각 구동할 수 있는 단축 명령어를 제공합니다:

| 명령어 (CMD) | 명령어 (PowerShell) | 설명 | 주요 특징 및 옵션 |
|:---|:---|:---|:---|
| `th init` | `.\th init` | **프로젝트 환경 초기화** | `truthhistory.json`, `uploads/` 폴더 및 `.env`(API 키 입력용) 생성. 기존 설정 초기화 시 `--force` 적용 (기존 `.env`는 덮어쓰지 않음) |
| `th dev` | `.\th dev` | **통합 개발 서버 실행** | 백엔드 API(8000) 및 프론트엔드 대시보드(5173)를 각각 다른 새 창으로 동시 구동 (추천) |
| `th api` | `.\th api` | **백엔드 API 서버 단독 실행** | FastAPI 서버를 현재 세션에서 실행 (`--port <포트>`, `--host <호스트>` 옵션 지원) |
| `th web` | `.\th web` | **대시보드 로컬 개발 서버 단독 실행** | 프론트엔드를 현재 세션에서 단독 실행(5173, 핫 리로드). **프로덕션은 Vercel 라이브 배포 사용** — 로컬 프론트 수정·전체 멀티미디어 기능 테스트용 (Vercel 백엔드는 멀티미디어 미지원) |
| `th cli <텍스트/파일/URL>` | `.\th cli <텍스트/파일/URL>` | **CLI 역사 콘텐츠 신뢰도 분석 (단축)** | `th scan` 명령어의 단축 별칭으로 터미널에서 신속하게 분석 (입력·옵션 동일) |
| `th scan <텍스트/파일/URL>` | `.\th scan <텍스트/파일/URL>` | **CLI 역사 콘텐츠 신뢰도 분석** | **크롬 확장 프로그램과 동일한 모티브** — 텍스트를 직접 인자로 전달하면 LLM 답변을 즉시 고증 검증(파일은 txt/md/이미지/영상/오디오, URL은 본문 크롤링 분석). (`-f text/json/table` 출력 형식, `-c <설정JSON>` 설정 파일 지정, `--threshold` 판정 임계점 지원) |
| `th mcp` | `.\th mcp` | **MCP Stdio 표준 서버 실행** | LLM Agent(예: Claude)와 연동하기 위해 stdio 기반 JSON-RPC로 대화하는 MCP 서버 구동 |

### 4.4 외부 연동 환경 변수 (선택)
텍스트 고증 검증의 **외부 검색 증거 수집**에 사용되는 환경 변수입니다(모두 선택 사항):

| 환경 변수 | 설명 |
|:---|:---|
| `FACT_CHECK_API_KEY` | Google Fact Check Search API 키 (팩트체크 증거 소스 활성화) |
| `NAVER_CLIENT_ID` / `NAVER_CLIENT_SECRET` | Naver 통합 웹검색 API 자격증명 (한국어·한국사 특화 증거 수집) |

> 한국어 위키백과·DuckDuckGo 증거 검색은 별도 API 키 없이 동작합니다.

**`.env` 파일 지원:** CLI(`th`), REST API 서버(`th api`), MCP 서버(`th mcp`)는 기동 시 프로젝트 루트의 `.env` 파일을 자동으로 읽어 위 환경 변수를 주입합니다(`th init`으로 생성, 템플릿: [`.env.example`](./.env.example)). `.env`는 `.gitignore`에 등록되어 **Git에 커밋되지 않으므로** API 키 노출을 방지합니다. 이미 설정된 OS 환경 변수가 `.env` 값보다 우선하며, Vercel 배포 환경에서는 Vercel 대시보드의 Environment Variables를 사용합니다([DEPLOY.md](DEPLOY.md)).




---

## 5. Vercel 배포 가이드 (프로덕션 배포)

프론트엔드(React 대시보드)와 백엔드(FastAPI 서버리스 함수)를 **Vercel 단일 프로젝트 하나로 같은 도메인에 배포**하는 전체 과정입니다. 배포가 완료되면 `https://<project>.vercel.app` 형태의 URL을 받게 되며, **크롬 확장 프로그램은 이 URL을 백엔드로 자동 사용**하므로 사용자 측 설정이 전혀 필요 없습니다.

### 5.1 배포 아키텍처 및 구성 파일

| 파일 | 역할 |
|:---|:---|
| `vercel.json` | `/api/v1/:path*` 요청을 Python 서버리스 함수로 **rewrite 라우팅**. 프론트와 백엔드가 같은 도메인이라 CORS 이슈가 없음 |
| `api/index.py` | FastAPI 앱(`truthhistory_server:app`)을 Vercel Python 런타임이 감지할 수 있는 **ASGI 엔트리**로 노출 |
| `requirements.txt` | 서버리스 함수 의존성 — **의도적으로 경량화**(opencv/numpy/pillow/librosa 미포함, 아래 §5.5 참고) |
| `.vercelignore` | `.venv`, `node_modules`, `tests`, `pyproject.toml` 등 배포 불필요 파일 제외 → 빌드 크기/시간 절감 |
| `src/` + `index.html` + `vite.config.ts` | React/Vite 프론트엔드 — Vercel이 자동 감지하여 정적 호스팅(`/`) |

프론트엔드는 빌드 모드에서 **상대경로(같은 출처)** 로 API를 호출하고, 개발 모드에서만 `localhost:8000`을 호출하도록 `src/App.tsx`에 자동 전환 로직이 포함되어 있어 환경변수 설정이 필요 없습니다.

### 5.2 사전 준비

1. **Vercel 계정** 생성 — [https://vercel.com/signup](https://vercel.com/signup) (GitHub 계정으로 가입 권장)
2. **Node.js 18 이상** 설치 (Vercel CLI 구동용)
3. 저장소를 GitHub에 푸시 완료 (`git push origin main`)

### 5.3 배포 단계 (Vercel CLI)

```bash
# 1. Vercel CLI 설치 및 로그인
npm i -g vercel
vercel login

# 2. 프로젝트 루트에서 Vercel 프로젝트로 연결/생성
vercel link
# → "Set up and deploy?" Y / 어떤 범위에 둘지 선택 / 프레임워크 프리셋은 Vite 자동 감지

# 3. (선택) 외부 검색 증거용 환경 변수 설정 — 대시보드에서도 가능
#    Settings → Environment Variables 에서 추가 (모두 선택 사항)
#      FACT_CHECK_API_KEY     : Google Fact Check Search API 키
#      NAVER_CLIENT_ID        : Naver 통합 웹검색 API
#      NAVER_CLIENT_SECRET    : Naver 통합 웹검색 API

# 4. 프로덕션 배포
vercel --prod --yes
```

배포가 끝나면 터미널에 **프로덕션 URL**이 출력됩니다 (예: `https://platy-rho.vercel.app`). 이후 코드 변경 시에도 `git push` 후 `vercel --prod --yes` 한 줄로 재배포됩니다.

### 5.4 배포 검증

```bash
# 대시보드 로딩 확인 (HTTP 200)
curl -I https://platy-rho.vercel.app/

# 텍스트 고증 검증 API 확인 (XAI JSON 응답)
curl -X POST https://platy-rho.vercel.app/api/v1/scan/text \
  -H "Content-Type: application/json" \
  -d '{"text":"이순신 장군은 임진왜란 때 거북선으로 한산도 대첩에서 승리했다."}'
```

| 엔드포인트 | 서버리스 동작 |
|:---|:---|
| `POST /api/v1/scan/text` | ✅ 정상 (AI 생성 어휘 다양도 + 외부 검색 증거 정합성 + 시대착오 + 선동성 + 출처) |
| `POST /api/v1/scan/url` | ✅ 정상 (웹페이지 본문 크롤링 → 고증 검증) |
| `POST /api/v1/scan/media` | ⚠️ 중립 폴백 (이미지·영상·오디오 의존성 미포함, §5.5 참고) |

### 5.5 서버리스 제약 (중요)

Vercel 서버리스 함수에는 **225MB 번들 크기 제한**이 있습니다. 그래서 `requirements.txt`에서 멀티미디어 분석용 대형 의존성(opencv-python, numpy, pillow, torch, librosa)을 제외하고 텍스트 고증 검증 중심으로 배포합니다.

* 이미지(ELA)·영상(딥페이크)·오디오(AI 복제 음성) 분석이 필요한 경우 → **로컬 실행**(`th api` + 대시보드) 또는 **Render / Railway / Fly.io** 같은 컨테이너 호스트에 `requirements.txt`에 위 의존성을 추가한 뒤 `truthhistory_server:app`을 그대로 구동하면 의존성 제한 없이 전체 기능을 서비스할 수 있습니다.
* 콜드스타트: 서버리스 특성상 유휴 상태 후 첫 요청이 수 초 지연될 수 있습니다.

### 5.6 크롬 확장 프로그램 연동 (자동)

확장 프로그램(`extension/`)은 `background.js`의 `API_BASE` 상수가 **배포 URL을 직접 가리키도록 하드코딩**되어 있습니다. 즉:

* 사용자는 **백엔드 실행도, API 주소 설정도 필요 없이** 확장 설치만 하면 즉시 검증 동작
* 백엔드 주소를 바꾸려면 `extension/background.js`의 `API_BASE` 상수 하나만 수정
* 로컬 백엔드로 확장을 개발/디버깅하려면 `API_BASE = "http://localhost:8000"`으로 변경

> 자세한 운영/트러블슈팅 기록(의존성 크기 제한 해결 과정 등)은 [DEPLOY.md](DEPLOY.md)를 참고하세요.

## 6. 상세 설계 및 구현 가이드 (Detailed Design Guides)

본 프레임워크를 직접 빌드하거나 커스터마이징하려는 개발자를 위해 모듈별 초상세 구현 가이드를 마련하였습니다.

> [!IMPORTANT]
> 실제로 라이브러리를 개발하거나 수정하기 전, 아래 상세 구현 명세서들을 차례로 학습해 주시기 바랍니다.

* 🛠️ **[개발자 환경 설정 가이드](docs/getting_started.md):** 패키지 의존성 관리 및 빌드/배포 절차
* 🏗️ **[시스템 아키텍처 및 공통 설계](docs/architecture.md):** 데이터 흐름 파이프라인 및 지연 로딩, 공통 추상 클래스 설계
* 📝 **[텍스트 고증 검증 모듈 구현 상세](docs/text_analyzer.md):** Perplexity, Burstiness 산출 공식 및 외부 역사 사료·팩트체크 API 통합 사양
* 🖼️ **[이미지 분석 모듈 구현 상세](docs/image_analyzer.md):** ELA 압축 왜곡 검출 및 FFT 주파수 노이즈 분석, GAN/Diffusion 합성 역사 이미지 탐지
* 🎬 **[영상 & 오디오 분석 모듈 구현 상세](docs/video_audio_analyzer.md):** 딥페이크 페이스 스왑(랜드마크 비대칭·temporal jitter) 및 HNR/MFCC 기반 AI 복제 음성 탐지 로드맵
* 💻 **[CLI & Explain API 구현 상세](docs/cli_explain.md):** Rich 기반 CLI 구성, XAI 판정 근거(픽셀·주파수 노이즈) 반환용 JSON 스키마 및 프로세스 종료 코드 정의
* 🚀 **[풀스택 및 MCP 확장 아키텍처 설계](docs/fullstack_spec.md):** FastAPI 게이트웨이(pip), Vite/React 대시보드(npm), 크롬 익스텐션 및 MCP 서버 연동 규격

---

## 7. 프로젝트 디렉토리 구조
```plaintext
TURTH_GUARD/
 ├── truthhistory/            # SDK 코어 패키지 (pip install -e .)
 │    ├── text/               # 한국사 텍스트 고증 검증 (AI 생성 탐지 + 외부 검색 증거 정합성 + 시대착오 탐지)
 │    ├── image/              # ELA 이미지 합성 탐지 (ELA 압축 왜곡 + FFT 주파수 노이즈)
 │    ├── video/              # 딥페이크 페이스 스왑 탐지 (랜드마크 비대칭·temporal jitter)
 │    ├── audio/              # AI 복제 음성 탐지 (MFCC + HNR)
 │    ├── explain/            # 판정 근거 추출 및 XAI 포맷팅 엔진
 │    ├── cli/                # 명령줄 인터페이스 로직 (th)
 │    └── utils/              # URL 파싱·웹 본문 추출 등 공통 유틸리티
 ├── truthhistory_server.py   # FastAPI 게이트웨이 (REST API /api/v1/scan/text|url|media)
 ├── truthhistory_mcp.py      # MCP stdio 서버 (LLM Agent 연동)
 ├── api/index.py             # Vercel 서버리스 엔트리 (FastAPI ASGI 래핑)
 ├── src/                     # React/Vite 프론트엔드 대시보드
 ├── extension/               # 크롬 확장 프로그램 (LLM 역사 할루시네이션 가드)
 ├── tests/                   # 단위/통합 테스트 코드
 ├── docs/                    # 상세 개발자 설계 문서 및 가이드
 ├── th.ps1 / th.bat          # Windows CLI 런처 (.venv th.exe 래퍼)
 └── run.bat                  # 백엔드+프론트엔드 일괄 기동 스크립트
```

---

## 8. 예상 활용 분야
* **뉴스 플랫폼 / 언론사:** 역사 관련 제보 자료·기사의 사료 교차 검증, 합성 사진·사칭 발언 사전 차단.
* **교육 플랫폼 / 학교 / 교과서 출판:** 교재·학습 자료·과제의 한국사 고증 오류 및 AI 생성 위변조 검증.
* **SNS / 커뮤니티:** 역사 왜곡 콘텐츠(조작 사진·딥페이크·사칭 음성) 확산 실시간 모니터링·차단.
* **공공기관 / 박물관 / 기록원:** 디지털 역사 자료·전시 콘텐츠의 진본성 보증 및 위변조 대응.
* **AI 챗봇 / LLM 서비스:** 한국사 질의응답의 할루시네이션 사전 필터링 가드레일.

---

## 9. 오픈소스 기술적 특징
* **MIT License:** 상업·비상업 사용에 제약 없는 유연한 라이선스로 자유로운 자사 임베딩·2차 창작 허용.
* **pip 설치 지원 (`pip install -e .[text|image|video|audio|all]`):** 저장소 클론 후 필요한 모듈의 의존성만 extras로 선택 설치하여 가벼운 도입 가능.
* **경량 로컬 추론 + 외부 API 연동 혼합 설계:** 경량 로컬 추론으로 기본 탐지를 처리하고 무거운 검증만 외부 API로 보내, 자체 검증 레이어 구축 비용을 **80% 이상 절감**.
* **지연 로딩(Lazy Loading) 모듈러 구조:** 사용하지 않는 모듈(이미지/영상/오디오)은 로드하지 않아 가볍고 빠른 도입 가능.
* **CLI & REST API / MCP 예제 제공:** 다양한 서비스 아키텍처와 Agentic AI 환경에 즉시 통합 가능.
* **Plugin 구조 지원:** 자체 모델·최신 가중치·외부 역사 사료/팩트체크 API를 쉽게 교체·주입 가능.
* **GitHub 기반 협업:** 이슈 및 PR을 통한 지속적인 생태계 고도화 및 한국사 특화 모델 업데이트.

---
## 10. 구현 완료 통합 환경 및 향후 확장 로드맵

### 10.1 구현 완료
* **크롬 확장 프로그램 → [extension/](extension/README.md):** ChatGPT/Claude/Gemini/AI Studio 어시스턴트 답변에 **적응형 글자색 배지**(호스트 페이지 라이트/다크 자동 적응)를 삽입해 한국사 할루시네이션을 실시간 교차 검증하고, **배지 클릭 → 상세 리포트 패널**(판정 근거 + 근거 자료 웹사이트 링크 + 참고 사료)을 제공. **우클릭 컨텍스트 메뉴는 모든 사이트에서 범용 동작**하며, **Vercel 배포 백엔드를 자동 사용(설정 불필요)**, 팝업에서 자동스캔 토글과 **최근 검사 결과**를 확인.
* **MCP 서버 (`th mcp`):** stdio 기반 JSON-RPC로 Claude 등 LLM 에이전트와 직접 통신. **대표 도구 `scan_text`는 크롬 확장 프로그램과 동일한 모티브**로 LLM 답변 텍스트의 역사 할루시네이션을 실시간 검증(AI 생성 확률·외부 검색 증거 정합성·시대착오 탐지·판정 근거/증거 출처 URL 반환)하며, `scan_file`로 멀티미디어 파일 검증 지원.
* **Vercel 라이브 배포:** React 대시보드 + FastAPI 서버리스 백엔드를 단일 도메인([https://platy-rho.vercel.app](https://platy-rho.vercel.app))에 통합 배포 → [DEPLOY.md](DEPLOY.md).

### 10.2 향후 확장 로드맵
* **VSCode Extension:** 에디터 내 한국사 텍스트 실시간 고증 검증.
* **Hugging Face 연동:** 최신 한국어·한국사 특화 모델과 다이렉트 동기화.
* **실시간 스트림/라이브 분석:** 라이브 방송·실시간 피드의 딥페이크·사칭 음성 검증 아키텍처.
* **한국사 사료·팩트체크 DB 고도화:** 국사편찬위원회·교과서·사료 기반 정합성 검증 커버리지 지속 확대.

---

## 11. 기대 효과
* **딥페이크 사기·역사 할루시네이션 실시간 차단 → 정보 환경 투명성 확보, 사회적 불신 최소화:** 위변조 역사 콘텐츠와 그럴듯한 거짓 역사 정보를 생성·유포 단계에서 조기 차단합니다.
* **자체 검증 레이어 구축 비용 80% 이상 절감:** 파편화된 탐지 모듈을 단일 SDK로 규격화하고, 경량 로컬 추론 + 외부 API 연동 혼합 설계를 채택해 자체 검증 시스템 구축 비용을 대폭 낮춥니다.
* **자사 규격 맞춤 임베딩/확장 → 뉴스·SNS·교육 시스템에 손쉬운 도입:** 지연 로딩 모듈러 구조와 MIT 라이선스 덕분에 각자의 인프라 규격에 맞춰 손쉽게 임베딩·확장할 수 있습니다.
* **투명한 미디어 소비 보장 + 윤리적 AI 생태계 조성 + 디지털 역사 주권 수호:** 설명 가능한 XAI 리포트(픽셀 위치·주파수 노이즈 패턴·랜드마크 오프셋)로 판정 근거를 투명하게 공개하며, 오염된 거짓 정보로부터 한국 역사의 신뢰성을 스스로 지킬 수 있습니다.
