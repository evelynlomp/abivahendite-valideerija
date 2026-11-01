import requests
import json
import sys

sys.stdout.reconfigure(encoding='utf-8')

# Check variable product in ITAK
r = requests.get('https://www.itak.ee/wp-json/wc/store/v1/products?type=variable&per_page=3', headers={'User-Agent': 'Mozilla/5.0'})
prods = r.json()
print("Variable products in ITAK:", len(prods))
for p in prods:
    print(f"Product: {p.get('name')} (id: {p.get('id')})")
    print(f"  Variations field ({len(p.get('variations', []))}):")
    for v in p.get('variations', [])[:3]:
        print(f"    Var: {v}")
    # Also check if endpoint /wp-json/wc/store/v1/products/{id}/variations works
    p_id = p.get('id')
    r_vars = requests.get(f"https://www.itak.ee/wp-json/wc/store/v1/products/{p_id}/variations", headers={'User-Agent': 'Mozilla/5.0'})
    print(f"  Endpoint /products/{p_id}/variations status: {r_vars.status_code}")
    if r_vars.status_code == 200:
        data = r_vars.json()
        print(f"    Returned {len(data)} items. Sample: {data[0].get('name') if data else None}")
