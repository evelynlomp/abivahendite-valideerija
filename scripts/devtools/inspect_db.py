import sqlite3
import sys

sys.stdout.reconfigure(encoding='utf-8')
conn = sqlite3.connect('data/valideer.db')
cursor = conn.cursor()
cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
print('Tables:', cursor.fetchall())
for t in ['ametlik_klassifikaator', 'teadmistebaas', 'tooteregister']:
    try:
        cursor.execute(f"PRAGMA table_info({t});")
        cols = [col[1] for col in cursor.fetchall()]
        if cols:
            print(f"Columns for {t}:", cols)
            cursor.execute(f"SELECT count(*) FROM {t};")
            print(f"  Count for {t}:", cursor.fetchone()[0])
    except Exception as e:
        print(f"Error for {t}:", e)
