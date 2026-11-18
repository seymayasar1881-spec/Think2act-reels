"""Telifsiz müzik + efekt üretici (tamamen sentez, örnek kullanılmaz).

Kullanım: python3 muzik.py cikti.wav --sure 35 --gecisler 3,6.5,10 --vurgu 0,29 --yukselen 29
"""
import argparse
import numpy as np
from scipy.io import wavfile
from scipy.signal import butter, sosfilt

SR = 44100
BPM = 120
BEAT = 60 / BPM
BAR = BEAT * 4

# Am - F - C - G (umutlu, enerjik)
CHORDS = [
    [57, 60, 64],  # Am
    [53, 57, 60],  # F
    [48, 52, 55],  # C
    [55, 59, 62],  # G
]


def hz(m):
    return 440 * 2 ** ((m - 69) / 12)


def env_adsr(n, a=0.005, d=0.1, s=0.0, r=0.05):
    t = np.arange(n) / SR
    e = np.ones(n) * s
    na, nd = int(a * SR), int(d * SR)
    e[:na] = np.linspace(0, 1, na, endpoint=False) if na else e[:na]
    e[na:na + nd] = np.linspace(1, s, max(len(e[na:na + nd]), 1))[:len(e[na:na + nd])]
    nr = int(r * SR)
    if nr and n > nr:
        e[-nr:] *= np.linspace(1, 0, nr)
    return e


def saw(f, n, phase=0.0):
    t = np.arange(n) / SR
    return 2 * ((t * f + phase) % 1) - 1


def lp(x, fc, order=2):
    return sosfilt(butter(order, fc, 'low', fs=SR, output='sos'), x)


def hp(x, fc, order=2):
    return sosfilt(butter(order, fc, 'high', fs=SR, output='sos'), x)


def bp(x, lo, hi, order=2):
    return sosfilt(butter(order, [lo, hi], 'band', fs=SR, output='sos'), x)


def add(buf, sig, at):
    i = int(at * SR)
    if i >= len(buf):
        return
    j = min(len(buf), i + len(sig))
    buf[i:j] += sig[:j - i]


def kick():
    n = int(0.35 * SR)
    t = np.arange(n) / SR
    f = 45 + 110 * np.exp(-t * 28)
    ph = 2 * np.pi * np.cumsum(f) / SR
    return np.sin(ph) * np.exp(-t * 9) * 0.9


def hat(rng):
    n = int(0.06 * SR)
    return hp(rng.standard_normal(n), 7000) * np.exp(-np.arange(n) / SR * 70) * 0.18


def clap(rng):
    n = int(0.22 * SR)
    t = np.arange(n) / SR
    e = np.exp(-t * 22) + 0.6 * np.exp(-((t - 0.012) % 0.011) * 300) * (t < 0.035)
    return bp(rng.standard_normal(n), 900, 4000) * e * 0.35


def whoosh(rng, dur=0.7, up=True):
    n = int(dur * SR)
    t = np.linspace(0, 1, n)
    noise = rng.standard_normal(n)
    out = np.zeros(n)
    # kaba zamanla değişen bant geçiren: parçalara bölüp farklı merkezlerle filtrele
    seg = 12
    edges = np.linspace(0, n, seg + 1, dtype=int)
    for k in range(seg):
        c = (k + 0.5) / seg
        fc = 400 * (12 ** (c if up else 1 - c))
        part = bp(noise, fc * 0.6, min(fc * 1.6, SR / 2 - 100))[edges[k]:edges[k + 1]]
        out[edges[k]:edges[k + 1]] = part
    e = np.sin(np.pi * t) ** 2
    return out * e * 0.5


def impact(rng):
    n = int(1.6 * SR)
    t = np.arange(n) / SR
    f = 30 + 70 * np.exp(-t * 6)
    boom = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t * 2.2)
    crash = lp(rng.standard_normal(n), 6000) * np.exp(-t * 3.5) * 0.25
    return (boom * 0.9 + crash) * 0.8


def riser(rng, dur=2.0):
    n = int(dur * SR)
    t = np.linspace(0, 1, n)
    w = whoosh(rng, dur, up=True) * (t ** 1.5) * 2
    tone = np.sin(2 * np.pi * np.cumsum(200 * 4 ** t) / SR) * t ** 2 * 0.12
    return w + tone


def pop():
    n = int(0.12 * SR)
    t = np.arange(n) / SR
    return np.sin(2 * np.pi * (900 + 1400 * t) * t) * np.exp(-t * 40) * 0.25


def build(total, transitions, impacts, risers, pops):
    rng = np.random.default_rng(7)
    n = int(total * SR)
    drums = np.zeros(n)
    bass = np.zeros(n)
    pad = np.zeros(n)
    arp = np.zeros(n)
    fx = np.zeros(n)
    duck = np.ones(n)

    K, music_end = kick(), total - 1.2
    nbeats = int(music_end / BEAT)
    for b in range(nbeats):
        t0 = b * BEAT
        bar = b // 4
        # ilk 2 vuruş sadece pad + vurgu, sonra davul girer
        if t0 >= 1.0:
            add(drums, K, t0)
            i = int(t0 * SR)
            dn = int(0.25 * SR)
            duck[i:i + dn] = np.minimum(duck[i:i + dn], 1 - 0.55 * np.exp(-np.arange(min(dn, n - i)) / SR * 14))
            add(drums, hat(rng), t0 + BEAT / 2)
            if b % 2 == 1:
                add(drums, clap(rng), t0)
            if t0 > 6:
                add(drums, hat(rng) * 0.5, t0 + BEAT / 4)
                add(drums, hat(rng) * 0.5, t0 + 3 * BEAT / 4)
        # bas: sekizlik notalar
        ch = CHORDS[(bar // 1) % 4]
        if t0 >= 1.0:
            for h in range(2):
                m = ch[0] - 24 + (12 if h == 1 else 0)
                bn = int(BEAT / 2 * SR)
                s = saw(hz(m), bn) * env_adsr(bn, 0.004, 0.18, 0.3, 0.03)
                add(bass, s, t0 + h * BEAT / 2)
        # arp: onaltılıklar, 3. saniyeden sonra
        if t0 >= 3.0:
            for q in range(4):
                m = ch[(b * 4 + q) % 3] + 12 + (12 if q == 3 else 0)
                an = int(BEAT / 4 * SR)
                s = (saw(hz(m), an) * 0.5 + np.sin(2 * np.pi * hz(m) * np.arange(an) / SR)) * env_adsr(an, 0.002, 0.09, 0.0, 0.01)
                add(arp, s, t0 + q * BEAT / 4)

    # pad: her ölçü bir akor
    nbars = int(np.ceil(music_end / BAR))
    for bar in range(nbars):
        ch = CHORDS[bar % 4]
        pn = int(BAR * SR) + int(0.3 * SR)
        s = np.zeros(pn)
        for m in ch:
            for det in (-0.12, 0.0, 0.12):
                s += saw(hz(m + 12) * 2 ** (det / 12), pn, phase=rng.random())
        s = lp(s, 1800) * env_adsr(pn, 0.25, 0.4, 0.7, 0.35) / 9
        add(pad, s, bar * BAR)

    bass = lp(bass, 600) * 0.45
    arp = lp(arp, 4500) * 0.10
    music = (drums * 0.9 + (bass + pad * 0.55 + arp) * duck)
    # müziğin sonunu yumuşat
    fade = np.ones(n)
    fs, fe = int((music_end - 0.6) * SR), int((music_end + 0.4) * SR)
    fade[fs:fe] = np.linspace(1, 0, fe - fs)
    fade[fe:] = 0
    music *= fade

    for t in transitions:
        add(fx, whoosh(rng, 0.6), max(0, t - 0.35))
    for t in impacts:
        add(fx, impact(rng), t)
    for t in risers:
        add(fx, riser(rng, 2.0), max(0, t - 2.0))
    for t in pops:
        add(fx, pop(), t)

    mix = music * 0.8 + fx * 0.9
    mix = np.tanh(mix * 1.3) / np.tanh(1.3)
    mix /= max(1e-9, np.max(np.abs(mix))) / 0.89
    # hafif stereo: arp ve efektleri biraz aç
    L = mix + 0.04 * np.roll(arp, 200)
    R = mix + 0.04 * np.roll(arp, -200)
    st = np.stack([L, R], axis=1)
    st /= np.max(np.abs(st)) / 0.89
    return (st * 32767).astype(np.int16)


def floats(s):
    return [float(x) for x in s.split(',') if x.strip()] if s else []


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('out')
    ap.add_argument('--sure', type=float, required=True)
    ap.add_argument('--gecisler', default='')
    ap.add_argument('--vurgu', default='')
    ap.add_argument('--yukselen', default='')
    ap.add_argument('--pop', default='')
    a = ap.parse_args()
    wavfile.write(a.out, SR, build(a.sure, floats(a.gecisler), floats(a.vurgu), floats(a.yukselen), floats(a.pop)))
    print('yazıldı', a.out)
