# Truth History SDK: 한국사 텍스트 고증 검증(Text Analyzer) 상세 구현 설계서

생성형 AI의 발전은 그럴듯하지만 허위인 한국 역사 서술(역사 할루시네이션)을 대량으로 생성·확산시키는 리스크를 낳고 있다. 본 문서는 `TextAnalyzer` 모듈이 이 위험에 어떻게 대응하는지를 상술합니다.

- **(1) AI 생성 탐지**: 텍스트의 AI 생성 여부를 Perplexity/Burstiness 통계로 정량화한다.
- **(2) 역사적 정합성 검증**: 검증 대상 텍스트를 권위 있는 한국사 사료·팩트체크(국사편찬위원회, 교과서, 사료 데이터베이스 등)와 교차 검증하여 역사적 정합성을 평가한다.

본 모듈은 4대 탐지 모듈 중 **텍스트 고증 검증**을 담당하며, ELA 이미지 합성 탐지·딥페이크 페이스 스왑 탐지·AI 복제 음성 탐지 모듈과 함께 단일 SDK의 텍스트·시청각 교차 검증 파이프라인을 구성합니다. 경량 로컬 추론과 외부 API 연동의 혼합 설계하에 동작하며, 판정 근거는 XAI 리포트(JSON)로 투명하게 제공합니다.

---

## 1. AI 생성 탐지 핵심 알고리즘 및 구현

AI가 생성한 텍스트는 사람이 작성한 텍스트에 비해 단어의 예측 가능성(Perplexity)이 매우 높고, 문장별 길이 및 복잡도의 기복(Burstiness)이 적습니다. 본 모듈은 이 두 지표로 한국사 텍스트의 AI 생성 가능성을 정량화합니다.

> **한국어·한국사 문맥 특화**: 영어 중심의 범용 언어모델(예: GPT-2)은 한글 토크나이징과 역사 도메인 용어 분포를 제대로 반영하지 못합니다. 따라서 한국어 언어모델(Korean LM)과 한국사 코퍼스로 추가 학습된 모델을 전제로 하며, 임계값 보정 역시 한국사 서술의 통계적 특성에 맞춰 적용되어야 합니다.

### 1.1 Perplexity (PPL) 계산 수식
Perplexity는 주어진 모델이 해당 문장을 예측할 때의 곤혹도로서, 아래 수식과 같이 손실값(Cross Entropy)의 지수함수로 계산됩니다.

$$PPL(W) = P(w_1, w_2, \dots, w_N)^{-\frac{1}{N}} = \exp\left( -\frac{1}{N} \sum_{i=1}^{N} \log P(w_i \mid w_{<i}) \right)$$

### 1.2 Burstiness 계산 수식
Burstiness는 각 문장별 Perplexity 값들의 표준편차($\sigma_{PPL}$)와 평균($\mu_{PPL}$)의 비율(변동계수, Coefficient of Variation)로 정의하여, 텍스트 전반의 다양성을 수치화합니다.

$$Burstiness = \frac{\sigma_{PPL}}{\mu_{PPL}}$$

### 1.3 파이썬 구현 예시 (Hugging Face Transformers 기반)

```python
import math
from typing import List
from truthhistory.architecture import LazyModuleImporter

class AIGenerationDetector:
    def __init__(self, model_name: str = "gpt2"):
        self.torch = LazyModuleImporter.import_module("torch", "text")
        transformers = LazyModuleImporter.import_module("transformers", "text")
        
        self.tokenizer = transformers.AutoTokenizer.from_pretrained(model_name)
        self.model = transformers.AutoModelForCausalLM.from_pretrained(model_name)
        
        if self.torch.cuda.is_available():
            self.model = self.model.to("cuda")

    def calculate_sentence_ppl(self, sentence: str) -> float:
        """
        단일 문장의 Perplexity를 산출합니다.
        """
        encodings = self.tokenizer(sentence, return_tensors="pt")
        input_ids = encodings.input_ids
        
        if self.torch.cuda.is_available():
            input_ids = input_ids.to("cuda")
            
        target_ids = input_ids.clone()
        
        with self.torch.no_grad():
            outputs = self.model(input_ids, labels=target_ids)
            neg_log_likelihood = outputs.loss
            
        return math.exp(neg_log_likelihood.item())

    def detect(self, text: str) -> dict:
        """
        전체 텍스트의 PPL 평균 및 Burstiness를 측정하여 AI 확률을 결정합니다.
        """
        # 문장 단위 분할
        sentences = [s.strip() for s in text.split(".") if len(s.strip()) > 5]
        if not sentences:
            return {"ai_probability": 0.5, "perplexity": 0.0, "burstiness": 0.0}
            
        ppls = [self.calculate_sentence_ppl(s) for s in sentences]
        
        mean_ppl = sum(ppls) / len(ppls)
        variance = sum((x - mean_ppl) ** 2 for x in ppls) / len(ppls)
        std_ppl = math.sqrt(variance)
        
        # Burstiness (변동계수)
        burstiness = std_ppl / mean_ppl if mean_ppl > 0 else 0
        
        # AI 생성 판별 확률 매핑 (낮은 PPL과 낮은 Burstiness 일 때 높은 AI 확률 도출)
        ai_probability = 1.0 - (1.0 / (1.0 + math.exp(-(mean_ppl - 40) / 10)))
        ai_probability = ai_probability * (1.0 - min(burstiness, 1.0))
        
        return {
            "ai_probability": round(ai_probability, 4),
            "perplexity": round(mean_ppl, 2),
            "burstiness": round(burstiness, 4)
        }
```

---

## 2. 외부 API 연동 설계

AI 생성 탐지와 더불어, 검증 대상 한국사 텍스트가 **권위 있는 역사 사료·팩트체크**와 정합성을 갖는지 평가하기 위해 외부 API를 연동합니다. Google Fact Check API는 사료·팩트체크 데이터베이스에서 일치하는 클레임을 검색하고, LLM(Gemini/OpenAI GPT)은 수집된 참조 문서(국사편찬위원회 자료, 교과서 서술, 디지털 사료 등)와 텍스트 간 주장 정합성을 자연어 추론으로 평가합니다. 두 결과는 경량 로컬 추론과 외부 API 연동의 혼합 설계 하에서 취합되어, 픽셀/주파수 기반의 시청각 모듈과 함께 XAI 판정 근거로 제공됩니다.

### 2.0 다중 검색 증거 계층 (구현됨 — `truthhistory/text/evidence.py`)
`analyze_fact_consistency`는 주장에서 키워드(한국어 조사 자동 제거)를 추출해 여러 검색 소스를 **병렬**로 조회하고, 수집된 증거 스니펫 대비 **키워드 커버리지 + 상충 단서**로 정합성 점수를 산출한다. 증거가 없으면 중립(0.5), 상충 단서(거짓·허위·왜곡 등) 발견 시 정합성을 0.4 이하로 상한한다.

| 소스 | 키 필요 | 비고 |
| :--- | :--- | :--- |
| **한국어 위키백과 검색 API** (`ko.wikipedia.org/w/api.php`) | ❌ 불필요 | 1순위 무료 소스, 한국사 사료 정합성에 가장 효과적 |
| **DuckDuckGo** (Instant Answer API + HTML 스크립트) | ❌ 불필요 | 보조 소스 |
| **Naver Search API** (`openapi.naver.com`) | ✅ `NAVER_CLIENT_ID/SECRET` | 한국어 웹결과 특화 |
| **Google Fact Check API** | ✅ `FACT_CHECK_API_KEY` | 기존 팩트체크 데이터베이스 |

```python
from truthhistory.text.evidence import gather_evidence, score_consistency

# 병렬 증거 수집 → 정합성 점수 산출 (키 불필요 소스만으로도 동작)
evidence = gather_evidence(query, naver_client_id=None, naver_client_secret=None)
result = score_consistency(text, evidence)
# → {"consistency_score": 0.775, "best_coverage": 0.75, "contradiction": False, ...}
```

> 키 불필요 소스(위키백과·DuckDuckGo)만으로 기본 정합성 검증이 동작하므로, 클라우드 서버리스(Vercel)에서도 추가 설정 없이 정확도가 향상된다.

### 2.1 Google Fact Check Explorer API 연동
주요 팩트체크 및 역사 사료 데이터베이스를 쿼리하여, 검증 대상 주장과 일치하는 클레임이 기존에 팩트체크된 내역이 있는지 검색합니다.

```python
import urllib.parse
import requests

def search_fact_check_claims(query: str, api_key: str) -> list:
    """
    Google Fact Check Tool API를 조회하여 팩트체크 내역을 가져옵니다.
    """
    encoded_query = urllib.parse.quote(query)
    url = f"https://factchecktools.googleapis.com/v1alpha1/claims:search?query={encoded_query}&key={api_key}"
    
    response = requests.get(url)
    if response.status_code != 200:
        raise RuntimeError(f"Google FactCheck API Error: {response.text}")
        
    data = response.json()
    claims = data.get("claims", [])
    
    parsed_claims = []
    for claim in claims:
        parsed_claims.append({
            "text": claim.get("text"),
            "claimant": claim.get("claimant"),
            "review": claim.get("claimReview", [{}])[0].get("textualRating")
        })
    return parsed_claims
```

### 2.2 LLM을 활용한 정합성 판별 (Gemini API 예시)
```python
import google.generativeai as genai

def evaluate_fact_consistency_with_gemini(text: str, context_documents: str, api_key: str) -> float:
    """
    수집된 역사 사료 레퍼런스 문서들과 검증 대상 텍스트 간의 주장 정합성을 LLM으로 평가합니다.
    """
    genai.configure(api_key=api_key)
    model = genai.GenerativeModel('gemini-1.5-flash')
    
    prompt = f"""
    아래 [검증 대상 텍스트]가 [참조 데이터](국사편찬위원회·교과서·사료 등 권위 있는 역사 사료)의 역사적 사실 정보와 얼마나 일치하는지 평가해라.
    오로지 0.0(완벽히 거짓/모순됨)에서 1.0(완벽히 사실이며 일치함) 사이의 실수값 하나만 반환하라.
    
    [참조 데이터]
    {context_documents}
    
    [검증 대상 텍스트]
    {text}
    """
    response = model.generate_content(prompt)
    try:
        score = float(response.text.strip())
        return score
    except ValueError:
        return 0.5  # 파싱 실패 시 기본 중간값 반환
```

---

## 3. 단위 테스트 및 모킹(Mocking) 가이드

외부 API 호출 비용과 검증 비결정성을 제거하기 위해, 테스트 시에는 `unittest.mock`을 활용해 API 응답을 모킹하도록 설계합니다. 이를 통해 역사 사료 기반 정합성 판정 역시 결정론적으로 검증할 수 있습니다.

```python
import unittest
from unittest.mock import patch
from truthhistory.text.analyzer import TextAnalyzer

class TestTextAnalyzer(unittest.TestCase):
    def setUp(self):
        self.config = {
            "backend": "remote",
            "api_key": "dummy_key",
            "weights": {"fact_weight": 0.5, "sensationalism_weight": 0.5}
        }
        self.analyzer = TextAnalyzer(self.config)

    @patch("truthhistory.text.analyzer.search_fact_check_claims")
    @patch("truthhistory.text.analyzer.evaluate_fact_consistency_with_gemini")
    def test_analyze_with_mocked_apis(self, mock_gemini, mock_factcheck):
        # 모킹 반환값 설정
        mock_factcheck.return_value = [{"text": "테스트 클레임", "review": "거짓"}]
        mock_gemini.return_value = 0.1  # 거짓에 가깝게 평가
        
        result = self.analyzer.analyze("실제 검사할 텍스트 본문")
        
        self.assertTrue(result.is_manipulated)
        self.assertLess(result.credibility_score, 0.4)
        self.assertIn("주장과 권위 있는 역사 사료 간의 불일치 다수 발견", result.reasons)

if __name__ == "__main__":
    unittest.main()
```
