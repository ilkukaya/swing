# ============================================================
#  Swing v2 — Yapilandirma
#  Tum esikler/parametreler tek yerde. Pine v2 ile ayni mantik.
# ============================================================

THRESHOLD       = 78      # Long Adayi skor esigi (frekans dugmesi)
BAND_GIRIS      = 12      # esik - 12 => Giris Bekle/Guclu Izle bandi
BAND_IZLE       = 18      # esik - 18 => Izle bandi
MAX_ATR_RISK    = 3.0     # gunluk icin 3 (haftalik tarama icin 4)
MIN_RR          = 1.5     # direnc hedefine asgari R/R
DEAD_BARS       = 10      # T1 gelmezse "olu para" gun esigi

# Likidite on-elemesi (cop sembolleri eler)
MIN_PRICE       = 5.0           # asgari fiyat (TL)
MIN_TL_VOLUME   = 20_000_000    # asgari ort. gunluk islem hacmi (TL, 20 gun)

MARKET_REF      = "XU100.IS"    # piyasa rejim referansi (haftalik okunur)

# Opsiyonel ek enstrumanlar (veri gelirse dahil edilir, gelmezse atlanir)
EXTRA_SYMBOLS   = ["GC=F", "XAUUSD=X"]   # altin proxy denemeleri (runner'da calisabilir)

# Hangi kararlar "kagit islem" olarak kaydedilip takip edilsin:
#   >=4  => Long Adayi (4) ve Long Adayi/dikkat... -> evet, izlenir
ENTRY_MIN_CODE  = 4
