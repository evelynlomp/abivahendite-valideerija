import json

with open("data/scanned_candidates_report.json", "r", encoding="utf-8") as f:
    d = json.load(f)

high_conf = d["by_confidence"]["KÕRGE KINDLUS"]

print(f"Kokku 'KÕRGE KINDLUS' kirjeid failis: {len(high_conf)}")
for idx, it in enumerate(high_conf, 1):
    raw_name = it["raw_name"]
    brand = it["brand"]
    mfg = it["manufacturer"]
    source = it["source_name"]
    iso = it["matching_isos"][0][0] if it["matching_isos"] else "NONE"
    iso_name = it["matching_isos"][0][1] if it["matching_isos"] else "NONE"
    reason = it["matching_isos"][0][2] if it["matching_isos"] else "NONE"
    print(f"{idx:2d}. [{iso}] {raw_name[:45]} | Bränd: {brand} | Tootja: {mfg[:25]} | Põhjendus: {reason}")
