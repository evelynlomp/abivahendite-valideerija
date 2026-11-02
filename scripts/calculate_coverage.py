import sys
import os
sys.path.insert(0, os.path.abspath("."))
import sqlite3
from collections import defaultdict
from src.product_registry_db import infer_iso_and_statutory_name

conn = sqlite3.connect("data/valideer.db")
conn.row_factory = sqlite3.Row
c = conn.cursor()

# 1. Laadi ametlik klassifikaator
class_rows = c.execute("SELECT iso_kood, maarusejargne_nimetus, valdkond, liik, piirlimiit, piirhind_muuk, piirhind_uur FROM ametlik_klassifikaator").fetchall()
all_isos = {r["iso_kood"]: dict(r) for r in class_rows}

print(f"Klassifikaatoris kokku ISO koode: {len(all_isos)}")

# 2. Kaardista kõik tooteregistri tooted
prods = c.execute("SELECT id, manufacturer, brand, product_family, official_product_name, product_type, ml_capacity, drop_rating, package_information FROM tooteregister").fetchall()
print(f"Tooteregistris tooteid kokku: {len(prods)}")

iso_counts = defaultdict(int)
valdkond_counts = defaultdict(int)
liik_counts = defaultdict(int)
unmapped = []

for p in prods:
    brand = p["brand"] or ""
    name = p["official_product_name"] or ""
    p_type = p["product_type"] or ""
    ml = p["ml_capacity"]
    drops = p["drop_rating"]
    pkg = p["package_information"] or ""
    
    iso, stat_name = infer_iso_and_statutory_name(brand, name, p_type, ml, drops, pkg)
    if iso:
        iso_counts[iso] += 1
        # Leia klassifikaatorist valdkond
        # Kui täpne kood puudub, otsi prefiksi järgi
        matched_cls = all_isos.get(iso)
        if not matched_cls:
            # Otsi prefiksiga
            for k, v in all_isos.items():
                if k.startswith(iso) or iso.startswith(k):
                    matched_cls = v
                    break
        if matched_cls:
            valdkond_counts[matched_cls["valdkond"]] += 1
            liik_counts[f"{matched_cls['valdkond']} > {matched_cls['liik']}"] += 1
        else:
            valdkond_counts["MÄÄRAMATA"] += 1
    else:
        unmapped.append(dict(p))

print(f"Edukalt kaardistatud ISO-le: {len(prods) - len(unmapped)} toodet")
print(f"Kaardistamata: {len(unmapped)} toodet")

print("\n=== TOODETE ARV VALDKONDADE KAUPA ===")
for v, cnt in sorted(valdkond_counts.items(), key=lambda x: x[1], reverse=True):
    print(f"{v}: {cnt} toodet")

print("\n=== KLASSIFIKAATORI VALDKONNAD JA NENDE KATTE MÄÄR ===")
# Arvutame iga valdkonna ametlike koodide arvu ja kaetud toodete arvu
valdkond_stat = defaultdict(lambda: {"iso_count": 0, "prod_count": 0, "covered_isos": 0})
for iso, info in all_isos.items():
    v = info["valdkond"]
    valdkond_stat[v]["iso_count"] += 1
    c_p = iso_counts.get(iso, 0)
    # kontrolli ka prefiksit
    if c_p == 0:
        c_p = sum(cnt for i_k, cnt in iso_counts.items() if i_k.startswith(iso) or iso.startswith(i_k))
    if c_p > 0:
        valdkond_stat[v]["covered_isos"] += 1
        valdkond_stat[v]["prod_count"] += c_p

for v, st in sorted(valdkond_stat.items(), key=lambda x: x[1]["prod_count"]):
    cov_pct = (st["covered_isos"] / st["iso_count"] * 100) if st["iso_count"] else 0
    print(f"Valdkond: {v:25} | ISO koode loetelus: {st['iso_count']:2} | Kaetud ISO-sid: {st['covered_isos']:2} ({cov_pct:4.1f}%) | Toodete arv registris: {st['prod_count']:4}")
