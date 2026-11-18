"""Horizontal -> vertical reframing with OpenCV face tracking.

Pass 1 samples the clip a few times per second, detects faces and scene cuts,
and turns that into a smooth per-frame horizontal crop position (a virtual
camera that only pans when the subject leaves a dead zone, and hard-cuts with
the edit). Pass 2 (``render.py``) applies those positions frame by frame.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

TARGET_W, TARGET_H = 1080, 1920
ASPECT = TARGET_W / TARGET_H  # 9:16


@dataclass
class CropPlan:
    src_w: int
    src_h: int
    crop_w: int
    crop_h: int
    y: int
    xs: np.ndarray  # left edge of the crop for every frame
    faces_found: int
    samples: int
    cuts: int
    detector: str = "none"

    def x_at(self, frame_index: int) -> int:
        if len(self.xs) == 0:
            return (self.src_w - self.crop_w) // 2
        return int(self.xs[min(frame_index, len(self.xs) - 1)])


def crop_box(src_w: int, src_h: int) -> tuple[int, int]:
    """Largest 9:16 box that fits the source (even dimensions)."""
    if src_w / src_h > ASPECT:
        ch = src_h
        cw = int(round(src_h * ASPECT))
    else:
        cw = src_w
        ch = int(round(src_w / ASPECT))
    return cw - cw % 2, ch - ch % 2


def is_vertical(src_w: int, src_h: int) -> bool:
    return src_w / src_h <= ASPECT * 1.05


YUNET_URL = (
    "https://media.githubusercontent.com/media/opencv/opencv_zoo/main/models/"
    "face_detection_yunet/face_detection_yunet_2023mar.onnx"
)
YUNET_SHA256 = "8f2383e4dd3cfbb4553ea8718107fc0423210dc964f9f4280604804ed2552fa4"


def _yunet_model() -> str | None:
    """Path to the YuNet face model, downloading it once into ~/.cache."""
    import hashlib
    import os
    import urllib.request
    from pathlib import Path

    override = os.environ.get("THINK2ACT_YUNET_MODEL")
    if override:
        return override
    path = Path.home() / ".cache" / "think2act-reels" / "face_detection_yunet_2023mar.onnx"
    if not path.exists():
        path.parent.mkdir(parents=True, exist_ok=True)
        try:
            with urllib.request.urlopen(YUNET_URL, timeout=30) as r:
                data = r.read()
        except Exception:
            return None
        if hashlib.sha256(data).hexdigest() != YUNET_SHA256:
            return None
        path.write_bytes(data)
    return str(path)


class FaceDetector:
    """YuNet (OpenCV DNN) when available, Haar cascades as a fallback."""

    def __init__(self):
        import cv2

        self.kind = "none"
        model = _yunet_model() if hasattr(cv2, "FaceDetectorYN") else None
        if model:
            self.yunet = cv2.FaceDetectorYN.create(model, "", (320, 320), 0.7, 0.3, 50)
            self.kind = "yunet"
        elif hasattr(cv2, "CascadeClassifier"):
            base = cv2.data.haarcascades
            self.front = cv2.CascadeClassifier(base + "haarcascade_frontalface_default.xml")
            self.profile = cv2.CascadeClassifier(base + "haarcascade_profileface.xml")
            self.kind = "haar"

    def __call__(self, frame, min_size: int) -> list[tuple[float, float, float, float]]:
        import cv2

        if self.kind == "yunet":
            h, w = frame.shape[:2]
            self.yunet.setInputSize((w, h))
            _, faces = self.yunet.detect(frame)
            if faces is None:
                return []
            return [tuple(f[:4]) for f in faces if f[2] >= min_size * 0.6]
        if self.kind == "haar":
            gray = cv2.equalizeHist(cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY))
            size = (min_size, min_size)
            faces = list(self.front.detectMultiScale(gray, 1.1, 6, minSize=size))
            if not faces:
                faces = list(self.profile.detectMultiScale(gray, 1.1, 6, minSize=size))
            if not faces:  # the profile cascade only knows one side; try the mirror image
                w = gray.shape[1]
                faces = [(w - x - fw, y, fw, fh) for (x, y, fw, fh)
                         in self.profile.detectMultiScale(cv2.flip(gray, 1), 1.1, 6, minSize=size)]
            return [tuple(map(float, f)) for f in faces]
        return []


def _hist(frame):
    import cv2

    hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
    h = cv2.calcHist([hsv], [0, 1], None, [32, 32], [0, 180, 0, 256])
    return cv2.normalize(h, h).flatten()


def _median(values: np.ndarray, k: int = 5) -> np.ndarray:
    if len(values) < 3:
        return values
    k = min(k, len(values) if len(values) % 2 else len(values) - 1)
    pad = k // 2
    padded = np.pad(values, pad, mode="edge")
    return np.array([np.median(padded[i : i + k]) for i in range(len(values))])


def plan(video_path: str, mode: str = "face", sample_fps: float = 5.0) -> CropPlan:
    """Build a crop plan. ``mode`` is 'face' (track speaker) or 'center'."""
    import cv2

    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        raise RuntimeError(f"OpenCV could not open {video_path}")
    src_w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    src_h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
    n_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    cw, ch = crop_box(src_w, src_h)
    y = (src_h - ch) // 2
    max_x = src_w - cw

    if mode == "center" or max_x <= 0:
        cap.release()
        xs = np.full(max(n_frames, 1), max_x // 2, dtype=np.int32)
        return CropPlan(src_w, src_h, cw, ch, y, xs, 0, 0, 0)

    detect = FaceDetector()
    step = max(1, int(round(fps / sample_fps)))
    scale = 480 / src_w if src_w > 480 else 1.0
    min_size = max(24, int(src_h * scale * 0.08))

    sample_idx: list[int] = []
    centers: list[float] = []  # NaN when no face
    cut_after: list[bool] = []
    prev_hist = None
    prev_center = None
    found = 0
    idx = 0
    while True:
        ok = cap.grab()
        if not ok:
            break
        if idx % step == 0:
            ok, frame = cap.retrieve()
            if not ok:
                break
            small = cv2.resize(frame, None, fx=scale, fy=scale) if scale != 1.0 else frame
            hist = _hist(small)
            is_cut = prev_hist is not None and cv2.compareHist(prev_hist, hist, cv2.HISTCMP_CORREL) < 0.55
            prev_hist = hist
            if is_cut:
                prev_center = None
            faces = detect(small, min_size)
            center = float("nan")
            if faces:
                found += 1
                biggest = max(f[2] * f[3] for f in faces)
                big = [f for f in faces if f[2] * f[3] >= 0.6 * biggest]
                if prev_center is not None:
                    pick = min(big, key=lambda f: abs((f[0] + f[2] / 2) / scale - prev_center))
                else:
                    pick = max(big, key=lambda f: f[2] * f[3])
                center = (pick[0] + pick[2] / 2) / scale
                prev_center = center
            sample_idx.append(idx)
            centers.append(center)
            cut_after.append(is_cut)
        idx += 1
    cap.release()
    n_frames = max(idx, 1)

    xs = np.empty(n_frames, dtype=np.float64)
    if not sample_idx:
        xs[:] = max_x / 2
        return CropPlan(src_w, src_h, cw, ch, y, xs.astype(np.int32), 0, 0, 0)

    # Split samples into shots at detected cuts.
    shots: list[tuple[int, int]] = []
    s0 = 0
    for i in range(1, len(sample_idx)):
        if cut_after[i]:
            shots.append((s0, i))
            s0 = i
    shots.append((s0, len(sample_idx)))

    deadzone = 0.06 * src_w
    for si, (a, b) in enumerate(shots):
        c = np.array(centers[a:b], dtype=np.float64)
        if np.all(np.isnan(c)):
            c[:] = src_w / 2
        else:  # fill gaps with nearest known face position
            known = np.where(~np.isnan(c))[0]
            c = np.interp(np.arange(len(c)), known, c[known])
        c = _median(c)
        f_start = sample_idx[a]
        f_end = sample_idx[b] if b < len(sample_idx) else n_frames
        frames = np.arange(f_start, f_end)
        target = np.interp(frames, np.array(sample_idx[a:b]), c)
        cam = target[0]
        for k, fi in enumerate(frames):
            err = target[k] - cam
            if abs(err) > deadzone:
                cam += (err - np.sign(err) * deadzone) * 0.12
            xs[fi] = cam
    xs = np.clip(xs - cw / 2, 0, max_x)
    return CropPlan(src_w, src_h, cw, ch, y, xs.round().astype(np.int32), found, len(sample_idx),
                    len(shots) - 1, detect.kind)
