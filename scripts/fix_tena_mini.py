import sqlite3
import json

conn = sqlite3.connect('data/valideer.db')
c = conn.cursor()

# Kustutame vigase TENA Comfort Mini Super rea, mis oli üle kirjutanud teised
c.execute("DELETE FROM tooteregister WHERE official_product_name LIKE 'TENA COMFORT MINI%'")

tena_rows = [
    (
        "Essity Hygiene and Health AB (Rootsi)",
        "TENA",
        "Tena Comfort Mini",
        "TENA COMFORT MINI PLUS 310ML",
        json.dumps([
            "TENA Comfort Mini Plus",
            "TENA Comfort Mini Plus 310 ml",
            "TENA Comfort Mini Plus 310ml",
            "TENA Comfort Mini Plus 310ml N30",
            "Naiste sidemed Tena Comfort Mini Plus (334 ml)",
            "TENA COMFORT MINI PLUS"
        ], ensure_ascii=False),
        310,
        3,
        "inkontinentsiside",
        "Invaru, ITAK"
    ),
    (
        "Essity Hygiene and Health AB (Rootsi)",
        "TENA",
        "Tena Comfort Mini",
        "TENA COMFORT MINI EXTRA 566ML",
        json.dumps([
            "TENA Comfort Mini Extra",
            "TENA Comfort Mini Extra 566 ml",
            "TENA Comfort Mini Extra 566ml",
            "Tena Comfort Mini Extra 566ml N30",
            "Naiste sidemed Tena Comfort Mini Extra (550 ml)",
            "TENA COMFORT MINI EXTRA"
        ], ensure_ascii=False),
        566,
        4,
        "inkontinentsiside",
        "Invaru, ITAK"
    ),
    (
        "Essity Hygiene and Health AB (Rootsi)",
        "TENA",
        "Tena Comfort Mini",
        "TENA COMFORT MINI SUPER 905ML",
        json.dumps([
            "TENA Comfort Mini Super",
            "TENA Comfort Mini Super 905 ml",
            "TENA Comfort Mini Super 905ml",
            "Tena Comfort Mini Super 905ml N30",
            "Naiste sidemed Tena Comfort Mini Super (860 ml)",
            "TENA COMFORT MINI SUPER"
        ], ensure_ascii=False),
        905,
        5,
        "inkontinentsiside",
        "Invaru, ITAK"
    )
]

c.executemany("""
    INSERT INTO tooteregister (manufacturer, brand, product_family, official_product_name, aliases, ml_capacity, drop_rating, product_type, source_supplier)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
""", tena_rows)

conn.commit()
print("Fixed TENA Comfort Mini rows.")
conn.close()
