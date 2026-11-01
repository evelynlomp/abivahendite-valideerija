import sqlite3
import re

conn = sqlite3.connect('data/valideer.db')
c = conn.cursor()

c.execute("""
    SELECT id, brand, official_product_name, product_type, ml_capacity, drop_rating
    FROM tooteregister
    WHERE ml_capacity IS NOT NULL
""")
rows = c.fetchall()
print(f"Total products with known ml_capacity: {len(rows)}")

# Let's see some samples across different ml values
sample_by_ml = sorted(rows, key=lambda x: x[4])
for r in sample_by_ml[:30]:
    print(f"ID {r[0]}: {r[1]} {r[2]} | Type: {r[3]} | ML: {r[4]} | Drops: {r[5]}")

print("\n--- Mid-range samples ---")
for r in sample_by_ml[len(sample_by_ml)//2 : len(sample_by_ml)//2 + 20]:
    print(f"ID {r[0]}: {r[1]} {r[2]} | Type: {r[3]} | ML: {r[4]} | Drops: {r[5]}")
conn.close()
