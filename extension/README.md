# Truth History: LLM 역사 할루시네이션 가드 (Chrome Extension)

생성형 AI(ChatGPT·Claude·Gemini·AI Studio 등)가 출력하는 한국사 텍스트를 **Truth History SDK** 고증 검증 엔진으로 실시간 교차 검증하여, 역사 왜곡·할루시네이션 의심 답변에 **적응형 글자색 경고 배지**(호스트 페이지 라이트/다크 자동 적응)를 표시하고, **배지 클릭 시 상세 리포트 패널**(판정 근거 + 근거 자료 웹사이트 + 참고 사료)을 제공하는 Manifest V3 크롬 확장 프로그램입니다.

## 작동 방식

1. **자동 스캔**: 지원 LLM 사이트에서 새 어시스턴트 답변이 렌더링되면 본문 텍스트를 추출해 **Vercel에 배포된 Truth History 백엔드**(`/api/v1/scan/text`)로 전송합니다.
2. **XAI 배지 삽입**: 각 답변 상단에 신뢰도·위험도·판정 근거(이유 목록) 배지를 인라인으로 삽입합니다. 배지는 **투명 배경 + 상속 글자색**으로 호스트 페이지의 라이트/다크 테마에 자동 적응하며, 역사 왜곡 의심 시 빨간 태그로 명확히 경고합니다. **배지를 클릭하면 상세 리포트 패널**(신뢰도·AI 생성 확률 + 판정 근거 + 근거 자료 웹사이트 클릭 가능 링크 + 참고 사료)이 열립니다.
3. **수동 검사**: 어떤 텍스트든 드래그 선택 후 우클릭 → "Truth History: 이 텍스트 역사 할루시네이션 검사"로 즉시 검증할 수 있습니다.
4. **팝업**: 자동 스캔 토글을 설정하고, 확장 팝업을 열 때마다 **최근 검사 결과**(신뢰도·판정 요약)를 확인합니다.

> 검증은 Vercel에 배포된 백엔드([https://platy-rho.vercel.app](https://platy-rho.vercel.app))가 수행합니다 — **별도 백엔드 실행이나 API 주소 설정 없이 설치 즉시 동작**합니다. 로컬 백엔드로 개발하려면 `background.js`의 `API_BASE` 상수를 `http://localhost:8000`으로 변경하세요.

## 설치 (개발자 모드)

1. Chrome / Whale / Edge에서 `chrome://extensions` 접속 → 우측 상단 **개발자 모드** 활성화.
2. **"압축 해제된 확장 프로그램 로드"** 클릭 → 이 `extension/` 폴더 선택.
3. ChatGPT/Claude/Gemini/AI Studio 에서 역사 질문 후 답변에 Truth History 배지가 나타나는지 확인. (설정·백엔드 준비 불필요)

## 지원 사이트

| 서비스 | 호스트 |
| :--- | :--- |
| ChatGPT | `chatgpt.com`, `chat.openai.com` |
| Claude | `claude.ai` |
| Gemini | `gemini.google.com` |
| Google AI Studio | `aistudio.google.com` |

> 위 LLM 사이트에서는 어시스턴트 답변 렌더링 시 **자동 배지**가 동작합니다. **우클릭 수동 검사는 사이트 제한 없이 Google AI Mode 등 모든 사이트에서 범용으로 동작**합니다. LLM 서비스들이 DOM 구조를 자주 변경하므로, 자동 배지가 동작하지 않을 때도 우클릭 수동 검사를 사용하세요.

## 파일 구성

* `manifest.json` — Manifest V3 메타데이터·권한·호스트 권한.
* `background.js` — 서비스 워커. 컨텍스트 메뉴 등록 및 `/api/v1/scan/text` API 중계.
* `content.js` — 콘텐츠 스크립트. 어시스턴트 메시지 관찰·배지 삽입·플로팅 결과 패널.
* `content.css` — 주입 스타일(`.th-ext-` 네임스페이스).
* `popup.html` / `popup.js` — 설정 UI 및 최근 결과 표시.
* `icons/` — 16/48/128 확장 프로그램 아이콘.

## 권한 안내

* `host_permissions`(`http://*/*`, `https://*/*`): 모든 사이트 우클릭 수동 검사 및 배포 백엔드(Vercel) API 호출용.
* `contextMenus`, `storage`, `activeTab`, `scripting`: 우클릭 메뉴·설정 저장·메시지 삽입용. 외부로 데이터를 전송하지 않습니다(오직 Truth History 백엔드로만 전송).
