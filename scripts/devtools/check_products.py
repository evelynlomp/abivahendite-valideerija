import sqlite3
import json
import sys

sys.stdout.reconfigure(encoding='utf-8')
conn = sqlite3.connect('data/valideer.db')
cursor = conn.cursor()

queries = ["ABENA SAN 4", "MOLICARE PAD 4", "LILLE SUPREME LIGHT"]
for q in queries:
    cursor.execute("SELECT id, official_product_name, brand, manufacturer, package_information, ml_capacity, drop_rating, product_type, source_supplier, aliases FROM tooteregister WHERE official_product_name LIKE ? OR aliases LIKE ? LIMIT 3;", (f"%{q}%", f"%{q}%"))
    rows = cursor.fetchall()
    print(f"=== Query: {q} ===")
    for r in rows:
        print(f"ID: {r[0]} | Name: {r[1]} | Brand: {r[2]} | Mfr: {r[3]}")
        print(f"  Pkg: {r[4]} | ml: {r[5]} | drop: {r[6]} | Type: {r[7]} | Supp: {r[8]}")
        aliases = json.loads(r[9])
        print(f"  Aliases ({len(aliases)}): {aliases[:5]}")
conn.close()
