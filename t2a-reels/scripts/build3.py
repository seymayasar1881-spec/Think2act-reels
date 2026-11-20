#!/usr/bin/env python3
"""Think2Act reels v3 — soft, bright, on-brand (T2A logo + gradient), polaroid collages.
Writes work3/reel3_silent.mp4 and work3/sections.json (section start times for music)."""
import os, subprocess, sys, json, math, random
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter

S = os.path.dirname(os.path.abspath(__file__))
MV, MP, BR = (os.path.join(S, d) for d in ("media", "media_n", "brand"))
WD = os.path.join(S, "work3"); os.makedirs(WD, exist_ok=True)
W, H, FPS = 1080, 1920, 30
XF = 0.4  # crossfade length
INTER = "/usr/share/fonts/opentype/inter/"
ANTON = os.path.join(BR, "Anton.ttf")
DARK = (21, 21, 26, 255)
random.seed(11)


def run(cmd):
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode:
        print(" ".join(cmd)[:1500]); print(r.stderr[-3000:]); sys.exit(1)


def tr_upper(s):
    return s.replace("i", "İ").replace("ı", "I").upper()


def ease_out(x): x = min(max(x, 0), 1); return 1 - (1 - x) ** 3


# ---------------------------------------------------------------- brand assets
GRAD = Image.open(os.path.join(BR, "gradient.jpg")).convert("RGB")
LOGO = Image.open(os.path.join(BR, "logo.png")).convert("RGBA")


def grad_frame(t, dur):
    """Slowly drifting brand gradient, full frame."""
    sc = H * 1.15 / GRAD.height
    g = GRAD.resize((int(GRAD.width * sc), int(GRAD.height * sc)), Image.LANCZOS) if not hasattr(grad_frame, "c") else grad_frame.c
    grad_frame.c = g
    maxx = g.width - W; maxy = g.height - H
    p = t / max(dur, 1e-3)
    x = int(maxx * (0.15 + 0.5 * p)); y = int(maxy * 0.5)
    return g.crop((x, y, x + W, y + H))


def badge_layer():
    L = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    sz, x0, y0 = 118, W - 118 - 46, 64
    sh = Image.new("L", (W, H), 0)
    ImageDraw.Draw(sh).rounded_rectangle([x0, y0 + 4, x0 + sz, y0 + sz + 4], 26, fill=90)
    L.paste((0, 0, 0, 255), (0, 0), sh.filter(ImageFilter.GaussianBlur(10)))
    ImageDraw.Draw(L).rounded_rectangle([x0, y0, x0 + sz, y0 + sz], 26, fill=(255, 255, 255, 255))
    lg = LOGO.copy(); lg.thumbnail((sz - 26, sz - 26), Image.LANCZOS)
    L.alpha_composite(lg, (x0 + (sz - lg.width) // 2, y0 + (sz - lg.height) // 2))
    # thin gradient strip at the bottom
    strip = GRAD.resize((W, 12), Image.LANCZOS).convert("RGBA")
    L.alpha_composite(strip, (0, H - 12))
    return L


BADGE = badge_layer()


def label_layer(text):
    """Gradient pill label (bottom-left), like 'ROBOTİK ATÖLYELERİ' in the brand posts."""
    L = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    f = ImageFont.truetype(ANTON, 58); d = ImageDraw.Draw(L)
    t = tr_upper(text); tw = d.textlength(t, font=f)
    w, h = int(tw + 64), 96; x0, y0 = 60, H - 330
    pill = GRAD.resize((w, h), Image.LANCZOS).convert("RGBA")
    m = Image.new("L", (w, h), 0); ImageDraw.Draw(m).rounded_rectangle([0, 0, w, h], 18, fill=255)
    sh = Image.new("L", (W, H), 0); ImageDraw.Draw(sh).rounded_rectangle([x0, y0 + 6, x0 + w, y0 + h + 6], 18, fill=110)
    L.paste((0, 0, 0, 255), (0, 0), sh.filter(ImageFilter.GaussianBlur(12)))
    L.paste(pill, (x0, y0), m)
    d.text((x0 + 32, y0 + 8), t, font=f, fill=(255, 255, 255, 255))
    return L


def caption_layer(lines, yc=1120, maxw=960, size=118):
    """lines: [(text, boxed)]. Plain = white Anton w/ soft shadow, boxed = dark text in white box."""
    L = Image.new("RGBA", (W, H), (0, 0, 0, 0)); d = ImageDraw.Draw(L)
    items = []
    for txt, boxed in lines:
        t = tr_upper(txt); s = size
        while d.textlength(t, font=ImageFont.truetype(ANTON, s)) > maxw - (60 if boxed else 0): s -= 4
        items.append((t, boxed, ImageFont.truetype(ANTON, s), s))
    hs = [int(s * 1.28) + (18 if b else 0) for _, b, _, s in items]
    y = yc - sum(hs) // 2
    shadow = Image.new("RGBA", (W, H), (0, 0, 0, 0)); sd = ImageDraw.Draw(shadow)
    for (t, boxed, f, s), lh in zip(items, hs):
        tw = d.textlength(t, font=f); x = (W - tw) / 2
        if boxed:
            pad = 30; bx0, by0, bx1, by1 = x - pad, y, x + tw + pad, y + s * 1.25
            sd.rounded_rectangle([bx0, by0 + 8, bx1, by1 + 8], 14, fill=(0, 0, 0, 120))
            d.rounded_rectangle([bx0, by0, bx1, by1], 14, fill=(255, 255, 255, 255))
            d.text((x, y + s * 0.06), t, font=f, fill=DARK)
        else:
            sd.text((x, y + 6), t, font=f, fill=(0, 0, 0, 170))
            d.text((x, y), t, font=f, fill=(255, 255, 255, 255))
        y += lh
    out = shadow.filter(ImageFilter.GaussianBlur(10)); out.alpha_composite(L)
    return out


def save(layer, name):
    p = os.path.join(WD, name); layer.save(p); return p


# ---------------------------------------------------------------- old paper
def make_paper():
    rng = np.random.default_rng(3)
    base = np.array([238, 228, 206], float)
    img = np.ones((H, W, 3)) * base
    def blob(scale, amp):
        n = rng.standard_normal((H // scale + 2, W // scale + 2))
        im = Image.fromarray(((n - n.min()) / np.ptp(n) * 255).astype(np.uint8)).resize((W, H), Image.BICUBIC)
        return (np.asarray(im, float) / 255 - 0.5) * amp
    tone = blob(300, 34) + blob(90, 16) + blob(25, 9) + blob(6, 6)
    img += tone[..., None] * np.array([1.0, 0.95, 0.8])
    img += rng.standard_normal((H, W, 1)) * 4.5  # grain
    # soft warm edge aging (light, not dark)
    yy, xx = np.mgrid[0:H, 0:W]
    r = np.sqrt(((xx - W / 2) / (W / 2)) ** 2 + ((yy - H / 2) / (H / 2)) ** 2)
    img -= (np.clip(r - 0.75, 0, 1) ** 1.6 * 45)[..., None] * np.array([0.6, 0.75, 1.0])
    # a few faint stains
    for _ in range(2):
        cx, cy, rad = rng.integers(0, W), rng.integers(0, H), rng.integers(80, 220)
        d = np.sqrt((xx - cx) ** 2 + (yy - cy) ** 2)
        ring = np.exp(-((d - rad) / 12) ** 2) * 4 + (d < rad) * 2
        img -= ring[..., None] * np.array([0.5, 0.8, 1.3])
    p = Image.fromarray(np.clip(img, 0, 255).astype(np.uint8))
    return p.filter(ImageFilter.GaussianBlur(0.6))


PAPER = make_paper()


def polaroid(path, width):
    ph = Image.open(path).convert("RGB")
    sc = width / ph.width; ph = ph.resize((width, int(ph.height * sc)), Image.LANCZOS)
    b, bb = 26, 110
    card = Image.new("RGBA", (width + 2 * b, ph.height + b + bb), (252, 251, 247, 255))
    card.paste(ph, (b, b))
    return card


def rotated_with_shadow(card, ang):
    pad = 40
    big = Image.new("RGBA", (card.width + 2 * pad, card.height + 2 * pad), (0, 0, 0, 0))
    sh = Image.new("RGBA", big.size, (0, 0, 0, 0))
    ImageDraw.Draw(sh).rectangle([pad + 6, pad + 14, pad + card.width + 6, pad + card.height + 14], fill=(60, 40, 20, 110))
    sh = sh.filter(ImageFilter.GaussianBlur(14))
    big.alpha_composite(sh); big.alpha_composite(card, (pad, pad))
    return big.rotate(ang, resample=Image.BICUBIC, expand=True)


# ---------------------------------------------------------------- clip writers
def write_frames(name, dur, fn):
    out = os.path.join(WD, f"{name}.mp4")
    if os.path.exists(out): return out
    n = int(round(dur * FPS))
    p = subprocess.Popen(["ffmpeg", "-y", "-v", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}",
                          "-r", str(FPS), "-i", "-", "-c:v", "libx264", "-crf", "17", "-preset", "fast",
                          "-pix_fmt", "yuv420p", out], stdin=subprocess.PIPE)
    for i in range(n):
        p.stdin.write(fn(i / FPS).convert("RGB").tobytes())
    p.stdin.close(); p.wait()
    return out


def fade_alpha(layer, a):
    if a >= 1: return layer
    l = layer.copy(); l.putalpha(layer.getchannel("A").point(lambda v: int(v * a))); return l


def video_clip(name, src, dur, start=0.0, label=None, caption=None, cap_at=0.3, z=(1.0, 1.05)):
    """Full-screen portrait footage (video or portrait photo) with gentle zoom-in + overlays."""
    out = os.path.join(WD, f"{name}.mp4")
    if os.path.exists(out): return out
    ov = BADGE.copy()
    if label: ov.alpha_composite(label_layer(label))
    ovp = save(ov, f"{name}_ov.png")
    is_img = src.lower().endswith(".jpg")
    inp = (["-loop", "1", "-framerate", str(FPS), "-t", str(dur + 0.1), "-i", src] if is_img
           else ["-ss", str(start), "-t", str(dur + 0.1), "-i", src])
    inp += ["-loop", "1", "-framerate", str(FPS), "-t", str(dur + 0.1), "-i", ovp]
    zz = f"({z[0]}+({z[1]}-{z[0]})*t/{dur})"
    fc = (f"[0:v]fps={FPS},scale={W}:{H}:force_original_aspect_ratio=increase,"
          f"scale=w='trunc(iw*{zz}/2)*2':h='trunc(ih*{zz}/2)*2':eval=frame,crop={W}:{H},"
          f"eq=saturation=1.08:brightness=0.02[v];[v][1:v]overlay=0:0[b]")
    last = "[b]"
    if caption:
        cp = save(caption_layer(caption), f"{name}_cap.png")
        inp += ["-loop", "1", "-framerate", str(FPS), "-t", str(dur + 0.1), "-i", cp]
        fc += (f";[2:v]format=rgba,fade=in:st={cap_at}:d=0.45:alpha=1[c];"
               f"[b][c]overlay=x=0:y='if(lt(t,{cap_at}),24,max(0,24-(t-{cap_at})*55))'[b2]")
        last = "[b2]"
    fc += f";{last}format=yuv420p,trim=duration={dur},setpts=PTS-STARTPTS[o]"
    run(["ffmpeg", "-y", "-v", "error", *inp, "-filter_complex", fc, "-map", "[o]", "-an",
         "-r", str(FPS), "-c:v", "libx264", "-crf", "17", "-preset", "fast", out])
    return out


def collage_clip(name, photos, dur, label=None, caption=None, cap_at=None):
    """Photos land one by one as polaroids on old paper, stacking on the same screen."""
    n = len(photos)
    slots = {2: [(540, 640), (540, 1230)],
             3: [(470, 560), (610, 1000), (480, 1420)],
             4: [(450, 500), (630, 860), (450, 1220), (620, 1540)],
             5: [(440, 470), (640, 780), (450, 1080), (640, 1380), (520, 1620)]}[n]
    cards = []
    for i, ph in enumerate(photos):
        ang = random.uniform(3, 7) * (-1 if i % 2 else 1)
        card = rotated_with_shadow(polaroid(ph, 720 if n <= 3 else 660), ang)
        cards.append(card)
    step = min(0.85, (dur - 1.4) / max(n - 1, 1))
    starts = [0.15 + i * step for i in range(n)]
    lab = label_layer(label) if label else None
    cap = caption_layer(caption, yc=1650 if n >= 4 else 1700, size=110) if caption else None
    cap_at = cap_at if cap_at is not None else starts[-1] + 0.4

    def fn(t):
        z = 1.0 + 0.03 * t / dur
        bg = PAPER.resize((int(W * z), int(H * z)), Image.BILINEAR)
        fr = bg.crop(((bg.width - W) // 2, (bg.height - H) // 2, (bg.width - W) // 2 + W, (bg.height - H) // 2 + H)).convert("RGBA")
        for (cx, cy), card, st in zip(slots, cards, starts):
            if t < st: continue
            p = ease_out((t - st) / 0.55)
            s = 1.18 - 0.18 * p
            c = card.resize((max(1, int(card.width * s)), max(1, int(card.height * s))), Image.BILINEAR) if p < 1 else card
            c = fade_alpha(c, min(1, p * 1.6))
            yoff = int(-50 * (1 - p))
            fr.alpha_composite(c, (int(cx - c.width / 2), int(cy - c.height / 2 + yoff)))
        if lab: fr.alpha_composite(fade_alpha(lab, ease_out((t - 0.2) / 0.4)))
        if cap and t >= cap_at:
            a = ease_out((t - cap_at) / 0.45)
            fr.alpha_composite(fade_alpha(cap, a), (0, int(22 * (1 - a))))
        fr.alpha_composite(BADGE)
        return fr
    return write_frames(name, dur, fn)


def counter_clip(name, dur):
    """Brand gradient, big number counting up fast: 1 -> 5 (şehir) -> 11 (il)."""
    fnum = ImageFont.truetype(ANTON, 640)
    keys = [(0.0, 1)]
    t = 0.75
    for v in range(2, 6): keys.append((t, v)); t += 0.2
    t += 0.55
    for v in range(6, 12): keys.append((t, v)); t += 0.13
    t_final = keys[-1][0]
    labs = {k: caption_layer([(w, True)], yc=1400, size=120) for k, w in (("s", "şehir"), ("i", "il"))}
    top_s = caption_layer([("sonra", False)], yc=520, size=110)
    top_b = caption_layer([("bugün", False)], yc=520, size=110)

    def fn(tt):
        fr = grad_frame(tt, dur).convert("RGBA")
        cur, t0 = 1, 0.0
        for kt, v in keys:
            if tt >= kt: cur, t0 = v, kt
        pop = 1 + 0.12 * (1 - ease_out((tt - t0) / 0.18))
        txt = str(cur)
        L = Image.new("RGBA", (W, H), (0, 0, 0, 0)); d = ImageDraw.Draw(L)
        bb = d.textbbox((0, 0), txt, font=fnum); tw, th = bb[2] - bb[0], bb[3] - bb[1]
        d.text(((W - tw) / 2 - bb[0], 930 - th / 2 - bb[1]), txt, font=fnum, fill=(255, 255, 255, 255))
        if pop > 1.001:
            L = L.resize((int(W * pop), int(H * pop)), Image.BILINEAR)
            L = L.crop(((L.width - W) // 2, int(930 * pop - 930), (L.width - W) // 2 + W, int(930 * pop - 930) + H))
        sh = L.getchannel("A").filter(ImageFilter.GaussianBlur(16)).point(lambda v: int(v * 0.35))
        shadow = Image.new("RGBA", (W, H), (0, 0, 0, 0)); shadow.putalpha(sh)
        fr.alpha_composite(shadow, (0, 10)); fr.alpha_composite(L)
        fr.alpha_composite(fade_alpha(labs["i" if tt >= t_final else "s"], ease_out(tt / 0.35)))
        if 0.75 <= tt < t_final: fr.alpha_composite(fade_alpha(top_s, ease_out((tt - 0.75) / 0.3)))
        if tt >= t_final: fr.alpha_composite(fade_alpha(top_b, ease_out((tt - t_final) / 0.3)))
        fr.alpha_composite(BADGE)
        return fr
    return write_frames(name, dur, fn)


def students_clip(name, dur):
    """Gradient card: 25.000+ counts up, then 'öğrenci ve' / [dev bir aile.]"""
    fnum = ImageFont.truetype(ANTON, 300)
    rest = caption_layer([("öğrenci ve", False), ("dev bir aile.", True)], yc=1240, size=124)

    def fn(t):
        fr = grad_frame(t + 3, dur + 6).convert("RGBA")
        v = int(round(25000 * ease_out(t / 1.4) / 100)) * 100
        txt = f"{v:,}".replace(",", ".") + ("+" if t >= 1.4 else "")
        L = Image.new("RGBA", (W, H), (0, 0, 0, 0)); d = ImageDraw.Draw(L)
        tw = d.textlength(txt, font=fnum)
        d.text(((W - tw) / 2, 640), txt, font=fnum, fill=(255, 255, 255, 255))
        sh = L.getchannel("A").filter(ImageFilter.GaussianBlur(14)).point(lambda a: int(a * 0.35))
        s = Image.new("RGBA", (W, H), (0, 0, 0, 0)); s.putalpha(sh)
        fr.alpha_composite(s, (0, 8)); fr.alpha_composite(L)
        if t >= 1.0:
            a = ease_out((t - 1.0) / 0.5); fr.alpha_composite(fade_alpha(rest, a), (0, int(24 * (1 - a))))
        fr.alpha_composite(BADGE)
        return fr
    return write_frames(name, dur, fn)


def hook_clip(name, dur):
    c1 = caption_layer([("birkaç lise öğrencisiyle", False), ("yola çıktığımızda...", True)], yc=900, size=118)
    c2 = caption_layer([("nereden", False), ("nereye.", True)], yc=1080, size=150)

    def fn(t):
        fr = grad_frame(t, dur).convert("RGBA")
        if t < 2.2:
            a = ease_out((t - 0.2) / 0.5) * (1 - ease_out((t - 1.95) / 0.25))
            fr.alpha_composite(fade_alpha(c1, max(a, 0)), (0, int(24 * (1 - min(1, max(0, (t - 0.2) / 0.5))))))
        else:
            a = ease_out((t - 2.2) / 0.45)
            fr.alpha_composite(fade_alpha(c2, a), (0, int(24 * (1 - a))))
        fr.alpha_composite(BADGE)
        return fr
    return write_frames(name, dur, fn)


def closing_clip(name, dur):
    lg = LOGO.copy(); lg = lg.resize((640, int(640 * LOGO.height / LOGO.width)), Image.LANCZOS)
    f1 = ImageFont.truetype(INTER + "Inter-ExtraBold.otf", 66)
    f2 = ImageFont.truetype(INTER + "Inter-SemiBold.otf", 40)
    T = Image.new("RGBA", (W, H), (0, 0, 0, 0)); d = ImageDraw.Draw(T)
    for i, line in enumerate(["Liseliler kurdu,", "liseliler yürütüyor."]):
        tw = d.textlength(line, font=f1); d.text(((W - tw) / 2, 1080 + i * 86), line, font=f1, fill=DARK)
    hd = "@think2actorg · iletisim@think2act.org"
    tw = d.textlength(hd, font=f2); d.text(((W - tw) / 2, 1320), hd, font=f2, fill=(232, 112, 22, 255))
    strip = GRAD.resize((W, 12), Image.LANCZOS).convert("RGBA")

    def fn(t):
        fr = Image.new("RGBA", (W, H), (255, 255, 255, 255))
        p = ease_out(t / 0.8); s = 0.9 + 0.1 * p
        l = lg.resize((int(lg.width * s), int(lg.height * s)), Image.LANCZOS)
        fr.alpha_composite(fade_alpha(l, p), ((W - l.width) // 2, int(820 - l.height / 2)))
        a = ease_out((t - 0.6) / 0.6)
        if a > 0: fr.alpha_composite(fade_alpha(T, a), (0, int(20 * (1 - a))))
        fr.alpha_composite(strip, (0, H - 12))
        return fr
    return write_frames(name, dur, fn)



def preview():
    P_ = lambda n: os.path.join(MP, n)
    save(Image.alpha_composite(PAPER.convert("RGBA"), BADGE), "pv_paper.png")
    v = caption_layer([("ortada ne bütçe vardı,", False), ("ne büyük bir destek...", True)])
    bg = Image.open(P_("p_mentor.jpg")).convert("RGBA").resize((W, H))
    bg.alpha_composite(label_layer("Mobil Bilim Merkezi")); bg.alpha_composite(v); bg.alpha_composite(BADGE)
    save(bg, "pv_caption.png")

if __name__ == "__main__" and len(sys.argv) > 1 and sys.argv[1] == "preview":
    preview(); sys.exit(0)

if __name__ == "__main__":
    # ================================================================ timeline
    V = lambda n: os.path.join(MV, n)
    P = lambda n: os.path.join(MP, n)
    C = lambda *l: list(l)

    TL = [  # (section, builder)
        ("hook", lambda: hook_clip("s00_hook", 4.2)),
        # ---------------- HATAY
        ("hatay", lambda: video_clip("s01", V("v_0824.mp4"), 2.6, 0.0, label="Hatay",
                                     caption=C(("ortada ne bütçe vardı,", False), ("ne büyük bir destek...", True)))),
        ("hatay", lambda: video_clip("s02", V("v_5492.mp4"), 2.4, 1.4, label="Hatay",
                                     caption=C(("sadece", False), ("koca bir hayal.", True)), cap_at=0.25)),
        ("hatay", lambda: video_clip("s03", P("p_shelving.jpg"), 1.8, label="Hatay")),
        ("hatay", lambda: video_clip("s04", V("v_0674.mov"), 2.0, 0.3, label="İlk kütüphanemiz")),
        ("hatay", lambda: video_clip("s05", V("v_85ca.mp4"), 2.6, 0.2, label="Hatay",
                                     caption=C(("bu, bizim üstümüze", False), ("düşen bir görevdi.", True)), cap_at=0.25)),
        ("hatay", lambda: collage_clip("s06_col_hatay", [P("p_libgroup.jpg"), P("p_school.jpg"), P("p_a1.jpg"), P("p_music.jpg")],
                                       4.8, label="Hatay")),
        ("hatay", lambda: video_clip("s07", V("v_083b.mp4"), 2.4, 9.3, label="Hatay",
                                     caption=C(("ve", False), ("kolları sıvadık.", True)), cap_at=0.25)),
        ("hatay", lambda: video_clip("s08", P("p_mentor.jpg"), 1.8, label="Hatay")),
        ("hatay", lambda: video_clip("s09", P("p_hatay1.jpg"), 2.0, label="Mobil Bilim Merkezi")),
        ("hatay", lambda: video_clip("s10", P("p_a33.jpg"), 2.0, label="Robotik")),
        # ---------------- COUNTER
        ("counter", lambda: counter_clip("s11_counter", 4.4)),
        # ---------------- 2026
        ("y2026", lambda: video_clip("s12", P("t_8051.jpg"), 2.6, label="Trabzon",
                                     caption=C(("bu yıl yine", False), ("yollardayız.", True)), cap_at=0.25)),
        ("y2026", lambda: video_clip("s13", P("t_8370.jpg"), 2.0, label="Robotik atölyeleri")),
        ("y2026", lambda: collage_clip("s14_col_trabzon", [P("t_7974.jpg"), P("t_8133.jpg"), P("t_8252.jpg")], 4.2,
                                       label="Trabzon")),
        ("y2026", lambda: video_clip("s15", P("t_8504.jpg"), 2.0, label="Mobil Bilim Merkezi")),
        ("y2026", lambda: video_clip("s16", V("r_8441.mov"), 2.4, 1.0, label="Rize",
                                     caption=C(("her sınıfta", False), ("yeni bir merak.", True)), cap_at=0.3)),
        ("y2026", lambda: video_clip("s17", V("r_8442.mov"), 2.2, 2.0, label="Rize")),
        ("y2026", lambda: video_clip("s18", V("g_4419.mov"), 2.6, 0.4, label="Gümüşhane",
                                     caption=C(("sıra", False), ("turnuvada.", True)), cap_at=0.3)),
        ("y2026", lambda: video_clip("s19", V("g_4463.mov"), 2.0, 0.2, label="Gümüşhane")),
        ("y2026", lambda: video_clip("s20b", V("g_4420.mov"), 2.6, 0.6, label="Gümüşhane",
                                 caption=C(("kağıt üzerinde değil,", False), ("sahada.", True)), cap_at=0.3)),
        ("y2026", lambda: collage_clip("s21b_col_kd", [P("k_4f4d.jpg"), P("k_917e.jpg"), P("d_9755.jpg"), P("d_9688.jpg")], 5.0,
                                       label="Kastamonu · Düzce")),
        # ---------------- PEAK + CLOSE
        ("peak", lambda: students_clip("s22_students", 4.0)),
        ("close", lambda: closing_clip("s23_close", 4.6)),
    ]

    clips, secs = [], []
    for sec, b in TL:
        clips.append(b()); secs.append(sec)
        print("ok", clips[-1].rsplit("/", 1)[-1], flush=True)


    def dur_of(p):
        return float(subprocess.check_output(["ffprobe", "-v", "error", "-show_entries", "format=duration",
                                              "-of", "csv=p=0", p]))

    durs = [dur_of(c) for c in clips]
    starts, t = [], 0.0
    for i, d in enumerate(durs):
        starts.append(t); t += d - (XF if i < len(durs) - 1 else 0)
    total = t
    sections = {}
    for s, st in zip(secs, starts):
        sections.setdefault(s, st)
    sections["total"] = total
    json.dump(sections, open(os.path.join(WD, "sections.json"), "w"), indent=1)
    print(sections)

    inp, fc, prev, off = [], "", "[0:v]", 0.0
    for c in clips: inp += ["-i", c]
    for i in range(1, len(clips)):
        off += durs[i - 1] - XF
        fc += f"{prev}[{i}:v]xfade=transition=fade:duration={XF}:offset={off:.3f}[x{i}];"
        prev = f"[x{i}]"
    final = os.path.join(WD, "reel3_silent.mp4")
    run(["ffmpeg", "-y", "-v", "error", *inp, "-filter_complex", fc + f"{prev}format=yuv420p[o]", "-map", "[o]",
         "-c:v", "libx264", "-crf", "18", "-preset", "medium", final])
    print("done", dur_of(final))
