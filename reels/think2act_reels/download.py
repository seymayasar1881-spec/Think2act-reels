"""Fetch the source video with yt-dlp (or accept a local file)."""

from __future__ import annotations

import re
from pathlib import Path


def is_url(source: str) -> bool:
    return bool(re.match(r"^https?://", source, re.I))


def fetch(source: str, workdir: Path, max_height: int = 1080) -> tuple[Path, str]:
    """Return (path to a local video file, human title)."""
    if not is_url(source):
        path = Path(source).expanduser()
        if not path.exists():
            raise FileNotFoundError(source)
        return path, path.stem

    existing = sorted(workdir.glob("source.*"))
    existing = [p for p in existing if p.suffix in (".mp4", ".mkv", ".webm", ".mov")]
    title_file = workdir / "source.title"
    if existing and title_file.exists():
        return existing[0], title_file.read_text(encoding="utf-8").strip()

    from yt_dlp import YoutubeDL

    workdir.mkdir(parents=True, exist_ok=True)
    opts = {
        "format": (
            f"bv*[height<={max_height}][vcodec^=avc1]+ba[ext=m4a]/"
            f"bv*[height<={max_height}]+ba/b[height<={max_height}]/b"
        ),
        "merge_output_format": "mp4",
        "outtmpl": str(workdir / "source.%(ext)s"),
        "noplaylist": True,
        "quiet": True,
        "no_warnings": True,
    }
    with YoutubeDL(opts) as ydl:
        info = ydl.extract_info(source, download=True)
    files = [p for p in workdir.glob("source.*") if p.suffix in (".mp4", ".mkv", ".webm", ".mov")]
    if not files:
        raise RuntimeError("yt-dlp finished but no video file was written")
    title = (info or {}).get("title") or "video"
    title_file.write_text(title, encoding="utf-8")
    return files[0], title
