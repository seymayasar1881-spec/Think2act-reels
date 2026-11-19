"""Prepare photos and video clips for the reel.

- Photos: face-aware crop (9:16 backgrounds at 106% of frame, 5:4 prints), look L2 grade.
- Videos: HDR (HLG) -> SDR Rec.709 tone-map, trim, 1080x1920 @ 30 fps, look L2 grade.

usage: python tools/prep.py <source-media-dir>
  <source-media-dir> holds full/<key>.jpg and vid/<key>.<ext> downloaded from Drive.
"""

import json
import subprocess
import sys
from pathlib import Path

import cv2
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "reels"))
from think2act_reels.reframe import FaceDetector  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
IMG, VID = ROOT / "assets" / "img", ROOT / "assets" / "vid"
GRADE = "eq=contrast=1.06:saturation=1.08,hue=h=-4"
TONEMAP = ("zscale=t=linear:npl=203,format=gbrpf32le,zscale=p=bt709,"
           "tonemap=hable:desat=0,zscale=t=bt709:m=bt709:r=tv,format=yuv420p")

BACKGROUNDS = ["Kastamonu4", "Trabzon3", "Duzce15", "Usak5", "Usak16", "Aksehir9", "Aksehir3", "Duzce17", "Rize7"]
# Sources whose full-size download lost its orientation (checked against the Drive preview).
ROTATE = {"Izmir_Odemis1": cv2.ROTATE_180}
PRINTS = ["Izmir_Odemis1", "Manisa1"]
# key: (source file, media start, media end, is HDR)
CLIPS = {
    "s1_izmir": ("Root_Ege_loose7.mp4", 0.0, 2.4, False),
    "s4_gumushane": ("Gumushane1.mov", 2.0, 4.8, True),
    "s5_konya": ("Aksehir29.mov", 2.8, 5.45, False),
    "s6_izmir": ("Root_Ege_loose1.mp4", 0.9, 4.45, False),
    "s7_duzce": ("Duzce2.mov", 2.5, 6.9, True),
}

det = FaceDetector()


def face_center_x(img) -> float:
    h, w = img.shape[:2]
    s = 900 / max(h, w)
    small = cv2.resize(img, None, fx=s, fy=s)
    faces = det(small, 14)
    if not faces:
        return w / 2
    wts = np.array([f[2] * f[3] for f in faces])
    xs = np.array([(f[0] + f[2] / 2) / s for f in faces])
    return float((xs * wts).sum() / wts.sum())


def crop_to(img, aspect: float):
    """Largest crop with width/height = aspect, centred on faces horizontally."""
    h, w = img.shape[:2]
    if w / h > aspect:
        cw, ch = int(h * aspect), h
        cx = face_center_x(img)
        x0 = int(np.clip(cx - cw / 2, 0, w - cw))
        return img[:, x0:x0 + cw]
    cw, ch = w, int(w / aspect)
    y0 = int((h - ch) * 0.4)  # keep a little more of the top (faces) than the floor
    return img[y0:y0 + ch]


def grade_jpg(src: Path, dst: Path, size: tuple[int, int]) -> None:
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", str(src),
                    "-vf", f"scale={size[0]}:{size[1]}:flags=lanczos,{GRADE},unsharp=5:5:0.4",
                    "-q:v", "2", str(dst)], check=True)


def main(src_dir: Path) -> None:
    IMG.mkdir(parents=True, exist_ok=True)
    VID.mkdir(parents=True, exist_ok=True)
    report = {}
    for key in BACKGROUNDS + PRINTS:
        from PIL import Image, ImageOps  # honour EXIF orientation (cv2 does not for every file)
        pil = ImageOps.exif_transpose(Image.open(src_dir / "full" / f"{key}.jpg")).convert("RGB")
        img = cv2.cvtColor(np.asarray(pil), cv2.COLOR_RGB2BGR)
        if key in ROTATE:
            img = cv2.rotate(img, ROTATE[key])
        bg = key in BACKGROUNDS
        crop = crop_to(img, 9 / 16 if bg else 5 / 4)
        tmp = IMG / f"_{key}.png"
        cv2.imwrite(str(tmp), crop)
        size = (1146, 2036) if bg else (1000, 800)
        grade_jpg(tmp, IMG / f"{key}.jpg", size)
        tmp.unlink()
        report[key] = {"crop": list(crop.shape[1::-1]), "upscale": round(size[0] / crop.shape[1], 2)}
    for key, (name, a, b, hdr) in CLIPS.items():
        vf = (TONEMAP + "," if hdr else "") + \
            f"scale=1080:1920:force_original_aspect_ratio=increase:flags=lanczos,crop=1080:1920,fps=30,{GRADE},format=yuv420p"
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-ss", f"{a}", "-i", str(src_dir / "vid" / name),
                        "-t", f"{b - a}", "-an", "-vf", vf, "-c:v", "libx264", "-preset", "medium",
                        "-crf", "16", "-g", "15", "-movflags", "+faststart", str(VID / f"{key}.mp4")], check=True)
        report[key] = {"seconds": round(b - a, 2), "hdr": hdr}
    (ROOT / "assets" / "prep_report.json").write_text(json.dumps(report, indent=1))
    for k, v in report.items():
        print(k, v)


if __name__ == "__main__":
    main(Path(sys.argv[1]))
