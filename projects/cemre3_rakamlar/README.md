# Cemre 3. Etap: istatistik reeli (IG)

9:16, 43 sn, 120 BPM (86 vuruş). v1 seçimi: 1A · 2B · 6B · 7A · 8A · L2 · T1 · M1.
v2 (istatistik) seçimi: H2 · D1A · D2A · D3A · D4A. Grafik renkleri: Karadeniz #3D8FD6, Ege #EC6612
(logo mavisi/turuncusu; renk körlüğü ve kontrast testinden geçti).

## Bilgiler (kaynak: T2A, 2026-11-19)
Toplam 4.507 öğrenci · 18 okul (Akşehir Bilim ve Sanat Merkezi okul sayılmıyor) · 9 il · 2 kol
- Karadeniz 2.304
  - Düzce/Kaynaşlı (5–6 Eki) 790: Kaynaşlı AKV Ortaokulu 369, Cumhuriyet 69, Üçköprü 71, Kumluca 233, Osmangazi 48
  - Kastamonu/Bozkurt (7 Eki) 368: Bozkurt Ortaokulu 230, Bozkurt İmam Hatip 138
  - Trabzon/Çarşıbaşı (12–13 Eki) 506: Çarşıbaşı Ortaokulu 344, İsmail Çavuş İmam Hatip 162 (kesin değil)
  - Gümüşhane/Şiran (14–15 Eki) 554: Atatürk 89, Yunus Emre 330, Şehit Alkın Aydın İmam Hatip 135
  - Rize/Çayeli (16 Eki) 86: Büyükköy Ortaokulu
- Ege 2.203
  - İzmir/Ödemiş (5–6 Eki) 175: Bademli Ortaokulu
  - Manisa (7 Eki) 421: Manisa TOKİ İlköğretim Okulu
  - Uşak (8 Eki) 338: Uşak Nori Demir Ortaokulu
  - Konya/Akşehir (10–11 Eki) 1.269: Akşehir Atatürk Ortaokulu 1.071, Akşehir BİLSEM 198
- YEĞİTEK Bilim Tırı bu etapta Kastamonu ve Düzce'de vardı.
- Etiketler: Akşehir → "Konya", İzmir → "İzmir · Ödemiş". Gün sayısı yazılmıyor.

## Sahneler
| # | Vuruş | Sn | İçerik |
|---|---|---|---|
| s1 | 8 | 0–4 | 4.507 sayacı + 9 il / 18 okul / 2 kol (Kastamonu foto → İzmir video) |
| s2 | 12 | 4–10 | Harita, iki rota, 9 pin |
| s3 | 10 | 10–15 | Ekim takvimi, iki kol, ★ Bilim Tırı |
| s4 | 10 | 15–20 | Toplam 4.507, Karadeniz %51 / Ege %49 |
| s5 | 12 | 20–26 | 9 il çubuk grafik |
| s6 | 10 | 26–31 | En kalabalık 5 okul |
| s7 | 8 | 31–35 | "Robot futbolu / sahada!" (Uşak foto → İzmir video) |
| s8 | 6 | 35–38 | "Evet!" (Düzce kutlama videosu) |
| s9 | 10 | 38–43 | "Kağıt üzerinde değil, sahada." + logo |

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
