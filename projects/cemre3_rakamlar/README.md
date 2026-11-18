# Cemre 3. Etap: rakamlarla (IG reel)

9:16, 40 sn, 120 BPM (80 vuruş). Storyboard seçimi: 1A · 2B · 3B · 4B · 6B · 7A · 8A · L2 · T1 · M1.

## Bilgiler (kaynak: kullanıcı, 2026-11-18)
- 9 il, 2 kol · 4.507 öğrenci · 18 okul
- Karadeniz 2.304: Düzce 790 · Kastamonu 368 · Trabzon 506 · Gümüşhane 554 · Rize 86
- Ege 2.203: İzmir (Ödemiş) 175 · Manisa 421 · Uşak 338 · Konya (Akşehir) 1.269
- YEĞİTEK Bilim Tırı bu etapta Kastamonu ve Düzce'de vardı.
- Etiketler: Akşehir → "Konya", İzmir → "İzmir · Ödemiş".

## Sahneler
| # | Vuruş | Sn | İçerik | Çekim |
|---|---|---|---|---|
| s1 | 8 | 0–4 | "Ekimde / 9 il." | Kastamonu foto → İzmir video |
| s2 | 12 | 4–10 | Harita, iki rota, 9 pin | marka gradyanı |
| s3 | 8 | 10–14 | 4.507 sayaç | Trabzon foto |
| s4 | 10 | 14–19 | Karadeniz 2.304 + baskılar, Bilim Tırı | Gümüşhane video → Rize, Düzce baskı → Düzce tır içi |
| s5 | 10 | 19–24 | Ege 2.203 + baskılar | Konya video → İzmir, Manisa baskı → Uşak foto |
| s6 | 12 | 24–30 | "Robot futbolu / sahada!" | Uşak foto → İzmir video |
| s7 | 8 | 30–34 | "Evet!" damgası | Düzce kutlama videosu |
| s8 | 12 | 34–40 | "Kağıt üzerinde değil, sahada." + logo | Konya foto |

## Kurulum
```
tools/timing.py   tek zaman kaynağı → assets/timing.js + audio/timing.json
tools/prep.py     fotoğraf kırpma (yüz merkezli) + L2 grade, video HDR→SDR, kesim, 1080x1920@30
tools/sound.py    efektler (tick/click/swell/thud/slide) + geçici müzik → audio/*.wav
tools/review.py   her vuruştan bir kare, kontak sayfası
index.html        HyperFrames sahne kodu (GSAP), DOM timing.js'ten kurulur
make.sh           hepsini sırayla çalıştırır, out/ içine MP4 + _SESSIZ yazar
```
Medya dosyaları (öğrenci fotoğrafları ve videoları) repoya konmaz. Drive'dan indirilip
`./make.sh <medya-klasörü>` ile hazırlanır; klasörde `full/<anahtar>.jpg` ve `vid/<anahtar>.<uzantı>` bulunur.

## Müzik
`audio/music_temp.wav` geçici, kodla üretilmiş bir yatak (D–A–Bm–G, 120 BPM, drop 4. sn'de).
Yayın için Pixabay'den lisanslı bir parça seçilip `sound.py`'deki yatak onunla değiştirilmeli,
ya da `_SESSIZ` sürüm Instagram'da uygulama içi müzikle paylaşılmalı.
