import requests

headers = {'User-Agent': 'Mozilla/5.0'}
for per_page in [100, 50, 20]:
    r = requests.get(f'https://www.itak.ee/wp-json/wc/store/v1/products?per_page={per_page}', headers=headers)
    print(f"itak per_page={per_page}: Status {r.status_code}, count={len(r.json()) if r.status_code == 200 else r.text[:100]}")
