# -*- coding: utf-8 -*-
"""순수 numpy Haar 캐스케이드 안면 검출기 — OpenCV 없이 서버리스에서도
안면 비대칭(페이스 스왑) 각도를 정밀 분석하기 위한 자체 구현.

OpenCV `haarcascade_frontalface_default.xml`(Apache-2.0, OpenCV 프로젝트)을
`data/`에 내장하고, 적분영상 + 벡터화 단계 평가로 다중 스케일 검출을 수행한다.
정확도는 cv2.CascadeClassifier와 동일 캐스케이드 데이터를 쓰므로 등가이며,
속도는 거친 스트라이드(창 크기의 1/8)로 실시간성을 확보한다.
"""
import functools
import os
import xml.etree.ElementTree as ET
from typing import List, Tuple

import numpy as np

CASCADE_PATH = os.path.join(os.path.dirname(__file__), "data", "haarcascade_frontalface_default.xml")


@functools.lru_cache(maxsize=1)
def _load_cascade(path: str = CASCADE_PATH):
    root = ET.parse(path).getroot().find("cascade")
    base = int(root.findtext("width"))
    if int(root.findtext("height")) != base:
        raise ValueError("비정사각 기저 창은 지원하지 않음")

    stages = []  # [(stage_threshold, [(feature_idx, thr, left_val, right_val), ...])]
    for st in root.find("stages"):
        weaks = []
        for w in st.find("weakClassifiers"):
            nodes = w.findtext("internalNodes").split()
            feature_idx = int(nodes[2])
            thr = float(nodes[3])
            leaves = [float(v) for v in w.findtext("leafValues").split()]
            weaks.append((feature_idx, thr, leaves[0], leaves[1]))
        stages.append((float(st.findtext("stageThreshold")), weaks))

    features = []  # [ [(x, y, w, h, weight), ...], ... ] (tilted 미지원 → 예외)
    for f in root.find("features"):
        rects = []
        for rc in f.find("rects"):
            x, y, w, h, weight = rc.text.split()
            rects.append((int(x), int(y), int(w), int(h), float(weight)))
        if int(f.findtext("tilted")):
            raise ValueError("tilted 특징은 지원하지 않음")
        features.append(rects)

    return base, stages, features


def _integral(gray: np.ndarray) -> np.ndarray:
    ii = np.zeros((gray.shape[0] + 1, gray.shape[1] + 1), dtype=np.float64)
    ii[1:, 1:] = gray.astype(np.float64).cumsum(0).cumsum(1)
    return ii


def _detect_scale(ii: np.ndarray, win: int, base: int, stages, features,
                  stride: int) -> np.ndarray:
    """단일 스케일에서 캐스케이드를 통과한 창 좌표 (N, 4) 반환."""
    h, w = ii.shape[0] - 1, ii.shape[1] - 1
    step = max(1, stride)
    ys = np.arange(0, h - win + 1, step)
    xs = np.arange(0, w - win + 1, step)
    if not len(ys) or not len(xs):
        return np.zeros((0, 4), dtype=int)
    Y, X = np.meshgrid(ys, xs, indexing="ij")
    X, Y = X.ravel(), Y.ravel()

    ratio = win / base
    area = float(win * win)
    # 스케일별 특징 직사각형 오프셋 캐시 — (x0o, y0o, x1o, y1o, weight)
    offsets = {}

    def _feature_values(fidx, Xa, Ya):
        if fidx not in offsets:
            rects = []
            for rx, ry, rw, rh, weight in features[fidx]:
                x0 = int(round(rx * ratio)); y0 = int(round(ry * ratio))
                x1 = int(round((rx + rw) * ratio)); y1 = int(round((ry + rh) * ratio))
                rects.append((x0, y0, x1, y1, weight))
            offsets[fidx] = rects
        fv = np.zeros(len(Xa), dtype=np.float64)
        for x0o, y0o, x1o, y1o, weight in offsets[fidx]:
            fv += weight * (
                ii[Ya + y1o, Xa + x1o] - ii[Ya + y0o, Xa + x1o]
                - ii[Ya + y1o, Xa + x0o] + ii[Ya + y0o, Xa + x0o]
            )
        return fv / area

    alive_idx = np.arange(len(X))
    for stage_thr, weaks in stages:
        if not len(alive_idx):
            break
        Xa, Ya = X[alive_idx], Y[alive_idx]
        ssum = np.zeros(len(alive_idx), dtype=np.float64)
        for fidx, thr, lv, rv in weaks:
            fv = _feature_values(fidx, Xa, Ya)
            ssum += np.where(fv < thr, lv, rv)
        alive_idx = alive_idx[ssum >= stage_thr]

    if not len(alive_idx):
        return np.zeros((0, 4), dtype=int)
    return np.stack([X[alive_idx], Y[alive_idx],
                     np.full(len(alive_idx), win), np.full(len(alive_idx), win)], axis=1)


def _merge_boxes(boxes: np.ndarray, min_neighbors: int, limit: int) -> List[Tuple[int, int, int, int]]:
    """교차 박스 클러스터 병합(cv2 groupRectangles 대체) — 평균 위치로 반환."""
    if not len(boxes):
        return []
    order = np.argsort(-(boxes[:, 2] * boxes[:, 3]))
    boxes = boxes[order][:limit]
    used = np.zeros(len(boxes), bool)
    out = []
    for i in range(len(boxes)):
        if used[i]:
            continue
        grp = [boxes[i]]
        used[i] = True
        x1, y1, w1, h1 = boxes[i]
        for j in range(i + 1, len(boxes)):
            if used[j]:
                continue
            x2, y2, w2, h2 = boxes[j]
            ix = max(0, min(x1 + w1, x2 + w2) - max(x1, x2))
            iy = max(0, min(y1 + h1, y2 + h2) - max(y1, y2))
            inter = ix * iy
            if inter == 0:
                continue
            if inter / min(w1 * h1, w2 * h2) > 0.3:
                grp.append(boxes[j]); used[j] = True
        if len(grp) < min_neighbors:
            continue
        g = np.stack(grp).astype(float)
        out.append(tuple(int(round(v)) for v in g.mean(axis=0)))
    return out


def detect_faces(gray: np.ndarray, min_size: Tuple[int, int] = (48, 48),
                 scale_factor: float = 1.2, min_neighbors: int = 3) -> List[Tuple[int, int, int, int]]:
    """다중 스케일 Haar 안면 검출 — cv2.CascadeClassifier.detectMultiScale 상위 호환 경량판."""
    g = np.asarray(gray)
    if g.ndim != 2:
        raise ValueError("2차원 그레이스케일 영상만 지원")
    base, stages, features = _load_cascade()
    ii = _integral(g)
    h, w = g.shape

    found = []
    scale = 1.0
    while True:
        win = int(round(base * scale))
        if win > h or win > w:
            break
        if win >= min_size[0] and win >= min_size[1]:
            hits = _detect_scale(ii, win, base, stages, features,
                                 stride=max(1, win // 8))
            if len(hits):
                found.append(hits)
        if win >= min(h, w):
            break
        scale *= scale_factor
    if not found:
        return []
    return _merge_boxes(np.concatenate(found), min_neighbors=min_neighbors, limit=400)
