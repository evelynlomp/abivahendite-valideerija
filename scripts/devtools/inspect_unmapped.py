import sqlite3
import json
import sys

sys.stdout.reconfigure(encoding='utf-8')
conn = sqlite3.connect('data/valideer.db')
cursor = conn.cursor()

cursor.execute("SELECT official_product_name, source_supplier, source_url FROM tooteregister WHERE manufacturer = 'Määramata' LIMIT 20;")
rows = cursor.fetchall()
print("Sample 'Määramata' products:")
for r in rows:
    print(f"  Name: {r[0]} | Supplier: {r[1]}")
