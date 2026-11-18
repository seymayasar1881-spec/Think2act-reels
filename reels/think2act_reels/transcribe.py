"""Speech-to-text with word timestamps via faster-whisper."""

from __future__ import annotations

import json
from pathlib import Path


def transcribe(
    media: Path,
    out_json: Path,
    model: str = "small",
    language: str | None = None,
    device: str = "auto",
    compute_type: str = "auto",
) -> dict:
    """Transcribe ``media`` and cache the result as JSON.

    Returned shape::

        {"language": "tr", "segments": [
            {"start": 0.0, "end": 2.1, "text": "...",
             "words": [{"start": 0.0, "end": 0.4, "word": "Merhaba"}, ...]}]}
    """
    if out_json.exists():
        cached = json.loads(out_json.read_text(encoding="utf-8"))
        if cached.get("model") == model and (language is None or cached.get("language") == language):
            return cached

    from faster_whisper import WhisperModel

    whisper = WhisperModel(model, device=device, compute_type=compute_type)
    segments, info = whisper.transcribe(
        str(media),
        language=language,
        word_timestamps=True,
        vad_filter=True,
        beam_size=5,
    )
    data = {"model": model, "language": info.language, "duration": info.duration, "segments": []}
    for seg in segments:
        words = [
            {"start": round(w.start, 3), "end": round(w.end, 3), "word": w.word.strip()}
            for w in (seg.words or [])
            if w.word.strip()
        ]
        data["segments"].append({
            "start": round(seg.start, 3),
            "end": round(seg.end, 3),
            "text": seg.text.strip(),
            "words": words,
        })
    out_json.write_text(json.dumps(data, ensure_ascii=False, indent=1), encoding="utf-8")
    return data


def words_between(transcript: dict, start: float, end: float) -> list[dict]:
    """Words whose midpoint falls in [start, end), with times shifted to start at 0."""
    out = []
    for seg in transcript["segments"]:
        if seg["end"] < start or seg["start"] > end:
            continue
        for w in seg["words"]:
            mid = (w["start"] + w["end"]) / 2
            if start <= mid < end:
                out.append({
                    "start": max(0.0, w["start"] - start),
                    "end": min(end - start, w["end"] - start),
                    "word": w["word"],
                })
    return out
