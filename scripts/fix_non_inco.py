import sqlite3

conn = sqlite3.connect('data/valideer.db')
c = conn.cursor()
c.execute("UPDATE tooteregister SET product_type='muu abivahend' WHERE id IN (2976, 985)")
c.execute("UPDATE tooteregister SET product_type='nahahooldusvahend' WHERE id IN (2995, 3005, 3426)")
conn.commit()
print("Updated successfully")
conn.close()
