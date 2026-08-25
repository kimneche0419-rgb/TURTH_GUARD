# Truth History SDK 풀스택 개발 진척 리포트 (Progress Report)

본 문서는 생성형 AI로 인한 **한국 역사 할루시네이션 및 멀티미디어 위변조**에 대응하는 통합 검증 프레임워크 **Truth History SDK**와 연동 대시보드 프로젝트의 핵심 개발 진척도를 요약한 리포트입니다. 텍스트 고증 검증·ELA 이미지 합성·딥페이크 페이스 스왑·AI 복제 음성 탐지를 단일 SDK로 통합하여, 뉴스·교육 시스템 등이 자사 인프라에 임베딩할 수 있는 한국 역사 데이터 안전 가드레일을 제공합니다.

---

## 1. 프로젝트 주요 성과 요약 (Milestones)

* **FastAPI 백엔드 서버 완비**: 파일 타입별 비동기 미디어 검증 게이트웨이 및 XAI(설명 가능한 판정 근거) 포맷팅 연동 완료. 픽셀 위치(ELA 편차)·주파수 노이즈 패턴(FFT 스파이크)·랜드마크 오프셋 등 판정 근거를 구조화해 반환.
* **React/Vite 프론트엔드 대시보드 개발**: Pydantic DTO 스키마와 완벽히 호환되는 모던하고 직관적인 신뢰도 시각화 대시보드 구축 완료.
* **CLI 통합 환경 구축 및 단순화 (`th`)**: `th init`, `th dev`, `th api`, `th web`, `th cli`, `th scan`, `th mcp` 등의 직관적인 통합 CLI 명령어 세트 개발.
* **환경 래퍼 지원**: 가상환경 진입 없이 프로젝트 루트에서 바로 동작 가능한 `th.ps1` (PowerShell) 및 `th.bat` (CMD) 래퍼 스크립트 작성 완료.
* **단위 테스트 수립 및 품질 검증**: CLI 서브 명령어 모킹 테스트 등을 포함하여 총 14개의 단위 테스트 통과 완료.
* **GitHub 원격 배포**: 원격 저장소(`https://github.com/kimneche0419-rgb/TURTH_GUARD.git`)의 `main` 브랜치로 소스코드 배포 완료.

---

## 2. 세부 개발 현황 (Details of Implementation)

### 2.1 백엔드 API 레이어
* **[truthhistory_server.py](truthhistory_server.py)**:
  * FastAPI 기반의 비동기 웹 백엔드 구축.
  * 멀티파트 파일 업로드를 수용하고 확장자 분류를 통해 텍스트 고증, 이미지 합성(ELA), 비디오 딥페이크, 오디오 복제 음성 탐지 파이프라인과 자동 매핑.
  * Explainable AI (XAI) 결과 포맷에 의거해 구조화된 탐지 근거 데이터 반환.

### 2.2 프론트엔드 시각화 레이어
* **[package.json](package.json) / [tsconfig.json](tsconfig.json) / [vite.config.ts](vite.config.ts)**:
  * React, Vite, TS 기반의 모던 웹 번들링 빌드 시스템 구축.
  * Axios(HTTP 통신용), Lucide-React(모던 아이콘 세트용) 라이브러리 추가 구성.
* **[src/main.tsx](src/main.tsx) / [index.html](index.html)**:
  * React DOM 마운팅 및 Vite 진입 레이아웃 구성.
* **[src/App.tsx](src/App.tsx)**:
  * 프리미엄 다크 모드(sleek dark theme) 테마의 인터랙티브 웹 UI 대시보드.
  * Drag & Drop 지원 파일 업로드 박스 및 파일 크기/유형 제한 가드 기능.
  * 실시간 프로그레스 바 및 신뢰도 수치 게이지 차트 컴포넌트 탑재.
  * 이상 탐지 포인트(Anomalies)와 XAI 판정 근거를 중요도(Warning, Critical)별 경고 카드로 렌더링.

### 2.3 CLI 명령어 및 환경 설정 도구
* **[truthhistory/cli/main.py](truthhistory/cli/main.py)**:
  * Click 프레임워크 기반의 커맨드 라인 인프라 구축.
  * `th init`: 기본 설정 파일(`truthhistory.json`) 및 미디어 업로드 폴더 생성.
  * `th dev`: 백엔드 서버와 프론트엔드 대시보드를 두 개의 다른 새 터미널 창으로 동시에 기동.
  * `th api`: 백엔드 FastAPI 서버를 현재 세션의 포그라운드에서 직접 구동.
  * `th web`: 프론트엔드 Vite 대시보드를 포그라운드에서 구동.
  * `th cli <파일경로>`: `th scan <파일경로>` 명령어의 단축용 별칭.
* **[pyproject.toml](pyproject.toml)**:
  * 스크립트 실행 엔트리포인터에 `th` 단축어 추가 등록.

### 2.4 루트 래퍼 스크립트 (Windows 간소화)
* **[th.bat](th.bat) / [th.ps1](th.ps1)**:
  * 사용자가 로컬 가상환경(`.venv`)을 켜지 않더라도 프로젝트 루트에서 편리하게 `.\th dev`, `.\th init` 등을 호출하여 자동으로 가상환경에 매핑되도록 지원하는 포워딩 스크립트.

### 2.5 빌드 관리 및 테스트 케이스
* **[.gitignore](.gitignore)**:
  * 가상환경 폴더(`.venv`), `node_modules`, 로컬 임시 업로드 폴더(`uploads/`), `truthhistory.json` 등 원격 관리가 불필요한 환경 변수/종속성 격리.
* **[tests/test_cli.py](tests/test_cli.py) / [tests/test_analyzers.py](tests/test_analyzers.py)**:
  * 텍스트 고증/이미지 합성(ELA)/오디오 복제 음성/비디오 딥페이크 탐지기(Analyzer)에 대한 스코어 테스트.
  * 신규 구현된 CLI 명령어들에 대한 모킹 단위 테스트(subprocess 기동 및 파일시스템 격리 테스트) 포함 100% 통과 완료.

---

## 3. 향후 로드맵 및 기여 방안

* **Browser Extension 배포**: 크롬/웨일 익스텐션을 제작하여 웹서핑 중 역사 왜곡 의문 문서나 딥페이크 의심 자료를 우클릭 한 번으로 탐지할 수 있는 플러그인 제공 예정.
* **Agentic AI용 MCP 서버**: LLM Agent가 진위 판단이 모호한 역사 지식 정보를 검증할 수 있도록 지원하는 Model Context Protocol API 노출 확장.
* **한국사 사료 DB 연동**: 국사편찬위원회·교과서·디지털 사료 등 권위 있는 한국사 지식베이스와 직접 연동하는 고증 검증 고도화.
* **대용량 미디어 스트리밍 지원**: 라이브 스트리밍 영상을 실시간으로 청크 단위 검사할 수 있는 비동기 비디오 분석 레이어 추가 예정.
