# -*- coding: utf-8 -*-
"""
역사 이미지 콘텐츠 분류기 (결정론 휴리스틱, 외부 의존성 없음).

확장 프로그램의 클라이언트 키워드 필터(alt/파일명/캡션)가 커버하지 못하는
'텍스트 신호가 전혀 없는 역사 이미지'를 서버 쪽에서 판별한다.

판별 신호 (모두 PIL만 사용 — 서버리스 Vercel 환경에서 cv2 없이 동작):
1. 파일명 키워드 — 한국사 인명·왕조·유물·문화재 용어 (강한 신호, 즉시 판정)
2. 세피아/유물 톤 — 낮은 채도 + 따뜻한 색조(황갈색) 우세 (고문서·회화·세피아 사진의 전형)
3. 흑백 우세 — 초기 사진·판화류 신호 (단독으로는 판정 불충분한 보조 신호)
4. 종이 질감 — 고채도 픽셀 거의 없음 + 난색조 + 종이색 밝기 대역

한계: 색채 기반 휴리스틱이므로 채도 높은 현대 재현 이미지(영화 스틸 등)는
점수가 낮게 나올 수 있다. 파일명 신호가 있으면 픽셀 점수와 무관하게 판정.
"""
import os
import re
from typing import Any, Dict

# 파일명·메타데이터 역사 키워드 (확장 content.js TH_HISTORY_RE와 동일 계열)
_HISTORY_KW_RE = re.compile(
    r"역사|사료|유물|유적|문화재|고궁|궁궐|왕|왕조|왕실|황제|세종|이순신|장군|조선|고조선"
    r"|고구려|백제|신라|가야|발해|고려|대한제국|개화기|일제|강점기|독립운동|의병|동학"
    r"|임진|병자|갑오|전투|전쟁|탑|불상|석굴|벽화|고분|갑옷|투구|도검|토기|청자|백자"
    r"|기와|목판|필사|고문서|교지|어보|국새|의궤|광화문|남대문|수원화성"
    r"|historical|history|dynasty|king|royal|emperor|joseon|chosun|goguryeo|baekje"
    r"|silla|goryeo|sejong|gwanggaeto|artifact|relic|heritage|temple|shrine|palace"
    r"|tomb|museum|medieval|armor|sword|scroll|annals|painting",
    re.IGNORECASE,
)

# 판정 임계값 — 픽셀 신호만으로 역사 이미지라 판단하는 최소 점수
_PIXEL_THRESHOLD = 0.55


def _filename_signal(path: str) -> bool:
    return bool(_HISTORY_KW_RE.search(os.path.basename(path)))


def _pixel_score(path: str) -> Dict[str, Any]:
    """HSV 통계 기반 세피아/흑백/종이질감 점수 (0.0 ~ 1.0) 및 근거 목록."""
    try:
        from PIL import Image, ImageStat
    except ImportError:
        return {"score": 0.0, "signals": ["PIL 미설치 — 픽셀 분석 불가"]}

    signals = []
    try:
        with Image.open(path) as im:
            im = im.convert("RGB").resize((128, 128))
            hsv = im.convert("HSV")
            stat = ImageStat.Stat(hsv)
            mean_s = stat.mean[1] / 255.0          # 평균 채도
            mean_v = stat.mean[2] / 255.0          # 평균 밝기
            hist = hsv.histogram()
    except Exception as e:
        return {"score": 0.0, "signals": [f"이미지 로드 실패: {e}"]}

    sat_hist = hist[256:512]                       # S 채널 256 bins
    sat_total = sum(sat_hist) or 1
    low_sat = sum(sat_hist[:97]) / sat_total       # S < ~38% (세피아·안정된 톤 포함)
    gray_sat = sum(sat_hist[:41]) / sat_total      # S < ~16% (사실상 무채색)
    high_sat = sum(sat_hist[128:]) / sat_total     # S > ~50% (현대 원색)
    hue_hist = hist[:256]                          # H 채널
    hue_total = sum(hue_hist) or 1
    warm = sum(hue_hist[14:32]) / hue_total        # 세피아 대역(황~갈색, 20-45°)

    score = 0.0
    # 세피아/유물 톤: 낮은 채도 + 난색조 우세 (고문서·회화·세피아 사진)
    if low_sat > 0.5 and warm > 0.25:
        score += 0.45
        signals.append(f"세피아/유물 톤 (저채도 {low_sat:.0%} · 난색조 {warm:.0%})")
    # 흑백 우세: 초기 사진·판화 — 단독으로는 판정 부족(보조 신호)
    if gray_sat > 0.85:
        score += 0.2
        signals.append(f"흑백 우세 (무채색 {gray_sat:.0%})")
    # 종이 질감: 원색 거의 없음 + 난색조 + 종이색 밝기 대역
    if high_sat < 0.05 and warm > 0.25 and 0.5 < mean_v < 0.95:
        score += 0.2
        signals.append(f"종이 질감 (고채도 {high_sat:.0%} 미만 · 난색조 {warm:.0%} · 밝기 {mean_v:.2f})")
    # 전반적 무채색 보정
    if mean_s < 0.12:
        score += 0.1
        signals.append(f"전반적 무채색 (평균 채도 {mean_s:.2f})")

    return {"score": min(score, 1.0), "signals": signals}


def classify_history_image(path: str) -> Dict[str, Any]:
    """
    이미지의 역사 콘텐츠 관련성 판별.

    반환: {"is_history": bool, "score": float, "signals": [str], "basis": str}
    - 파일명 키워드 → 즉시 판정 (score 0.9)
    - 픽셀 점수 ≥ 0.55 → 판정
    - 확장 프로그램은 is_history=False면 배지를 붙이지 않는다.
    """
    if _filename_signal(path):
        return {
            "is_history": True,
            "score": 0.9,
            "signals": ["파일명 역사 키워드"],
            "basis": "filename",
        }

    px = _pixel_score(path)
    return {
        "is_history": px["score"] >= _PIXEL_THRESHOLD,
        "score": round(px["score"], 2),
        "signals": px["signals"],
        "basis": "pixel",
    }
