# -*- coding: utf-8 -*-
from typing import Any, Dict

from truthhistory.base import LazyModuleImporter


def face_asymmetry_score(gray: Any) -> Dict[str, Any]:
    """
    OpenCV Haar Cascade로 얼굴을 검출한 뒤, 좌우 반전 대칭 편차를 측정하여
    페이스 스왑(딥페이크) 의심 점수를 산출하는 경량 휴리스틱.

    * 얼굴이 검출되지 않으면 중립값(asymmetry_score=0.0)을 반환한다.
    * 합성/스왑된 얼굴은 좌우 홍채 반사·랜드마크 정렬이 어긋나 평균 픽셀 편차가 커지는
      경향을 이용하며, 이 값은 판정 근거(XAI)로 그대로 노출된다.
    * OpenCV/numpy 의존성은 호출 시점에 지연 로딩된다.
    """
    cv2 = LazyModuleImporter.import_module("cv2", "image")
    np = LazyModuleImporter.import_module("numpy", "image")

    cascade_path = cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
    classifier = cv2.CascadeClassifier(cascade_path)
    faces = classifier.detectMultiScale(
        gray, scaleFactor=1.1, minNeighbors=5, minSize=(48, 48)
    )

    if len(faces) == 0:
        return {"is_deepfake_suspect": False, "asymmetry_score": 0.0, "detected_faces": 0}

    # 가장 큰 얼굴 영역 선택 후 64x64로 정규화
    x, y, w, h = max(faces, key=lambda f: f[2] * f[3])
    face = gray[y:y + h, x:x + w]
    face = cv2.resize(face, (64, 64))

    # 좌반부와 우반부(수평 반전)의 평균 절대 편차 → 비대칭 지수
    left = face[:, :32].astype(np.float32)
    right_mirrored = cv2.flip(face[:, 32:], 1).astype(np.float32)
    raw_asymmetry = float(np.mean(np.abs(left - right_mirrored))) / 255.0

    # 0.25 평균 편차를 최대 의심 기준으로 정규화 (0.0 ~ 1.0)
    score = min(raw_asymmetry / 0.25, 1.0)

    return {
        "is_deepfake_suspect": bool(score > 0.5),
        "asymmetry_score": round(score, 4),
        "detected_faces": int(len(faces)),
        "raw_asymmetry": round(raw_asymmetry, 4),
    }
