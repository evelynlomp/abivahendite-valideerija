import requests
import re
import sys

sys.stdout.reconfigure(encoding='utf-8')
headers = {'User-Agent': 'Mozilla/5.0'}
r = requests.get('https://www.invaru.ee/ee/aluslinad', headers=headers)

# Find any inline script mentioning klevu
scripts = re.findall(r'<script\b[^>]*>(.*?)</script>', r.text, re.DOTALL | re.IGNORECASE)
for i, s in enumerate(scripts):
    if 'klevu' in s.lower() and ('url' in s.lower() or 'server' in s.lower() or 'search' in s.lower() or 'setsetting' in s.lower()):
        print(f"--- Script {i} ---")
        lines = [line.strip() for line in s.split('\n') if any(w in line.lower() for w in ['url', 'server', 'search', 'klevu', 'api'])]
        print('\n'.join(lines[:20]))
