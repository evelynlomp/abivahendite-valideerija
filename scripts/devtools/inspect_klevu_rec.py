import requests
import json
import sys

sys.stdout.reconfigure(encoding='utf-8')

payload = {
    "context": {
        "apiKeys": ["klevu-168199975832915684"]
    },
    "recordQueries": [
        {
            "id": "productList",
            "typeOfRequest": "SEARCH",
            "settings": {
                "query": {
                    "term": "Abena San"
                },
                "typeOfRecords": ["KLEVU_PRODUCT"],
                "limit": 2
            }
        }
    ]
}
headers = {'User-Agent': 'Mozilla/5.0', 'Content-Type': 'application/json'}
r = requests.post('https://eucs32v2.ksearchnet.com/cs/v2/search', json=payload, headers=headers)
rec = r.json()['queryResults'][0]['records'][0]
print("Keys in Klevu record:", list(rec.keys()))
for k, v in rec.items():
    if isinstance(v, (str, int, float, list)):
        print(f"  {k}: {str(v)[:150]}")
