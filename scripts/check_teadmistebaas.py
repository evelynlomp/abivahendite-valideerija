import sqlite3
import re

conn = sqlite3.connect("data/valideer.db")
c = conn.cursor()

# Check teadmistebaas table
print("=== TEADMISTEBAAS SCHEMA & COUNT ===")
print(c.execute("SELECT count(*) FROM teadmistebaas").fetchone())
for r in c.execute("PRAGMA table_info(teadmistebaas)"):
    print(r)
for r in c.execute("SELECT * FROM teadmistebaas LIMIT 5"):
    print(r)
