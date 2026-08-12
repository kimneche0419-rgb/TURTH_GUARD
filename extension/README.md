# Truth History: LLM 역사 할루시네이션 가드 (Chrome Extension)

생성형 AI(ChatGPT·Claude·Gemini 등)가 출력하는 한국사 텍스트를 **Truth History SDK** 고증 검증 엔진으로 실시간 교차 검증하여, 역사 왜곡·할루시네이션 의심 답변에 즉시 경고 배지를 표시하는 Manifest V3 크롬 확장 프로그램입니다.

## 작동 방식

1. **자동 스캔**: 지원 LLM 사이트에서 새 어시스턴트 답변이 렌더링되면 본문 텍스트를 추출해 로컬 Truth History 백엔드(`/api/v1/scan/text`)로 전송합니다.
2. **XAI 배지 삽입**: 각 답변 상단에 신뢰도·위험도·판정 근거(이유 목록) 배지를 인라인으로 삽입합니다. 역사 왜곡 의심 시 빨간 배지로 명확히 경고합니다.
3. **수동 검사**: 어떤 텍스트든 드래그 선택 후 우클릭 → "Truth History: 이 텍스트 역사 할루시네이션 검사"로 즉시 검증할 수 있습니다.
4. **팝업 설정**: API 엔드포인트 주소·API Key·자동 스캔 토글을 설정하고 최근 검사 결과를 확인합니다.

> 검증은 로컬 Truth History REST 서버가 수행하므로 확장 사용 전 백엔드를 먼저 띄워야 합니다.

## 설치 (개발자 모드)

1. Truth History 백엔드 실행: 프로젝트 루트에서 `th api` (기본 `http://localhost:8000`).
2. Chrome / Whale / Edge에서 `chrome://extensions` 접속 → 우측 상단 **개발자 모드** 활성화.
3. **"압축 해제된 확장 프로그램 로드"** 클릭 → 이 `extension/` 폴더 선택.
4. 툴바의 🛡️ 아이콘 클릭 → 팝업에서 API 주소(`http://localhost:8000`) 확인 후 **설정 저장**.
5. ChatGPT/Claude/Gemini 에서 역사 질문 후 답변에 Truth History 배지가 나타나는지 확인.

## 지원 사이트

| 서비스 | 호스트 |
| :--- | :--- |
| ChatGPT | `chatgpt.com`, `chat.openai.com` |
| Claude | `claude.ai` |
| Gemini | `gemini.google.com` |

> LLM 서비스들이 DOM 구조를 자주 변경하므로, 자동 배지가 동작하지 않을 때는 **우클릭 수동 검사**를 사용하세요 (어디서나 동작).

## 파일 구성

* `manifest.json` — Manifest V3 메타데이터·권한·호스트 권한.
* `background.js` — 서비스 워커. 컨텍스트 메뉴 등록 및 `/api/v1/scan/text` API 중계.
* `content.js` — 콘텐츠 스크립트. 어시스턴트 메시지 관찰·배지 삽입·플로팅 결과 패널.
* `content.css` — 주입 스타일(`.th-ext-` 네임스페이스).
* `popup.html` / `popup.js` — 설정 UI 및 최근 결과 표시.
* `icons/` — 16/48/128 확장 프로그램 아이콘.

## 권한 안내

* `host_permissions`(localhost + LLM 4개 호스트): 백엔드 API 호출 및 페이지 내 텍스트 읽기용.
* `contextMenus`, `storage`, `activeTab`, `scripting`: 우클릭 메뉴·설정 저장·메시지 삽입용. 외부로 데이터를 전송하지 않습니다(오직 사용자가 지정한 Truth History 백엔드로만 전송).
