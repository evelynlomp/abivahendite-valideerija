import sqlite3

conn = sqlite3.connect('data/valideer.db')
c = conn.cursor()
c.execute("SELECT id, brand, official_product_name, product_type, aliases FROM tooteregister WHERE official_product_name LIKE '%TSINK%' OR aliases LIKE '%tsink%' OR official_product_name LIKE '%ZINC%'")
rows = c.fetchall()
print(f"Zinc products found: {len(rows)}")
for r in rows:
    print(r)
conn.close()
