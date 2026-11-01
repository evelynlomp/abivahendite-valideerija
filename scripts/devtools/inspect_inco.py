import sqlite3
import sys

sys.stdout.reconfigure(encoding='utf-8')
conn = sqlite3.connect('data/valideer.db')
cursor = conn.cursor()

cursor.execute("SELECT brand, official_product_name, source_supplier, aliases FROM tooteregister WHERE brand in ('ABENA', 'MOLICARE', 'TENA', 'LILLE', 'SENI') LIMIT 30;")
rows = cursor.fetchall()
print("Sample incontinence entries in tooteregister:")
for r in rows:
    print(f"[{r[0]}] {r[1]} | Supp: {r[2]}")
