import sqlite3
import json

conn = sqlite3.connect('data/valideer.db')
conn.row_factory = sqlite3.Row
c = conn.cursor()

queries = [
    "TENA COMFORT",
    "ABENA SAN 1",
    "SENSILIND",
    "MOLICARE PAD LADY",
    "FORMA-CARE",
    "ATTENDS"
]

for q in queries:
    print(f"\n==================== SEARCH: {q} ====================")
    c.execute("""
        SELECT id, brand, official_product_name, product_family, product_type, ml_capacity, drop_rating, aliases
        FROM tooteregister
        WHERE official_product_name LIKE ? OR brand LIKE ? OR aliases LIKE ?
    """, (f"%{q}%", f"%{q}%", f"%{q}%"))
    rows = c.fetchall()
    print(f"Found {len(rows)} products:")
    for r in rows:
        al = json.loads(r['aliases']) if r['aliases'] else []
        print(f"ID {r['id']}: [{r['brand']}] {r['official_product_name']} | Family: {r['product_family']} | Type: {r['product_type']} | ML: {r['ml_capacity']} | Drops: {r['drop_rating']} | Aliases: {al[:3]}")

conn.close()
