import sqlite3
import sys

sys.stdout.reconfigure(encoding='utf-8')
conn = sqlite3.connect('data/valideer.db')
cursor = conn.cursor()

cursor.execute("SELECT source_supplier, count(*) FROM tooteregister GROUP BY source_supplier ORDER BY count(*) DESC LIMIT 20;")
rows = cursor.fetchall()
print("Top supplier combinations in tooteregister:")
for r in rows:
    print(f"  {r[0]}: {r[1]} products")
