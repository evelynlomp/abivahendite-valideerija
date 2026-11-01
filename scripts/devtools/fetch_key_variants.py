import requests
import re
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
import json
import os
import sys

sys.stdout.reconfigure(encoding='utf-8')

session = requests.Session()
retries = Retry(total=3, backoff_factor=0.5, status_forcelist=[500, 502, 503, 504])
session.mount('https://', HTTPAdapter(max_retries=retries))

HEADERS = {'User-Agent': 'Mozilla/5.0'}

with open('data/raw_supplier_products.json', 'r', encoding='utf-8') as f:
    raw_items = json.load(f)

# Collect Invaru incontinence and key mobility items
key_urls = set()
for it in raw_items:
    if it.get('source_supplier') == 'Invaru':
        name = (it.get('raw_name') or '').lower()
        if any(w in name for w in ['abena', 'molicare', 'tena', 'seni', 'lille', 'mähe', 'püksid', 'side', 'kark', 'ratastool', 'lina', 'form', 'san', 'pad', 'lady', 'slip']):
            url = it.get('source_url')
            if url and 'invaru.ee' in url:
                key_urls.add(url)

print(f"Total key Invaru URLs to expand: {len(key_urls)}")

variant_cache_file = "data/invaru_variant_cache.json"
cache = {}
if os.path.exists(variant_cache_file):
    with open(variant_cache_file, "r", encoding="utf-8") as f:
        cache = json.load(f)

print(f"Already cached: {len(cache)} URLs.")

to_fetch = [u for u in key_urls if u not in cache]
print(f"Need to fetch: {len(to_fetch)} URLs.")

def fetch_one(u):
    try:
        r = session.get(u, headers=HEADERS, timeout=12)
        descs = re.findall(r'<meta\s+itemprop=description\s+content=[\'"]([^\'"]+)[\'"]', r.text)
        vars = [d.strip() for d in descs if len(d.strip()) < 90 and not d.strip().endswith('.')]
        return u, vars
    except Exception as e:
        return u, []

from concurrent.futures import ThreadPoolExecutor

with ThreadPoolExecutor(max_workers=5) as ex:
    for u, vars in ex.map(fetch_one, to_fetch):
        cache[u] = vars

with open(variant_cache_file, "w", encoding="utf-8") as f:
    json.dump(cache, f, ensure_ascii=False, indent=2)

print(f"Total cached variants across {len(cache)} URLs: {sum(len(v) for v in cache.values())}")
print("Abena San variants in cache:", cache.get("https://www.invaru.ee/abena-san-5-54x28-cm-1200-ml-n36-4"))
