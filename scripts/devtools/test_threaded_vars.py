import requests
import re
from concurrent.futures import ThreadPoolExecutor
import time
import sys

sys.stdout.reconfigure(encoding='utf-8')

urls = [
    "https://www.invaru.ee/abena-san-5-54x28-cm-1200-ml-n36-4",
    "https://www.invaru.ee/abena-pants-m1-80-110-1400-ml-n15-7",
    "https://www.invaru.ee/side-naistele-abena-light-2",
    "https://www.invaru.ee/side-meestele-abena-man-2",
    "https://www.invaru.ee/molicare-mobile-imavad-puksid"
]

def fetch_variants(url):
    try:
        r = requests.get(url, headers={'User-Agent': 'Mozilla/5.0'}, timeout=5)
        descs = re.findall(r'<meta\s+itemprop=description\s+content=[\'"]([^\'"]+)[\'"]', r.text)
        vars = [d for d in descs if len(d) < 90 and not d.endswith('.')]
        return url, vars
    except Exception as e:
        return url, []

t0 = time.time()
with ThreadPoolExecutor(max_workers=5) as ex:
    results = list(ex.map(fetch_variants, urls))

print(f"Fetched {len(results)} pages in {time.time() - t0:.2f}s")
for u, v in results:
    print(f"{u.split('/')[-1]}: {len(v)} variants")
    for var in v[:3]:
        print(f"  - {var}")
