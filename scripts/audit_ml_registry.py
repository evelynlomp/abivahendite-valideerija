import sqlite3
import sys
sys.path.insert(0, '.')
from src.product_registry_db import infer_iso_and_statutory_name

conn = sqlite3.connect('data/valideer.db')
conn.row_factory = sqlite3.Row
c = conn.cursor()

c.execute("""
    SELECT id, brand, manufacturer, official_product_name, product_type, ml_capacity, drop_rating
    FROM tooteregister
    WHERE ml_capacity IS NOT NULL
""")
rows = c.fetchall()
print(f"Total products with ml_capacity: {len(rows)}")

discrepancies = []
for r in rows:
    p_id = r['id']
    brand = r['brand']
    mfg = r['manufacturer']
    name = r['official_product_name']
    p_type = r['product_type']
    ml = r['ml_capacity']
    drops = r['drop_rating']

    # Current inference
    curr_iso, curr_stat = infer_iso_and_statutory_name(brand, name, p_type, ml=ml, drops=drops)

    # Pure volume range calculation for incontinence products
    # Based on Sotsiaalministeeriumi määrus nr 74:
    name_upper = name.upper()
    is_men = any(m in name_upper for m in ["MEN", "MAN", "MEESTE"]) and not any(w in name_upper for w in ["WOMEN", "NAISTE", "LADY"])
    
    calc_iso = None
    if any(x in (p_type or '').lower() for x in ["side", "pad", "inkontinentsiside", "vorm", "vormmähe", "vormmähkmed", "püks", "pants", "pull-up", "mähk"]):
        if is_men and any(x in (p_type or '').lower() for x in ["side", "pad", "inkontinentsiside"]):
            if ml <= 399: calc_iso = "09.30.24.11"
            elif 400 <= ml <= 599: calc_iso = "09.30.24.12"
            else: calc_iso = "09.30.24.13"
        elif any(x in (p_type or '').lower() for x in ["püks", "pants", "pull-up"]):
            # Püksmähkmed mahuvahemikud
            if ml < 1400: calc_iso = "09.30.24.82" # imavad püksid kuni 1399 ml M / S
            elif 1400 <= ml <= 1899: calc_iso = "09.30.24.32" # püksmähkmed kuni 1899 ml M
            elif 1900 <= ml <= 2499: calc_iso = "09.30.24.36" # püksmähkmed 1900 - 2499 ml M
            elif 2500 <= ml <= 2999: calc_iso = "09.30.24.42" # püksmähkmed 2500 - 2999 ml M
            else: calc_iso = "09.30.24.47"
        elif any(x in (p_type or '').lower() for x in ["side", "pad", "inkontinentsiside"]) or "MINI" in name_upper or "LIGHT" in name_upper:
            if 201 <= ml <= 299: calc_iso = "09.30.24.14"
            elif 300 <= ml <= 599: calc_iso = "09.30.24.15"
            elif 600 <= ml <= 999: calc_iso = "09.30.24.16"
            elif 1000 <= ml <= 1499: calc_iso = "09.30.24.17"
            elif 1500 <= ml <= 1999: calc_iso = "09.30.24.18"
            elif 2000 <= ml <= 2499: calc_iso = "09.30.24.19"
            elif 2500 <= ml <= 2999: calc_iso = "09.30.24.20"
            elif ml >= 3000: calc_iso = "09.30.24.21"
        elif any(x in (p_type or '').lower() for x in ["vorm", "vormmähe", "vormmähkmed"]):
            if 201 <= ml <= 299: calc_iso = "09.30.24.22"
            elif 300 <= ml <= 599: calc_iso = "09.30.24.23"
            elif 600 <= ml <= 999: calc_iso = "09.30.24.24"
            elif 1000 <= ml <= 1499: calc_iso = "09.30.24.25"
            elif 1500 <= ml <= 1999: calc_iso = "09.30.24.26"
            elif 2000 <= ml <= 2499: calc_iso = "09.30.24.27"
            elif 2500 <= ml <= 2999: calc_iso = "09.30.24.28"
            elif ml >= 3000: calc_iso = "09.30.24.29"

    if calc_iso and curr_iso != calc_iso:
        discrepancies.append({
            'id': p_id,
            'product': f"{brand} {name}",
            'manufacturer': mfg,
            'type': p_type,
            'ml': ml,
            'current_iso': curr_iso,
            'expected_iso': calc_iso
        })

print(f"Total discrepancies found: {len(discrepancies)}")
for d in discrepancies[:25]:
    print(f"ID {d['id']}: {d['product']} | Type: {d['type']} | ML: {d['ml']} | Curr: {d['current_iso']} -> Exp: {d['expected_iso']}")

conn.close()
