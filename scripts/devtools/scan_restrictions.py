import sqlite3

conn = sqlite3.connect('data/valideer.db')
c = conn.cursor()

c.execute("""
    SELECT iso_kood, maarusejargne_nimetus, tapsustus, kirjeldus 
    FROM ametlik_klassifikaator 
    WHERE tapsustus IS NOT NULL AND (
        tapsustus LIKE '%ei kuulu%' OR 
        tapsustus LIKE '%v.a%' OR 
        tapsustus LIKE '%ainult%' OR 
        tapsustus LIKE '%põhised%' OR 
        tapsustus LIKE '%põhine%' OR 
        tapsustus LIKE '%veevaba%' OR
        tapsustus LIKE '%tsink%' OR
        tapsustus LIKE '%kuni%'
    )
    ORDER BY iso_kood
""")
rows = c.fetchall()
print(f"Total codes with technical restrictions in Column C: {len(rows)}")
for r in rows:
    print(f"=== {r[0]}: {r[1]} ===")
    print(f"  Täpsustus (C): {r[2]}")
    if r[3] and ("ei kuulu" in r[3] or "ei rakendu" in r[3]):
        print(f"  Kirjeldus (M): {r[3][:150]}...")
    print()

conn.close()
