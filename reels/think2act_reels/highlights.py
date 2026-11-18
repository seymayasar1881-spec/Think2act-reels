"""Pick the most "Reels-worthy" windows of a transcript.

This is a transparent heuristic, not a black box: every candidate window is
aligned to whole speech segments, scored on a few signals, and the best
non-overlapping windows win. Scores are written to the manifest so you can see
why a clip was chosen.
"""

from __future__ import annotations

import re
from dataclasses import asdict, dataclass, field

# Words that tend to open a strong hook (Turkish + English, lower-case).
HOOK_WORDS = {
    "neden", "nasıl", "niye", "sır", "sırrı", "asla", "kimse", "hiç", "aslında", "gerçek",
    "gerçekten", "dikkat", "önemli", "hata", "hatası", "yanlış", "en", "ilk", "tek", "bilmiyor",
    "why", "how", "secret", "never", "nobody", "actually", "truth", "mistake", "wrong",
    "stop", "best", "worst", "first", "only", "most", "nobody", "everyone",
}
SENTENCE_END = re.compile(r"[.!?…]['\"”’)]*$")
WORD_RE = re.compile(r"\w+", re.UNICODE)


@dataclass
class Clip:
    start: float
    end: float
    text: str
    score: float = 0.0
    signals: dict = field(default_factory=dict)
    hook: str = ""

    @property
    def duration(self) -> float:
        return self.end - self.start

    def to_dict(self) -> dict:
        d = asdict(self)
        d["duration"] = round(self.duration, 3)
        return d


def parse_timestamp(value: str) -> float:
    """'83', '1:23', '01:02:03.5' -> seconds."""
    parts = value.strip().split(":")
    if not 1 <= len(parts) <= 3:
        raise ValueError(f"bad timestamp: {value!r}")
    total = 0.0
    for p in parts:
        total = total * 60 + float(p)
    return total


def parse_range(value: str) -> tuple[float, float]:
    """'1:20-2:05' -> (80.0, 125.0)."""
    if "-" not in value:
        raise ValueError(f"expected START-END, got {value!r}")
    a, b = value.split("-", 1)
    start, end = parse_timestamp(a), parse_timestamp(b)
    if end <= start:
        raise ValueError(f"end must be after start: {value!r}")
    return start, end


def make_hook(text: str, max_words: int = 9) -> str:
    """First sentence of the clip, trimmed to a punchy length."""
    text = text.strip()
    first = re.split(r"(?<=[.!?…])\s+", text, maxsplit=1)[0]
    words = first.split()
    if len(words) > max_words:
        first = " ".join(words[:max_words]).rstrip(",;:") + "…"
    return first


def _score(segs: list[dict], keywords: set[str]) -> tuple[float, dict]:
    start, end = segs[0]["start"], segs[-1]["end"]
    dur = max(end - start, 1e-6)
    text = " ".join(s["text"] for s in segs)
    tokens = [t.lower() for t in WORD_RE.findall(text)]
    n_words = len(tokens)

    speech = sum(s["end"] - s["start"] for s in segs)
    gaps = [b["start"] - a["end"] for a, b in zip(segs, segs[1:])]
    long_gaps = sum(1 for g in gaps if g > 1.5)

    opener = " ".join(s["text"] for s in segs[:2]).lower()
    opener_tokens = set(WORD_RE.findall(opener))

    signals = {
        # Talking pace: ~2.5 words/s is lively speech; cap so rapid mumbling doesn't dominate.
        "pace": min(n_words / dur / 2.5, 1.2),
        # Fraction of the window actually containing speech.
        "speech_ratio": min(speech / dur, 1.0),
        # Opening line asks a question / uses a hook word / has a number.
        "hook": (0.5 if "?" in opener else 0.0)
        + (0.4 if opener_tokens & HOOK_WORDS else 0.0)
        + (0.2 if re.search(r"\d", opener) else 0.0),
        # Ends on a complete sentence rather than mid-thought.
        "clean_end": 1.0 if SENTENCE_END.search(segs[-1]["text"].strip()) else 0.0,
        "keywords": min(sum(1 for t in tokens if t in keywords) / 3, 1.0) if keywords else 0.0,
        "dead_air": float(long_gaps),
    }
    score = (
        1.0 * signals["pace"]
        + 1.0 * signals["speech_ratio"]
        + 1.0 * signals["hook"]
        + 0.6 * signals["clean_end"]
        + 1.5 * signals["keywords"]
        - 0.4 * signals["dead_air"]
    )
    return round(score, 4), {k: round(v, 3) for k, v in signals.items()}


def candidates(transcript: dict, min_len: float, max_len: float, keywords: set[str]) -> list[Clip]:
    segs = [s for s in transcript["segments"] if s["text"].strip()]
    out: list[Clip] = []
    for i in range(len(segs)):
        for j in range(i, len(segs)):
            dur = segs[j]["end"] - segs[i]["start"]
            if dur > max_len:
                break
            if dur < min_len:
                continue
            window = segs[i : j + 1]
            score, signals = _score(window, keywords)
            text = " ".join(s["text"] for s in window)
            out.append(Clip(window[0]["start"], window[-1]["end"], text, score, signals))
    return out


def pick(
    transcript: dict,
    count: int = 3,
    min_len: float = 20.0,
    max_len: float = 60.0,
    keywords: list[str] | None = None,
    pad: float = 0.25,
    media_duration: float | None = None,
) -> list[Clip]:
    """Best ``count`` non-overlapping windows, returned in timeline order."""
    kw = {k.lower() for k in (keywords or [])}
    pool = sorted(candidates(transcript, min_len, max_len, kw), key=lambda c: -c.score)
    chosen: list[Clip] = []
    for c in pool:
        if all(c.end <= o.start or c.start >= o.end for o in chosen):
            chosen.append(c)
            if len(chosen) == count:
                break
    for c in chosen:
        c.start = max(0.0, c.start - pad)
        c.end = c.end + pad if media_duration is None else min(media_duration, c.end + pad)
        c.hook = make_hook(c.text)
    return sorted(chosen, key=lambda c: c.start)


def manual(transcript: dict | None, ranges: list[tuple[float, float]]) -> list[Clip]:
    clips = []
    for start, end in ranges:
        text = ""
        if transcript:
            text = " ".join(
                s["text"] for s in transcript["segments"]
                if s["end"] > start and s["start"] < end
            )
        clips.append(Clip(start, end, text, hook=make_hook(text) if text else ""))
    return clips
