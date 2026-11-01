import sqlite3
import json
import re
from collections import defaultdict, Counter
import sys

sys.stdout.reconfigure(encoding='utf-8')

conn = sqlite3.connect('data/valideer.db')
conn.row_factory = sqlite3.Row
cursor = conn.cursor()

# 1. Total records
cursor.execute("SELECT count(*) FROM tooteregister;")
total_records = cursor.fetchone()[0]

# 2. Duplicate official product names
cursor.execute("""
    SELECT official_product_name, count(*) as cnt, GROUP_CONCAT(id) as ids, GROUP_CONCAT(brand) as brands
    FROM tooteregister
    GROUP BY official_product_name
    HAVING count(*) > 1
    ORDER BY cnt DESC;
""")
name_duplicates = cursor.fetchall()

# 3. Duplicate aliases (alias collisions across different products)
cursor.execute("SELECT id, official_product_name, aliases FROM tooteregister;")
all_rows = cursor.fetchall()

alias_to_ids = defaultdict(list)
for r in all_rows:
    p_id = r['id']
    aliases = json.loads(r['aliases']) if r['aliases'] else []
    for a in aliases:
        a_clean = a.strip().upper()
        alias_to_ids[a_clean].append(p_id)

alias_collisions = {a: ids for a, ids in alias_to_ids.items() if len(ids) > 1}

# 4. Incomplete or unmapped attributes
cursor.execute("SELECT count(*) FROM tooteregister WHERE manufacturer = 'Määramata';")
unmapped_mfg = cursor.fetchone()[0]

cursor.execute("SELECT count(*) FROM tooteregister WHERE brand = 'MÄÄRAMATA';")
unmapped_brand = cursor.fetchone()[0]

cursor.execute("SELECT count(*) FROM tooteregister WHERE product_type = 'muu abivahend';")
unmapped_type = cursor.fetchone()[0]

# 5. HTML entities or encoding artifacts in names
cursor.execute("SELECT id, official_product_name, aliases FROM tooteregister WHERE official_product_name LIKE '%&%' OR official_product_name LIKE '%#%' OR aliases LIKE '%&%' LIMIT 10;")
html_artifacts = cursor.fetchall()

# 6. Incontinence products missing volume or drops
cursor.execute("""
    SELECT count(*) FROM tooteregister 
    WHERE product_type IN ('inkontinentsiside', 'vormmähe', 'püksmähe', 'klassikaline mähe')
      AND ml_capacity IS NULL AND drop_rating IS NULL;
""")
inco_missing_params = cursor.fetchone()[0]

cursor.execute("""
    SELECT count(*) FROM tooteregister 
    WHERE product_type IN ('inkontinentsiside', 'vormmähe', 'püksmähe', 'klassikaline mähe');
""")
inco_total = cursor.fetchone()[0]

print("=== REGISTRY AUDIT SUMMARY ===")
print(f"Total physical records: {total_records}")
print(f"Duplicate official product names: {len(name_duplicates)} names duplicated across {sum(r['cnt'] for r in name_duplicates)} records")
print(f"Top 10 duplicated names:")
for r in name_duplicates[:10]:
    print(f"  '{r['official_product_name']}': {r['cnt']} occurrences (IDs: {r['ids'][:30]}...)")

print(f"\nAlias collisions (same alias pointing to multiple products): {len(alias_collisions)} aliases")
sample_coll = list(alias_collisions.items())[:5]
for a, ids in sample_coll:
    print(f"  Alias '{a}': mapped to IDs {ids}")

print(f"\nUnmapped manufacturer: {unmapped_mfg} ({unmapped_mfg/total_records*100:.1f}%)")
print(f"Unmapped brand: {unmapped_brand} ({unmapped_brand/total_records*100:.1f}%)")
print(f"Generic 'muu abivahend' category: {unmapped_type} ({unmapped_type/total_records*100:.1f}%)")
print(f"HTML artifacts in names: {len(html_artifacts)} records found")
print(f"Incontinence products: {inco_total} total, {inco_missing_params} missing both ml & drops ({inco_missing_params/inco_total*100:.1f}%)")

conn.close()
