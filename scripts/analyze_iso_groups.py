import sys
import os
sys.path.insert(0, os.path.abspath("."))
import sqlite3
from collections import defaultdict
from src.product_registry_db import infer_iso_and_statutory_name

conn = sqlite3.connect("data/valideer.db")
conn.row_factory = sqlite3.Row
c = conn.cursor()

# 1. Klassifikaatori grupid (2- ja 4-kohalised ISO-d)
class_rows = c.execute("SELECT iso_kood, maarusejargne_nimetus, valdkond, liik, piirlimiit, piirhind_muuk, piirhind_uur FROM ametlik_klassifikaator").fetchall()

iso_groups = defaultdict(list)
for r in class_rows:
    parts = r["iso_kood"].split(".")
    grp2 = parts[0]
    grp4 = ".".join(parts[:2]) if len(parts) >= 2 else grp2
    iso_groups[grp4].append(dict(r))

# 2. Tooteregistri toodete vastendus
prods = c.execute("SELECT id, manufacturer, brand, product_family, official_product_name, product_type, ml_capacity, drop_rating, package_information FROM tooteregister").fetchall()

prods_per_iso = defaultdict(int)
prods_per_grp4 = defaultdict(int)

for p in prods:
    iso, _ = infer_iso_and_statutory_name(
        p["brand"] or "",
        p["official_product_name"] or "",
        p["product_type"] or "",
        p["ml_capacity"],
        p["drop_rating"],
        p["package_information"] or ""
    )
    if iso:
        prods_per_iso[iso] += 1
        parts = iso.split(".")
        grp4 = ".".join(parts[:2]) if len(parts) >= 2 else parts[0]
        prods_per_grp4[grp4] += 1

print("=== 4-KOHALISTE ISO RÜHMADE KATVUS AMETLIKUS KLASSIFIKAATORIS ===")
grp_summary = []
for grp4, items in iso_groups.items():
    valdkonnad = set(it["valdkond"] for it in items)
    liigid = set(it["liik"] for it in items if it["liik"])
    nimetused = [it["maarusejargne_nimetus"] for it in items]
    prod_cnt = prods_per_grp4[grp4]
    iso_cnt = len(items)
    
    # Hinda piirhindade taset
    prices = [it["piirhind_muuk"] for it in items if it["piirhind_muuk"]]
    rent_prices = [it["piirhind_uur"] for it in items if it["piirhind_uur"]]
    avg_price = (sum(prices)/len(prices)) if prices else 0
    avg_rent = (sum(rent_prices)/len(rent_prices)) if rent_prices else 0
    
    grp_summary.append({
        "grp4": grp4,
        "valdkond": ", ".join(valdkonnad),
        "liigid": ", ".join(list(liigid)[:2]),
        "sample_name": nimetused[0],
        "iso_cnt": iso_cnt,
        "prod_cnt": prod_cnt,
        "avg_price": avg_price,
        "avg_rent": avg_rent
    })

# Sorteerime toodete arvu järgi kasvavalt (kõige vähem kaetud ees)
for g in sorted(grp_summary, key=lambda x: (x["prod_cnt"], -x["iso_cnt"], -x["avg_price"])):
    print(f"ISO {g['grp4']:7} | Valdkond: {g['valdkond']:22} | ISO koode: {g['iso_cnt']:2} | Tooteid: {g['prod_cnt']:4} | Keskm. piirhind: {g['avg_price']:6.1f} € | Keskm. üür: {g['avg_rent']:5.1f} € | Näidis: {g['sample_name'][:35]}")
