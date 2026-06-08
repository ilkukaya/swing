# ============================================================
#  Swing v2 — Cekirdek tarayici
#  Pine "BIST Swing v2" ile ayni mantik: 3 sert kapi + agirlikli
#  skor (0-100) + frekans esigi. Karar kodlari 5..-2.
# ============================================================
import os, warnings
import pandas as pd, numpy as np
import yfinance as yf
import config as C
from indicators import ema, sma, rsi, macd, atr

warnings.filterwarnings("ignore")

KARAR = {5: "Long Adayi", 4: "Long Adayi/dikkat", 3: "Plan Bekle",
         2: "Giris Bekle", 1: "Guclu Izle", 0: "Izle", -1: "Riskli", -2: "Islem Yok"}


def load_universe(path="universe.txt"):
    syms = []
    with open(path) as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            syms += [w.strip().upper() for w in line.split() if w.strip()]
    # benzersiz, sirayi koru
    seen, out = set(), []
    for s in syms:
        if s not in seen:
            seen.add(s); out.append(s)
    return out


def _download(symbols, interval, period):
    """Toplu indirir; {sembol: df} doner (basarisizlari atlar)."""
    tickers = [s if s.endswith((".IS", "=F", "=X")) or "=" in s else s + ".IS" for s in symbols]
    data = yf.download(tickers, period=period, interval=interval, progress=False,
                       auto_adjust=True, group_by="ticker", threads=True)
    out = {}
    for s, t in zip(symbols, tickers):
        try:
            df = data[t].dropna() if len(tickers) > 1 else data.dropna()
            if len(df) > 0:
                out[s] = df
        except Exception:
            pass
    return out


def market_regime():
    """Piyasa rejimi HAFTALIK XU100'den okunur (Pine refTF=1W ile ayni)."""
    try:
        x = yf.download(C.MARKET_REF, period="3y", interval="1wk", progress=False, auto_adjust=True)
        x.columns = [c[0] if isinstance(c, tuple) else c for c in x.columns]
        c = x["Close"].dropna()
        return bool(c.iloc[-1] > ema(c, 21).iloc[-1] and c.iloc[-1] > sma(c, 50).iloc[-1])
    except Exception:
        return True  # veri yoksa engelleme


def _passes_liquidity(df):
    px = df["Close"].iloc[-1]
    if px < C.MIN_PRICE:
        return False
    tl_vol = (df["Close"] * df["Volume"]).rolling(20).mean().iloc[-1]
    return bool(tl_vol >= C.MIN_TL_VOLUME)


def compute(df, market_ok, max_atr=None):
    """Tek hisse icin v2 skor + karar + plan dondurur (dict) ya da None."""
    max_atr = C.MAX_ATR_RISK if max_atr is None else max_atr
    if len(df) < 210:
        return None
    c = df["Close"]; px = float(c.iloc[-1])
    e21 = ema(c, 21).iloc[-1]; s50 = sma(c, 50).iloc[-1]; s200 = sma(c, 200).iloc[-1]
    s50up = sma(c, 50).iloc[-1] > sma(c, 50).iloc[-5]
    pos_order = e21 > s50 > s200
    r = rsi(c).iloc[-1]
    m, sig, h = macd(c); mv, sv, hv, hp = m.iloc[-1], sig.iloc[-1], h.iloc[-1], h.iloc[-2]
    a = atr(df).iloc[-1]
    vol_avg = df["Volume"].rolling(20).mean().iloc[-1]
    volr = df["Volume"].iloc[-1] / vol_avg if vol_avg > 0 else 0.0
    dist50 = (px - s50) / s50 * 100.0

    # yapi bazli stop
    swing = df["Low"].iloc[-6:].min()
    stop = min(swing * 0.99, s50 * 0.98) if px > s50 else swing * 0.99
    if stop >= px:
        stop = px * 0.93
    R = px - stop
    stop_pct = R / px * 100.0
    atr_risk = R / a if a > 0 else 99.0
    t1 = px + 1.5 * R; t2 = px + 2.0 * R
    t3 = float(df["High"].iloc[-52:].max())
    rr = (t3 - px) / R if R > 0 else 0.0

    # --- skor (Pine ile ayni agirliklar) ---
    trend = (9 if px > s200 else 0) + (6 if px > s50 else 0) + (4 if px > e21 else 0) \
            + (5 if s50up else 0) + (6 if pos_order else 0)
    mom = (8 if r > 60 else 5 if r > 50 else 2 if r > 45 else 0) \
          + (6 if mv > 0 else 0) + (6 if mv > sv else 0) + (5 if hv > hp else 0)
    vol = 15 if volr > 1.3 else 8 if volr > 1 else 3 if volr > 0.7 else 0
    near21 = px > e21 and abs(px - e21) / px * 100.0 < 5.0
    brk = px > float(df["High"].iloc[-21:-1].max())
    setup = min(20, (8 if 0 < dist50 < 15 else 0) + (7 if near21 else 0) + (5 if brk else 0))
    riskq = (6 if dist50 < 15 else 3 if dist50 < 20 else 0) + (4 if atr_risk <= max_atr else 0)
    score = max(0, min(100, trend + mom + vol + setup + riskq))

    # --- kapilar + karar ---
    trend_floor = px > s200
    plan_ok = (R > 0) and (atr_risk <= max_atr) and (stop < px)
    gates = market_ok and trend_floor and plan_ok
    at_high = px >= t3 * 0.99
    plan_rr_ok = at_high or rr >= C.MIN_RR

    if not gates:
        code = -1 if (px < s200 and mv < 0) else -2
    else:
        if score >= C.THRESHOLD and dist50 <= 20:
            code = 5
        elif score >= C.THRESHOLD:
            code = 4
        elif score >= C.THRESHOLD - C.BAND_GIRIS:
            code = 2 if (r < 55 or mv < sv) else 1
        elif score >= C.THRESHOLD - C.BAND_IZLE:
            code = 0
        else:
            code = -2
        if not plan_rr_ok:
            code = min(code, 3)

    return dict(
        karar=KARAR[code], kod=int(code), skor=int(round(score)),
        fiyat=round(px, 2), rsi=int(round(r)), macd=(">0" if mv > 0 else "<0"),
        volx=round(volr, 2), sma50_uz=round(dist50, 1),
        stop=round(stop, 2), stop_pct=round(stop_pct, 1), atr_risk=round(atr_risk, 1),
        rr=round(rr, 2), t1=round(t1, 2), t2=round(t2, 2), direnc=round(t3, 2),
        trend=trend, mom=mom, vol=vol, setup=setup, riskq=riskq,
    )


def scan(timeframe="1d"):
    """Tum evreni tarar; sinyal DataFrame'i dondurur (kod azalan sirali)."""
    syms = load_universe()
    max_atr = 4.0 if timeframe in ("1wk", "1w") else C.MAX_ATR_RISK
    mkt = market_regime()
    period = "5y" if timeframe in ("1wk", "1w") else "2y"
    data = _download(syms, "1wk" if timeframe in ("1wk", "1w") else "1d", period)
    # opsiyonel ek enstrumanlar (altin vb.) — veri gelirse
    data.update(_download(C.EXTRA_SYMBOLS, "1wk" if timeframe in ("1wk", "1w") else "1d", period))

    rows = []
    for s, df in data.items():
        try:
            if s not in C.EXTRA_SYMBOLS and not _passes_liquidity(df):
                continue
            res = compute(df, mkt, max_atr)
            if res:
                res["sembol"] = s
                res["tf"] = "haftalik" if timeframe in ("1wk", "1w") else "gunluk"
                res["asof"] = df.index[-1].date().isoformat()
                rows.append(res)
        except Exception:
            pass
    if not rows:
        return pd.DataFrame(), mkt
    cols = ["sembol", "tf", "asof", "karar", "kod", "skor", "fiyat", "rsi", "macd",
            "volx", "sma50_uz", "stop", "stop_pct", "atr_risk", "rr", "t1", "t2", "direnc",
            "trend", "mom", "vol", "setup", "riskq"]
    df = pd.DataFrame(rows)[cols].sort_values(["kod", "skor"], ascending=[False, False]).reset_index(drop=True)
    return df, mkt
