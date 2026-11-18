"""Word-by-word "pop" captions as an ASS subtitle file (burned in by ffmpeg/libass)."""

from __future__ import annotations

from pathlib import Path


def _ass_time(t: float) -> str:
    t = max(0.0, t)
    cs = int(round(t * 100))
    h, cs = divmod(cs, 360000)
    m, cs = divmod(cs, 6000)
    s, cs = divmod(cs, 100)
    return f"{h}:{m:02d}:{s:02d}.{cs:02d}"


def _hex_to_ass(color: str) -> str:
    """'#FFD400' -> '&H0000D4FF' (ASS is AABBGGRR)."""
    c = color.lstrip("#")
    r, g, b = c[0:2], c[2:4], c[4:6]
    return f"&H00{b}{g}{r}".upper()


def upper(text: str, language: str | None) -> str:
    """Upper-case that respects Turkish/Azeri dotted and dotless i."""
    if language in ("tr", "az"):
        text = text.replace("i", "İ").replace("ı", "I")
    return text.upper()


def _clean(word: str) -> str:
    return word.replace("\\", "").replace("{", "(").replace("}", ")").strip()


def chunk_words(words: list[dict], max_words: int = 3, max_gap: float = 0.6, max_chars: int = 18) -> list[list[dict]]:
    """Group words into short on-screen phrases."""
    chunks: list[list[dict]] = []
    cur: list[dict] = []
    for w in words:
        if cur:
            gap = w["start"] - cur[-1]["end"]
            chars = sum(len(x["word"]) + 1 for x in cur) + len(w["word"])
            ends_sentence = cur[-1]["word"].rstrip()[-1:] in ".!?…,;:"
            if len(cur) >= max_words or gap > max_gap or chars > max_chars or ends_sentence:
                chunks.append(cur)
                cur = []
        cur.append(w)
    if cur:
        chunks.append(cur)
    return chunks


def build_ass(
    words: list[dict],
    language: str | None = None,
    font: str = "Montserrat",
    font_size: int = 86,
    color: str = "#FFFFFF",
    highlight: str = "#FFD400",
    margin_v: int = 560,
    uppercase: bool = True,
    max_words: int = 3,
) -> str:
    base, hi = _hex_to_ass(color), _hex_to_ass(highlight)
    header = f"""[Script Info]
ScriptType: v4.00+
PlayResX: 1080
PlayResY: 1920
WrapStyle: 0
ScaledBorderAndShadow: yes

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Word,{font},{font_size},{base},{base},&H00000000,&H80000000,-1,0,0,0,100,100,0,0,1,7,3,2,80,80,{margin_v},1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
    lines = []
    for chunk in chunk_words(words, max_words=max_words):
        texts = [_clean(w["word"]) for w in chunk]
        if uppercase:
            texts = [upper(t, language) for t in texts]
        chunk_end = chunk[-1]["end"] + 0.15
        for i, w in enumerate(chunk):
            start = w["start"]
            end = chunk[i + 1]["start"] if i + 1 < len(chunk) else chunk_end
            if end - start < 0.05:
                continue
            parts = []
            for j, t in enumerate(texts):
                if j == i:
                    pop = r"\t(0,80,\fscx112\fscy112)\t(80,160,\fscx106\fscy106)"
                    parts.append(f"{{\\c{hi}\\fscx100\\fscy100{pop}}}{t}{{\\c{base}\\fscx100\\fscy100}}")
                else:
                    parts.append(t)
            lines.append(
                f"Dialogue: 0,{_ass_time(start)},{_ass_time(end)},Word,,0,0,0,,{' '.join(parts)}"
            )
    return header + "\n".join(lines) + "\n"


def write_ass(path: Path, words: list[dict], **style) -> Path:
    path.write_text(build_ass(words, **style), encoding="utf-8")
    return path
