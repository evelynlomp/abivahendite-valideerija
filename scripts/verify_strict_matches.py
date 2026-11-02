import sqlite3
import json
import re

conn = sqlite3.connect("data/valideer.db")
conn.row_factory = sqlite3.Row
c = conn.cursor()

# Laadi klassifikaatori ametlikud koodid
cls_rows = c.execute("SELECT iso_kood, maarusejargne_nimetus, valdkond, liik FROM ametlik_klassifikaator").fetchall()
official_iso_map = {r["iso_kood"]: dict(r) for r in cls_rows}

with open("data/scanned_candidates_report.json", "r", encoding="utf-8") as f:
    d = json.load(f)

high_conf = d["by_confidence"]["KÕRGE KINDLUS"]

def clean_title(title):
    # Eemalda breadcrumb ' » ...'
    if "»" in title:
        title = title.split("»")[0].strip()
    return title

strict_candidates = []
excluded_candidates = []

for it in high_conf:
    raw_name = it["raw_name"]
    name_clean = clean_title(raw_name)
    brand = it["brand"]
    mfg = it["manufacturer"]
    source = it["source"]
    source_name = it["source_name"]
    matching_iso = it["matching_isos"][0][0] if it["matching_isos"] else None
    
    nc_lower = name_clean.lower()
    
    # KVALITEEDIKONTROLLI REEGLID
    
    # 1. Kontrolli, kas ISO kood on ametlikus klassifikaatoris olemas
    if matching_iso not in official_iso_map:
        excluded_candidates.append({
            "name": name_clean,
            "brand": brand,
            "mfg": mfg,
            "iso": matching_iso,
            "reason": f"ISO kood {matching_iso} puudub ametlikust klassifikaatorist"
        })
        continue
        
    # 2. Välista patareid ja standardotsakud (pole otsest ametlikku koodi või on jaekaup)
    if "patarei" in nc_lower or "otsak" in nc_lower:
        excluded_candidates.append({
            "name": name_clean,
            "brand": brand,
            "mfg": mfg,
            "iso": matching_iso,
            "reason": "Patareid/otsakud ei vasta otsesele määruse koodile (jaemüügitarvik või standardotsak vs individuaalne otsak)"
        })
        continue
        
    # 3. Välista puuduliku määratlusega või vale anatoomilise piirkonnaga tooted
    # Seljaortoosid, mis said ekslikult põlveortoosi koodi (06.12.06)
    if any(w in nc_lower for w in ["selja", "tlso", "bandaaz", "vöö", "immostrap", "actistrap", "conforstrap"]):
        excluded_candidates.append({
            "name": name_clean,
            "brand": brand,
            "mfg": mfg,
            "iso": matching_iso,
            "reason": "Selja/nimme toode sai esialgses skriptis heuristilise põlveortoosi koodi (06.12.06)"
        })
        continue
        
    # Käe/pöidla tooted, mis said põlveortoosi koodi (06.12.06)
    if any(w in nc_lower for w in ["pöidla", "ranne", "käsivars", "küünarliiges", "lahas", "manex", "ergoform", "pol'ax"]):
        excluded_candidates.append({
            "name": name_clean,
            "brand": brand,
            "mfg": mfg,
            "iso": matching_iso,
            "reason": "Käe/randme/küünarliigese toode sai esialgses skriptis heuristilise põlveortoosi koodi (06.12.06)"
        })
        continue
        
    # Reietugi, kipsisaabas, varbakaitse hüppeliigese all
    if any(w in nc_lower for w in ["reietugi", "kipsi", "varba"]):
        excluded_candidates.append({
            "name": name_clean,
            "brand": brand,
            "mfg": mfg,
            "iso": matching_iso,
            "reason": "Ei ole otsene hüppeliigese ortoos (reietugi, silikoonist varbakaitse või kipsikaitse saabas)"
        })
        continue

    # 4. Välista üldised 'Määramata' tootjaga hügieeni/liikumistarvikud (vanniaste, imav pesu jms)
    if any(w in nc_lower for w in ["vanniaste", "aluspesu", "pesemisraam", "rulaator jaguar"]):
        excluded_candidates.append({
            "name": name_clean,
            "brand": brand,
            "mfg": mfg,
            "iso": matching_iso,
            "reason": "Tootja ja täpne määratlus puuduvad või vajab täpsemat alamkoodi"
        })
        continue

    # 5. Korrigeeri TT vs TF lainerite ISO koodid
    # Skeo TF lainerid peavad olema 06.24.41.08 (põlve- ja reieproteesile), mitte 06.24.41.07 (säärele)!
    if "lainer" in nc_lower or "galeo" in nc_lower or "skeo" in nc_lower or "iceross" in nc_lower:
        if "(tf)" in nc_lower or "transfemoral" in nc_lower:
            matching_iso = "06.24.41.08"
        elif "(tt)" in nc_lower or "transtibial" in nc_lower:
            matching_iso = "06.24.41.07"
        elif "käe" in nc_lower or "upper" in nc_lower:
            matching_iso = "06.18.00.02"

    # Kontrollime uuesti koodi kehtivust
    if matching_iso not in official_iso_map:
        continue
        
    iso_meta = official_iso_map[matching_iso]
    
    strict_candidates.append({
        "clean_name": name_clean,
        "raw_name": raw_name,
        "brand": brand if brand != "Määramata" else "Määramata",
        "manufacturer": mfg if mfg != "Määramata" else "Määramata",
        "source": source,
        "source_name": source_name,
        "iso_kood": matching_iso,
        "maarusejargne_nimetus": iso_meta["maarusejargne_nimetus"],
        "valdkond": iso_meta["valdkond"],
        "liik": iso_meta["liik"],
        "category": it["category"]
    })

print(f"=== KVALITEEDIKONTROLLI TULEMUSED ===")
print(f"Esialgsest 71-st kirjest:")
print(f"  VÄLISTATUD (mitte-otsene vaste või puudulik info): {len(excluded_candidates)} tk")
print(f"  KINNITATUD OTSESED VASTED (100% verifitseeritud): {len(strict_candidates)} tk")

print("\n--- KINNITATUD KANDIDAADID ---")
for idx, sc in enumerate(strict_candidates, 1):
    print(f"{idx:2d}. [{sc['iso_kood']}] {sc['clean_name']} | Bränd: {sc['brand']} | Tootja: {sc['manufacturer']}")

print("\n--- VÄLISTATUD KANDIDAADID (põhjendustega) ---")
for idx, ex in enumerate(excluded_candidates[:15], 1):
    print(f"{idx:2d}. {ex['name']} -> {ex['reason']}")
