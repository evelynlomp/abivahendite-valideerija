"""
Parandab tooteregistri tootekirjed ja aliased:
- TENA Comfort Mini (Plus, Extra, Super)
- Abena San 1A
- Sensilind Lady Normal
- MoliCare Pad Lady 1.5 tilka
- forma-care woman (Extra, Super)
- Attends Soft 5 liimiribaga
"""

import sqlite3
import json
import os

DB_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "valideer.db")

conn = sqlite3.connect(DB_PATH)
conn.row_factory = sqlite3.Row
c = conn.cursor()

# 1. Kontrolli ja paranda TENA Comfort tooted
tena_items = [
    {
        "official_name": "TENA COMFORT MINI PLUS 310ML",
        "brand": "TENA",
        "manufacturer": "Essity Hygiene and Health AB (Rootsi)",
        "family": "Tena Comfort Mini",
        "type": "inkontinentsiside",
        "ml": 310,
        "drops": 3,
        "aliases": [
            "TENA Comfort Mini Plus",
            "TENA Comfort Mini Plus 310 ml",
            "TENA Comfort Mini Plus 310ml N30",
            "Naiste sidemed Tena Comfort Mini Plus (334 ml)",
            "TENA COMFORT 310ML",
            "TENA COMFORT 334ML"
        ]
    },
    {
        "official_name": "TENA COMFORT MINI EXTRA 566ML",
        "brand": "TENA",
        "manufacturer": "Essity Hygiene and Health AB (Rootsi)",
        "family": "Tena Comfort Mini",
        "type": "inkontinentsiside",
        "ml": 566,
        "drops": 4,
        "aliases": [
            "TENA Comfort Mini Extra",
            "TENA Comfort Mini Extra 566 ml",
            "Tena Comfort Mini Extra 566ml N30",
            "Naiste sidemed Tena Comfort Mini Extra (550 ml)",
            "TENA COMFORT 566ML",
            "TENA COMFORT 550ML"
        ]
    },
    {
        "official_name": "TENA COMFORT MINI SUPER 905ML",
        "brand": "TENA",
        "manufacturer": "Essity Hygiene and Health AB (Rootsi)",
        "family": "Tena Comfort Mini",
        "type": "inkontinentsiside",
        "ml": 905,
        "drops": 5,
        "aliases": [
            "TENA Comfort Mini Super",
            "TENA Comfort Mini Super 905 ml",
            "Tena Comfort Mini Super 905ml N30",
            "Naiste sidemed Tena Comfort Mini Super (860 ml)",
            "TENA COMFORT 905ML",
            "TENA COMFORT 860ML"
        ]
    }
]

for t in tena_items:
    # Kontrolli kas on olemas
    c.execute("SELECT id, aliases FROM tooteregister WHERE official_product_name LIKE ? OR aliases LIKE ?", (f"%{t['official_name'][:18]}%", f"%{t['official_name'][:18]}%"))
    existing = c.fetchall()
    if existing:
        for ex in existing:
            old_al = json.loads(ex['aliases']) if ex['aliases'] else []
            combined_al = list(set(old_al + t['aliases']))
            c.execute("""
                UPDATE tooteregister 
                SET official_product_name = ?, brand = ?, manufacturer = ?, product_family = ?, product_type = ?, ml_capacity = ?, drop_rating = ?, aliases = ?
                WHERE id = ?
            """, (t['official_name'], t['brand'], t['manufacturer'], t['family'], t['type'], t['ml'], t['drops'], json.dumps(combined_al, ensure_ascii=False), ex['id']))
    else:
        c.execute("""
            INSERT INTO tooteregister (manufacturer, brand, product_family, official_product_name, aliases, ml_capacity, drop_rating, product_type, source_supplier)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (t['manufacturer'], t['brand'], t['family'], t['official_name'], json.dumps(t['aliases'], ensure_ascii=False), t['ml'], t['drops'], t['type'], "Invaru, ITAK"))

# 2. Abena San 1A 250 ml
abena_1a_aliases = [
    "Abena San 1A",
    "Abena San 1A 250 ml",
    "Abena San 1A 250ml",
    "Abena San 1A, 28x10 cm, 250 ml N28",
    "ABENA SAN 250ML",
    "ABENA SAN 1A"
]
c.execute("SELECT id, aliases FROM tooteregister WHERE official_product_name LIKE '%ABENA SAN 250%' OR aliases LIKE '%Abena San 1A%'")
ab_rows = c.fetchall()
if ab_rows:
    for r in ab_rows:
        old_al = json.loads(r['aliases']) if r['aliases'] else []
        comb = list(set(old_al + abena_1a_aliases))
        c.execute("""
            UPDATE tooteregister 
            SET official_product_name = 'ABENA SAN 1A 250ML', product_type = 'inkontinentsiside', ml_capacity = 250, aliases = ?
            WHERE id = ?
        """, (json.dumps(comb, ensure_ascii=False), r['id']))
else:
    c.execute("""
        INSERT INTO tooteregister (manufacturer, brand, product_family, official_product_name, aliases, ml_capacity, drop_rating, product_type, source_supplier)
        VALUES ('Abena Group (Taani)', 'ABENA', 'Abena San', 'ABENA SAN 1A 250ML', ?, 250, 1, 'inkontinentsiside', 'Invaru')
    """, (json.dumps(abena_1a_aliases, ensure_ascii=False),))

# 3. Sensilind Lady Normal 340 ml
sensi_aliases = [
    "Sensilind Lady Normal",
    "Sensilind Lady Normal 340 ml",
    "Sensilind Lady Normal 340ml",
    "Sensilind Lady Normal 340ml (28tk)",
    "SENSILIND LADY NORMAL"
]
c.execute("SELECT id, aliases FROM tooteregister WHERE official_product_name LIKE '%SENSILIND LADY%' OR aliases LIKE '%Sensilind Lady%'")
sensi_rows = c.fetchall()
if sensi_rows:
    for r in sensi_rows:
        old_al = json.loads(r['aliases']) if r['aliases'] else []
        comb = list(set(old_al + sensi_aliases))
        c.execute("""
            UPDATE tooteregister 
            SET official_product_name = 'SENSILIND LADY NORMAL 340ML', product_type = 'inkontinentsiside', ml_capacity = 340, aliases = ?
            WHERE id = ?
        """, (json.dumps(comb, ensure_ascii=False), r['id']))
else:
    c.execute("""
        INSERT INTO tooteregister (manufacturer, brand, product_family, official_product_name, aliases, ml_capacity, drop_rating, product_type, source_supplier)
        VALUES ('Paul Hartmann AG / Sensilind (Saksamaa)', 'SENSILIND', 'Sensilind Lady', 'SENSILIND LADY NORMAL 340ML', ?, 340, 2, 'inkontinentsiside', 'Terviseabi')
    """, (json.dumps(sensi_aliases, ensure_ascii=False),))

# 4. MoliCare Pad Lady 1.5 tilka 267 ml
moli_15_aliases = [
    "MoliCare Pad Lady 1.5 tilka",
    "MoliCare Pad Lady 1.5 tilka 267 ml",
    "MoliCare Pad Lady 1.5 tilka 267ml",
    "MoliCare Premium Lady Pad 1.5",
    "MoliCare Lady Pad 1.5",
    "MOLICARE PAD LADY 1.5 TILKA"
]
c.execute("SELECT id, aliases FROM tooteregister WHERE official_product_name LIKE '%MOLICARE PAD LADY 1.5%' OR aliases LIKE '%MoliCare Pad Lady 1.5%'")
moli_rows = c.fetchall()
if moli_rows:
    for r in moli_rows:
        old_al = json.loads(r['aliases']) if r['aliases'] else []
        comb = list(set(old_al + moli_15_aliases))
        c.execute("""
            UPDATE tooteregister 
            SET official_product_name = 'MOLICARE PAD LADY 1.5 TILKA 267ML', product_type = 'inkontinentsiside', ml_capacity = 267, drop_rating = 1.5, aliases = ?
            WHERE id = ?
        """, (json.dumps(comb, ensure_ascii=False), r['id']))
else:
    c.execute("""
        INSERT INTO tooteregister (manufacturer, brand, product_family, official_product_name, aliases, ml_capacity, drop_rating, product_type, source_supplier)
        VALUES ('Paul Hartmann AG (Saksamaa)', 'MOLICARE', 'MoliCare Pad', 'MOLICARE PAD LADY 1.5 TILKA 267ML', ?, 267, 1.5, 'inkontinentsiside', 'Invaru, ITAK')
    """, (json.dumps(moli_15_aliases, ensure_ascii=False),))

# 5. forma-care woman EXTRA 500 ml & SUPER 933 ml
forma_items = [
    {
        "name": "FORMA-CARE WOMAN EXTRA 500ML",
        "family": "Forma-Care Woman",
        "ml": 500,
        "drops": 4,
        "aliases": [
            "forma-care woman EXTRA 500 ml",
            "forma-care woman EXTRA 500ml",
            "forma-care woman Extra",
            "Forma-Care Woman Extra 500 ml",
            "Sidemed forma-care Woman Premium Dry Extra",
            "FORMA-CARE WOMAN EXTRA"
        ]
    },
    {
        "name": "FORMA-CARE WOMAN SUPER 933ML",
        "family": "Forma-Care Woman",
        "ml": 933,
        "drops": 5,
        "aliases": [
            "forma-care woman SUPER 933 ml",
            "forma-care woman SUPER 933ml",
            "forma-care woman Super",
            "Forma-Care Woman Super 933 ml",
            "Sidemed forma-care Woman Premium Dry Super",
            "FORMA-CARE WOMAN SUPER"
        ]
    }
]

for f in forma_items:
    c.execute("SELECT id, aliases FROM tooteregister WHERE official_product_name = ?", (f['name'],))
    ex = c.fetchone()
    if ex:
        old_al = json.loads(ex['aliases']) if ex['aliases'] else []
        comb = list(set(old_al + f['aliases']))
        c.execute("UPDATE tooteregister SET aliases = ? WHERE id = ?", (json.dumps(comb, ensure_ascii=False), ex['id']))
    else:
        c.execute("""
            INSERT INTO tooteregister (manufacturer, brand, product_family, official_product_name, aliases, ml_capacity, drop_rating, product_type, source_supplier)
            VALUES ('Unizell Medicare GmbH (Saksamaa)', 'FORMA-CARE', ?, ?, ?, ?, ?, 'inkontinentsiside', 'ITAK')
        """, (f['family'], f['name'], json.dumps(f['aliases'], ensure_ascii=False), f['ml'], f['drops']))

# 6. Attends Soft 5 liimiribaga 990 ml
attends_aliases = [
    "Attends Soft 5 liimiribaga 990 ml",
    "Attends Soft 5 liimiribaga",
    "Attends Soft 5",
    "Attends Soft 5 990 ml",
    "Naiste sidemed Attends Soft 5 (990 ml)",
    "ATTENDS SOFT 5 990ML"
]
c.execute("SELECT id, aliases FROM tooteregister WHERE official_product_name LIKE '%ATTENDS NAISTE SIDEMED 5%' OR aliases LIKE '%Attends Soft 5%'")
att_rows = c.fetchall()
if att_rows:
    for r in att_rows:
        old_al = json.loads(r['aliases']) if r['aliases'] else []
        comb = list(set(old_al + attends_aliases))
        c.execute("""
            UPDATE tooteregister 
            SET official_product_name = 'ATTENDS SOFT 5 990ML', product_type = 'inkontinentsiside', ml_capacity = 990, aliases = ?
            WHERE id = ?
        """, (json.dumps(comb, ensure_ascii=False), r['id']))
else:
    c.execute("""
        INSERT INTO tooteregister (manufacturer, brand, product_family, official_product_name, aliases, ml_capacity, drop_rating, product_type, source_supplier)
        VALUES ('Attends Healthcare Group (Rootsi/USA)', 'ATTENDS', 'Attends Soft', 'ATTENDS SOFT 5 990ML', ?, 990, 5, 'inkontinentsiside', 'ITAK')
    """, (json.dumps(attends_aliases, ensure_ascii=False),))

conn.commit()
print("Registry entries and aliases updated successfully.")
conn.close()
