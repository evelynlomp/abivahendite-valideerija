import sqlite3

conn = sqlite3.connect('data/valideer.db')
c = conn.cursor()
c.execute("SELECT name FROM sqlite_master WHERE type='table';")
print('Tables:', c.fetchall())

c.execute("SELECT count(*) FROM tooteregister;")
print('tooteregister count:', c.fetchone()[0])

c.execute("PRAGMA table_info(tooteregister);")
for col in c.fetchall():
    print(' ', col[1], col[2])

conn.close()
