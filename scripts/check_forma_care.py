import sqlite3
import json

conn = sqlite3.connect('data/valideer.db')
conn.row_factory = sqlite3.Row
c = conn.cursor()

c.execute("""
    SELECT id, brand, manufacturer, official_product_name, product_type, ml_capacity, aliases, source_supplier
    FROM tooteregister 
    WHERE official_product_name LIKE '%FORMA%' 
       OR brand LIKE '%FORMA%' 
       OR aliases LIKE '%forma%'
""")
rows = c.fetchall()
print(f"Total forma-care products in tooteregister: {len(rows)}")
for r in rows:
    al = json.loads(r['aliases']) if r['aliases'] else []
    print(f"ID {r['id']}: [{r['brand']}] {r['official_product_name']} | Mfg: {r['manufacturer']} | Type: {r['product_type']} | ML: {r['ml_capacity']} | Aliases: {al}")

conn.close()
