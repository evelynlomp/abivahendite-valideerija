import requests
import re
import html
import sys

sys.stdout.reconfigure(encoding='utf-8')

r = requests.get('https://www.invaru.ee/abena-san-5-54x28-cm-1200-ml-n36-4', headers={'User-Agent': 'Mozilla/5.0'})

descs = re.findall(r'<meta\s+itemprop=description\s+content=[\'"]([^\'"]+)[\'"]', r.text)
print("Variants found via itemprop=description:")
for d in descs:
    print("  -", d)
