import requests
import sys

sys.stdout.reconfigure(encoding='utf-8')

sites = [
    ('itak.ee', 'https://www.itak.ee/wp-json/wc/store/v1/products'),
    ('terviseabi.ee', 'https://terviseabi.ee/wp-json/wc/store/v1/products'),
    ('invaabi.ee', 'https://invaabi.ee/wp-json/wc/store/v1/products'),
    ('invatooted.ee', 'https://pood.invatooted.ee/wp-json/wc/store/v1/products')
]
headers = {'User-Agent': 'Mozilla/5.0'}

for name, url in sites:
    r = requests.get(f"{url}?per_page=1", headers=headers)
    total = r.headers.get('x-wp-total')
    total_pages = r.headers.get('x-wp-totalpages')
    print(f"{name}: Total products = {total}, Total pages = {total_pages}")
