import sqlite3
import json

conn = sqlite3.connect("data/valideer.db")
conn.row_factory = sqlite3.Row
c = conn.cursor()

cls_rows = c.execute("SELECT iso_kood, maarusejargne_nimetus, valdkond, liik FROM ametlik_klassifikaator").fetchall()
official_codes = {r["iso_kood"]: dict(r) for r in cls_rows}

print(f"Ametlikke koode: {len(official_codes)}")

with open("data/scanned_candidates_report.json", "r", encoding="utf-8") as f:
    d = json.load(f)

for cat_name, items in d["by_confidence"].items():
    print(f"\n=== {cat_name} ({len(items)} tk) ===")
    valid_direct = []
    for it in items:
        isos = it.get("matching_isos", [])
        if isos:
            for iso, name, reason in isos:
                if iso in official_codes:
                    valid_direct.append((it["raw_name"], iso, name, it["brand"], it["manufacturer"]))
    print(f"  Otsese ametliku koodiga tooteid: {len(valid_direct)}")
    for vd in valid_direct[:5]:
        print(f"    - [{vd[1]}] {vd[0][:40]} | Bränd: {vd[3]} | Tootja: {vd[4]}")
