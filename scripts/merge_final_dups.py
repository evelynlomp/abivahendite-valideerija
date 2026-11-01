import sqlite3
import json
import re

conn = sqlite3.connect('data/valideer.db')
c = conn.cursor()

c.execute("SELECT id, official_product_name, brand, aliases, source_supplier FROM tooteregister")
rows = c.fetchall()

groups = {}
to_delete = []

for rid, name, brand, aliases_raw, supp in rows:
    clean_name = re.sub(r'[^A-Z0-9]', '', name.upper())
    key = clean_name
    if not key:
        continue
    if key in groups:
        # Merge into existing
        orig_id, orig_al, orig_supp = groups[key]
        try:
            al1 = json.loads(orig_al) if orig_al else []
            al2 = json.loads(aliases_raw) if aliases_raw else []
        except Exception:
            al1, al2 = [], []
        unified_al = list(set(al1 + al2))
        supp_set = set((orig_supp or '').split(', ') + (supp or '').split(', '))
        unified_supp = ', '.join(sorted([s.strip() for s in supp_set if s.strip()]))
        
        c.execute("UPDATE tooteregister SET aliases = ?, source_supplier = ? WHERE id = ?", (json.dumps(unified_al, ensure_ascii=False), unified_supp, orig_id))
        to_delete.append(rid)
    else:
        groups[key] = (rid, aliases_raw, supp)

for rid in to_delete:
    c.execute("DELETE FROM tooteregister WHERE id = ?", (rid,))

conn.commit()
print(f"Cleaned up {len(to_delete)} secondary duplicates.")

c.execute("SELECT count(*) FROM tooteregister")
print("Final count:", c.fetchone()[0])
conn.close()
