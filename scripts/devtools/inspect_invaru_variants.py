import requests
import re
import html
import sys

sys.stdout.reconfigure(encoding='utf-8')

r = requests.get('https://www.invaru.ee/abena-san-5-54x28-cm-1200-ml-n36-4', headers={'User-Agent': 'Mozilla/5.0'})
# Search for variants or attributes in page text
for m in re.finditer(r'abena[\-_]san[\-_](\d+)', r.text, re.IGNORECASE):
    print("Found in page:", m.group(0))

# Search for select options
options = re.findall(r'<option[^>]*value=[\'"]([^\'"]*)[\'"][^>]*>(.*?)</option>', r.text, re.DOTALL | re.IGNORECASE)
print(f"Total select options: {len(options)}")
for val, text in options[:20]:
    t = ' '.join(html.unescape(text).split())
    if len(t) > 3:
        print(f"  Opt: {t}")
