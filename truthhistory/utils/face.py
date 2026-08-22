# -*- coding: utf-8 -*-
from typing import Any, Dict

import numpy as np

from truthhistory.base import LazyModuleImporter


def _detect_faces_dual(gray: np.ndarray, min_size=(48, 48)):
    """cv2 캐스케이드 우선, 미설치 시 자체 numpy Haar 검출기로 폴백."""
    try:
        cv2 = LazyModuleImporter.import_module("cv2", "image")
        cascade_path = cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
        classifier = cv2.CascadeClassifier(cascade_path)
        faces = classifier.detectMultiScale(
            gray, scaleFactor=1.1, minNeighbors=5, minSize=min_size
        )
        return [tuple(int(v) for v in f) for f in faces]
    except ImportError:
        from truthhistory.utils.haar import detect_faces
        return detect_faces(gray, min_size=min_size, scale_factor=1.2, min_neighbors=3)


def _resize_64(face: np.ndarray) -> np.ndarray:
    """64x64 최근접 리샘플(cv2.resize 대체 — numpy 인덱싱)."""
    h, w = face.shape
    if h < 2 or w < 2:
        raise ValueError("안면 영역이 너무 작음")
    ys = np.clip((np.arange(64) * (h - 1) / 63).round().astype(int), 0, h - 1)
    xs = np.clip((np.arange(64) * (w - 1) / 63).round().astype(int), 0, w - 1)
    return face[ys][:, xs].astype(np.float32)


def face_asymmetry_score(gray: Any) -> Dict[str, Any]:
    """
    Haar Cascade로 얼굴을 검출한 뒤, 좌우 반전 대칭 편차를 측정하여
    페이스 스왑(딥페이크) 의심 점수를 산출하는 경량 휴리스틱.

    * 얼굴이 검출되지 않으면 중립값(asymmetry_score=0.0)을 반환한다.
    * 합성/스왑된 얼굴은 좌우 홍채 반사·랜드마크 정렬이 어긋나 평균 픽셀 편차가 커지는
      경향을 이용하며, 이 값은 판정 근거(XAI)로 그대로 노출된다.
    * OpenCV가 없으면 자체 numpy Haar 검출기(서버리스)로 폴백 — numpy만 필수.
    """
    gray = np.asarray(gray)
    if gray.ndim != 2:
        raise ValueError("2차원 그레이스케일 영상만 지원")

    faces = _detect_faces_dual(gray)

    if len(faces) == 0:
        return {"is_deepfake_suspect": False, "asymmetry_score": 0.0, "detected_faces": 0}

    # 가장 큰 얼굴 영역 선택 후 64x64로 정규화
    x, y, w, h = max(faces, key=lambda f: f[2] * f[3])
    face = _resize_64(gray[y:y + h, x:x + w])

    # 좌반부와 우반부(수평 반전 = 슬라이싱 역순)의 평균 절대 편차 → 비대칭 지수
    left = face[:, :32]
    right_mirrored = face[:, 32:][:, ::-1]
    raw_asymmetry = float(np.mean(np.abs(left - right_mirrored))) / 255.0

    # 내부 얼굴 밴드(눈~코, rows 16-48, 내부 32px) — 머리카락·배경·조명 그림자 제외한
    # 순수 안면 영역의 편차. 실측 기준(위키미디어 실존 인물 사진 6종):
    #   전체 박스 0.107~0.387 · 내부 0.065~0.336 — 실제 인물은 안면 비대칭이 필연적으로 존재
    inner = face[16:48, 16:48]
    inner_asymmetry = float(np.mean(np.abs(inner[:, :16] - inner[:, 16:][:, ::-1]))) / 255.0

    # 과대칭 판정 — GAN/Diffusion 완전 합성 얼굴은 실제 인물보다 훨씬 대칭에 가깝다.
    # 실측 최소값(전체 0.107 / 내부 0.065)에 안전 마진을 둔 임계값.
    synthetic_symmetry = raw_asymmetry < 0.07 and inner_asymmetry < 0.06

    # 0.25 평균 편차를 최대 의심 기준으로 정규화 (0.0 ~ 1.0)
    score = min(raw_asymmetry / 0.25, 1.0)

    # 유효 의심 점수 — ① 스왑형 비대칭(score>0.5) ② 완전 합성형 과대칭(0.85 고정)
    effective = max(score, 0.85) if synthetic_symmetry else score

    return {
        "is_deepfake_suspect": bool(effective > 0.5),
        "asymmetry_score": round(score, 4),
        "detected_faces": int(len(faces)),
        "raw_asymmetry": round(raw_asymmetry, 4),
        "inner_asymmetry": round(inner_asymmetry, 4),
        "synthetic_symmetry": bool(synthetic_symmetry),
    }
