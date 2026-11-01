import requests
import json

sites = [
    'https://www.itak.ee',
    'https://terviseabi.ee',
    'https://invaabi.ee',
    'https://pood.invatooted.ee'
]
headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}

for base in sites:
    for ep in ['/wp-json/wc/store/v1/products?per_page=5', '/wp-json/wp/v2/product?per_page=5', '/wp-json/wc/v3/products?per_page=5']:
        url = base + ep
        try:
            r = requests.get(url, headers=headers, timeout=5)
            ct = r.headers.get('content-type', '')
            print(f"{url}: Status {r.status_code}, type {ct}")
            if r.status_code == 200 and 'json' in ct:
                data = r.json()
                print(f"   Items: {len(data)}")
                if len(data) > 0:
                    sample = data[0]
                    name = sample.get('name') or (sample.get('title', {}).get('rendered') if isinstance(sample.get('title'), dict) else None)
                    print(f"   Sample: {name}")
        except Exception as e:
            print(f"{url}: Error {e}")
