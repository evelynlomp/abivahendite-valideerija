import requests
import re
import sys

sys.stdout.reconfigure(encoding='utf-8')

r = requests.get('https://www.invaru.ee/abena-san-5-54x28-cm-1200-ml-n36-4', headers={'User-Agent': 'Mozilla/5.0'})
for m in re.finditer(r'abena[\-_]san[\-_]4', r.text, re.IGNORECASE):
    start = max(0, m.start() - 150)
    end = min(len(r.text), m.end() + 150)
    print("MATCH CONTEXT:")
    print(r.text[start:end])
    print("-" * 50)
