"""Compose the final 1080x1920 reel: reframed video + captions + hook + loudness-normalised audio."""

from __future__ import annotations

import subprocess
from pathlib import Path

import numpy as np

from .media import VideoInfo, require
from .reframe import TARGET_H, TARGET_W, CropPlan

FIT_FILTER = (
    "split[a][b];"
    "[a]scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,"
    "boxblur=30:5,eq=brightness=-0.08[bg];"
    "[b]scale=1080:-2[fg];[bg][fg]overlay=(W-w)/2:(H-h)/2"
)
FILL_FILTER = "scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920"


def _encode_args(out: Path) -> list[str]:
    return [
        "-c:v", "libx264", "-preset", "medium", "-crf", "20", "-pix_fmt", "yuv420p",
        "-c:a", "aac", "-b:a", "192k", "-ar", "48000",
        "-movflags", "+faststart", str(out),
    ]


def _overlay_chain(first_label: str, captions: Path | None, hook: Path | None, hook_input: int) -> str:
    chain = []
    cur = first_label
    if captions:
        # Relative name: ffmpeg runs with cwd=clip dir, which avoids filtergraph path escaping.
        chain.append(f"[{cur}]subtitles=filename={captions.name}[cap]")
        cur = "cap"
    if hook:
        chain.append(f"[{cur}][{hook_input}:v]overlay=0:0:eof_action=pass:format=auto[hk]")
        cur = "hk"
    chain.append(f"[{cur}]format=yuv420p[vout]")
    return ";".join(chain)


def compose(
    clip: Path,
    info: VideoInfo,
    out: Path,
    mode: str,
    crop: CropPlan | None = None,
    captions: Path | None = None,
    hook: Path | None = None,
    cover_frame: Path | None = None,
    cover_at: float = 1.0,
    loudnorm: bool = True,
) -> Path:
    """mode: 'crop' (use ``crop`` plan), 'fit' (blurred background) or 'fill' (source already vertical)."""
    cwd = clip.parent
    ffmpeg = require("ffmpeg")
    audio_filter = ["-af", "loudnorm=I=-14:TP=-1.5:LRA=11"] if loudnorm and info.has_audio else []

    if mode == "crop":
        assert crop is not None
        cmd = [
            ffmpeg, "-y", "-hide_banner", "-loglevel", "error",
            "-f", "rawvideo", "-pix_fmt", "bgr24", "-s", f"{TARGET_W}x{TARGET_H}",
            "-r", f"{info.fps:.6f}", "-i", "pipe:0",
            "-i", clip.name,
        ]
        hook_input = 2
        if hook:
            cmd += ["-c:v", "libvpx-vp9", "-i", hook.name]
        graph = _overlay_chain("0:v", captions, hook, hook_input)
        cmd += ["-filter_complex", graph, "-map", "[vout]"]
        if info.has_audio:
            cmd += ["-map", "1:a:0", *audio_filter]
        cmd += ["-shortest", *_encode_args(out.resolve())]
        _pipe_cropped(clip, crop, cmd, cwd, info, cover_frame, cover_at)
        return out

    base = FIT_FILTER if mode == "fit" else FILL_FILTER
    cmd = [ffmpeg, "-y", "-hide_banner", "-loglevel", "error", "-i", clip.name]
    if hook:
        cmd += ["-c:v", "libvpx-vp9", "-i", hook.name]
    graph = f"[0:v]{base}[base];" + _overlay_chain("base", captions, hook, 1)
    cmd += ["-filter_complex", graph, "-map", "[vout]"]
    if info.has_audio:
        cmd += ["-map", "0:a:0", *audio_filter]
    cmd += _encode_args(out.resolve())
    _run(cmd, cwd)
    if cover_frame:
        _run([ffmpeg, "-y", "-hide_banner", "-loglevel", "error", "-ss", f"{cover_at:.2f}",
              "-i", clip.name, "-vf", base,
              "-frames:v", "1", "-q:v", "2", str(cover_frame.resolve())], cwd)
    return out


def _run(cmd: list[str], cwd: Path) -> None:
    proc = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True)
    if proc.returncode != 0:
        raise RuntimeError("ffmpeg failed:\n" + "\n".join(proc.stderr.strip().splitlines()[-20:]))


def _pipe_cropped(clip: Path, crop: CropPlan, cmd: list[str], cwd: Path, info: VideoInfo,
                  cover_frame: Path | None, cover_at: float) -> None:
    import cv2

    cap = cv2.VideoCapture(str(clip))
    if not cap.isOpened():
        raise RuntimeError(f"OpenCV could not open {clip}")
    log = cwd / "ffmpeg_compose.log"
    cover_index = int(cover_at * info.fps)
    upscale = crop.crop_w < TARGET_W
    interp = cv2.INTER_LANCZOS4 if upscale else cv2.INTER_AREA
    with open(log, "w") as errf:
        proc = subprocess.Popen(cmd, cwd=cwd, stdin=subprocess.PIPE, stderr=errf)
        i = 0
        try:
            while True:
                ok, frame = cap.read()
                if not ok:
                    break
                x = crop.x_at(i)
                view = frame[crop.y : crop.y + crop.crop_h, x : x + crop.crop_w]
                out = cv2.resize(view, (TARGET_W, TARGET_H), interpolation=interp)
                if cover_frame is not None and i == cover_index:
                    cv2.imwrite(str(cover_frame), out, [cv2.IMWRITE_JPEG_QUALITY, 92])
                proc.stdin.write(np.ascontiguousarray(out).tobytes())
                i += 1
        except BrokenPipeError:
            pass
        finally:
            cap.release()
            if proc.stdin:
                try:
                    proc.stdin.close()
                except BrokenPipeError:
                    pass
            code = proc.wait()
    if code != 0:
        raise RuntimeError("ffmpeg failed:\n" + "\n".join(log.read_text().strip().splitlines()[-20:]))
    log.unlink(missing_ok=True)
