# ============================================================
#  Swing v3 — Yapilandirma
#  Her parametrenin gerekce notu var. Suslu parametre eklemiyoruz;
#  asiri-uydurma (overfitting) en buyuk dusman.
# ============================================================

SISTEM_V        = 3       # sinyaller bu versiyonla damgalanir (kanit karismaz)

THRESHOLD       = 78      # Long Adayi skor esigi (frekans dugmesi)
BAND_GIRIS      = 12      # esik-12 => Giris Bekle/Guclu Izle bandi
BAND_IZLE       = 18      # esik-18 => Izle bandi
MAX_ATR_RISK    = 3.0     # gunluk stop genisligi tavani (ATR carpani); haftalik 4
MIN_RR          = 1.5     # direnc hedefine asgari R/R
DEAD_BARS       = 10      # T1 gelmezse "olu para" bar esigi

# v3: gercekci dolum — giris ertesi gun ACILISI; buyuk gap kovalanmaz
GAP_LIMIT       = 0.03    # acilis > plan*1.03 ise GAP_IPTAL (profesyonel kural)

# v3: T1 sonrasi kosucu icin iz suren stop (chandelier)
TRAIL_ATR       = 2.5     # stop = en yuksek kapanis - 2.5*ATR(14)

# v3: piyasa nefesi (breadth) — zayif nefeste esik SIKILASIR (asla gevsemez)
ZAYIF_NEFES     = 40.0    # SMA50 ustu hisse %'si bunun altindaysa...
NEFES_SIKILASTIRMA = 6    # ...esik +6 (yeni sinyal acmak zorlasir)
GUCLU_NEFES     = 60.0    # etiketleme icin (skoru degistirmez)

# Likidite on-elemesi
MIN_PRICE       = 3.0
MIN_TL_VOLUME   = 10_000_000   # 20 gunluk ort. TL hacim

MARKET_REF      = "XU100.IS"
RS_BARS         = 63      # goreli guc penceresi (~3 ay) — momentum literaturu standardi

EXTRA_SYMBOLS   = ["GC=F", "XAUUSD=X"]   # altin (veri gelirse dahil, gelmezse atlanir)
ENTRY_MIN_CODE  = 4       # >=4 (Long Adayi) kagit isleme girer
