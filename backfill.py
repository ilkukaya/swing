#!/usr/bin/env python3
# Tek seferlik: 5 Haziran haftalik 4 Long Adayi'ni signals.csv'ye tohumlar.
# Calistirdiktan sonra normal run.py (ya da Action) bunlari Cuma'dan ileri takip eder.
# Idempotent: zaten varsa tekrar eklemez. Bir kez calistir, sonra silebilirsin.
import os, pandas as pd
SIG = "data/signals.csv"
COLS = ["id","tarih","tf","sembol","karar","kod","skor","giris","stop","t1","t2","direnc","rr","durum"]
D = "2026-06-05"
seed = [
    # sembol, skor, giris, stop, t1, t2, rr  (5 Haz haftalik plan)
    ("AGHOL", 82, 32.30, 29.05, 37.18, 38.81, 1.2),
    ("TTKOM", 81, 62.30, 55.69, 72.22, 75.52, 1.4),
    ("MAVI",  81, 43.60, 39.12, 50.31, 52.55, 1.6),
    ("AKSA",  78, 10.65,  9.89, 11.79, 12.17, 1.0),
]
df = pd.read_csv(SIG) if os.path.exists(SIG) else pd.DataFrame(columns=COLS)
rows = []
for sym, skor, giris, stop, t1, t2, rr in seed:
    sid = f"{D}_{sym}_haftalik"
    if len(df) and (df["id"] == sid).any():
        print(f"  atlandi (zaten var): {sid}"); continue
    direnc = round(giris + rr * (giris - stop), 2)
    rows.append(dict(id=sid, tarih=D, tf="haftalik", sembol=sym, karar="Long Adayi",
                     kod=5, skor=skor, giris=giris, stop=stop, t1=t1, t2=t2,
                     direnc=direnc, rr=rr, durum="ACIK"))
if rows:
    df = pd.concat([df, pd.DataFrame(rows)], ignore_index=True)
    df[COLS].to_csv(SIG, index=False)
    print(f"  {len(rows)} sinyal tohumlandi (5 Haz): {[r['sembol'] for r in rows]}")
print("Bitti. Simdi: python run.py  (ya da Action) takibi baslatir.")
