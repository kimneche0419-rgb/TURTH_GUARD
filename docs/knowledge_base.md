# 📜 한국사 사료 지식베이스(오프라인 고증 계층) 구현 상세

> 모듈: `truthhistory/text/knowledge.py` · 테스트: `tests/test_knowledge.py`

## 1. 목적

LLM 역사 할루시네이션의 가장 흔한 패턴은 **"그럴듯한 사건/인물 + 틀린 연도"** 조합입니다(예: *"임진왜란은 1920년에 발발했다"*). 외부 검색 증거는 네트워크·API 키·지연에 의존하므로, Truth History SDK는 **국사편찬위원회 「한국사연표」 기반으로 큐레이션한 사건 연표와 인물 생존/활동 연도를 SDK에 내장**하여 네트워크 없이 즉시 결정론 판정을 제공합니다.

## 2. 내장 데이터

| 데이터셋 | 내용 | 규격 |
|:---|:---|:---|
| `_TIMELINE` | 고구려 건국(기원전 37년) ~ 남북정상회담까지 주요 사건 | `{event, start, end, aliases[]}` |
| `_FIGURES` | 이순신·세종·안중근 등 주요 인물 | `{name, birth, death}` 또는 활동기 `{active_start, active_end}` |

별칭(`aliases`)으로 표기 변형(세종대왕/세종, 한글/훈민정음, 6·25/한국전쟁)을 흡수합니다.

## 3. 핵심 API

### `verify_chronology(text) -> Dict`
문장(`.!?\n` 분리) 단위로 다음을 추출·교차 검증합니다.

1. **연도 언급**: `N년`(기원전 포함, 1~2100 범위) — `extract_year_mentions`
2. **세기 언급**: `N세기` → 100년 구간 — `extract_century_mentions`
3. **사건/인물 매칭**: 사건명 구성 토큰이 모두 문장에 있으면 매칭(조사 개입 `"고구려가 건국되었다"` 흡수)

판정 규칙:
- 사건: 연도가 `[start-1, end+1]` 구간 내 → **verified**, 밖 → **contradiction**
- 인물: 연도가 생존/활동기 내 → **verified**, 밖 → **contradiction**(시대착오)
- 연도 언급이 없으면 판정하지 않음(과신 방지)

### `search_knowledge_base(query) -> List[Evidence]`
키워드 겹침 기반으로 KB 항목을 `truthhistory-kb` 소스 증거로 반환. `gather_evidence()`의 **1순위 로컬 증거 소스**로 위키백과·DuckDuckGo와 병렬 병합됩니다.

## 4. 스코어링 통합 (`TextAnalyzer.analyze_fact_consistency`)

| 결과 | 정합성 점수 | 근거(reasons) |
|:---|:---|:---|
| 연표 상충 있음 | `min(score, 0.2)` + `contradiction=True` | "한국사 연표 KB 검증 상충 — …" |
| 검증 일치만 있음 | `+0.05` 가산 | "한국사 연표 KB 검증 일치(N건)" |

## 5. 사용 예

```python
from truthhistory.text.knowledge import verify_chronology
verify_chronology("임진왜란은 1920년에 일어났다")
# {'contradiction_count': 1, 'contradictions': [{'subject': '임진왜란', 'claim_year': 1920, 'expected': [1592, 1598], ...}]}
```
