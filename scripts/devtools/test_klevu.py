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
                    "term": "*"
                },
                "typeOfRecords": ["KLEVU_PRODUCT"],
                "limit": 100,
                "offset": 0
            }
        }
    ]
}
headers = {'User-Agent': 'Mozilla/5.0', 'Content-Type': 'application/json'}
r = requests.post('https://eucs32v2.ksearchnet.com/cs/v2/search', json=payload, headers=headers)
print("Offset 0 status:", r.status_code)
if r.status_code == 200:
    recs = r.json()['queryResults'][0]['records']
    print(f"Retrieved {len(recs)} records at offset 0.")
    print("First record:", recs[0].get('name'))
    
# Now test offset 100
payload['recordQueries'][0]['settings']['offset'] = 100
r2 = requests.post('https://eucs32v2.ksearchnet.com/cs/v2/search', json=payload, headers=headers)
if r2.status_code == 200:
    recs2 = r2.json()['queryResults'][0]['records']
    print(f"Retrieved {len(recs2)} records at offset 100.")
    print("First record at offset 100:", recs2[0].get('name'))
