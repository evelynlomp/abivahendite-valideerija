import csv
import sqlite3
import os

CSV_PATH = 'data/Sotsiaalministeeriumi abivahendite loetelu_ametlik.csv'
DB_PATH = 'data/valideer.db'

conn = sqlite3.connect(DB_PATH)
c = conn.cursor()

updated = 0
with open(CSV_PATH, 'r', encoding='utf-8') as f:
    reader = csv.reader(f)
    for row in reader:
        if not row or len(row) < 3:
            continue
        iso = row[0].strip()
        # Check if it looks like an ISO code (e.g. 04, 04.33, 04.33.03.01)
        if not iso or not any(c.isdigit() for c in iso):
            continue
        
        name = row[1].strip() if len(row) > 1 else ""
        tapsustus = row[2].strip() if len(row) > 2 else ""
        kirjeldus = row[12].strip() if len(row) > 12 else ""
        
        # Clean ISO code
        clean_iso = iso.replace('.', '').strip()
        
        c.execute("""
            UPDATE ametlik_klassifikaator 
            SET tapsustus = ?, kirjeldus = ?
            WHERE iso_kood = ? OR iso_kood_puhas = ?
        """, (tapsustus, kirjeldus, iso, clean_iso))
        if c.rowcount > 0:
            updated += c.rowcount

conn.commit()
print(f"Updated {updated} records in ametlik_klassifikaator with official full Column C and M texts.")
conn.close()
