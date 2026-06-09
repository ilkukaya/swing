#!/usr/bin/env python3
# ============================================================
#  Swing v3 — Orkestrator (GitHub Actions her aksam calistirir)
#  Akis: tara -> yeni Long Adayi ekle (v damgali) -> acik sinyalleri
#  ileri coz -> kapananlari closed.csv ARSIVINE ekle -> performans +
#  rejim + korelasyon yaz -> snapshot + manifest.
#  signals.csv ve closed.csv APPEND-ONLY: gecmis silinmez (denetim izi).
# ============================================================
import os, json, glob, datetime as dt
import pandas as pd
import config as C
import swing_core as core
import track as T

DATA = "data"
SIG = f"{DATA}/signals.csv"
TRK = f"{DATA}/tracking.csv"
CLS = f"{DATA}/closed.csv"
PERF = f"{DATA}/performance.json"
REJ = f"{DATA}/regime.json"
SNAP = f"{DATA}/snapshots"

SIG_COLS = ["id", "tarih", "tf", "sembol", "karar", "kod", "skor",
            "giris", "stop", "t1", "t2", "direnc", "rr", "durum", "v"]
TRK_COLS = ["id", "sembol", "tf", "tarih", "giris", "giris_fiili", "stop", "t1", "t2",
            "son_fiyat", "getiri_pct", "durum", "R", "gun", "mfe", "mae", "son_tarih", "v"]


def _load_signals():
    if os.path.exists(SIG):
        df = pd.read_csv(SIG)
        if "v" not in df.columns:
            df["v"] = 2  # eski sinyaller v2 damgali kalir
        return df
    return pd.DataFrame(columns=SIG_COLS)


def _load_closed():
    if os.path.exists(CLS):
        return pd.read_csv(CLS)
    return pd.DataFrame(columns=TRK_COLS)


def _open_symbols(sig_df):
    if len(sig_df) == 0:
        return set()
    return set(sig_df[~sig_df["durum"].isin(T.CLOSED)]["sembol"])


def _add_new(sig_df, scan_df, today):
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
                             direnc=r["direnc"], rr=r["rr"], durum="ACIK", v=C.SISTEM_V))
        open_syms.add(r["sembol"])
    return new_rows


def main():
    os.makedirs(SNAP, exist_ok=True)
    today = dt.date.today().isoformat()
    is_friday = dt.date.today().weekday() == 4
    ozet = []  # GitHub Actions is ozeti icin

    sig_df = _load_signals()
    closed_hist = _load_closed()

    # 1) Taramalar
    daily_df, rejim = core.scan("1d")
    print(f"[{today}] Gunluk tarama: {len(daily_df)} hisse | rejim: {rejim['rejim']} "
          f"(nefes %{rejim['breadth']}, esik {rejim['esik']})")
    ozet.append(f"- Gunluk tarama: **{len(daily_df)}** hisse · rejim **{rejim['rejim']}** "
                f"(nefes %{rejim['breadth']}, esik {rejim['esik']})")
    scans = [("gunluk", daily_df)]
    if is_friday:
        weekly_df, _ = core.scan("1wk")
        print(f"[{today}] Haftalik tarama (Cuma): {len(weekly_df)} hisse")
        ozet.append(f"- Haftalik tarama: **{len(weekly_df)}** hisse")
        scans.append(("haftalik", weekly_df))

    # rejim dosyasi (pano banner'i)
    json.dump({"tarih": today, **{k: v for k, v in rejim.items()}},
              open(REJ, "w"), ensure_ascii=False, indent=2)

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
        adlar = [r["sembol"] for r in all_new]
        print(f"  + {len(all_new)} yeni sinyal: {adlar}")
        ozet.append(f"- Yeni sinyal: **{len(all_new)}** → {', '.join(adlar)}")
    else:
        print("  Yeni Long Adayi yok.")
        ozet.append("- Yeni Long Adayi yok")

    # 3) Takip — tum acik sinyaller (v3 cozumleyici: fiili giris + trail)
    open_sigs = sig_df[~sig_df["durum"].isin(T.CLOSED)].to_dict("records")
    trk_rows, kapanan, korr = T.update_tracking(open_sigs)
    if kapanan:
        st = {r["id"]: r["durum"] for r in trk_rows}
        sig_df["durum"] = sig_df.apply(
            lambda x: st.get(x["id"], x["durum"]) if x["id"] in kapanan else x["durum"], axis=1)
        # yeni kapananlari arsive ekle (id tekil)
        yeni_kapanan = [r for r in trk_rows if r["id"] in kapanan
                        and not (len(closed_hist) and (closed_hist["id"] == r["id"]).any())]
        if yeni_kapanan:
            closed_hist = pd.concat([closed_hist, pd.DataFrame(yeni_kapanan)], ignore_index=True)
            closed_hist.to_csv(CLS, index=False)
        adlar = [f"{r['sembol']}({r['durum']} {r['R']:+.2f}R)" for r in trk_rows if r["id"] in kapanan]
        print(f"  Kapanan: {adlar}")
        ozet.append(f"- Kapanan: {', '.join(adlar)}")

    # 4) tracking + performans (+ korelasyon)
    if trk_rows:
        pd.DataFrame(trk_rows)[TRK_COLS].to_csv(TRK, index=False)
    perf = T.performance(trk_rows, closed_hist)
    perf_out = {"guncelleme": today, "rejim": rejim["rejim"], "nefes": rejim["breadth"], **perf}
    if korr:
        perf_out["maks_korelasyon"] = korr
    json.dump(perf_out, open(PERF, "w"), ensure_ascii=False, indent=2)
    print(f"  Performans: {perf}")
    if korr:
        print(f"  Maks korelasyon: {korr}")

    # 5) signals.csv kaydet (append-only)
    sig_df[SIG_COLS].to_csv(SIG, index=False)

    # 6) snapshot manifesti
    snaps = sorted([os.path.basename(p) for p in glob.glob(f"{SNAP}/*.json")
                    if "manifest" not in os.path.basename(p)], reverse=True)
    manifest = []
    for fn in snaps:
        parts = fn[:-5].split("_")
        if len(parts) >= 2:
            manifest.append({"date": parts[0], "tf": parts[1], "file": fn})
    json.dump(manifest, open(f"{SNAP}/manifest.json", "w"), ensure_ascii=False, indent=2)

    acik = int((~sig_df["durum"].isin(T.CLOSED)).sum())
    print(f"[{today}] Tamam. Toplam sinyal: {len(sig_df)} (acik: {acik})")
    ozet.append(f"- Toplam sinyal: **{len(sig_df)}** (acik {acik}, kapanan {perf.get('kapanan', 0)}, "
                f"gap iptal {perf.get('gap_iptal', 0)})")

    # GitHub Actions is ozeti (Actions sayfasinda gorunur)
    sumf = os.environ.get("GITHUB_STEP_SUMMARY")
    if sumf:
        with open(sumf, "a") as f:
            f.write(f"## Swing v{C.SISTEM_V} — {today}\n" + "\n".join(ozet) + "\n")


if __name__ == "__main__":
    main()
