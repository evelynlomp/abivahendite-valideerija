import sqlite3
import json
import sys

sys.stdout.reconfigure(encoding='utf-8')
conn = sqlite3.connect('data/valideer.db')
conn.row_factory = sqlite3.Row
c = conn.cursor()

c.execute("""
    SELECT id, official_product_name, brand, manufacturer, package_information,
           ml_capacity, drop_rating, product_type, source_supplier, source_url, aliases
    FROM tooteregister
    WHERE source_supplier LIKE '%,%' AND product_type IN ('inkontinentsiside', 'vormmähe', 'püksmähe', 'imav lina / voodikaitse')
    LIMIT 5;
""")
rows = c.fetchall()
for r in rows:
    print(f"ID: {r['id']} | Name: {r['official_product_name']} | Brand: {r['brand']}")
    print(f"  Suppliers: {r['source_supplier']}")
    print(f"  Aliases: {json.loads(r['aliases'])}")
    print(f"  URLs: {r['source_url']}")
    print("-" * 50)
conn.close()
