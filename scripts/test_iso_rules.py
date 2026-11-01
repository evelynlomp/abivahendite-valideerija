import sys
sys.path.insert(0, '.')
from src.product_registry_db import infer_iso_and_statutory_name

test_volumes = [
    ("Tena Lady 250ml", "side", 250, None, "09.30.24.14", "inkontinentsisidemed naistele 201- 299 ml"),
    ("Lille Supreme Light 340ml", "side", 340, None, "09.30.24.15", "inkontinentsisidemed naistele 300 - 599 ml"),
    ("Abena San 4 800ml", "side", 800, None, "09.30.24.16", "inkontinentsisidemed naistele 600 - 999 ml"),
    ("MoliCare Pad 4 782ml", "side", 782, None, "09.30.24.16", "inkontinentsisidemed naistele 600 - 999 ml"),
    ("Abena San 5 1200ml", "side", 1200, None, "09.30.24.17", "inkontinentsisidemed naistele 1000 - 1499 ml"),
    ("Tena Lady Maxi 1600ml", "side", 1600, None, "09.30.24.18", "inkontinentsisidemed naistele 1500 - 1999 ml"),
    ("Tena Men Level 1 250ml", "side", 250, None, "09.30.24.11", "inkontinentsisidemed meestele kuni 399 ml"),
    ("Tena Men Level 2 450ml", "side", 450, None, "09.30.24.12", "inkontinentsisidemed meestele 400 - 599 ml"),
    ("Tena Men Level 3 710ml", "side", 710, None, "09.30.24.13", "inkontinentsisidemed meestele üle 600 ml"),
    ("Abena San 6 1600ml", "vormmähe", 1600, None, "09.30.24.26", "vormmähkmed 1500 - 1999 ml"),
]

all_passed = True
for name, p_type, ml, drops, expected_iso, expected_name in test_volumes:
    iso, stat = infer_iso_and_statutory_name("TEST", name, p_type, ml=ml, drops=drops)
    passed = (iso == expected_iso and stat == expected_name)
    print(f"[{'PASS' if passed else 'FAIL'}] {name} ({ml} ml) -> ISO: {iso} (Expected: {expected_iso}) | Name: {stat}")
    if not passed:
        all_passed = False

print(f"\nAll tests passed: {all_passed}")
