import sqlite3
import json
import sys

sys.stdout.reconfigure(encoding='utf-8')
conn = sqlite3.connect('data/valideer.db')
cursor = conn.cursor()

cursor.execute("SELECT id, official_product_name, brand, product_family, ml_capacity, drop_rating, package_information, aliases FROM tooteregister WHERE aliases LIKE '%Abena San%' OR official_product_name LIKE '%ABENA%SAN%' LIMIT 20;")
rows = cursor.fetchall()
print(f"Total Abena San entries in tooteregister: {len(rows)}")
for r in rows:
    print(f"ID {r[0]}: Name='{r[1]}', Family='{r[3]}', ml={r[4]}, drop={r[5]}, pkg={r[6]}")
    aliases = json.loads(r[7])
    print(f"  Aliases: {aliases}")
conn.close()
