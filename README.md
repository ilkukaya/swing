# Swing v2 — BIST otomatik radar & paper-test kanit toplayicisi

Cuma kapanisinda haftalik radari, her gun gunluk radari tarar; her **Long Adayi**
sinyalini v2 cikis merdiveniyle ileri dogru izleyip sonucu R cinsinden kaydeder.
Amac: sistemin gercek edge'i olup olmadigina dair **kanit biriktirmek** (canli para degil).

## Nasil calisir
- `swing_core.py` — v2 tarayici (3 sert kapi + agirlikli skor 0-100 + frekans esigi). Pine "BIST Swing v2" ile ayni mantik.
- `track.py` — acik sinyalleri cozer: STOP (-1R) / T1+maliyet (0.75R) / T1+T2 (1.75R) / olu para / acik.
- `run.py` — orkestrator: tara -> yeni sinyalleri ekle -> takip et -> performans hesapla.
- `.github/workflows/daily.yml` — hafta ici 16:00 UTC cron; `data/` klasorunu repoya commit'ler.

## Veri (kaynak = repo, degistirilemez denetim izi)
- `data/signals.csv` — APPEND-ONLY sinyal defteri (gecmis silinmez).
- `data/tracking.csv` — acik sinyallerin guncel ileri performansi.
- `data/performance.json` — kazanma orani, ortalama R (beklenti), toplam R.
- `data/snapshots/<tarih>_<tf>.json` — o gunun tam radari.

## Ayarlar
`config.py` — skor esigi (frekans), ATR risk limiti, min R/R, olu-para bar sayisi,
likidite filtresi (min fiyat / min TL hacim). `universe.txt` — taranan hisseler;
"tum BIST" icin tum kodlari buraya yapistir, likidite filtresi copu eler.

## Elle calistirma
```bash
pip install -r requirements.txt
python run.py
```

## Durust sinirlar
- Veri yfinance (yaklasik), borsa verisi degil -> **goreli kanit** icin yeterli, kurus kurus P/L degil.
- Altin (GC=F/XAUUSD) bu ortamda gelmeyebilir; runner'da denenir, gelmezse atlanir.
- yfinance ara sira rate-limit verebilir; XU100 okunamazsa piyasa filtresi "engelleme" varsayar.
- Bu bir arastirma/validasyon aracidir, yatirim tavsiyesi degildir.

## Sonraki adim (opsiyonel)
`data/` JSON/CSV'lerini okuyan bir Netlify statik panosu (performans egrisi, radar tablosu).
Once veri birikmeli; pano sonra eklenir.
