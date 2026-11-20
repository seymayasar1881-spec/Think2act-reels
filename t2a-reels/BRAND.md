# Think2Act (T2A) — Reels marka kuralları

Her Think2Act videosunda bunlar kullanılır:

- **Logo:** `brand/logo.png` (şeffaf, `logo_src.jpg`'den çıkarıldı). Her karede sağ üstte beyaz yuvarlak köşeli rozet içinde.
- **Gradyan:** `brand/gradient.jpg` (mavi → mor → pembe → turuncu). Yazı kartları, sayaç, etiket kutuları ve alt şerit bu gradyandan.
- **Başlık fontu:** `brand/Anton.ttf` (SIL OFL). Büyük harf; ilk satır beyaz, vurgu satırı beyaz kutu içinde koyu yazı.
- **Kapanış:** beyaz ekran + ortada logo + "Liseliler kurdu, liseliler yürütüyor." + "@think2actorg · iletisim@think2act.org".

Yapılmayacaklar (kullanıcı geri bildirimi):
- Zikzak/zıplayan zoom ve beyaz flaş geçişleri yok; sadece hafif tek yönlü zoom ve yumuşak crossfade.
- Karanlık hava yok: siyah ekran, karartma, vinyet kullanma.
- Kalp/emoji gibi küçük süsler yok.
- Yatay fotoğrafları tam ekran kırpma; eskitme kağıt zemin üzerinde polaroid çerçeveler halinde üst üste getir.
- Sayılar (1 → 5 → 11 il, 25.000+) gradyan üzerinde büyük ve hızlı artan sayaç olarak.
- Genel ton soft: sıcak piyano/pad müzik, sert EDM efektleri yok.

Medya: Drive > "T2A Galeri" (Hatay 1/2, Trabzon/Rize/Gümüşhane/Kastamonu/Düzce 2026). Drive bağlantısı 10 MB üstü dosyaları indiremiyor.

Scriptler: `scripts/build3.py` (video, `media/` + `media_n/` + `brand/` klasörlerini bekler), `scripts/music_soft.py` (özgün müzik, `work3/sections.json`'a göre).
