# ============================================================
#  Swing v3 — Takip / Cozumleyici
#  v2 -> v3 farklari (kanit kalitesi icin):
#   - GIRIS = sinyalin ERTESI GUN ACILISI (gercekci dolum).
#     Acilis > plan*1.03 -> GAP_IPTAL (kovalanmaz, istatistik disi).
#     Acilis stop altina gap'lediyse -> GAP_IPTAL.
#   - T1 (fiili giristen 1.5R): yari kapanir (+0.75R kilit), stop maliyete.
#   - T1 sonrasi kosucu: CHANDELIER iz suren stop
#     (en yuksek kapanis - TRAIL_ATR*ATR14). Trend buyurse kosar.
#   - OLU PARA: DEAD_BARS barda T1 yoksa kapanista cik.
#   - Ayni bar hem stop hem T1 -> temkinli: STOP sayilir.
#  Ek: acik pozisyonlar arasi 60 gunluk korelasyon (yogunlasma uyarisi).
#  Veri yfinance (yaklasik) — goreli kanit icindir.
# ============================================================
import pandas as pd, numpy as np
import yfinance as yf
import config as C
from indicators import atr

CLOSED = {"STOP", "T1_BE", "T2", "TRAIL", "DEAD", "GAP_IPTAL"}
GERCEK_KAPANIS = {"STOP", "T1_BE", "T2", "TRAIL", "DEAD"}  # istatistige girenler


def _resolve(df, sig_date, plan, stop):
    """Sinyal tarihinden sonraki barlarda v3 cozumu."""
    fwd = df[df.index.date > pd.to_datetime(sig_date).date()]
    if len(fwd) == 0:
        return dict(durum="ACIK", R=0.0, gun=0, mfe=0.0, mae=0.0,
                    giris_fiili=plan, son_tarih="")
    e0 = float(fwd["Open"].iloc[0])
    son_t = fwd.index[-1].date().isoformat()
    # gap kurallari
    if e0 > plan * (1 + C.GAP_LIMIT) or e0 <= stop:
        return dict(durum="GAP_IPTAL", R=0.0, gun=0, mfe=0.0, mae=0.0,
                    giris_fiili=round(e0, 2), son_tarih=fwd.index[0].date().isoformat())
    Run = e0 - stop
    t1 = e0 + 1.5 * Run
    a14 = atr(df).reindex(fwd.index)
    t1_hit = False; hi_close = e0
    mfe = mae = 0.0; n = 0
    for ts, b in fwd.iterrows():
        n += 1
        hi, lo, cl = float(b["High"]), float(b["Low"]), float(b["Close"])
        mfe = max(mfe, (hi - e0) / Run); mae = min(mae, (lo - e0) / Run)
        if not t1_hit:
            if lo <= stop:
                return dict(durum="STOP", R=-1.0, gun=n, mfe=round(mfe, 2), mae=round(mae, 2),
                            giris_fiili=round(e0, 2), son_tarih=ts.date().isoformat())
            if hi >= t1:
                t1_hit = True; hi_close = cl
            elif n >= C.DEAD_BARS:
                R = (cl - e0) / Run
                return dict(durum="DEAD", R=round(R, 2), gun=n, mfe=round(mfe, 2), mae=round(mae, 2),
                            giris_fiili=round(e0, 2), son_tarih=ts.date().isoformat())
        else:
            hi_close = max(hi_close, cl)
            av = float(a14.loc[ts]) if pd.notna(a14.loc[ts]) else 0.0
            trail = max(e0, hi_close - C.TRAIL_ATR * av)
            if lo <= trail:
                R = 0.75 + 0.5 * (trail - e0) / Run
                return dict(durum="TRAIL", R=round(R, 2), gun=n, mfe=round(mfe, 2), mae=round(mae, 2),
                            giris_fiili=round(e0, 2), son_tarih=ts.date().isoformat())
    last = float(fwd["Close"].iloc[-1])
    cur = (last - e0) / Run
    if t1_hit:
        return dict(durum="T1_ACIK", R=round(0.75 + 0.5 * cur, 2), gun=n, mfe=round(mfe, 2),
                    mae=round(mae, 2), giris_fiili=round(e0, 2), son_tarih=son_t)
    return dict(durum="ACIK", R=round(cur, 2), gun=n, mfe=round(mfe, 2), mae=round(mae, 2),
                giris_fiili=round(e0, 2), son_tarih=son_t)


def update_tracking(signals):
    """signals: acik sinyal dict listesi.
       Doner: (tracking_rows, kapanan_id_set, maks_korelasyon_dict)"""
    if not signals:
        return [], set(), {}
    syms = sorted({s["sembol"] for s in signals})
    tickers = [x if ("=" in x or x.endswith(".IS")) else x + ".IS" for x in syms]
    data = yf.download(tickers, period="1y", interval="1d", progress=False,
                       auto_adjust=True, group_by="ticker", threads=True)
    rows, kapanan = [], set()
    closes = {}
    for s in signals:
        sym = s["sembol"]
        tk = sym if ("=" in sym or sym.endswith(".IS")) else sym + ".IS"
        try:
            df = data[tk].dropna() if len(tickers) > 1 else data.dropna()
            res = _resolve(df, s["tarih"], float(s["giris"]), float(s["stop"]))
            last = float(df["Close"].iloc[-1])
            closes[sym] = df["Close"]
        except Exception:
            res = dict(durum=s.get("durum", "ACIK"), R=0.0, gun=0, mfe=0.0, mae=0.0,
                       giris_fiili=float(s["giris"]), son_tarih="")
            last = float(s["giris"])
        gf = res["giris_fiili"]
        rows.append(dict(id=s["id"], sembol=sym, tf=s["tf"], tarih=s["tarih"],
                         giris=s["giris"], giris_fiili=gf, stop=s["stop"], t1=s["t1"], t2=s["t2"],
                         son_fiyat=round(last, 2),
                         getiri_pct=round((last / gf - 1) * 100, 2) if gf else 0.0,
                         durum=res["durum"], R=res["R"], gun=res["gun"],
                         mfe=res["mfe"], mae=res["mae"], son_tarih=res["son_tarih"],
                         v=s.get("v", 2)))
        if res["durum"] in CLOSED:
            kapanan.add(s["id"])
    # acik pozisyonlar arasi 60g korelasyon (en yuksek cift)
    korr = {}
    open_syms = [r["sembol"] for r in rows if r["durum"] not in CLOSED]
    try:
        if len(open_syms) >= 2:
            rets = pd.DataFrame({s: closes[s].pct_change() for s in open_syms if s in closes}).tail(60)
            cm = rets.corr()
            best, pair = -2.0, ""
            cols = list(cm.columns)
            for i in range(len(cols)):
                for j in range(i + 1, len(cols)):
                    v = cm.iloc[i, j]
                    if pd.notna(v) and v > best:
                        best, pair = float(v), f"{cols[i]}–{cols[j]}"
            if pair:
                korr = {"cift": pair, "deger": round(best, 2)}
    except Exception:
        pass
    return rows, kapanan, korr


def performance(tracking_rows, closed_hist_df=None):
    """tracking_rows + (varsa) closed.csv arsivi uzerinden istatistik.
       GAP_IPTAL istatistik DISI tutulur (islem gerceklesmedi)."""
    frames = []
    if tracking_rows:
        frames.append(pd.DataFrame(tracking_rows))
    if closed_hist_df is not None and len(closed_hist_df):
        frames.append(closed_hist_df)
    if not frames:
        return {}
    df = pd.concat(frames, ignore_index=True).drop_duplicates(subset=["id"], keep="first")
    closed = df[df["durum"].isin(GERCEK_KAPANIS)]
    gaps = df[df["durum"] == "GAP_IPTAL"]
    out = {"toplam_sinyal": int(len(df)),
           "acik": int((~df["durum"].isin(CLOSED)).sum()),
           "kapanan": int(len(closed)), "gap_iptal": int(len(gaps))}
    if len(closed):
        out["kazanan"] = int((closed["R"] > 0).sum())
        out["kaybeden"] = int((closed["R"] <= 0).sum())
        out["kazanma_orani_pct"] = round(out["kazanan"] / len(closed) * 100, 1)
        out["ort_R_beklenti"] = round(closed["R"].mean(), 3)
        out["toplam_R"] = round(closed["R"].sum(), 2)
        out["ort_gun"] = round(closed["gun"].mean(), 1)
        w = closed[closed["R"] > 0]["R"]; l = closed[closed["R"] <= 0]["R"]
        out["ort_kazanc_R"] = round(float(w.mean()), 3) if len(w) else 0.0
        out["ort_kayip_R"] = round(abs(float(l.mean())), 3) if len(l) else 0.0
        for tf in closed["tf"].unique():
            sub = closed[closed["tf"] == tf]
            out[f"{tf}_kazanma_pct"] = round((sub["R"] > 0).mean() * 100, 1)
            out[f"{tf}_ort_R"] = round(sub["R"].mean(), 3)
    return out
