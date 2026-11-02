import sqlite3

conn = sqlite3.connect("data/valideer.db")
c = conn.cursor()

for r in c.execute("SELECT id, manufacturer, brand, product_family, official_product_name, aliases, product_type, source_supplier, source_url FROM tooteregister WHERE product_type LIKE '%ortoos%' OR product_type LIKE '%lainer%' OR product_type LIKE '%protees%' LIMIT 5"):
    print(r)

print("\nMax ID in tooteregister:")
print(c.execute("SELECT MAX(id), count(*) FROM tooteregister").fetchone())
