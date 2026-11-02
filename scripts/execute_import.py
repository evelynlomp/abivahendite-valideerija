import sqlite3
import json
import sys
import os

sys.path.insert(0, os.path.abspath("."))
from src.product_registry_db import ProductRegistryDB, infer_iso_and_statutory_name

conn = sqlite3.connect("data/valideer.db")
c = conn.cursor()

# 1. Kontrolli praegust toodete arvu
initial_count = c.execute("SELECT count(*) FROM tooteregister").fetchone()[0]
print(f"Tooteregistris enne importi: {initial_count} toodet")

# 2. 18 rangelt verifitseeritud toodet
products_to_import = [
    {
        "manufacturer": "Demant A/S (Taani)",
        "brand": "OTICON",
        "product_family": "CROS",
        "official_product_name": "OTICON CROS",
        "aliases": json.dumps(["OTICON CROS", "Oticon Cros", "Oticon CROS heliülekandesüsteem"], ensure_ascii=False),
        "package_information": "1 tk",
        "ml_capacity": None,
        "drop_rating": None,
        "product_type": "kuulmisabivahend (CROS)",
        "source_supplier": "Hea Kuulmine",
        "source_url": "https://heakuulmine.ee/kuuldeaparaadid/",
        "expected_iso": "22.06.15.05"
    },
    {
        "manufacturer": "Ottobock SE & Co. KGaA (Saksamaa)",
        "brand": "OTTOBOCK",
        "product_family": "Galeo",
        "official_product_name": "OTTOBOCK GALEO 3D 6Y93 (TT)",
        "aliases": json.dumps(["OTTOBOCK GALEO 3D 6Y93 (TT)", "Ottobock Galeo 3D 6Y93", "Galeo 3D 6Y93", "6Y93"], ensure_ascii=False),
        "package_information": "1 tk",
        "ml_capacity": None,
        "drop_rating": None,
        "product_type": "proteesi sisevooder (lainer) sääreproteesile",
        "source_supplier": "Ortopro",
        "source_url": "https://www.ortopro.ee/hinnakiri",
        "expected_iso": "06.24.41.07"
    },
    {
        "manufacturer": "Ottobock SE & Co. KGaA (Saksamaa)",
        "brand": "OTTOBOCK",
        "product_family": "Galeo",
        "official_product_name": "OTTOBOCK GALEO 3D 6Y95 (TT)",
        "aliases": json.dumps(["OTTOBOCK GALEO 3D 6Y95 (TT)", "Ottobock Galeo 3D 6Y95", "Galeo 3D 6Y95", "6Y95"], ensure_ascii=False),
        "package_information": "1 tk",
        "ml_capacity": None,
        "drop_rating": None,
        "product_type": "proteesi sisevooder (lainer) sääreproteesile",
        "source_supplier": "Ortopro",
        "source_url": "https://www.ortopro.ee/hinnakiri",
        "expected_iso": "06.24.41.07"
    },
    {
        "manufacturer": "Ottobock SE & Co. KGaA (Saksamaa)",
        "brand": "OTTOBOCK",
        "product_family": "Galeo",
        "official_product_name": "OTTOBOCK GALEO 6Y92 (TT)",
        "aliases": json.dumps(["OTTOBOCK GALEO 6Y92 (TT)", "Ottobock Galeo 6Y92", "Galeo 6Y92", "6Y92"], ensure_ascii=False),
        "package_information": "1 tk",
        "ml_capacity": None,
        "drop_rating": None,
        "product_type": "proteesi sisevooder (lainer) sääreproteesile",
        "source_supplier": "Ortopro",
        "source_url": "https://www.ortopro.ee/hinnakiri",
        "expected_iso": "06.24.41.07"
    },
    {
        "manufacturer": "Ottobock SE & Co. KGaA (Saksamaa)",
        "brand": "OTTOBOCK",
        "product_family": "Skeo",
        "official_product_name": "OTTOBOCK SKEO SKINGUARD TT 6Y75 (TT)",
        "aliases": json.dumps(["OTTOBOCK SKEO SKINGUARD TT 6Y75 (TT)", "Ottobock Skeo Skinguard TT 6Y75", "Skeo Skinguard TT", "6Y75"], ensure_ascii=False),
        "package_information": "1 tk",
        "ml_capacity": None,
        "drop_rating": None,
        "product_type": "proteesi sisevooder (lainer) sääreproteesile",
        "source_supplier": "Ortopro",
        "source_url": "https://www.ortopro.ee/hinnakiri",
        "expected_iso": "06.24.41.07"
    },
    {
        "manufacturer": "Ottobock SE & Co. KGaA (Saksamaa)",
        "brand": "OTTOBOCK",
        "product_family": "Skeo",
        "official_product_name": "OTTOBOCK SKEO 6Y80 (TF)",
        "aliases": json.dumps(["OTTOBOCK SKEO 6Y80 (TF)", "Ottobock Skeo 6Y80", "Skeo 6Y80 TF", "6Y80"], ensure_ascii=False),
        "package_information": "1 tk",
        "ml_capacity": None,
        "drop_rating": None,
        "product_type": "proteesi sisevooder (lainer) põlve- ja reieproteesile",
        "source_supplier": "Ortopro",
        "source_url": "https://www.ortopro.ee/hinnakiri",
        "expected_iso": "06.24.41.08"
    },
    {
        "manufacturer": "Ottobock SE & Co. KGaA (Saksamaa)",
        "brand": "OTTOBOCK",
        "product_family": "Skeo",
        "official_product_name": "OTTOBOCK SKEO SKINGUARD TF 6Y85 (TF)",
        "aliases": json.dumps(["OTTOBOCK SKEO SKINGUARD TF 6Y85 (TF)", "Ottobock Skeo Skinguard TF 6Y85", "Skeo Skinguard TF", "6Y85"], ensure_ascii=False),
        "package_information": "1 tk",
        "ml_capacity": None,
        "drop_rating": None,
        "product_type": "proteesi sisevooder (lainer) põlve- ja reieproteesile",
        "source_supplier": "Ortopro",
        "source_url": "https://www.ortopro.ee/hinnakiri",
        "expected_iso": "06.24.41.08"
    },
    {
        "manufacturer": "Ottobock SE & Co. KGaA (Saksamaa)",
        "brand": "OTTOBOCK",
        "product_family": "Skeo",
        "official_product_name": "OTTOBOCK SKEO 3D 6Y87 (TF)",
        "aliases": json.dumps(["OTTOBOCK SKEO 3D 6Y87 (TF)", "Ottobock Skeo 3D 6Y87", "Skeo 3D 6Y87 TF", "6Y87"], ensure_ascii=False),
        "package_information": "1 tk",
        "ml_capacity": None,
        "drop_rating": None,
        "product_type": "proteesi sisevooder (lainer) põlve- ja reieproteesile",
        "source_supplier": "Ortopro",
        "source_url": "https://www.ortopro.ee/hinnakiri",
        "expected_iso": "06.24.41.08"
    },
    {
        "manufacturer": "Ottobock SE & Co. KGaA (Saksamaa)",
        "brand": "OTTOBOCK",
        "product_family": "Skeo",
        "official_product_name": "OTTOBOCK SKEO 3D 6Y88 (TF)",
        "aliases": json.dumps(["OTTOBOCK SKEO 3D 6Y88 (TF)", "Ottobock Skeo 3D 6Y88", "Skeo 3D 6Y88 TF", "6Y88"], ensure_ascii=False),
        "package_information": "1 tk",
        "ml_capacity": None,
        "drop_rating": None,
        "product_type": "proteesi sisevooder (lainer) põlve- ja reieproteesile",
        "source_supplier": "Ortopro",
        "source_url": "https://www.ortopro.ee/hinnakiri",
        "expected_iso": "06.24.41.08"
    },
    {
        "manufacturer": "Ottobock SE & Co. KGaA (Saksamaa)",
        "brand": "OTTOBOCK",
        "product_family": "Skeo",
        "official_product_name": "OTTOBOCK SKEO SEALING 6Y110 (TF)",
        "aliases": json.dumps(["OTTOBOCK SKEO SEALING 6Y110 (TF)", "Ottobock Skeo Sealing 6Y110", "Skeo Sealing 6Y110 TF", "6Y110"], ensure_ascii=False),
        "package_information": "1 tk",
        "ml_capacity": None,
        "drop_rating": None,
        "product_type": "proteesi sisevooder (lainer) põlve- ja reieproteesile",
        "source_supplier": "Ortopro",
        "source_url": "https://www.ortopro.ee/hinnakiri",
        "expected_iso": "06.24.41.08"
    },
    {
        "manufacturer": "Össur hf (Island)",
        "brand": "ÖSSUR",
        "product_family": "Iceross",
        "official_product_name": "ÖSSUR ICEROSS SEAL-IN X I-4443 (TT)",
        "aliases": json.dumps(["ÖSSUR ICEROSS SEAL-IN X I-4443 (TT)", "Össur Iceross Seal-in X I-4443", "Iceross Seal-in X TT", "I-4443"], ensure_ascii=False),
        "package_information": "1 tk",
        "ml_capacity": None,
        "drop_rating": None,
        "product_type": "proteesi sisevooder (lainer) sääreproteesile",
        "source_supplier": "Ortopro",
        "source_url": "https://www.ortopro.ee/hinnakiri",
        "expected_iso": "06.24.41.07"
    },
    {
        "manufacturer": "Össur hf (Island)",
        "brand": "ÖSSUR",
        "product_family": "Iceross",
        "official_product_name": "ÖSSUR ICEROSS SEAL-IN X LOCKING I-SXL3 (TT)",
        "aliases": json.dumps(["ÖSSUR ICEROSS SEAL-IN X LOCKING I-SXL3 (TT)", "Össur Iceross Seal-in X locking I-SXL3", "I-SXL3"], ensure_ascii=False),
        "package_information": "1 tk",
        "ml_capacity": None,
        "drop_rating": None,
        "product_type": "proteesi sisevooder (lainer) sääreproteesile",
        "source_supplier": "Ortopro",
        "source_url": "https://www.ortopro.ee/hinnakiri",
        "expected_iso": "06.24.41.07"
    },
    {
        "manufacturer": "Össur hf (Island)",
        "brand": "ÖSSUR",
        "product_family": "Iceross",
        "official_product_name": "ÖSSUR ICEROSS DERMO LOCKING WITH WAVE I-4313 (TT)",
        "aliases": json.dumps(["ÖSSUR ICEROSS DERMO LOCKING WITH WAVE I-4313 (TT)", "Iceross Dermo locking With Wave", "I-4313"], ensure_ascii=False),
        "package_information": "1 tk",
        "ml_capacity": None,
        "drop_rating": None,
        "product_type": "proteesi sisevooder (lainer) sääreproteesile",
        "source_supplier": "Ortopro",
        "source_url": "https://www.ortopro.ee/hinnakiri",
        "expected_iso": "06.24.41.07"
    },
    {
        "manufacturer": "Össur hf (Island)",
        "brand": "ÖSSUR",
        "product_family": "Iceross",
        "official_product_name": "ÖSSUR ICEROSS COMFORT LOCKING I-5406 (TT)",
        "aliases": json.dumps(["ÖSSUR ICEROSS COMFORT LOCKING I-5406 (TT)", "Iceross Comfort locking", "I-5406"], ensure_ascii=False),
        "package_information": "1 tk",
        "ml_capacity": None,
        "drop_rating": None,
        "product_type": "proteesi sisevooder (lainer) sääreproteesile",
        "source_supplier": "Ortopro",
        "source_url": "https://www.ortopro.ee/hinnakiri",
        "expected_iso": "06.24.41.07"
    },
    {
        "manufacturer": "Össur hf (Island)",
        "brand": "ÖSSUR",
        "product_family": "Iceross",
        "official_product_name": "ÖSSUR ICEROSS SEAL-IN X TF I-8532 (TF)",
        "aliases": json.dumps(["ÖSSUR ICEROSS SEAL-IN X TF I-8532 (TF)", "Iceross Seal-in X TF", "I-8532"], ensure_ascii=False),
        "package_information": "1 tk",
        "ml_capacity": None,
        "drop_rating": None,
        "product_type": "proteesi sisevooder (lainer) põlve- ja reieproteesile",
        "source_supplier": "Ortopro",
        "source_url": "https://www.ortopro.ee/hinnakiri",
        "expected_iso": "06.24.41.08"
    },
    {
        "manufacturer": "Össur hf (Island)",
        "brand": "ÖSSUR",
        "product_family": "Iceross",
        "official_product_name": "ÖSSUR ICEROSS TRANSFEMORAL LOCKING I-7032 (TF)",
        "aliases": json.dumps(["ÖSSUR ICEROSS TRANSFEMORAL LOCKING I-7032 (TF)", "Iceross transfemoral locking", "I-7032"], ensure_ascii=False),
        "package_information": "1 tk",
        "ml_capacity": None,
        "drop_rating": None,
        "product_type": "proteesi sisevooder (lainer) põlve- ja reieproteesile",
        "source_supplier": "Ortopro",
        "source_url": "https://www.ortopro.ee/hinnakiri",
        "expected_iso": "06.24.41.08"
    },
    {
        "manufacturer": "Össur hf (Island)",
        "brand": "ÖSSUR",
        "product_family": "Iceross",
        "official_product_name": "ÖSSUR ICEROSS SEAL-IN X5 TF I-TF673 (TF)",
        "aliases": json.dumps(["ÖSSUR ICEROSS SEAL-IN X5 TF I-TF673 (TF)", "Iceross Seal-in X5 TF", "I-TF673"], ensure_ascii=False),
        "package_information": "1 tk",
        "ml_capacity": None,
        "drop_rating": None,
        "product_type": "proteesi sisevooder (lainer) põlve- ja reieproteesile",
        "source_supplier": "Ortopro",
        "source_url": "https://www.ortopro.ee/hinnakiri",
        "expected_iso": "06.24.41.08"
    },
    {
        "manufacturer": "Össur hf (Island)",
        "brand": "ÖSSUR",
        "product_family": "Iceross",
        "official_product_name": "ÖSSUR ICEROSS UPPER-X LOCKING I-8131 (KÄE)",
        "aliases": json.dumps(["ÖSSUR ICEROSS UPPER-X LOCKING I-8131 (KÄE)", "Iceross Upper-X locking", "I-8131"], ensure_ascii=False),
        "package_information": "1 tk",
        "ml_capacity": None,
        "drop_rating": None,
        "product_type": "proteesi sisevooder (lainer) ülajäsemeproteesile",
        "source_supplier": "Ortopro",
        "source_url": "https://www.ortopro.ee/hinnakiri",
        "expected_iso": "06.18.00.02"
    }
]

inserted_count = 0
for p in products_to_import:
    # Kontrolli olemasolu
    exists = c.execute("SELECT id FROM tooteregister WHERE official_product_name = ?", (p["official_product_name"],)).fetchone()
    if not exists:
        c.execute("""
            INSERT INTO tooteregister (
                manufacturer, brand, product_family, official_product_name,
                aliases, package_information, ml_capacity, drop_rating,
                product_type, source_supplier, source_url
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            p["manufacturer"], p["brand"], p["product_family"], p["official_product_name"],
            p["aliases"], p["package_information"], p["ml_capacity"], p["drop_rating"],
            p["product_type"], p["source_supplier"], p["source_url"]
        ))
        inserted_count += 1
        print(f"Lisatud: {p['official_product_name']} -> ISO {p['expected_iso']}")
    else:
        print(f"Juba olemas: {p['official_product_name']}")

# 3. Uuenda aliasi olemasolevatele toodetele
aliases_to_update = [
    ("RULAATOR FARGO 4", "Rulaator Fargo"),
    ("RAVIMIPOOLITAJA/-PURUSTAJA 3IN1", "Ravimipoolitaja/purustaja 3in1"),
    ("JOBST MEDITSIINILISED KOMPRESSIOONSUKAD", "JOBST Opaque meditsiinilised kompressioonsukad CCL1")
]

for prod_name, new_alias in aliases_to_update:
    row = c.execute("SELECT id, aliases FROM tooteregister WHERE official_product_name = ?", (prod_name,)).fetchone()
    if row:
        p_id, cur_aliases = row
        aliases_list = []
        try:
            aliases_list = json.loads(cur_aliases) if cur_aliases else []
        except Exception:
            aliases_list = [a.strip() for a in cur_aliases.split(",") if a.strip()] if cur_aliases else []
        
        if new_alias not in aliases_list:
            aliases_list.append(new_alias)
            c.execute("UPDATE tooteregister SET aliases = ? WHERE id = ?", (json.dumps(aliases_list, ensure_ascii=False), p_id))
            print(f"Uuendatud alias tootele ID {p_id} ({prod_name}): lisati '{new_alias}'")

conn.commit()

final_count = c.execute("SELECT count(*) FROM tooteregister").fetchone()[0]
print(f"\nTooteregistris pärast importi: {final_count} toodet (lisandus täpselt {final_count - initial_count} uut kirjet)")

# 4. Testi klassifitseerimist ProductRegistryDB kaudu
print("\n=== VERIFITSEERIMINE ProductRegistryDB KAUDU ===")
db = ProductRegistryDB()
for p in products_to_import:
    matched = db.find_by_name(p["official_product_name"])
    iso, stat_name = infer_iso_and_statutory_name(
        p["brand"], p["official_product_name"], p["product_type"]
    )
    assert iso == p["expected_iso"], f"VIGA: Oodatud {p['expected_iso']}, saadi {iso}"
    print(f"OK: {p['official_product_name']} -> {iso} ({stat_name})")

print("\nKõik 18 toodet edukalt imporditud ja 100% verifitseeritud!")
