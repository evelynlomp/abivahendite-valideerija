import requests
import json
import sys

sys.stdout.reconfigure(encoding='utf-8')

# 1. Check Klevu variations for Invaru
payload = {
    "context": {"apiKeys": ["klevu-168199975832915684"]},
    "recordQueries": [{
        "id": "q",
        "typeOfRequest": "SEARCH",
        "settings": {
            "query": {"term": "Abena San"},
            "typeOfRecords": ["KLEVU_PRODUCT"],
            "limit": 1
        }
    }]
}
r = requests.post("https://eucs32v2.ksearchnet.com/cs/v2/search", json=payload, headers={'User-Agent': 'Mozilla/5.0'})
rec = r.json()['queryResults'][0]['records'][0]
print("Klevu swatchesInfo:", rec.get('swatchesInfo'))

# 2. Check WooCommerce variations in ITAK or Terviseabi
r_wc = requests.get("https://www.itak.ee/wp-json/wc/store/v1/products?search=Abena", headers={'User-Agent': 'Mozilla/5.0'})
print(f"ITAK products with 'Abena': {len(r_wc.json())}")
for p in r_wc.json()[:3]:
    print(f"  Name: {p.get('name')}, Type: {p.get('type')}, Variations: {len(p.get('variations', []))}")
    if p.get('variations'):
        print(f"    Sample variation keys: {p['variations'][0]}")
