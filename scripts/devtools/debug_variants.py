import requests
import re
import sys

sys.stdout.reconfigure(encoding='utf-8')

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Accept': 'application/json, text/plain, */*'
}

url = "https://www.invaru.ee/abena-san-5-54x28-cm-1200-ml-n36-4"
r = requests.get(url, headers=HEADERS, timeout=6)
print("Status:", r.status_code)
descs = re.findall(r'<meta\s+itemprop=description\s+content=[\'"]([^\'"]+)[\'"]', r.text)
print("descs len:", len(descs))
variants = [d.strip() for d in descs if len(d.strip()) < 90 and not d.strip().endswith('.')]
print("variants len:", len(variants))
for v in variants:
    print("  ", v)
