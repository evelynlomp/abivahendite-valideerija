import requests
import sys

sys.stdout.reconfigure(encoding='utf-8')
headers = {'User-Agent': 'Mozilla/5.0'}

for name, base in [
    ('itak', 'https://www.itak.ee'),
    ('terviseabi', 'https://terviseabi.ee'),
    ('invaabi', 'https://invaabi.ee'),
    ('invatooted', 'https://pood.invatooted.ee')
]:
    url = f"{base}/wp-json/wc/store/v1/products?per_page=100&page=2"
    r = requests.get(url, headers=headers, timeout=10)
    print(f"{name} page 2: status {r.status_code}, items = {len(r.json()) if r.status_code == 200 else r.status_code}")
