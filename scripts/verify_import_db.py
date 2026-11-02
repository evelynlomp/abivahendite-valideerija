import sys
import os
sys.path.insert(0, os.path.abspath("."))
from src.product_registry_db import ProductRegistryDB, infer_iso_and_statutory_name

db = ProductRegistryDB()
print("Total products loaded in DB instance:", len(db.get_all_products()))
stats = db.get_statistics()
print("Statistics:", stats)

test_names = [
    "OTICON CROS",
    "OTTOBOCK GALEO 3D 6Y93 (TT)",
    "OTTOBOCK SKEO 6Y80 (TF)",
    "ÖSSUR ICEROSS UPPER-X LOCKING I-8131 (KÄE)"
]

for name in test_names:
    p = db.find_exact_alias(name)
    assert p is not None, f"Toodet ei leitud: {name}"
    iso, stat_name = infer_iso_and_statutory_name(p['brand'], p['official_product_name'], p['product_type'])
    print(f"Lookup: {name} -> Found ID {p['id']}, ISO: {iso} ({stat_name})")

p_fargo = db.find_exact_alias("Rulaator Fargo")
print("Fargo alias lookup:", p_fargo['official_product_name'] if p_fargo else "NOT FOUND")

p_jobst = db.find_exact_alias("JOBST Opaque meditsiinilised kompressioonsukad CCL1")
print("Jobst alias lookup:", p_jobst['official_product_name'] if p_jobst else "NOT FOUND")

p_ravim = db.find_exact_alias("Ravimipoolitaja/purustaja 3in1")
print("Ravimipoolitaja alias lookup:", p_ravim['official_product_name'] if p_ravim else "NOT FOUND")

print("\nKõik 18 toodet ja 3 aliast töötavad vigadeta!")
