"""Sound for the reel: synthesized effects on the cue sheet + a temporary music bed.

All times come from audio/timing.json (written by timing.py). Effects follow the
approved recipes (tick / click / swell / thud / slide). The music bed is a simple
120 BPM uplifting progression (D - A - Bm - G) so the cuts can be judged on the
beat; replace it with a licensed track before publishing (see README).

Outputs (48 kHz):
  audio/sfx.wav         effects only
  audio/music_temp.wav  temporary music bed
  audio/mix.wav         music x.55 + sfx x.45, loudness-normalised later by make.sh
"""

import json
import wave
from pathlib import Path

import numpy as np
from scipy.signal import butter, sosfilt

SR = 48000
ROOT = Path(__file__).resolve().parent.parent
rng = np.random.default_rng(7)  # deterministic


def bp(x, lo, hi):
    return sosfilt(butter(2, [lo, hi], "bandpass", fs=SR, output="sos"), x)


def lp(x, f):
    return sosfilt(butter(2, f, "lowpass", fs=SR, output="sos"), x)


def hp(x, f):
    return sosfilt(butter(2, f, "highpass", fs=SR, output="sos"), x)


def env(n, a, d):
    t = np.arange(n) / SR
    e = np.minimum(t / max(a, 1e-4), 1.0) * np.exp(-np.maximum(t - a, 0) / max(d, 1e-4) * 5)
    return e


def norm(x):
    m = np.abs(x).max()
    return x / m if m else x


# ---------------- effects (approved recipes) ----------------
def tick(bright=4500):
    n = int(.012 * SR)
    return norm(bp(rng.standard_normal(n), bright * .5, bright * 1.6) * env(n, .0005, .011))


def click():
    a, b = tick(5200), tick(3200) * .6
    out = np.zeros(int(.03 * SR))
    out[:len(a)] += a
    o = int(.011 * SR)
    out[o:o + len(b)] += b
    return norm(out)


def swell(d=0.5, f0=60, f1=85):
    n = int(d * SR)
    t = np.arange(n) / SR
    f = np.linspace(f0, f1, n)
    s = np.sin(2 * np.pi * np.cumsum(f) / SR) + .35 * lp(rng.standard_normal(n), 300)
    return norm(s * np.sin(np.pi * t / d) ** 2)


def thud(f=68):
    n = int(.22 * SR)
    t = np.arange(n) / SR
    fr = f * (1 - .25 * t / .22)
    body = np.sin(2 * np.pi * np.cumsum(fr) / SR) * np.exp(-22 * t)
    slap = bp(rng.standard_normal(n), 400, 2500) * np.exp(-60 * t) * .5
    return norm(body + slap)


def slide(d=.22):
    n = int(d * SR)
    t = np.arange(n) / SR
    return norm(bp(rng.standard_normal(n), 1500, 6000) * np.sin(np.pi * t / d) ** 1.5) * .6


def place(buf, x, t, gain, pan=0.0):
    i = int(t * SR)
    if i < 0:
        x, i = x[-i:], 0
    j = min(len(buf), i + len(x))
    l, r = np.sqrt(.5 * (1 - pan)), np.sqrt(.5 * (1 + pan))
    buf[i:j, 0] += x[:j - i] * gain * l * 1.414
    buf[i:j, 1] += x[:j - i] * gain * r * 1.414


def build_sfx(T):
    buf = np.zeros((int(T["duration"] * SR) + SR, 2))
    gen = {"tick": tick, "click": click, "swell": swell, "thud": thud, "slide": slide}
    for cue in T["cues"]:
        if cue[0] == "counter":
            _, t0, t1, g, _note = cue
            k, t = 0, t0
            while t < t1:
                place(buf, tick(3800 + (k % 4) * 400), t, g, pan=.3 * np.sin(k * .7))
                t += .035
                k += 1
            continue
        t, kind, g, _note = cue
        place(buf, gen[kind](), t, g)
    return buf


# ---------------- temporary music bed ----------------
def note(f, n, harmonics=6, detune=0.0):
    t = np.arange(n) / SR
    out = np.zeros(n)
    for h in range(1, harmonics + 1):
        out += np.sin(2 * np.pi * f * h * (1 + detune) * t) / h
    return out


def build_music(T):
    beat, dur, drop = T["beat"], T["duration"], T["drop"]
    n = int(dur * SR) + SR
    L = np.zeros(n)
    bar = 4 * beat
    roots = [73.42, 55.0, 61.74, 49.0]                 # D A Bm G (bass)
    chords = [[293.7, 370.0, 440.0], [277.2, 329.6, 440.0], [293.7, 370.0, 493.9], [293.7, 392.0, 493.9]]
    nbars = int(np.ceil(dur / bar))
    pump = np.ones(n)
    for b in range(int(dur / beat)):
        t = b * beat
        i = int(t * SR)
        if t >= drop:
            k = int(.25 * SR)
            tt = np.arange(k) / SR
            kick = np.sin(2 * np.pi * np.cumsum(50 + 70 * np.exp(-tt * 30)) / SR) * np.exp(-tt * 9)
            L[i:i + k] += kick[:len(L[i:i + k])] * .9
            p = np.linspace(.45, 1, int(.22 * SR)) ** 1.5
            pump[i:i + len(p)] = np.minimum(pump[i:i + len(p)], p)
            if b % 2 == 1:
                k2 = int(.18 * SR)
                tt = np.arange(k2) / SR
                sn = (bp(rng.standard_normal(k2), 1200, 6000) * .7 + np.sin(2 * np.pi * 190 * tt) * .5) * np.exp(-tt * 22)
                L[i:i + k2] += sn * .45
        for half in (0, .5):                            # hats on eighths after drop
            if t >= drop:
                k3 = int(.04 * SR)
                j = int((t + half * beat) * SR)
                L[j:j + k3] += hp(rng.standard_normal(k3), 7000) * env(k3, .001, .035) * .12
    pad = np.zeros(n)
    bass = np.zeros(n)
    pluck = np.zeros(n)
    for b in range(nbars):
        t0 = b * bar
        i0 = int(t0 * SR)
        m = int(bar * SR)
        ch = chords[b % 4]
        seg = sum(note(f, m, 5, d) for f in ch for d in (-.004, .004)) / 6
        pad[i0:i0 + m] += seg[:len(pad[i0:i0 + m])]
        for e in range(8):                              # bass eighths
            j = int((t0 + e * beat / 2) * SR)
            k = int(beat / 2 * SR * .9)
            x = note(roots[b % 4], k, 8) * env(k, .004, .18)
            if t0 + e * beat / 2 >= drop - beat * 2:
                bass[j:j + k] += x[:len(bass[j:j + k])]
        for s in range(16):                             # 16th plucks, arpeggio
            j = int((t0 + s * beat / 4) * SR)
            k = int(.16 * SR)
            f = ch[s % 3] * (2 if s % 4 == 3 else 1)
            pluck[j:j + k] += (note(f, k, 3) * env(k, .002, .08))[:len(pluck[j:j + k])]
    # intro: pad opens up towards the drop
    t = np.arange(n) / SR
    pad = lp(pad, 2600) * np.where(t < drop, .55 + .45 * t / drop, 1.0)
    pad_intro = lp(pad, 700)
    pad = np.where(t < drop, pad_intro * (1 - t / drop) + pad * (t / drop), pad)
    music = L + lp(bass, 420) * .55 + np.tanh(pad * 1.6) * .32 * pump + lp(pluck, 5000) * .14 * pump
    # soft low riser into the drop, and crashes on section peaks
    rn = int(2 * SR)
    ri = int((drop - 2) * SR)
    music[ri:ri + rn] += lp(rng.standard_normal(rn), 900) * np.linspace(0, 1, rn) ** 2 * .12
    for tc in T["peaks"]:
        k = int(1.6 * SR)
        j = int(tc * SR)
        music[j:j + k] += hp(rng.standard_normal(k), 5000) * np.exp(-np.arange(k) / SR * 3) * .18
    # fade out over the last 2.2 s
    fade = np.clip((dur - t) / (dur - T["musicFadeAt"]), 0, 1)
    music *= fade
    music[t > dur] = 0
    st = np.stack([music, music], 1)
    return st


def write(path, x):
    x = np.clip(x, -1, 1)
    with wave.open(str(path), "wb") as w:
        w.setnchannels(2)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes((x * 32767).astype("<i2").tobytes())


def main():
    T = json.loads((ROOT / "audio" / "timing.json").read_text(encoding="utf-8"))
    n = int(T["duration"] * SR)
    sfx = build_sfx(T)[:n]
    mus = build_music(T)[:n]
    sfx_n = sfx / max(np.abs(sfx).max(), 1e-6) * .9
    mus_n = mus / max(np.abs(mus).max(), 1e-6) * .9
    write(ROOT / "audio" / "sfx.wav", sfx_n)
    write(ROOT / "audio" / "music_temp.wav", mus_n)
    mix = mus_n * .55 + sfx_n * .45
    write(ROOT / "audio" / "mix.wav", mix / np.abs(mix).max() * .9)
    print("wrote sfx.wav, music_temp.wav, mix.wav", f"{n / SR:.1f}s")


if __name__ == "__main__":
    main()
