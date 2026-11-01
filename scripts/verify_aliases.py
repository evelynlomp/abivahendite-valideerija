import sqlite3
import json
import re
from collections import defaultdict

conn = sqlite3.connect('data/valideer.db')
c = conn.cursor()

c.execute("SELECT id, official_product_name, aliases FROM tooteregister")
rows = c.fetchall()

alias_to_prods = defaultdict(set)
total_aliases = 0
for pid, name, aliases_raw in rows:
    try:
        al = json.loads(aliases_raw) if aliases_raw else []
    except Exception:
        al = []
    for a in al:
        total_aliases += 1
        norm_a = re.sub(r'[^A-Z0-9]', '', a.upper())
        if norm_a:
            alias_to_prods[norm_a].add(name)

colliding = {k: v for k, v in alias_to_prods.items() if len(v) > 1}
print('Total aliases in registry:', total_aliases)
print('Unique normalized alias keys:', len(alias_to_prods))
print('Colliding alias keys mapping to >1 product name:', len(colliding))
