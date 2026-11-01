import json
import requests
import re
import html
import sys

sys.stdout.reconfigure(encoding='utf-8')

with open('data/raw_supplier_products.json', 'r', encoding='utf-8') as f:
    items = json.load(f)

# Find Invaru items where url has product page and name suggests incontinence/pads/pants
variable_candidates = []
for it in items:
    if it.get('source_supplier') == 'Invaru':
        name = (it.get('raw_name') or '').lower()
        if any(w in name for w in ['abena', 'molicare', 'tena', 'seni', 'lille', 'mähe', 'püksid', 'side', 'lina', 'kark', 'ratastool']):
            url = it.get('source_url')
            if url and 'invaru.ee' in url:
                variable_candidates.append(it)

print(f"Found {len(variable_candidates)} key candidate products to expand from Invaru.")
for c in variable_candidates[:10]:
    print(" ", c.get('raw_name'), c.get('source_url'))
