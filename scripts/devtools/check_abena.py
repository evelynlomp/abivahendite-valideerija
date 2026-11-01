import sqlite3
import json
import sys

sys.stdout.reconfigure(encoding='utf-8')
conn = sqlite3.connect('data/valideer.db')
cursor = conn.cursor()

cursor.execute("SELECT id, official_product_name, brand, product_family, aliases FROM tooteregister WHERE official_product_name LIKE '%ABENA SAN%' OR aliases LIKE '%Abena San%' OR aliases LIKE '%Abri-San%' LIMIT 10;")
rows = cursor.fetchall()
print("Abena San rows:", len(rows))
for r in rows:
    print(f"ID {r[0]}: Name='{r[1]}', Family='{r[3]}'")
    aliases = json.loads(r[4])
    print(f"  Aliases: {aliases}")
conn.close()
