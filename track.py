# ============================================================
#  Swing v2 — Takip / Cozumleyici
#  Her acik sinyali v2 cikis merdiveniyle ileri dogru cozer:
#   - STOP (T1 oncesi)        -> R = -1.0
#   - T1 sonra maliyet stopu  -> R = +0.75  (yari 1.5R + yari 0R)
#   - T1 sonra T2             -> R = +1.75  (yari 1.5R + yari 2R)
#   - T1 + kosucu acik        -> realized 0.75 + kosucu unrealized
#   - OLU PARA (T1 yok, DEAD_BARS bar) -> kapanista cik, R = gercek
#   - ACIK                    -> unrealized R
#  Not: ayni gun hem stop hem t1 teterse temkinli olarak STOP varsayilir.
#  Veri yfinance (yaklasik) — goreli kanit icin, kurus kurus P/L degil.
# ============================================================
import pandas as pd, numpy as np
import yfinance as yf
import config as C

CLOSED = {"STOP", "T1_BE", "T2", "DEAD"}


def _resolve(df_fwd, entry, stop, t1, t2):
    """entry sonrasi barlar uzerinde sonucu cozer."""
    if stop >= entry:
        return dict(durum="GECERSIZ", R=0.0, gun=0, mfe=0.0, mae=0.0)
    Runit = entry - stop
    t1_hit = False
    mfe = mae = 0.0
    n = 0
    for _, b in df_fwd.iterrows():
        n += 1
        hi, lo, cl = float(b["High"]), float(b["Low"]), float(b["Close"])
        mfe = max(mfe, (hi - entry) / Runit)
        mae = min(mae, (lo - entry) / Runit)
        if not t1_hit:
            if lo <= stop:                      # T1 oncesi stop
                return dict(durum="STOP", R=-1.0, gun=n, mfe=round(mfe, 2), mae=round(mae, 2))
            if hi >= t1:                        # T1 vuruldu -> yari kapanir, stop maliyete
                t1_hit = True
            elif n >= C.DEAD_BARS:              # olu para
                R = (cl - entry) / Runit
                return dict(durum="DEAD", R=round(R, 2), gun=n, mfe=round(mfe, 2), mae=round(mae, 2))
        else:
            if hi >= t2:                        # kosucu T2
                return dict(durum="T2", R=1.75, gun=n, mfe=round(mfe, 2), mae=round(mae, 2))
            if lo <= entry:                     # kosucu maliyet stopu
                return dict(durum="T1_BE", R=0.75, gun=n, mfe=round(mfe, 2), mae=round(mae, 2))
    # cozulmedi -> acik
    last = float(df_fwd["Close"].iloc[-1]) if len(df_fwd) else entry
    cur = (last - entry) / Runit
    if t1_hit:
        return dict(durum="T1_ACIK", R=round(0.75 + 0.5 * cur, 2), gun=n, mfe=round(mfe, 2), mae=round(mae, 2))
    return dict(durum="ACIK", R=round(cur, 2), gun=n, mfe=round(mfe, 2), mae=round(mae, 2))


def update_tracking(signals):
    """signals: acik sinyal dict listesi. (tracking_rows, kapanan_id_set) doner."""
    if not signals:
        return [], set()
    syms = sorted({s["sembol"] for s in signals})
    tickers = [x if ("=" in x or x.endswith(".IS")) else x + ".IS" for x in syms]
    data = yf.download(tickers, period="1y", interval="1d", progress=False,
                       auto_adjust=True, group_by="ticker", threads=True)
    rows, kapanan = [], set()
    for s in signals:
        sym = s["sembol"]
        tk = sym if ("=" in sym or sym.endswith(".IS")) else sym + ".IS"
        try:
            df = data[tk].dropna() if len(tickers) > 1 else data.dropna()
            fwd = df[df.index.date > pd.to_datetime(s["tarih"]).date()]
            res = _resolve(fwd, float(s["giris"]), float(s["stop"]), float(s["t1"]), float(s["t2"]))
            last = float(df["Close"].iloc[-1])
        except Exception:
            res = dict(durum=s.get("durum", "ACIK"), R=0.0, gun=0, mfe=0.0, mae=0.0); last = float(s["giris"])
        rows.append(dict(id=s["id"], sembol=sym, tf=s["tf"], tarih=s["tarih"],
                         giris=s["giris"], stop=s["stop"], t1=s["t1"], t2=s["t2"],
                         son_fiyat=round(last, 2), getiri_pct=round((last/float(s["giris"])-1)*100, 2),
                         durum=res["durum"], R=res["R"], gun=res["gun"], mfe=res["mfe"], mae=res["mae"]))
        if res["durum"] in CLOSED:
            kapanan.add(s["id"])
    return rows, kapanan


def performance(tracking_rows):
    if not tracking_rows:
        return {}
    df = pd.DataFrame(tracking_rows)
    closed = df[df["durum"].isin(CLOSED)]
    out = {"toplam_sinyal": int(len(df)), "acik": int((~df["durum"].isin(CLOSED)).sum()),
           "kapanan": int(len(closed))}
    if len(closed):
        out["kazanan"] = int((closed["R"] > 0).sum())
        out["kaybeden"] = int((closed["R"] <= 0).sum())
        out["kazanma_orani_pct"] = round(out["kazanan"] / len(closed) * 100, 1)
        out["ort_R_beklenti"] = round(closed["R"].mean(), 3)
        out["toplam_R"] = round(closed["R"].sum(), 2)
        out["ort_gun"] = round(closed["gun"].mean(), 1)
        w = closed[closed["R"] > 0]["R"]; l = closed[closed["R"] <= 0]["R"]
        out["ort_kazanc_R"] = round(float(w.mean()), 3) if len(w) else 0.0   # Kelly icin
        out["ort_kayip_R"] = round(abs(float(l.mean())), 3) if len(l) else 0.0
        for tf in closed["tf"].unique():
            sub = closed[closed["tf"] == tf]
            out[f"{tf}_kazanma_pct"] = round((sub["R"] > 0).mean() * 100, 1)
            out[f"{tf}_ort_R"] = round(sub["R"].mean(), 3)
    return out
