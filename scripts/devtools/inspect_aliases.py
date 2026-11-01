import sqlite3
import json
import sys

sys.stdout.reconfigure(encoding='utf-8')
conn = sqlite3.connect('data/valideer.db')
cursor = conn.cursor()

cursor.execute("SELECT official_product_name, aliases, source_supplier FROM tooteregister WHERE aliases LIKE '%Abena San%' OR aliases LIKE '%MoliCare%' LIMIT 25;")
rows = cursor.fetchall()
print("Matches for Abena San / MoliCare:")
for r in rows:
    print(f"Name: {r[0]} | Supp: {r[2]}")
    aliases = json.loads(r[1])
    print(f"  Aliases: {aliases[:3]}")
