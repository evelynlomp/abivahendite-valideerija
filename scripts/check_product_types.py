import sqlite3

conn = sqlite3.connect("data/valideer.db")
c = conn.cursor()

print("Distinct product_types in tooteregister:")
for r in c.execute("SELECT product_type, COUNT(*) FROM tooteregister GROUP BY product_type ORDER BY COUNT(*) DESC LIMIT 20"):
    print(r)

print("\nDistinct valdkond in ametlik_klassifikaator:")
for r in c.execute("SELECT valdkond, COUNT(*) FROM ametlik_klassifikaator GROUP BY valdkond ORDER BY COUNT(*) DESC"):
    print(r)

print("\nDistinct liik in ametlik_klassifikaator:")
for r in c.execute("SELECT valdkond, liik, COUNT(*) FROM ametlik_klassifikaator GROUP BY valdkond, liik ORDER BY valdkond, COUNT(*) DESC LIMIT 30"):
    print(r)
