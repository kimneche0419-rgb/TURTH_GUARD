# Walkthrough: TruthGuard 풀스택 코드베이스 구축 및 기능 검증 완료

`npm install`과 `npm run dev` 명령이 루트 경로(`C:\TURTH_GUARD`)에서 오류 없이 올바르게 작동하도록 웹 대시보드 및 FastAPI 연동용 풀스택 파일들을 구성하고 Git 원격 배포를 완료했습니다.

---

## 1. 생성된 웹 풀스택 파일 목록 (Full-stack Workspace Files)

* **파이썬 백엔드 API:** [truthguard_server.py](file:///c:/TURTH_GUARD/truthguard_server.py)
  * 비동기 멀티파트 업로드를 수용하고 미디어 타입에 매핑하여 스캐닝한 후, XAI JSON 리포트를 반환하는 FastAPI 게이트웨이 서버 스크립트.
* **프론트엔드 환경 설정 (루트):**
  * [package.json](file:///c:/TURTH_GUARD/package.json): React, Vite, TS, Axios, Lucide-React가 선언된 Node 패키지 메타데이터.
  * [vite.config.ts](file:///c:/TURTH_GUARD/vite.config.ts): Vite 번들러 환경 설정 파일.
  * [tsconfig.json](file:///c:/TURTH_GUARD/tsconfig.json): TypeScript 컴파일 컴파일러 옵션 설정.
  * [index.html](file:///c:/TURTH_GUARD/index.html): HTML 뼈대 및 Vite 스크립트 진입점 지정.
* **React 소스코드 (src/):**
  * [src/main.tsx](file:///c:/TURTH_GUARD/src/main.tsx): React App 진입 마운팅 소스.
  * [src/App.tsx](file:///c:/TURTH_GUARD/src/App.tsx): 파일 업로드 드롭존, 로딩 에니메이션, Pydantic DTO 기반 신뢰도 점수 및 게이지 차트, Anomalies 경고 카드 리스트를 갖춘 프리미엄 다크 모드 스타일 시각화 UI 컴포넌트 코드.
* **프로젝트 루트 실행 래퍼 스크립트:**
  * [tg.bat](file:///c:/TURTH_GUARD/tg.bat): CMD 환경에서 가상환경 활성화 없이 바로 `tg` 명령어를 프록시 실행하는 배치 파일.
  * [tg.ps1](file:///c:/TURTH_GUARD/tg.ps1): PowerShell 환경에서 가상환경 활성화 없이 바로 `.\tg` 명령어를 프록시 실행하는 파워셸 스크립트.

---

## 2. 검증 완료 및 오류 해결 (ENOENT Resolved)

* 기존에 존재하지 않았던 `package.json` 및 프론트엔드 설정 파일들과 소스 디렉터리가 작업 공간에 온전히 보강되었으므로, 터미널에서 `npm install` 및 `npm run dev`를 실행 시 발생하던 **ENOENT (no such file or directory) 오류가 완벽히 차단**되었습니다.

---

## 3. Git 원격 저장소 추가 및 푸시 완료 (Git Push to Remote)

* **Git 초기화 및 `.gitignore` 설정**:
  * 로컬 가상환경(`.venv`), `node_modules`, `uploads` 폴더 등 대용량 불필요 파일들이 원격에 들어가지 않도록 `.gitignore` 파일을 작성하고 Git 저장소를 초기화했습니다.
* **원격 전송 완료**:
  * 로컬 코드베이스 전체를 커밋한 후 `https://github.com/kimneche0419-rgb/TURTH_GUARD.git`을 origin 원격 저장소로 연동하고 `main` 브랜치에 성공적으로 푸시(`git push -u origin main`)를 완료했습니다.

---

## 4. `tg init` 및 개발자 명령어 (`dev`, `api`, `web`, `cli`) 제공

* **`tg` 단축어 및 다중 명령어 지원**:
  * `pyproject.toml` 스크립트에 등록하여 사용자는 `truthguard` 뿐만 아니라 `tg` 명령어로도 모든 CLI 기능을 신속하게 호출할 수 있습니다.
* **추가된 명령어 요약**:
  * **`tg dev`**: 백엔드 API와 React 대시보드를 동시에 독립적인 새 창으로 띄워 실행합니다.
  * **`tg api`**: 백엔드 FastAPI 서버를 현재 터미널 포그라운드에서 직접 실행합니다 (`--port`, `--host` 옵션 지원).
  * **`tg web`**: React 프론트엔드 대시보드를 현재 터미널 포그라운드에서 단독 실행합니다.
  * **`tg cli <파일경로>`**: `tg scan <파일경로>`의 축약형 별칭으로, CLI에서 즉시 파일을 검증 및 리포팅합니다.
* **`tg init` 환경 구성 명령어**:
  * `tg init` 실행 시 `truthguard.json` 설정 파일과 `uploads/` 폴더를 생성합니다.
* **단위 테스트 추가 및 검증 완료**:
  * [test_cli.py](file:///c:/TURTH_GUARD/tests/test_cli.py)에 각 서브 명령어의 단위 테스트를 구성하고 전체 **12개 테스트 전원 통과(PASSED)**를 기록했습니다.

---

## 5. API Key 보안 메커니즘 구축 및 CLI/GUI 연동

* **FastAPI 백엔드 보안 헤더 검증**:
  * [truthguard_server.py](file:///c:/TURTH_GUARD/truthguard_server.py)에 `X-API-Key` 헤더 및 `api_key` 쿼리 파라미터를 검증하는 FastAPI Security Dependency 레이어를 적용했습니다.
  * 서버 설정 파일(`truthguard.json`) 또는 환경 변수(`TRUTHGUARD_API_KEY`)에 API Key가 설정되어 있을 때만 강제 검증을 실행하여 하위 호환성(기본값은 퍼블릭)을 유지했습니다.
  * 권한이 유효하지 않을 시 `401 Unauthorized` 에러를 반환합니다.
* **React GUI 대시보드 UI 통합**:
  * [src/App.tsx](file:///c:/TURTH_GUARD/src/App.tsx) 대시보드 상단에 마스크 처리된 API Key 입력 제어부를 설계했습니다.
  * 입력된 API Key는 브라우저의 `localStorage`에 자동 보관 및 영구 지속됩니다.
  * 분석 요청 전송 시 `X-API-Key` 헤더를 Axios 호출 헤더에 자동 바인딩합니다. 만약 401 Unauthorized가 발생할 경우 한글로 명확한 안내 얼럿을 출력합니다.
* **CLI 초기화 템플릿 제공**:
  * `tg init` 시 생성되는 설정 구조에 `"api_key": ""` 필드를 기본 제공하여 사용자가 쉽게 API Key를 지정하고 서버를 구동하도록 개선하였습니다.

---

## 6. MCP (Model Context Protocol) 서버 구축 및 연동

* **Stdio 기반 MCP 서버 구축**:
  * [truthguard_mcp.py](file:///c:/TURTH_GUARD/truthguard_mcp.py) 파일을 생성하여 JSON-RPC 2.0 표준을 준수하는 Stdio 통신 방식의 MCP 서버를 순수 파이썬(의존성 없음)으로 완벽하게 구현했습니다.
  * AI Agent가 활용할 수 있는 두 가지 핵심 도구(Tools)를 바인딩했습니다:
    * `scan_file`: 지정된 절대/상대 경로에 존재하는 미디어를 로컬 분석하여 종합적인 신뢰 지표 반환.
    * `scan_text`: 텍스트 주장에 대해 실시간 AI 생성률, 자극성 지수, 판단 근거(XAI) 반환.
* **CLI 통합 환경 연동 (`tg mcp`)**:
  * `tg mcp` 명령어를 추가 구현하여 사용자는 복잡한 파이썬 스크립트 실행 경로 없이 즉각적이고 손쉽게 Stdio MCP 서버 프로세스를 실행할 수 있습니다.
* **단위 테스트 수립 및 품질 검증**:
  * [test_cli.py](file:///c:/TURTH_GUARD/tests/test_cli.py)에 Stdio MCP 루틴 호출 무결성을 입증하는 단위 테스트를 추가 구성하여 전체 **13개 단위 테스트 전원 정상 통과(PASSED)**를 달성했습니다.

---

## 7. 인터넷 웹사이트 URL 신뢰도 스캔 기능 구축

* **HTML 본문 텍스트 추출 파서 탑재**:
  * [truthguard/utils/url_parser.py](file:///c:/TURTH_GUARD/truthguard/utils/url_parser.py)에 Python 표준 모듈인 `html.parser.HTMLParser`를 응용하여 외부 라이브러리 의존성 없이 스크립트, 스타일, 네비게이션바 등 불필요 태그를 제외한 핵심 기사 본문만 크롤링하는 유틸리티를 제작했습니다.
* **FastAPI 백엔드 API 라우트 추가**:
  * [truthguard_server.py](file:///c:/TURTH_GUARD/truthguard_server.py)에 `/api/v1/scan/url` 신규 포스트 엔드포인트를 개설하여 JSON 바디로 외부 뉴스 주소를 전달받아 분석 결과를 리포팅할 수 있게 하였습니다.
* **CLI 명령어 다형성 지원**:
  * `tg scan <주소>` 또는 `tg cli <주소>` 형식으로 호출 시 입력값이 URL임을 파싱 엔진이 자동 분기 처리하여 즉각적으로 웹페이지 본문을 읽어와 팩트체크 리포트를 구성하게끔 [truthguard/cli/main.py](file:///c:/TURTH_GUARD/truthguard/cli/main.py)를 개선했습니다.
* **React 대시보드 탭 UI 적용**:
  * [src/App.tsx](file:///c:/TURTH_GUARD/src/App.tsx)에 **[파일 업로드]** 및 **[웹사이트 URL 분석]** 탭 전환부를 신설하여 사용자가 브라우저에서 주소 입력만으로 실시간 신뢰성 레이팅 스크롤뷰 차트를 볼 수 있도록 업그레이드했습니다.
* **단위 테스트 수립 및 무결성 검증 완료**:
  * 크롤링 모킹 연동 테스트 `test_cli_scan_url_success`를 수립하고, **전체 14개 단위 테스트 100% 성공(PASSED)** 및 프론트엔드 빌드 패스를 입증했습니다.
