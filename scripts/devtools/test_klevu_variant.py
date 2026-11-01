import requests
import json
import sys

sys.stdout.reconfigure(encoding='utf-8')

payload = {
    "context": {"apiKeys": ["klevu-168199975832915684"]},
    "recordQueries": [{
        "id": "q",
        "typeOfRequest": "SEARCH",
        "settings": {
            "query": {"term": "Abena San 4"},
            "typeOfRecords": ["KLEVU_PRODUCT"],
            "limit": 5
        }
    }]
}
r = requests.post("https://eucs32v2.ksearchnet.com/cs/v2/search", json=payload, headers={'User-Agent': 'Mozilla/5.0'})
recs = r.json()['queryResults'][0]['records']
print("Found records for 'Abena San 4':", len(recs))
for rec in recs:
    print(f"Name: {rec.get('name')}, SKU: {rec.get('sku')}, URL: {rec.get('url')}")
    print(f"  Img: {rec.get('imageUrl')}")
    # print any field that mentions 4 or 800
    for k, v in rec.items():
        if isinstance(v, str) and ('4' in v or '800' in v):
            print(f"  {k}: {v}")
