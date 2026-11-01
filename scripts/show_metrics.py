import sqlite3
import json

conn = sqlite3.connect('data/valideer.db')
c = conn.cursor()

c.execute("SELECT count(*) FROM tooteregister")
total = c.fetchone()[0]

c.execute("SELECT count(*) FROM tooteregister WHERE manufacturer != 'Määramata'")
mfg_count = c.fetchone()[0]

c.execute("SELECT count(*) FROM tooteregister WHERE product_type != 'muu abivahend'")
cat_count = c.fetchone()[0]

c.execute("SELECT count(DISTINCT manufacturer) FROM tooteregister WHERE manufacturer != 'Määramata'")
distinct_mfgs = c.fetchone()[0]

c.execute("SELECT count(DISTINCT product_type) FROM tooteregister")
distinct_cats = c.fetchone()[0]

c.execute("SELECT count(*) FROM tooteregister WHERE source_supplier LIKE '%,%'")
cross_supp = c.fetchone()[0]

print('Total products:', total)
print('Manufacturer coverage count:', mfg_count, f'({mfg_count/total*100:.1f}%)')
print('Distinct manufacturers:', distinct_mfgs)
print('Category coverage count (non-muu):', cat_count, f'({cat_count/total*100:.1f}%)')
print('Distinct categories:', distinct_cats)
print('Cross supplier count:', cross_supp)
