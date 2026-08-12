# Truth History SDK — 배포 가이드 (Vercel)

> **현재 상태(오늘):** Vercel 배포용 구성 파일은 모두 준비·커밋 완료. 서버리스 대응 패치(읽기전용 FS)도 적용됨.
> **내일 남은 일:** Vercel 계정 연결 + 환경변수 1개 + 배포 명령 1줄.

---

## 아키텍처 (Vercel 단일 프로젝트)
- **프론트엔드**(React/Vite 대시보드) → 정적 호스팅
- **백엔드**(FastAPI) → `api/index.py` Python 서버리스 함수
- `vercel.json`: `/api/v1/*` 만 서버리스 함수로 라우팅, 나머지 경로는 정적 프론트 → **같은 도메인, CORS 이슈 없음**

### 준비된 파일 (이미 커밋됨)
| 파일 | 역할 |
| :--- | :--- |
| `requirements.txt` | 서버리스 백엔드 의존성(경량: torch/librosa 제외) |
| `api/index.py` | FastAPI 앱을 ASGI 서버리스 함수로 노출 |
| `vercel.json` | `/api/v1/*` 라우팅 rewrite |
| `.vercelignore` | `.venv`/`node_modules`/`tests` 등 배포 제외 |
| `src/vite-env.d.ts` | `import.meta.env` 타입 |
| `src/App.tsx` | `VITE_API_URL` 환경변수 기반 API 호출(기본 localhost:8000) |
| 서버/ELA 패치 | `uploads`·ELA 임시파일을 `/tmp`로 → 읽기전용 FS 대응 |

---

## 내일 배포 절차 (3단계)

### 1. Vercel 로그인 (최초 1회)
```bash
vercel login
```
→ 안내된 코드를 https://vercel.com/device 에서 입력해 본인 계정 연결.

### 2. 프로젝트 연결 + 환경변수
```bash
vercel link          # 현재 디렉터리를 Vercel 프로젝트로 연결
vercel               # 최초 Preview 배포 → 배포 URL 획득 (예: https://truth-history-xxx.vercel.app)
```
프론트가 같은 도메인 백엔드를 가리키도록 환경변수 설정(배포된 최종 URL 사용):
```bash
vercel env add VITE_API_URL production
# 값 입력: https://truth-history-xxx.vercel.app  (위에서 받은 프로덕션 URL)
```

### 3. 프로덕션 배포
```bash
vercel --prod
```
출력된 URL로 확인:
- `https://<url>/` → React 대시보드
- `POST https://<url>/api/v1/scan/text` (body: `{"text":"..."}`) → XAI JSON 리포트

> 프로덕션 URL이 확정되면 `VITE_API_URL` 값을 그 URL로 맞추고 다시 `vercel --prod` 한 번 더.

---

## 배포 후: 크롬 확장 프로그램 연결
1. `chrome://extensions` → 🛡️ 확장 카드의 "세부정보" 또는 팝업
2. 팝업의 **API 엔드포인트**를 `https://<배포된-URL>` 로 변경 → **설정 저장**
3. (host_permissions는 `http://*/*`, `https://*/*` 로 열려 있어 재로드만 하면 어떤 배포 URL이든 즉시 호출 가능)

---

## 서버리스 지원 범위 / 제약
| 모듈 | 상태 |
| :--- | :--- |
| 텍스트 고증 검증 (`/scan/text`) | ✅ 정상 (어휘 다양도 휴리스틱) |
| URL 스캔 (`/scan/url`) | ✅ 정상 |
| 이미지 ELA/FFT/안면대칭 (`/scan/media`) | ✅ 정상 (opencv-headless 포함) |
| 비디오 temporal jitter/안면 | ✅ 정상 |
| 오디오 스펙트럼(MFCC/HNR) | ⚠️ librosa 미포함 → 중립값 폴백 (키워드 문맥 분석은 동작) |
| 콜드스타트 / 타임아웃 | ⚠️ 유휴 후 첫 요청 수초 지연, 10s(Hobby)/60s(Pro) |

> 전체 멀티미디어·장시간 처리·상시 구동이 필요하면 **Render/Railway/Fly.io** 컨테이너 권장
> (`Dockerfile` + `truthhistory_server:app` 그대로 구동, 의존성 제한 없음).

---

## 로컬 개발 (기존 그대로)
프론트 dev 서버는 기본적으로 로컬 백엔드(`http://localhost:8000`)를 호출.
```bash
th api            # 백엔드
npm run dev       # 프론트(http://localhost:5173) → localhost:8000 호출
```
원하면 프로젝트 루트 `.env.local` 에 `VITE_API_URL=http://localhost:8000` 명시 가능.

---

## 체크리스트 (내일)
- [ ] `vercel login`
- [ ] `vercel link`
- [ ] `vercel`(preview) → URL 확인
- [ ] `vercel env add VITE_API_URL production` → URL 입력
- [ ] `vercel --prod`
- [ ] 대시보드 + `/api/v1/scan/text` 동작 확인
- [ ] 크롬 확장 팝업 API 주소 → 배포 URL로 변경
