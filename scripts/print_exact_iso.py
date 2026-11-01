import sqlite3

conn = sqlite3.connect('data/valideer.db')
c = conn.cursor()
c.execute("SELECT iso_kood, maarusejargne_nimetus FROM ametlik_klassifikaator WHERE maarusejargne_nimetus LIKE '%ml%' ORDER BY iso_kood")
for r in c.fetchall():
    print(f"{r[0]}: {r[1]}")
conn.close()


