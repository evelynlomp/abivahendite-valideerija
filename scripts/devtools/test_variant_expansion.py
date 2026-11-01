import requests
import re
import html
import sys

sys.stdout.reconfigure(encoding='utf-8')

urls = [
    "https://www.invaru.ee/abena-san-5-54x28-cm-1200-ml-n36-4",
    "https://www.invaru.ee/abena-pants-m1-80-110-1400-ml-n15-7",
    "https://www.invaru.ee/side-naistele-abena-light-2",
    "https://www.invaru.ee/side-meestele-abena-man-2",
    "https://www.invaru.ee/molicare-mobile-imavad-puksid"
]

for url in urls:
    r = requests.get(url, headers={'User-Agent': 'Mozilla/5.0'})
    descs = re.findall(r'<meta\s+itemprop=description\s+content=[\'"]([^\'"]+)[\'"]', r.text)
    print(f"=== {url.split('/')[-1]} ===")
    for d in descs:
        if len(d) < 100: # Variant line
            print("  Variant:", d)
