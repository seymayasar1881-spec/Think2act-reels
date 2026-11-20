#!/usr/bin/env python3
"""Soft, warm, hopeful original track (~92 BPM) shaped to the reel's sections (work3/sections.json)."""
import numpy as np, wave, os, json, sys

HERE = os.path.dirname(os.path.abspath(__file__))
sec = json.load(open(os.path.join(HERE, "work3", "sections.json")))
DUR = sec["total"]
SR = 44100; N = int(SR * DUR)
BPM = 92; BEAT = 60 / BPM; BAR = 4 * BEAT
rng = np.random.default_rng(5)
out = os.path.join(HERE, "work3", "music_soft.wav")
T_H, T_C, T_Y, T_P, T_E = sec["hatay"], sec["counter"], sec["y2026"], sec["peak"], sec["close"]


def midi(n): return 440.0 * 2 ** ((n - 69) / 12)
def buf(): return np.zeros(N)
def add(dst, sig, t0):
    i = int(t0 * SR)
    if i >= N or i < 0: return
    j = min(N, i + len(sig)); dst[i:j] += sig[: j - i]
def lp(x, hi=None, lo=None):
    X = np.fft.rfft(x); fr = np.fft.rfftfreq(len(x), 1 / SR); g = np.ones_like(fr)
    if lo: g *= 1 / np.sqrt(1 + (lo / np.maximum(fr, 1)) ** 4)
    if hi: g *= 1 / np.sqrt(1 + (fr / hi) ** 4)
    return np.fft.irfft(X * g, len(x))


def piano(freq, dur, vel=1.0):
    t = np.arange(int(SR * (dur + 2.0))) / SR
    s = sum(a * np.sin(2 * np.pi * freq * k * (1 + 0.0003 * k * k) * t) * np.exp(-t * (0.9 + 0.8 * k))
            for k, a in enumerate([1, .5, .22, .12, .06, .03], 1))
    return vel * s * np.minimum(1, t / 0.006) * np.where(t > dur, np.exp(-(t - dur) * 4), 1) * 0.3


def pad(freqs, dur, vel=1.0):
    t = np.arange(int(SR * (dur + 1.0))) / SR
    s = np.zeros_like(t)
    for f0 in freqs:
        for det in (-0.07, 0.0, 0.07):
            f = f0 * 2 ** (det / 12)
            s += np.sin(2 * np.pi * f * t) + 0.3 * np.sin(2 * np.pi * 2 * f * t) + 0.1 * np.sin(2 * np.pi * 3 * f * t)
    env = np.minimum(1, t / 0.9) * np.where(t > dur, np.exp(-(t - dur) * 3), 1)
    return vel * s * env / (len(freqs) * 3) * 0.32


def mallet(freq, vel=1.0):  # soft marimba-ish
    t = np.arange(int(SR * 0.7)) / SR
    s = np.sin(2 * np.pi * freq * t) * np.exp(-t * 7) + 0.25 * np.sin(2 * np.pi * 4 * freq * t) * np.exp(-t * 25)
    return vel * s * np.minimum(1, t / 0.003) * 0.22


def bass(freq, dur, vel=1.0):
    t = np.arange(int(SR * dur)) / SR
    s = np.sin(2 * np.pi * freq * t) + 0.2 * np.sin(2 * np.pi * 2 * freq * t)
    return vel * s * np.minimum(1, t / 0.02) * np.minimum(1, (dur - t) / 0.05) * np.exp(-t * 0.8) * 0.42


def kick(vel=1.0):
    t = np.arange(int(SR * 0.35)) / SR
    f = 50 + 60 * np.exp(-t * 25)
    return vel * np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t * 9) * 0.55


def shaker(vel=1.0):
    n = int(SR * 0.09); t = np.arange(n) / SR
    return vel * lp(rng.standard_normal(n), lo=5000) * np.minimum(1, t / 0.015) * np.exp(-t * 45) * 0.07


def snap(vel=1.0):
    n = int(SR * 0.18); t = np.arange(n) / SR
    return vel * lp(rng.standard_normal(n), hi=4500, lo=1200) * np.exp(-t * 35) * 0.14


def swell(dur, vel=1.0):  # soft cymbal swell
    n = int(SR * dur); t = np.arange(n) / SR
    return vel * lp(rng.standard_normal(n), hi=9000, lo=3000) * (t / dur) ** 2.5 * 0.05


# I–V–vi–IV in D major (warm, hopeful)
PROG = [(50, [62, 66, 69]), (45, [61, 64, 69]), (47, [62, 66, 71]), (43, [62, 67, 71])]
pianoB, padB, malB, bassB, drB, fxB = (buf() for _ in range(6))
kenv = buf()

nb = int(DUR / BAR) + 2
for b in range(nb):
    t0 = b * BAR
    if t0 > DUR: break
    root, ch = PROG[b % 4]
    s = ("hook" if t0 < T_H - 0.5 else "hatay" if t0 < T_C - 0.5 else "counter" if t0 < T_Y - 0.5
         else "y" if t0 < T_P - 0.5 else "peak" if t0 < T_E - 0.5 else "close")
    if s == "close": continue
    # piano: broken chord, always
    patt = [0, 1, 2, 1, 0, 2, 1, 2] if s != "hook" else [0, 1, 2, 1]
    step = BAR / len(patt)
    for i, k in enumerate(patt):
        add(pianoB, piano(midi(ch[k]), step * 1.8, 0.55 if s != "hook" else 0.6), t0 + i * step)
    add(pianoB, piano(midi(root), BAR, 0.6), t0)
    # pad from hatay on
    if s != "hook":
        add(padB, pad([midi(n) for n in ch] + [midi(root + 12)], BAR, 0.7 if s == "hatay" else 1.0), t0)
    # mallet melody in y/peak
    if s in ("y", "peak", "counter"):
        mel = [ch[2] + 12, ch[1] + 12, ch[2] + 12, ch[0] + 24, ch[2] + 12, ch[1] + 12]
        for i, n in enumerate(mel):
            add(malB, mallet(midi(n), 0.7 if s != "counter" else 0.45), t0 + i * BEAT * 2 / 3)
    # bass
    if s in ("y", "peak") or (s == "hatay" and t0 > T_H + 6):
        add(bassB, bass(midi(root - 12), BEAT * 2 * 0.95, 0.8), t0)
        add(bassB, bass(midi(root - 12), BEAT * 2 * 0.95, 0.7), t0 + 2 * BEAT)
    # drums (soft)
    for q in range(4):
        tb = t0 + q * BEAT
        if s == "hatay" and t0 > T_H + 6:
            if q in (0, 2): add(drB, kick(0.6), tb); add(kenv, np.exp(-np.arange(int(SR * .25)) / SR * 12), tb)
            add(drB, shaker(0.7), tb + BEAT / 2)
        elif s in ("y", "peak"):
            if q in (0, 2) or (s == "peak" and q == 3 and b % 2): add(drB, kick(0.75), tb); add(kenv, np.exp(-np.arange(int(SR * .25)) / SR * 12), tb)
            if q in (1, 3): add(drB, snap(0.8 if s == "y" else 1.0), tb)
            for e in (0.25, 0.5, 0.75): add(drB, shaker(0.5 if e != 0.5 else 0.8), tb + e * BEAT)

add(fxB, swell(2.0), T_Y - 2.0)
add(fxB, swell(1.6, 0.8), T_P - 1.6)
# closing: one big warm chord
for n in (50, 57, 62, 66, 69, 74):
    add(pianoB, piano(midi(n), 3.5, 0.65), T_E - 0.1)
add(padB, pad([midi(n) for n in (62, 66, 69, 74)], 3.0, 0.8), T_E - 0.1)

duck = 1 - 0.35 * np.clip(kenv, 0, 1)
padB = lp(padB, hi=2600) * duck; bassB *= duck
mix = 0.95 * pianoB + 0.6 * padB + 0.5 * malB + 0.7 * bassB + 0.7 * drB + fxB
ir_len = int(SR * 2.6); ti = np.arange(ir_len) / SR
ir = lp(rng.standard_normal(ir_len) * np.exp(-ti * 2.4), hi=5000, lo=150)
send = pianoB + 0.6 * padB + 0.8 * malB + 0.2 * drB
L = 1 << int(np.ceil(np.log2(N + ir_len)))
wet = np.fft.irfft(np.fft.rfft(send, L) * np.fft.rfft(ir, L), L)[:N]
mix += wet / (np.abs(wet).max() + 1e-9) * np.abs(mix).max() * 0.28
d = int(SR * 0.011); wide = 0.6 * padB + 0.5 * malB
left = mix + 0.12 * wide; right = mix - 0.12 * wide + 0.12 * np.concatenate([np.zeros(d), wide[:-d]])
st = np.stack([lp(left, lo=30), lp(right, lo=30)], 1)
st /= np.abs(st).max(); st = np.tanh(st * 1.3) / np.tanh(1.3)
t = np.arange(N) / SR
st *= (np.clip(t / 0.3, 0, 1) * np.clip((DUR - t) / 2.0, 0, 1) ** 1.3)[:, None] * 0.9
with wave.open(out, "wb") as w:
    w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR); w.writeframes((st * 32767).astype(np.int16).tobytes())
print("wrote", out, DUR)
