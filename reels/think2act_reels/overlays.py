"""Node-side renders: animated hook overlay (HyperFrames) and cover image (Puppeteer)."""

from __future__ import annotations

import html
import os
import shutil
import subprocess
from pathlib import Path

from .media import require, run

NODE_DIR = Path(__file__).resolve().parent.parent / "node"
TEMPLATES = NODE_DIR / "templates"


def node_ready() -> tuple[bool, str]:
    if not shutil.which("node"):
        return False, "node is not installed"
    if not (NODE_DIR / "node_modules" / "hyperframes").exists():
        return False, f"run `npm install` in {NODE_DIR}"
    return True, ""


def _fill(template: str, **values: str) -> str:
    for key, val in values.items():
        template = template.replace("{{" + key + "}}", val)
    return template


def render_hook(text: str, out_webm: Path, duration: float = 3.0, accent: str = "#FFD400") -> Path:
    """Render a transparent WebM hook card with HyperFrames."""
    ok, why = node_ready()
    if not ok:
        raise RuntimeError(why)
    project = out_webm.parent / (out_webm.stem + "_hf")
    if project.exists():
        shutil.rmtree(project)
    project.mkdir(parents=True)
    words = " ".join(f'<span class="w">{html.escape(w)}</span>' for w in text.split())
    page = _fill(
        (TEMPLATES / "hook.html").read_text(encoding="utf-8"),
        WORDS=words, DURATION=f"{duration:g}", ACCENT=accent,
    )
    (project / "index.html").write_text(page, encoding="utf-8")
    shutil.copy(NODE_DIR / "node_modules" / "gsap" / "dist" / "gsap.min.js", project / "gsap.min.js")
    npx = require("npx")
    env = {**os.environ, "HYPERFRAMES_SKIP_SKILLS": "1", "HYPERFRAMES_TELEMETRY": "0", "DO_NOT_TRACK": "1"}
    run(
        [npx, "--no-install", "hyperframes", "render", str(project),
         "--format", "webm", "--fps", "30", "--quiet", "-o", str(out_webm.resolve())],
        cwd=NODE_DIR, env=env, stdin=subprocess.DEVNULL,
    )
    if not out_webm.exists():
        raise RuntimeError("HyperFrames finished without writing the hook video")
    return out_webm


def render_cover(background: Path, title: str, out_png: Path, tag: str = "", accent: str = "#FFD400") -> Path:
    """Render a 1080x1920 cover with Puppeteer from a background frame."""
    ok, why = node_ready()
    if not ok:
        raise RuntimeError(why)
    words = html.escape(title).split()
    # Highlight the longest word in the accent colour - a cheap but effective focal point.
    if words:
        k = max(range(len(words)), key=lambda i: len(words[i]))
        words[k] = f"<em>{words[k]}</em>"
    page = _fill(
        (TEMPLATES / "cover.html").read_text(encoding="utf-8"),
        IMAGE=background.resolve().as_uri(), TITLE=" ".join(words),
        TAG=html.escape(tag), ACCENT=accent,
    )
    page_path = out_png.with_suffix(".cover.html")
    page_path.write_text(page, encoding="utf-8")
    run([require("node"), str(NODE_DIR / "cover.mjs"), str(page_path), str(out_png)], cwd=NODE_DIR)
    page_path.unlink(missing_ok=True)
    return out_png
