# ============================================================
#  Swing v3 — Cekirdek tarayici
#  v2 -> v3 farklari:
#   - RS (goreli guc): 63 gunluk getiri, evren ici yuzdelik -> skora %15
#   - Piyasa nefesi (breadth): SMA50 ustu hisse %'si; zayifsa esik +6
#   - Indirmede retry/backoff (yfinance rate-limit dostu)
#  Karar kodlari ayni: 5..-2. Agirliklar: Trend25 Mom20 RS15 Vol10 Setup20 Risk10
# ============================================================
import os, time, warnings, logging
import pandas as pd, numpy as np
import yfinance as yf
import config as C
from indicators import ema, sma, rsi, macd, atr

warnings.filterwarnings("ignore")
logging.getLogger("yfinance").setLevel(logging.CRITICAL)

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
    seen, out = set(), []
    for s in syms:
        if s not in seen:
            seen.add(s); out.append(s)
    return out


def _yf(tickers, interval, period, tries=3):
    """yf.download + retry/backoff."""
    for i in range(tries):
        try:
            return yf.download(tickers, period=period, interval=interval, progress=False,
                               auto_adjust=True, group_by="ticker", threads=True)
        except Exception:
            if i < tries - 1:
                time.sleep(3 * (i + 1))
    return None


def _download(symbols, interval, period):
    """Parcali toplu indirme; {sembol: df} doner."""
    out = {}
    CH = 40
    for k in range(0, len(symbols), CH):
        part = symbols[k:k + CH]
        tickers = [s if s.endswith((".IS", "=F", "=X")) or "=" in s else s + ".IS" for s in part]
        data = _yf(tickers, interval, period)
        if data is None:
            continue
        for s, t in zip(part, tickers):
            try:
                df = data[t].dropna() if len(tickers) > 1 else data.dropna()
                if len(df) > 0:
                    out[s] = df
            except Exception:
                pass
        time.sleep(0.5)
    return out


def market_regime():
    """Endeks kapisi: HAFTALIK XU100 > EMA21 ve > SMA50. (bool, aciklama)"""
    for tk in (C.MARKET_REF, "^XU100"):
        try:
            x = yf.download(tk, period="3y", interval="1wk", progress=False, auto_adjust=True)
            x.columns = [c[0] if isinstance(c, tuple) else c for c in x.columns]
            c = x["Close"].dropna()
            if len(c) < 60:
                continue
            ok = bool(c.iloc[-1] > ema(c, 21).iloc[-1] and c.iloc[-1] > sma(c, 50).iloc[-1])
            return ok, ("endeks haftalik EMA21+SMA50 ustu" if ok else "endeks haftalik ortalamalarin altinda")
        except Exception:
            continue
    return True, "endeks verisi alinamadi (engellemiyor)"


def _passes_liquidity(df):
    px = df["Close"].iloc[-1]
    if px < C.MIN_PRICE:
        return False
    tl_vol = (df["Close"] * df["Volume"]).rolling(20).mean().iloc[-1]
    return bool(tl_vol >= C.MIN_TL_VOLUME)


def compute(df, market_ok, rs_pct, max_atr=None, thr_add=0):
    """Tek hisse: v3 skor + karar + plan. rs_pct: evren ici goreli guc yuzdeligi (0-100)."""
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

    # --- v3 skor: Trend25 Mom20 RS15 Vol10 Setup20 Risk10 ---
    trend = (8 if px > s200 else 0) + (5 if px > s50 else 0) + (3 if px > e21 else 0) \
            + (4 if s50up else 0) + (5 if pos_order else 0)
    mom = (6 if r > 60 else 4 if r > 50 else 2 if r > 45 else 0) \
          + (5 if mv > 0 else 0) + (5 if mv > sv else 0) + (4 if hv > hp else 0)
    rs = 15 if rs_pct >= 80 else 10 if rs_pct >= 60 else 5 if rs_pct >= 40 else 0
    vol = 10 if volr > 1.3 else 6 if volr > 1 else 2 if volr > 0.7 else 0
    near21 = px > e21 and abs(px - e21) / px * 100.0 < 5.0
    brk = px > float(df["High"].iloc[-21:-1].max())
    setup = min(20, (8 if 0 < dist50 < 15 else 0) + (7 if near21 else 0) + (5 if brk else 0))
    riskq = (6 if dist50 < 15 else 3 if dist50 < 20 else 0) + (4 if atr_risk <= max_atr else 0)
    score = max(0, min(100, trend + mom + rs + vol + setup + riskq))

    # --- kapilar + karar (zayif nefeste esik thr_add kadar sikilasir) ---
    thr = C.THRESHOLD + thr_add
    trend_floor = px > s200
    plan_ok = (R > 0) and (atr_risk <= max_atr) and (stop < px)
    gates = market_ok and trend_floor and plan_ok
    at_high = px >= t3 * 0.99
    plan_rr_ok = at_high or rr >= C.MIN_RR

    if not gates:
        code = -1 if (px < s200 and mv < 0) else -2
    else:
        if score >= thr and dist50 <= 20:
            code = 5
        elif score >= thr:
            code = 4
        elif score >= thr - C.BAND_GIRIS:
            code = 2 if (r < 55 or mv < sv) else 1
        elif score >= thr - C.BAND_IZLE:
            code = 0
        else:
            code = -2
        if not plan_rr_ok:
            code = min(code, 3)

    return dict(
        karar=KARAR[code], kod=int(code), skor=int(round(score)),
        fiyat=round(px, 2), rsi=int(round(r)), macd=(">0" if mv > 0 else "<0"),
        volx=round(volr, 2), sma50_uz=round(dist50, 1), rs=int(round(rs_pct)),
        stop=round(stop, 2), stop_pct=round(stop_pct, 1), atr_risk=round(atr_risk, 1),
        rr=round(rr, 2), t1=round(t1, 2), t2=round(t2, 2), direnc=round(t3, 2),
        trend=trend, mom=mom, vol=vol, setup=setup, riskq=riskq, rs_puan=rs,
    )


def scan(timeframe="1d"):
    """Iki gecisli tarama: (1) veri + getiri topla, (2) RS yuzdeligi + skor.
       Doner: (DataFrame, rejim_dict)"""
    syms = load_universe()
    max_atr = 4.0 if timeframe in ("1wk", "1w") else C.MAX_ATR_RISK
    mkt_ok, mkt_note = market_regime()
    period = "5y" if timeframe in ("1wk", "1w") else "2y"
    interval = "1wk" if timeframe in ("1wk", "1w") else "1d"
    data = _download(syms, interval, period)
    data.update(_download(C.EXTRA_SYMBOLS, interval, period))

    # --- gecis 1: likidite + 63 bar getiri + SMA50 ustu bayragi ---
    feats = {}
    for s, df in data.items():
        try:
            if s not in C.EXTRA_SYMBOLS and not _passes_liquidity(df):
                continue
            c = df["Close"]
            if len(c) < 210:
                continue
            ret = c.iloc[-1] / c.iloc[-C.RS_BARS] - 1.0 if len(c) > C.RS_BARS else 0.0
            feats[s] = dict(ret=float(ret), above50=bool(c.iloc[-1] > sma(c, 50).iloc[-1]))
        except Exception:
            pass

    # piyasa nefesi (yalnizca hisselerden; altin haric)
    flags = [f["above50"] for s, f in feats.items() if s not in C.EXTRA_SYMBOLS]
    breadth = round(100.0 * sum(flags) / len(flags), 1) if flags else 50.0
    thr_add = C.NEFES_SIKILASTIRMA if breadth < C.ZAYIF_NEFES else 0

    # rejim etiketi
    if not mkt_ok:
        rejim = "ZAYIF"
    elif breadth >= C.GUCLU_NEFES:
        rejim = "GUCLU"
    elif breadth >= C.ZAYIF_NEFES:
        rejim = "POZITIF"
    else:
        rejim = "TEMKINLI"
    rejim_info = dict(rejim=rejim, breadth=breadth, endeks_ok=bool(mkt_ok),
                      not_=mkt_note, esik=C.THRESHOLD + thr_add)

    # RS yuzdelikleri (evren ici sira)
    rets = pd.Series({s: f["ret"] for s, f in feats.items() if s not in C.EXTRA_SYMBOLS})
    rs_pct = (rets.rank(pct=True) * 100.0).to_dict() if len(rets) else {}

    # --- gecis 2: skor + karar ---
    rows = []
    for s, df in data.items():
        if s not in feats:
            continue
        try:
            res = compute(df, mkt_ok, rs_pct.get(s, 50.0), max_atr, thr_add)
            if res:
                res["sembol"] = s
                res["tf"] = "haftalik" if timeframe in ("1wk", "1w") else "gunluk"
                res["asof"] = df.index[-1].date().isoformat()
                rows.append(res)
        except Exception:
            pass
    if not rows:
        return pd.DataFrame(), rejim_info
    cols = ["sembol", "tf", "asof", "karar", "kod", "skor", "fiyat", "rsi", "macd",
            "volx", "rs", "sma50_uz", "stop", "stop_pct", "atr_risk", "rr", "t1", "t2", "direnc",
            "trend", "mom", "vol", "setup", "riskq", "rs_puan"]
    out = pd.DataFrame(rows)[cols].sort_values(["kod", "skor"], ascending=[False, False]).reset_index(drop=True)
    return out, rejim_info
