from scripts.extract_suppliers import expand_invaru_variants, deduplicate_and_build_registry
import json
import sys

sys.stdout.reconfigure(encoding='utf-8')

with open('data/raw_supplier_products.json', 'r', encoding='utf-8') as f:
    items = json.load(f)

# Find just abena san
abena_item = [it for it in items if 'abena-san' in (it.get('source_url') or '')]
print("Abena san raw:", abena_item)

expanded = expand_invaru_variants(abena_item)
print(f"Expanded count: {len(expanded)}")
for it in expanded:
    print("  Exp:", it.get('raw_name'))

canonical = deduplicate_and_build_registry(expanded)
print(f"Canonical count: {len(canonical)}")
for c in canonical:
    print("  Canon:", c['official_product_name'], "Family:", c['product_family'], "Aliases:", json.loads(c['aliases'])[:2])
