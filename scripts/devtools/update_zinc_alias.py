import sqlite3
import json

conn = sqlite3.connect('data/valideer.db')
c = conn.cursor()

c.execute("SELECT id, aliases FROM tooteregister WHERE id = 45")
r = c.fetchone()
if r:
    al = json.loads(r[1]) if r[1] else []
    new_al = list(set(al + ["Abena tsinksalv 100ml", "Abena tsinksalv", "Nahka kaitsev tsinksalv Abena", "ABENA TSINKSALV"]))
    c.execute("UPDATE tooteregister SET aliases = ?, official_product_name = 'ABENA TSINKSALV' WHERE id = 45", (json.dumps(new_al, ensure_ascii=False),))
    conn.commit()
    print("Updated ID 45 aliases.")

conn.close()
