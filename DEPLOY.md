# Truth History SDK — 배포 가이드 (Vercel)

> **상태: 🟢 라이브** — `https://platy-rho.vercel.app`
> 프론트엔드(React 대시보드) + 백엔드(FastAPI 서버리스)가 같은 도메인에서 동작 중.

---

## 배포된 구성 (Vercel 단일 프로젝트 `jlab0419/platy`)
- **프론트엔드**(React/Vite) → 정적 호스팅 (`/`)
- **백엔드**(FastAPI) → `api/index.py` Python 서버리스 함수 (`/api/v1/*`)
- `vercel.json`: `/api/v1/:path*` → 서버리스 함수 라우팅, 같은 도메인이라 CORS 이슈 없음
- 프론트는 빌드 모드로 자동 전환 (`PROD` → 상대경로 동일 출처 / dev → `localhost:8000`) — 환경변수 불필요

## 검증된 엔드포인트
| URL | 동작 |
| :--- | :--- |
| `GET  https://platy-rho.vercel.app/` | ✅ React 대시보드 (200) |
| `POST https://platy-rho.vercel.app/api/v1/scan/text` | ✅ 한국사 텍스트 고증 검증 XAI JSON (200) |
| `POST https://platy-rho.vercel.app/api/v1/scan/url`  | ✅ 웹페이지 본문 크롤링 → 고증 검증 |
| `POST .../api/v1/scan/media` (이미지/영상/오디오) | ⚠️ 중립 폴백 (아래 참고) |

요청 예:
```bash
curl -X POST https://platy-rho.vercel.app/api/v1/scan/text \
  -H "Content-Type: application/json" \
  -d '{"text":"이순신 장군은 임진왜란 때 거북선으로 한산도 대첩에서 승리했다."}'
```

## 서버리스 지원 범위 / 제약 (중요)
서버리스 함수 225MB 한계로 **opencv/numpy/pillow/torch/librosa 미포함**.
| 모듈 | 상태 |
| :--- | :--- |
| 텍스트 고증 검증 (`/scan/text`) | ✅ 정상 (AI 생성 어휘 다양도 + 팩트체크 + 선동성 + 출처) |
| URL 스캔 (`/scan/url`) | ✅ 정상 |
| 이미지/영상/오디오 (`/scan/media`) | ⚠️ 의존성 미포함 → 중립값 폴백(실제 탐지 안 됨) |
| 콜드스타트 / 타임아웃 | ⚠️ 유휴 후 첫 요청 수초 지연, 60s(Pro) 타임아웃 |

> **전체 멀티미디어(ELA/딥페이크/AI 복제 음성) 탐지가 필요하면** Vercel 대신
> **Render / Railway / Fly.io** 같은 컨테이너 호스트 사용 (`requirements.txt`에 opencv/numpy/pillow/librosa 추가 + `truthhistory_server:app` 그대로 구동, 의존성 한계 없음).

---

## 크롬 확장 프로그램 → 배포 URL 연결 (자동)
확장 프로그램은 `extension/background.js`의 `API_BASE` 상수가 배포 URL을 **직접 하드코딩**합니다.
- 배포 URL이 바뀌면 `API_BASE` 상수 하나만 수정
- 로컬 백엔드로 확장을 개발할 때는 `API_BASE = "http://localhost:8000"`으로 변경
- 사용자 측 설정(팝업)은 필요 없음 — 설치만 하면 ChatGPT/Claude/Gemini 어디서든 역사 할루시네이션 검증 동작

---

## 재배포 (코드 변경 시)
프로젝트는 이미 Vercel에 링크됨(`.vercel/project.json`). 코드 push 후:
```bash
vercel --prod --yes
```

## 로컬 개발
```bash
th api          # 백엔드 (http://localhost:8000)
npm run dev     # 프론트 (http://localhost:5173) → dev 모드이므로 localhost:8000 호출
```

---

## 트러블슈팅 기록 (참고)
- `uv lock` / `No project table` 에러 → `pyproject.toml`(Poetry)을 `.vercelignore`로 제외, `requirements.txt` 기반 빌드 유도.
- `Total bundle size 297MB exceeds 225MB` → opencv/numpy/pillow 제거(텍스트 중심 최소 의존성)로 해결.
