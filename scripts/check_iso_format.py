import sqlite3

conn = sqlite3.connect("data/valideer.db")
c = conn.cursor()

print("Codes matching 04.06%:")
for r in c.execute("SELECT iso_kood, maarusejargne_nimetus FROM ametlik_klassifikaator WHERE iso_kood LIKE '04.06%'"):
    print(r)

print("\nCodes matching 06.06%:")
for r in c.execute("SELECT iso_kood, maarusejargne_nimetus FROM ametlik_klassifikaator WHERE iso_kood LIKE '06.06%'"):
    print(r)

print("\nCodes matching 06.12%:")
for r in c.execute("SELECT iso_kood, maarusejargne_nimetus FROM ametlik_klassifikaator WHERE iso_kood LIKE '06.12%'"):
    print(r)

print("\nCodes matching 06.24%:")
for r in c.execute("SELECT iso_kood, maarusejargne_nimetus FROM ametlik_klassifikaator WHERE iso_kood LIKE '06.24%'"):
    print(r)

print("\nCodes matching 22.06%:")
for r in c.execute("SELECT iso_kood, maarusejargne_nimetus FROM ametlik_klassifikaator WHERE iso_kood LIKE '22.06%'"):
    print(r)
