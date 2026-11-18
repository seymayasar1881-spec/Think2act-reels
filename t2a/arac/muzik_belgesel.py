"""Belgesel tarzı telifsiz müzik: piyano + yaylılar + saat + daktilo + vurgular.

Kullanım: python3 muzik_belgesel.py cikti.wav --sure 58.5 --gecisler 5,10 --vurgu 1.6,41 \
          --yukselen 52.5 --daktilo 6.1-7.9,11.1-12.9 --nabiz 21 --doruk 41
"""
import argparse
import numpy as np
from scipy.io import wavfile
from muzik import SR, hz, lp, hp, bp, add, whoosh, impact, riser

BPM = 80
BEAT = 60 / BPM
BAR = BEAT * 4
# Am - F - C - G (her ölçü bir akor)
CH = [[57, 60, 64], [53, 57, 60], [48, 52, 55], [55, 59, 62]]


def piyano(m, dur=2.5, vel=1.0):
    n = int(dur * SR)
    t = np.arange(n) / SR
    f = hz(m)
    s = np.zeros(n)
    for k, a in enumerate([1, .55, .3, .18, .1, .06], start=1):
        s += a * np.sin(2 * np.pi * f * k * (1 + 0.0004 * k * k) * t) * np.exp(-t * (1.6 + k * 0.9))
    atk = np.minimum(1, t / 0.004)
    return s * atk * vel * 0.28


def yayli(ms, dur):
    n = int(dur * SR)
    t = np.arange(n) / SR
    s = np.zeros(n)
    rng = np.random.default_rng(int(sum(ms)))
    for m in ms:
        for det in (-0.08, 0, 0.08):
            f = hz(m) * 2 ** (det / 12) * (1 + 0.002 * np.sin(2 * np.pi * 5.2 * t + rng.random() * 6))
            s += 2 * ((np.cumsum(f) / SR + rng.random()) % 1) - 1
    s = lp(s, 1400)
    e = np.minimum(1, t / 0.9) * np.minimum(1, (dur - t) / 0.9)
    return s * e / (len(ms) * 3) * 0.5


def tik(rng, hi=True):
    n = int(0.03 * SR)
    return hp(rng.standard_normal(n), 3000 if hi else 1800) * np.exp(-np.arange(n) / SR * 260) * 0.22


def tus(rng):
    n = int(0.05 * SR)
    t = np.arange(n) / SR
    clack = bp(rng.standard_normal(n), 1500, 6000) * np.exp(-t * 180)
    thump = np.sin(2 * np.pi * 180 * t) * np.exp(-t * 90) * 0.4
    return (clack + thump) * 0.2


def nabiz_sesi():
    n = int(0.6 * SR)
    t = np.arange(n) / SR
    f = 50 + 40 * np.exp(-t * 20)
    return np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t * 7) * 0.7


def build(total, gecis, vurgu, yuk, daktilo, nabiz, doruk):
    rng = np.random.default_rng(3)
    n = int(total * SR)
    mus = np.zeros(n)
    fx = np.zeros(n)
    end = total - 0.8
    nbars = int(np.ceil(end / BAR))
    for b in range(nbars):
        t0 = b * BAR
        ch = CH[b % 4]
        # piyano arpeji (sekizlik), ilerledikçe yoğunlaşır
        pat = [0, 1, 2, 1, 0 + 3, 2, 1, 2]
        for i in range(8):
            ti = t0 + i * BEAT / 2
            if ti >= end:
                break
            idx = pat[i]
            m = ch[idx % 3] + (12 if idx >= 3 else 0)
            vel = 0.75 + 0.25 * (i % 4 == 0)
            if ti < 5 and i % 2:
                continue  # açılışta seyrek
            add(mus, piyano(m, vel=vel), ti)
        add(mus, piyano(ch[0] - 12, 4, 0.9), t0)  # bas notası
        if t0 >= 4.5:
            add(mus, yayli([c - 12 for c in ch] + [ch[0] + 12], BAR + 0.9), t0 - 0.3)
        if t0 >= doruk - 0.1:
            add(mus, yayli([ch[0] + 12, ch[2] + 12], BAR + 0.9) * 0.8, t0 - 0.3)
    # nabız: yolculuk hızlanırken davul gibi
    b = 0
    while True:
        ti = nabiz + b * BEAT
        if ti >= end - 1:
            break
        g = 0.5 if ti < doruk else 1.0
        add(mus, nabiz_sesi() * g, ti)
        if ti >= doruk:
            add(mus, nabiz_sesi() * 0.5, ti + BEAT / 2)
        b += 1
    # saat tiktakları: açılış ve harita sahneleri boyunca hafifçe
    k = 0
    while k * 0.5 < min(end, doruk):
        add(fx, tik(rng, k % 2 == 0) * (1.0 if k * 0.5 < 5 else 0.45), k * 0.5)
        k += 1
    for a, z in daktilo:
        ti = a
        while ti < z:
            add(fx, tus(rng), ti)
            ti += 0.05 + rng.random() * 0.06
    for t in gecis:
        add(fx, whoosh(rng, 0.7) * 0.6, max(0, t - 0.4))
    for t in vurgu:
        add(fx, impact(rng), t)
    for t in yuk:
        add(fx, riser(rng, 2.5) * 0.8, max(0, t - 2.5))
    # son akor
    for m in CH[0]:
        add(mus, piyano(m, 5, 0.9) + piyano(m + 12, 5, 0.5), end - 4.2)

    fade = np.ones(n)
    a, z = int((total - 1.4) * SR), n
    fade[a:z] = np.linspace(1, 0, z - a)
    mix = (mus * 0.85 + fx * 0.8) * fade
    mix = np.tanh(mix * 1.2) / np.tanh(1.2)
    L = mix + 0.02 * np.roll(mus, 300)
    R = mix + 0.02 * np.roll(mus, -300)
    st = np.stack([L, R], 1)
    st /= np.max(np.abs(st)) / 0.89
    return (st * 32767).astype(np.int16)


def fl(s):
    return [float(x) for x in s.split(',') if x.strip()] if s else []


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('out')
    ap.add_argument('--sure', type=float, required=True)
    ap.add_argument('--gecisler', default='')
    ap.add_argument('--vurgu', default='')
    ap.add_argument('--yukselen', default='')
    ap.add_argument('--daktilo', default='')
    ap.add_argument('--nabiz', type=float, default=20)
    ap.add_argument('--doruk', type=float, default=40)
    a = ap.parse_args()
    dk = [tuple(map(float, p.split('-'))) for p in a.daktilo.split(',') if p]
    wavfile.write(a.out, SR, build(a.sure, fl(a.gecisler), fl(a.vurgu), fl(a.yukselen), dk, a.nabiz, a.doruk))
    print('yazıldı', a.out)
