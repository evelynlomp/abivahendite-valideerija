import requests
import json

headers = {'User-Agent': 'Mozilla/5.0'}
r = requests.get('https://www.itak.ee/wp-json/wc/store/v1/products?per_page=1', headers=headers)
p = r.json()[0]
print("Keys in product:", list(p.keys()))
print("Name:", p.get('name'))
print("Categories:", [c.get('name') for c in p.get('categories', [])])
print("Attributes:", [(a.get('name'), [t.get('name') for t in a.get('terms', [])]) for a in p.get('attributes', [])])
print("Description snippet:", p.get('short_description', '')[:200])
print("Permalink:", p.get('permalink'))
