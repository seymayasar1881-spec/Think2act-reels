"""think2act-reels command line.

    python -m think2act_reels "https://youtu.be/..." --clips 3 --lang tr
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import time
import unicodedata
from pathlib import Path

from . import captions, highlights, media, overlays, reframe, render
from .download import fetch, is_url
from .transcribe import transcribe, words_between


def slugify(text: str, limit: int = 48) -> str:
    text = unicodedata.normalize("NFKD", text.replace("ı", "i")).encode("ascii", "ignore").decode()
    text = re.sub(r"[^a-zA-Z0-9]+", "-", text).strip("-").lower()
    return (text[:limit].rstrip("-")) or "video"


def log(msg: str) -> None:
    print(f"[reels {time.strftime('%H:%M:%S')}] {msg}", flush=True)


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="think2act-reels",
        description="Turn a long video (URL or file) into vertical 9:16 Reels with captions.",
    )
    p.add_argument("source", help="Video URL (anything yt-dlp supports) or local file path")
    p.add_argument("-o", "--out", default="output", help="Output root directory (default: ./output)")
    p.add_argument("-n", "--clips", type=int, default=3, help="How many reels to auto-pick (default 3)")
    p.add_argument("--min", dest="min_len", type=float, default=20, help="Min clip length in seconds")
    p.add_argument("--max", dest="max_len", type=float, default=60, help="Max clip length in seconds")
    p.add_argument("--clip", action="append", default=[], metavar="START-END",
                   help="Use this exact range instead of auto-picking (repeatable), e.g. 1:20-2:05")
    p.add_argument("-k", "--keywords", nargs="*", default=[], help="Boost windows mentioning these words")
    p.add_argument("--lang", default=None, help="Spoken language code (tr, en, ...). Auto-detect if omitted")
    p.add_argument("--model", default="small",
                   help="faster-whisper model: tiny, base, small, medium, large-v3, turbo (default small)")
    p.add_argument("--device", default="auto", help="faster-whisper device: auto, cpu, cuda")
    p.add_argument("--reframe", choices=["face", "center", "fit"], default="face",
                   help="face: track the speaker; center: static center crop; fit: full frame on blurred bg")
    p.add_argument("--no-captions", action="store_true", help="Skip burned-in captions")
    p.add_argument("--no-hook", action="store_true", help="Skip the animated HyperFrames hook card")
    p.add_argument("--no-cover", action="store_true", help="Skip the Puppeteer cover image")
    p.add_argument("--hook-text", action="append", default=[],
                   help="Override hook text (repeat once per clip, in order)")
    p.add_argument("--hook-seconds", type=float, default=3.0, help="Hook card duration (default 3s)")
    p.add_argument("--accent", default="#FFD400", help="Accent colour for captions/hook/cover")
    p.add_argument("--font", default="Montserrat", help="Caption font family (falls back if missing)")
    p.add_argument("--words-per-caption", type=int, default=3)
    p.add_argument("--no-loudnorm", action="store_true", help="Keep original audio levels")
    p.add_argument("--dry-run", action="store_true", help="Only transcribe + pick clips, write clips.json")
    return p


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    for tool in ("ffmpeg", "ffprobe"):
        media.require(tool)

    out_root = Path(args.out)
    out_root.mkdir(parents=True, exist_ok=True)
    work_key = slugify(args.source if is_url(args.source) else Path(args.source).stem)
    work = out_root / ".work" / work_key
    work.mkdir(parents=True, exist_ok=True)

    log(f"source: {args.source}")
    src, title = fetch(args.source, work)
    info = media.probe(src)
    log(f"video: {info.width}x{info.height} @ {info.fps:.2f}fps, {info.duration:.1f}s, audio={info.has_audio}")

    project = out_root / slugify(title)
    project.mkdir(parents=True, exist_ok=True)

    need_transcript = info.has_audio and (not args.clip or not args.no_captions)
    transcript = None
    if need_transcript:
        log(f"transcribing with faster-whisper '{args.model}' (cached after first run)…")
        transcript = transcribe(src, work / f"transcript.{args.model}.json", model=args.model,
                                language=args.lang, device=args.device)
        log(f"language={transcript['language']}, {len(transcript['segments'])} segments")
    language = args.lang or (transcript or {}).get("language")

    if args.clip:
        clips = highlights.manual(transcript, [highlights.parse_range(r) for r in args.clip])
    else:
        if not transcript or not transcript["segments"]:
            log("no speech found; use --clip START-END to choose ranges manually")
            return 1
        clips = highlights.pick(transcript, args.clips, args.min_len, args.max_len,
                                args.keywords, media_duration=info.duration)
        if not clips:
            log(f"no window fits {args.min_len}-{args.max_len}s; try different --min/--max")
            return 1
    for i, text in enumerate(args.hook_text[: len(clips)]):
        clips[i].hook = text

    manifest = {"source": args.source, "title": title, "language": language, "clips": []}
    for i, c in enumerate(clips, 1):
        log(f"clip {i}: {c.start:.1f}-{c.end:.1f}s score={c.score} hook={c.hook!r}")
        manifest["clips"].append({"file": f"reel_{i:02d}.mp4", **c.to_dict()})
    (project / "clips.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    if args.dry_run:
        log(f"dry run: wrote {project / 'clips.json'}")
        return 0

    node_ok, node_why = overlays.node_ready()
    if not node_ok and not (args.no_hook and args.no_cover):
        log(f"hook/cover disabled: {node_why}")
    caption_ok = not args.no_captions and transcript is not None and media.has_filter("subtitles")
    if not args.no_captions and transcript is not None and not caption_ok:
        log("captions disabled: this ffmpeg build lacks the libass 'subtitles' filter")

    for i, c in enumerate(clips, 1):
        cdir = work / f"clip_{i:02d}"
        cdir.mkdir(exist_ok=True)
        raw = media.cut(src, c.start, c.end, cdir / "clip.mp4")
        cinfo = media.probe(raw)

        if reframe.is_vertical(cinfo.width, cinfo.height):
            mode, plan = "fill", None
        elif args.reframe == "fit":
            mode, plan = "fit", None
        else:
            log(f"clip {i}: tracking faces ({args.reframe})…")
            plan = reframe.plan(str(raw), args.reframe)
            mode = "crop"
            if args.reframe == "face":
                log(f"clip {i}: faces in {plan.faces_found}/{plan.samples} samples, {plan.cuts} scene cuts, detector={plan.detector}")

        ass = None
        if caption_ok:
            words = words_between(transcript, c.start, c.end)
            if words:
                ass = captions.write_ass(cdir / "captions.ass", words, language=language,
                                         font=args.font, highlight=args.accent,
                                         max_words=args.words_per_caption)

        hook_video = None
        if node_ok and not args.no_hook and c.hook:
            log(f"clip {i}: rendering hook card with HyperFrames…")
            try:
                hook_video = overlays.render_hook(c.hook, cdir / "hook.webm",
                                                  duration=min(args.hook_seconds, c.duration),
                                                  accent=args.accent)
            except Exception as e:  # keep going without the hook
                log(f"clip {i}: hook skipped ({str(e).splitlines()[0]})")

        out = project / f"reel_{i:02d}.mp4"
        cover_bg = cdir / "cover_bg.jpg"
        log(f"clip {i}: composing {out.name}…")
        render.compose(raw, cinfo, out, mode, crop=plan, captions=ass, hook=hook_video,
                       cover_frame=cover_bg, cover_at=min(c.duration / 3, 4.0),
                       loudnorm=not args.no_loudnorm)

        if node_ok and not args.no_cover and cover_bg.exists():
            try:
                overlays.render_cover(cover_bg, c.hook or title, project / f"reel_{i:02d}_cover.png",
                                      tag=title[:40], accent=args.accent)
            except Exception as e:
                log(f"clip {i}: cover skipped ({str(e).splitlines()[0]})")
        log(f"clip {i}: done -> {out}")

    log(f"all done: {project}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
