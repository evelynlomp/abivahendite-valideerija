import sqlite3
import json
import sys

sys.stdout.reconfigure(encoding='utf-8')
conn = sqlite3.connect('data/valideer.db')
conn.row_factory = sqlite3.Row
cursor = conn.cursor()

print("--- 1. DUPLICATE PRODUCTS AUDIT ---")
cursor.execute("""
    SELECT official_product_name, brand, count(*) as cnt, GROUP_CONCAT(id) as ids,
           GROUP_CONCAT(COALESCE(ml_capacity, 'NULL')) as mls,
           GROUP_CONCAT(COALESCE(drop_rating, 'NULL')) as drops,
           GROUP_CONCAT(source_supplier) as supps
    FROM tooteregister
    GROUP BY official_product_name, brand
    HAVING count(*) > 1
    ORDER BY cnt DESC
    LIMIT 10;
""")
dupe_samples = cursor.fetchall()
for d in dupe_samples:
    print(f"Product: '{d['official_product_name']}' | Brand: {d['brand']} | Count: {d['cnt']}")
    print(f"  IDs: {d['ids']}")
    print(f"  Capacities (ml): {d['mls']}")
    print(f"  Drop ratings: {d['drops']}")
    print(f"  Suppliers: {d['supps']}")
    print()

print("--- 2. ALIAS COLLISIONS AUDIT ---")
cursor.execute("SELECT id, official_product_name, aliases FROM tooteregister;")
rows = cursor.fetchall()
alias_map = {}
for r in rows:
    p_id = r['id']
    name = r['official_product_name']
    aliases = json.loads(r['aliases']) if r['aliases'] else []
    for a in aliases:
        a_clean = a.strip().upper()
        if a_clean not in alias_map:
            alias_map[a_clean] = []
        alias_map[a_clean].append((p_id, name))

collisions = {a: prods for a, prods in alias_map.items() if len(prods) > 1}
print(f"Total unique aliases in registry: {len(alias_map)}")
print(f"Total colliding aliases: {len(collisions)} ({len(collisions)/len(alias_map)*100:.1f}%)")

print("\nSample top collisions:")
for a, prods in sorted(collisions.items(), key=lambda x: -len(x[1]))[:8]:
    print(f"Alias: '{a}' -> {len(prods)} products:")
    for pid, pname in prods[:4]:
        print(f"   ID {pid}: {pname}")
    if len(prods) > 4:
        print(f"   ... and {len(prods)-4} more")

print("\n--- 3. UNMAPPED ATTRIBUTES ---")
cursor.execute("SELECT count(*) FROM tooteregister WHERE manufacturer = 'Määramata';")
unmapped_mfg = cursor.fetchone()[0]

cursor.execute("SELECT count(*) FROM tooteregister WHERE product_type = 'muu abivahend';")
unmapped_cat = cursor.fetchone()[0]

cursor.execute("SELECT count(*) FROM tooteregister WHERE ml_capacity IS NULL AND drop_rating IS NULL;")
missing_ml_drops = cursor.fetchone()[0]

print(f"Unmapped manufacturers: {unmapped_mfg} / 4994 ({unmapped_mfg/4994*100:.1f}%)")
print(f"Generic category 'muu abivahend': {unmapped_cat} / 4994 ({unmapped_cat/4994*100:.1f}%)")
print(f"Missing both ml and drop rating: {missing_ml_drops} / 4994 ({missing_ml_drops/4994*100:.1f}%)")

print("\n--- 4. ENCODING ARTIFACTS ---")
cursor.execute("""
    SELECT id, official_product_name, aliases 
    FROM tooteregister 
    WHERE official_product_name LIKE '%&#%' OR aliases LIKE '%&#%'
    LIMIT 5;
""")
encoded = cursor.fetchall()
for e in encoded:
    print(f"ID {e['id']}: {e['official_product_name']}")
    for a in json.loads(e['aliases']):
        if '&#8211;' in a or '&#215;' in a:
            print(f"  Artifact alias: {a}")

conn.close()
