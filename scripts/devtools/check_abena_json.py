import json
import sys

sys.stdout.reconfigure(encoding='utf-8')

with open('data/raw_supplier_products.json', 'r', encoding='utf-8') as f:
    items = json.load(f)

for it in items:
    url = it.get('source_url') or ''
    if 'abena-san' in url:
        print("Found abena-san item:")
        print("  raw_name:", it.get('raw_name'))
        print("  title:", it.get('title'))
        print("  source_supplier:", it.get('source_supplier'))
        print("  source_url:", it.get('source_url'))
