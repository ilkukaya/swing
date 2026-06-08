#!/usr/bin/env python3
# ============================================================
#  Swing v2 — Orkestrator (GitHub Actions her gun calistirir)
#  1) Gunluk tarama (Cuma ek olarak haftalik)
#  2) Yeni Long Adayi'lari signals.csv'ye ekler (acik degilse)
#  3) Tum acik sinyalleri ileri dogru takip eder -> tracking.csv
#  4) Performans ozetini hesaplar -> performance.json
#  5) Gunun tam radarini snapshots/ altina yazar
#  signals.csv APPEND-ONLY mantiktadir: gecmis silinmez, denetim izi kalir.
# ============================================================
import os, json, glob, datetime as dt
import pandas as pd
import config as C
import swing_core as core
import track as T

DATA = "data"
SIG = f"{DATA}/signals.csv"
TRK = f"{DATA}/tracking.csv"
PERF = f"{DATA}/performance.json"
SNAP = f"{DATA}/snapshots"

SIG_COLS = ["id", "tarih", "tf", "sembol", "karar", "kod", "skor",
            "giris", "stop", "t1", "t2", "direnc", "rr", "durum"]


def _load_signals():
    if os.path.exists(SIG):
        return pd.read_csv(SIG)
    return pd.DataFrame(columns=SIG_COLS)


def _open_symbols(sig_df):
    if len(sig_df) == 0:
        return set()
    return set(sig_df[~sig_df["durum"].isin(T.CLOSED)]["sembol"])


def _add_new(sig_df, scan_df, today):
    """Yeni Long Adayi'lari (acik olmayan) signals'a ekler."""
    open_syms = _open_symbols(sig_df)
    new_rows = []
    cand = scan_df[scan_df["kod"] >= C.ENTRY_MIN_CODE]
    for _, r in cand.iterrows():
        if r["sembol"] in open_syms:
            continue
        sid = f"{today}_{r['sembol']}_{r['tf']}"
        if len(sig_df) and (sig_df["id"] == sid).any():
            continue
        new_rows.append(dict(id=sid, tarih=today, tf=r["tf"], sembol=r["sembol"],
                             karar=r["karar"], kod=int(r["kod"]), skor=int(r["skor"]),
                             giris=r["fiyat"], stop=r["stop"], t1=r["t1"], t2=r["t2"],
                             direnc=r["direnc"], rr=r["rr"], durum="ACIK"))
        open_syms.add(r["sembol"])
    return new_rows


def main():
    os.makedirs(SNAP, exist_ok=True)
    today = dt.date.today().isoformat()
    is_friday = dt.date.today().weekday() == 4

    sig_df = _load_signals()

    # 1) Taramalar
    daily_df, mkt = core.scan("1d")
    print(f"[{today}] Gunluk tarama: {len(daily_df)} gecerli hisse | piyasa: {'POZITIF' if mkt else 'ZAYIF'}")
    scans = [("gunluk", daily_df)]
    if is_friday:
        weekly_df, _ = core.scan("1wk")
        print(f"[{today}] Haftalik tarama (Cuma): {len(weekly_df)} hisse")
        scans.append(("haftalik", weekly_df))

    # 2) Yeni sinyaller + snapshot
    all_new = []
    for tf_name, sdf in scans:
        if len(sdf) == 0:
            continue
        all_new += _add_new(sig_df, sdf, today)
        radar = sdf[sdf["kod"] >= 2]
        radar.to_json(f"{SNAP}/{today}_{tf_name}.json", orient="records", force_ascii=False, indent=2)
    if all_new:
        sig_df = pd.concat([sig_df, pd.DataFrame(all_new)], ignore_index=True)
        print(f"  + {len(all_new)} yeni sinyal eklendi: {[r['sembol'] for r in all_new]}")
    else:
        print("  Yeni Long Adayi yok.")

    # 3) Takip — tum acik sinyaller
    open_sigs = sig_df[~sig_df["durum"].isin(T.CLOSED)].to_dict("records")
    trk_rows, kapanan = T.update_tracking(open_sigs)
    if kapanan:
        # signals durumunu guncelle
        st = {row["id"]: row["durum"] for row in trk_rows}
        sig_df["durum"] = sig_df.apply(lambda x: st.get(x["id"], x["durum"]) if x["id"] in kapanan else x["durum"], axis=1)
        print(f"  {len(kapanan)} sinyal kapandi.")

    # 4) tracking.csv (tum acik + bugun kapananlarin son hali)
    if trk_rows:
        pd.DataFrame(trk_rows).to_csv(TRK, index=False)

    # tum zamanlarin tracking'i icin: kapanmis olanlari da koru
    # (tracking.csv sadece acik+yeni kapananlari tutar; gecmis kapananlar performansta birikir)
    # performans: signals'taki tum kapanmislari da hesaba kat
    closed_hist = sig_df[sig_df["durum"].isin(T.CLOSED)]
    perf_rows = trk_rows + [
        dict(id=r["id"], sembol=r["sembol"], tf=r["tf"], tarih=r["tarih"],
             giris=r["giris"], stop=r["stop"], t1=r["t1"], t2=r["t2"],
             son_fiyat=r["giris"], getiri_pct=0, durum=r["durum"], R=0, gun=0, mfe=0, mae=0)
        for _, r in closed_hist.iterrows() if r["id"] not in {x["id"] for x in trk_rows}
    ]
    perf = T.performance(trk_rows)
    with open(PERF, "w") as f:
        json.dump({"guncelleme": today, **perf}, f, ensure_ascii=False, indent=2)
    print(f"  Performans: {perf}")

    # 5) signals.csv kaydet (append-only)
    sig_df[SIG_COLS].to_csv(SIG, index=False)

    # 6) snapshot manifesti (panonun gunluk gezinmesi icin)
    snaps = sorted([os.path.basename(p) for p in glob.glob(f"{SNAP}/*.json")
                    if "manifest" not in os.path.basename(p)], reverse=True)
    manifest = []
    for fn in snaps:
        parts = fn[:-5].split("_")
        if len(parts) >= 2:
            manifest.append({"date": parts[0], "tf": parts[1], "file": fn})
    json.dump(manifest, open(f"{SNAP}/manifest.json", "w"), ensure_ascii=False, indent=2)

    print(f"[{today}] Tamam. Toplam sinyal: {len(sig_df)} (acik: {(~sig_df['durum'].isin(T.CLOSED)).sum()})")


if __name__ == "__main__":
    main()
