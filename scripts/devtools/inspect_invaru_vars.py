import json
import sys

sys.stdout.reconfigure(encoding='utf-8')

with open('data/raw_supplier_products.json', 'r', encoding='utf-8') as f:
    items = json.load(f)

invaru_items = [it for it in items if it.get('source_supplier') == 'Invaru']
print(f"Total Invaru items: {len(invaru_items)}")

# How many have image with specific variant names or descriptions?
for it in invaru_items[:15]:
    raw = it.get('raw_name')
    url = it.get('source_url')
    print(f"Invaru item: {raw} | {url}")
