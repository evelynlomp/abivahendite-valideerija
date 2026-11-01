import sqlite3

conn = sqlite3.connect('data/valideer.db')
c = conn.cursor()
c.execute("""
    SELECT iso_kood, maarusejargne_nimetus, tapsustus, piirlimiit, kirjeldus
    FROM ametlik_klassifikaator 
    WHERE iso_kood LIKE '09.30.24%'
    ORDER BY iso_kood
""")
for r in c.fetchall():
    print(f"ISO: {r[0]} | Nimetus: {r[1]} | Täpsustus: {r[2]} | Limiit: {r[3]}")
conn.close()
