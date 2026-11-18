"""Thin wrappers around the ffmpeg / ffprobe command line tools."""

from __future__ import annotations

import json
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path


class ToolMissing(RuntimeError):
    pass


def require(tool: str) -> str:
    path = shutil.which(tool)
    if not path:
        raise ToolMissing(f"'{tool}' was not found on PATH. Install it first (see reels/README.md).")
    return path


def run(cmd: list[str], **kw) -> subprocess.CompletedProcess:
    """Run a command, raising with its stderr tail on failure."""
    proc = subprocess.run(cmd, capture_output=True, text=True, **kw)
    if proc.returncode != 0:
        tail = "\n".join((proc.stderr or proc.stdout or "").strip().splitlines()[-25:])
        raise RuntimeError(f"command failed ({proc.returncode}): {' '.join(cmd[:4])} ...\n{tail}")
    return proc


@dataclass
class VideoInfo:
    width: int
    height: int
    fps: float
    duration: float
    has_audio: bool


def probe(path: Path) -> VideoInfo:
    out = run([
        require("ffprobe"), "-v", "error", "-print_format", "json",
        "-show_streams", "-show_format", str(path),
    ]).stdout
    data = json.loads(out)
    video = next(s for s in data["streams"] if s["codec_type"] == "video")
    num, den = (video.get("avg_frame_rate") or video.get("r_frame_rate") or "30/1").split("/")
    fps = float(num) / float(den) if float(den) else 30.0
    if not 1 <= fps <= 240:
        fps = 30.0
    width, height = int(video["width"]), int(video["height"])
    rotation = 0
    for sd in video.get("side_data_list", []) or []:
        if "rotation" in sd:
            rotation = abs(int(sd["rotation"]))
    if rotation in (90, 270):
        width, height = height, width
    duration = float(data["format"].get("duration") or video.get("duration") or 0)
    has_audio = any(s["codec_type"] == "audio" for s in data["streams"])
    return VideoInfo(width, height, fps, duration, has_audio)


def cut(src: Path, start: float, end: float, dst: Path, fps: float | None = None) -> Path:
    """Frame-accurate cut (re-encodes) so later stages can work from t=0."""
    cmd = [
        require("ffmpeg"), "-y", "-hide_banner", "-loglevel", "error",
        "-ss", f"{start:.3f}", "-i", str(src), "-t", f"{end - start:.3f}",
        "-map", "0:v:0", "-map", "0:a:0?",
    ]
    if fps:
        cmd += ["-r", f"{fps:.3f}"]
    cmd += [
        "-c:v", "libx264", "-preset", "veryfast", "-crf", "16", "-pix_fmt", "yuv420p",
        "-c:a", "aac", "-b:a", "192k", "-ar", "48000",
        str(dst),
    ]
    run(cmd)
    return dst


def has_filter(name: str) -> bool:
    out = run([require("ffmpeg"), "-hide_banner", "-filters"]).stdout
    return any(line.split()[1:2] == [name] for line in out.splitlines() if line.strip())

