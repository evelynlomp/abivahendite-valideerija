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
print(f"Total products in registry with ml_capacity: {len(rows)}")

discrepancies = []
for r in rows:
    p_id = r['id']
    brand = r['brand']
    mfg = r['manufacturer']
    name = r['official_product_name']
    p_type = r['product_type']
    ml = r['ml_capacity']
    drops = r['drop_rating']

    iso, stat = infer_iso_and_statutory_name(brand, name, p_type, ml=ml, drops=drops)

    # Let's verify if the assigned ISO matches the ml range in the statutory name
    # e.g. if stat is "inkontinentsisidemed naistele 600 - 999 ml", ml MUST be between 600 and 999!
    m_range = None
    if stat:
        import re
        rng_match = re.search(r'(\d+)\s*[-–]\s*(\d+)\s*ml', stat, re.I)
        if rng_match:
            low, high = int(rng_match.group(1)), int(rng_match.group(2))
            if not (low <= ml <= high):
                discrepancies.append({
                    'id': p_id,
                    'product': f"{brand} {name}",
                    'manufacturer': mfg,
                    'ml': ml,
                    'current_iso': iso,
                    'statutory_name': stat,
                    'expected_range': f"{low}-{high} ml",
                    'type': p_type
                })
        elif "kuni" in stat:
            kuni_match = re.search(r'kuni\s*(\d+)\s*ml', stat, re.I)
            if kuni_match:
                high = int(kuni_match.group(1))
                if ml > high:
                    discrepancies.append({
                        'id': p_id,
                        'product': f"{brand} {name}",
                        'manufacturer': mfg,
                        'ml': ml,
                        'current_iso': iso,
                        'statutory_name': stat,
                        'expected_range': f"kuni {high} ml",
                        'type': p_type
                    })
        elif "üle" in stat:
            ule_match = re.search(r'üle\s*(\d+)\s*ml', stat, re.I)
            if ule_match:
                low = int(ule_match.group(1))
                if ml < low:
                    discrepancies.append({
                        'id': p_id,
                        'product': f"{brand} {name}",
                        'manufacturer': mfg,
                        'ml': ml,
                        'current_iso': iso,
                        'statutory_name': stat,
                        'expected_range': f"üle {low} ml",
                        'type': p_type
                    })

print(f"Total range-discrepant products found: {len(discrepancies)}")
for d in discrepancies[:30]:
    print(f"ID {d['id']}: {d['product']} | ML: {d['ml']} | ISO: {d['current_iso']} ({d['statutory_name']}) | Range: {d['expected_range']}")

conn.close()
