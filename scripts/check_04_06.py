import sqlite3

conn = sqlite3.connect("data/valideer.db")
c = conn.cursor()
print("04 codes:")
for r in c.execute("SELECT iso_kood, maarusejargne_nimetus FROM ametlik_klassifikaator WHERE iso_kood LIKE '04%'"):
    print(r)
print("\n06 codes:")
for r in c.execute("SELECT iso_kood, maarusejargne_nimetus FROM ametlik_klassifikaator WHERE iso_kood LIKE '06%'"):
    print(r)
