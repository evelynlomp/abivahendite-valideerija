import requests
import json
import sys
from collections import Counter

sys.stdout.reconfigure(encoding='utf-8')

for name, base in [('ITAK', 'https://www.itak.ee'), ('Terviseabi', 'https://terviseabi.ee')]:
    r = requests.get(f"{base}/wp-json/wc/store/v1/products?per_page=100&page=1", headers={'User-Agent': 'Mozilla/5.0'})
    brands = []
    for item in r.json():
        b_list = item.get('brands', [])
        for b in b_list:
            brands.append(b.get('name'))
    print(f"{name} top brands on page 1:", Counter(brands).most_common(10))
