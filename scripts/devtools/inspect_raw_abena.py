import json
import sys

sys.stdout.reconfigure(encoding='utf-8')

with open("data/raw_supplier_products.json", "r", encoding="utf-8") as f:
    items = json.load(f)

print(f"Total raw items: {len(items)}")
abena_items = [it for it in items if 'abena' in (it.get('raw_name') or '').lower() or 'abri' in (it.get('raw_name') or '').lower()]
print(f"Total Abena/Abri items: {len(abena_items)}")

san_items = [it for it in abena_items if 'san' in (it.get('raw_name') or '').lower()]
print(f"Total Abena San/Abri-San items: {len(san_items)}")
for it in san_items:
    print(f"[{it.get('source_supplier')}] {it.get('raw_name')} (url: {it.get('source_url')})")
