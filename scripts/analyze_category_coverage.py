import sqlite3

conn = sqlite3.connect("data/valideer.db")
c = conn.cursor()

print("=== TABLES ===")
for r in c.execute("SELECT name FROM sqlite_master WHERE type='table'"):
    print(r[0])

print("\n=== TOOTEREGISTER SCHEMA ===")
for r in c.execute("PRAGMA table_info(tooteregister)"):
    print(r)

print("\n=== AMETLIK_KLASSIFIKAATOR SCHEMA ===")
for r in c.execute("PRAGMA table_info(ametlik_klassifikaator)"):
    print(r)

print("\n=== SAMPLE TOOTEREGISTER ===")
for r in c.execute("SELECT * FROM tooteregister LIMIT 3"):
    print(r)

print("\n=== SAMPLE AMETLIK_KLASSIFIKAATOR ===")
for r in c.execute("SELECT * FROM ametlik_klassifikaator LIMIT 3"):
    print(r)
