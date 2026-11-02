import sys
import os
sys.path.insert(0, os.path.abspath("."))
import sqlite3
from collections import Counter
from src.product_registry_db import infer_iso_and_statutory_name

conn = sqlite3.connect("data/valideer.db")
conn.row_factory = sqlite3.Row
c = conn.cursor()

prods = c.execute("SELECT id, manufacturer, brand, product_family, official_product_name, product_type, ml_capacity, drop_rating, package_information FROM tooteregister").fetchall()

unmapped_types = Counter()
unmapped_samples = []
for p in prods:
    brand = p["brand"] or ""
    name = p["official_product_name"] or ""
    p_type = p["product_type"] or ""
    ml = p["ml_capacity"]
    drops = p["drop_rating"]
    pkg = p["package_information"] or ""
    
    iso, stat_name = infer_iso_and_statutory_name(brand, name, p_type, ml, drops, pkg)
    if not iso:
        unmapped_types[p_type] += 1
        if len(unmapped_samples) < 15:
            unmapped_samples.append((p["official_product_name"], p_type, p["brand"], p["manufacturer"]))

print("=== UNMAPPED PRODUCT TYPES ===")
for pt, cnt in unmapped_types.most_common(15):
    print(f"{pt}: {cnt}")

print("\n=== UNMAPPED SAMPLES ===")
for s in unmapped_samples:
    print(s)
