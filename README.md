# Swing v3 — BIST otomatik radar & paper-test kanit toplayicisi

Her aksam BIST'in tamamini (likit alt kume) tarar, **Long Adayi** sinyallerini
gercekci dolum varsayimiyla ileri dogru izler, sonuclari R cinsinden arsivler.
Amac: sistemin gercek edge'i olup olmadigina dair **kanit biriktirmek**.

## v3'un v2'den farklari (her biri literatur destekli, susleme yok)
1. **RS — goreli guc (%15 agirlik):** 63 gunluk getirinin evren ici yuzdeligi.
   Endeksi yenen hisse onceliklidir (momentum literaturunun en saglam bulgusu).
2. **Rejim + nefes:** XU100 haftalik kapisi AYNEN durur; ek olarak nefes
   (SMA50 ustu hisse %'si) %40 altindaysa sinyal esigi +6 SIKILASIR (asla gevsemez).
3. **Gercekci dolum:** giris = sinyalin ertesi gun ACILISI. Acilis plani %3+
   gecerse veya stop altina gap'lerse GAP_IPTAL (kovalanmaz, istatistik disi).
4. **Iz suren cikis:** T1 (1.5R) yarim kapanis + maliyet stopu AYNEN; kosucu artik
   sabit T2 yerine chandelier (en yuksek kapanis - 2.5*ATR14) ile izlenir —
   buyuk trendi koparmaz, "aylarca tutma" sorununu da cozer (DEAD kurali durur).
5. **Korelasyon uyarisi:** acik pozisyonlarin 60 gunluk en yuksek korelasyon
   cifti performance.json'a yazilir; pano Kasa sekmesinde uyarir.
6. **Kanit hijyeni:** kapananlar `data/closed.csv` arsivine eklenir (equity egrisi
   buradan), her sinyal sistem versiyonuyla (v) damgalanir — v2/v3 kaniti karismaz.

## Skor (0-100): Trend 25 · Momentum 20 · RS 15 · Hacim 10 · Setup 20 · Risk 10
3 sert kapi ayni: piyasa filtresi, fiyat>SMA200, gecerli plan (stop/ATR/R-R).

## Veri dosyalari (kaynak = repo, append-only denetim izi)
- `data/signals.csv` sinyal defteri · `data/closed.csv` kapanan arsivi
- `data/tracking.csv` acik takip · `data/performance.json` istatistik
- `data/regime.json` gunun rejimi · `data/snapshots/` gunluk radar

## Dürüst sinirlar
- Veri yfinance (yaklasik) -> goreli kanit; kurus kurus P/L degil.
- Sonuclar gecmis/ileri kagit-test kanitidir; gelecegi garanti etmez.
- Yatirim tavsiyesi degildir.

Calistirma: `pip install -r requirements.txt && python run.py`
Otomasyon: hafta ici 16:10 UTC (~19:10 TR) GitHub Actions; Netlify panoyu otomatik yeniler.
