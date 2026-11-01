import sqlite3
import json
import os
import sys

sys.stdout.reconfigure(encoding='utf-8')

DB_PATH = 'data/valideer.db'

conn = sqlite3.connect(DB_PATH)
conn.row_factory = sqlite3.Row
cursor = conn.cursor()

# 1. Count query
cursor.execute("SELECT count(*) FROM tooteregister;")
total_count = cursor.fetchone()[0]

# 2. First 20 rows
cursor.execute("""
    SELECT id, manufacturer, brand, product_family, official_product_name,
           package_information, ml_capacity, drop_rating, product_type,
           source_supplier
    FROM tooteregister
    ORDER BY id ASC
    LIMIT 20;
""")
first_20 = cursor.fetchall()

# 3. Example merged product sold by multiple suppliers
cursor.execute("""
    SELECT id, official_product_name, brand, manufacturer, package_information,
           ml_capacity, drop_rating, product_type, source_supplier, source_url, aliases
    FROM tooteregister
    WHERE source_supplier LIKE '%,%'
    LIMIT 5;
""")
merged_products = cursor.fetchall()

# 4. Example alias groups for ABENA, MOLICARE, TENA
alias_examples = {}
for brand_name in ["ABENA", "MOLICARE", "TENA"]:
    cursor.execute("""
        SELECT official_product_name, brand, manufacturer, product_family,
               package_information, ml_capacity, drop_rating, product_type,
               source_supplier, aliases
        FROM tooteregister
        WHERE brand = ? AND json_array_length(aliases) > 1
        ORDER BY json_array_length(aliases) DESC
        LIMIT 1;
    """, (brand_name,))
    row = cursor.fetchone()
    if row:
        alias_examples[brand_name] = dict(row)

# 5. Database file stats
db_size_bytes = os.path.getsize(DB_PATH)

conn.close()

# Print results in structured JSON / readable form
print("=== 1. COUNT QUERY ===")
print("Query: SELECT count(*) FROM tooteregister;")
print(f"Result: {total_count}")

print("\n=== 2. FIRST 20 ROWS ===")
for r in first_20:
    print(f"ID {r['id']:<5} | Brand: {r['brand']:<12} | Name: {r['official_product_name']:<30} | Supp: {r['source_supplier']:<15} | Type: {r['product_type']}")

print("\n=== 3. MERGED PRODUCTS (MULTIPLE SUPPLIERS) ===")
for mp in merged_products:
    print(f"ID: {mp['id']}")
    print(f"  Official Name: {mp['official_product_name']}")
    print(f"  Brand: {mp['brand']} | Manufacturer: {mp['manufacturer']}")
    print(f"  Suppliers: {mp['source_supplier']}")
    print(f"  URLs: {mp['source_url']}")
    print(f"  Aliases: {json.loads(mp['aliases'])}")
    print("-" * 50)

print("\n=== 4. ALIAS GROUPS ===")
for b, data in alias_examples.items():
    print(f"[{b}] {data['official_product_name']}")
    print(f"  Tootja: {data['manufacturer']}")
    print(f"  Tarnijad: {data['source_supplier']}")
    aliases = json.loads(data['aliases'])
    print(f"  Aliaste arv: {len(aliases)}")
    for a in aliases:
        print(f"    - {a}")
    print()

print("=== 5. PHYSICAL SQLITE STATS ===")
print(f"File path: {os.path.abspath(DB_PATH)}")
print(f"File size: {db_size_bytes} bytes ({db_size_bytes / (1024*1024):.2f} MB)")
