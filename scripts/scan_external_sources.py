"""
Skaneerib 5 avalikku veebiallikat ja tuvastab tooted, tootjad, kaubamärgid ning ISO vastavused.
"""

import sys
import sqlite3
import requests
import re
from html import unescape
from rapidfuzz import fuzz

sys.stdout.reconfigure(encoding="utf-8")

conn = sqlite3.connect("data/valideer.db")
c = conn.cursor()

# 1. Laadi andmebaasist olemasolevad kirjed
db_products = c.execute("SELECT id, official_product_name, brand, manufacturer, aliases FROM tooteregister").fetchall()
db_product_map = {}
for p in db_products:
    p_id, name, brand, mfg, aliases = p
    db_product_map[name.upper()] = (p_id, name, brand, mfg)
    if aliases:
        for a in aliases.split(","):
            if a.strip():
                db_product_map[a.strip().upper()] = (p_id, name, brand, mfg)

db_brands = set(p[2].upper() for p in db_products if p[2])
db_mfg = set(p[3].upper() for p in db_products if p[3])

class_rows = c.execute("SELECT iso_kood, maarusejargne_nimetus, tapsustus FROM ametlik_klassifikaator").fetchall()
classifier_list = [(r[0], r[1], r[2]) for r in class_rows]

headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}

scanned_items = []

# --- ALLIKAS 1: heakuulmine.ee ---
print("Scanning heakuulmine.ee...")
try:
    r = requests.get("https://heakuulmine.ee/pood/", headers=headers, timeout=10)
    items = re.findall(r'<li[^>]*class="[^"]*product[^"]*"[^>]*>(.*?)</li>', r.text, re.DOTALL)
    for it in items:
        title_m = re.findall(r'<h[2-4][^>]*>(.*?)</h[2-4]>', it)
        if title_m:
            t = unescape(re.sub(r'<[^>]+>', '', title_m[0]).strip())
            scanned_items.append({
                "raw_name": t,
                "source": "https://heakuulmine.ee/pood/",
                "source_name": "Hea Kuulmine",
                "brand_hint": "Oticon" if "oticon" in t.lower() or "prowax" in t.lower() else "Määramata",
                "mfg_hint": "Demant A/S (Taani)",
                "category_hint": "Kuulmisabivahendid ja tarvikud"
            })
    
    # Kuuldeaparaadid
    r_ka = requests.get("https://heakuulmine.ee/kuuldeaparaadid/", headers=headers, timeout=10)
    headings = re.findall(r'<h[23][^>]*>(.*?)</h[23]>', r_ka.text, re.DOTALL)
    for h in headings:
        clean = unescape(re.sub(r'<[^>]+>', '', h).strip())
        if clean.startswith("Oticon ") and "rakendus" not in clean.lower():
            scanned_items.append({
                "raw_name": clean,
                "source": "https://heakuulmine.ee/kuuldeaparaadid/",
                "source_name": "Hea Kuulmine",
                "brand_hint": "Oticon",
                "mfg_hint": "Demant A/S (Taani)",
                "category_hint": "Kuulmisabivahendid (kuuldeaparaadid)"
            })
except Exception as e:
    print("Error scanning heakuulmine:", e)

# --- ALLIKAS 2: teresa.ee ---
print("Scanning teresa.ee...")
try:
    r = requests.get("https://teresa.ee/pood/", headers=headers, timeout=10)
    pattern = r'<a\s+[^>]*href="(https://teresa\.ee/pood/[^"]+)"[^>]*>(.*?)</a>'
    matches = re.findall(pattern, r.text, re.DOTALL)
    for href, txt in matches:
        clean = unescape(re.sub(r'<[^>]+>', '', txt).strip())
        if clean and clean != "E-pood" and "Lisa korvi" not in clean and len(clean) > 3:
            # Extract brand hint
            b_hint = "Määramata"
            mfg_hint = "Määramata"
            if "JOBST" in clean.upper():
                b_hint = "JOBST"
                mfg_hint = "Essity Hygiene and Health AB (Rootsi)"
            elif "COMPRITEX" in clean.upper():
                b_hint = "CompriTex"
                mfg_hint = "Vannini Medica S.r.l. (Itaalia)"
            elif "TENA" in clean.upper():
                b_hint = "TENA"
                mfg_hint = "Essity Hygiene and Health AB (Rootsi)"
            elif "MOLICARE" in clean.upper():
                b_hint = "Molicare"
                mfg_hint = "Paul Hartmann AG (Saksamaa)"
            elif "GEHWOL" in clean.upper():
                b_hint = "Gehwol"
                mfg_hint = "Eduard Gerlach GmbH (Saksamaa)"
            elif "EVERCARE" in clean.upper():
                b_hint = "Evercare"
                mfg_hint = "OneMed Group"
            elif "SCABO" in clean.upper():
                b_hint = "Scabo"
                mfg_hint = "Scabo Medical"
            elif "FARGO" in clean.upper():
                b_hint = "Fargo"
                mfg_hint = "Meyra / MDH"
            
            scanned_items.append({
                "raw_name": clean,
                "source": href,
                "source_name": "Teresa Abivahendikeskus",
                "brand_hint": b_hint,
                "mfg_hint": mfg_hint,
                "category_hint": "Liikumis- ja hooldusabivahendid"
            })
except Exception as e:
    print("Error scanning teresa.ee:", e)

# --- ALLIKAS 3: ortoosikeskus.ee ---
print("Scanning ortoosikeskus.ee...")
try:
    # Groups: 21 (Hüppeliiges), 22 (Põlv), 24 (Selg), 25 (Käsi/ranne)
    groups = [21, 22, 24, 25]
    for g in groups:
        url_g = f"https://www.ortoosikeskus.ee/index.php?page=99&group_id={g}"
        rg = requests.get(url_g, headers=headers, timeout=10)
        p_ids = list(set(re.findall(r'product_id=(\d+)', rg.text)))[:8]
        for pid in p_ids:
            try:
                p_url = f"https://www.ortoosikeskus.ee/index.php?page=99&action=show_product_details&product_id={pid}&group_id={g}"
                rp = requests.get(p_url, headers=headers, timeout=8)
                t_m = re.findall(r'<title>(.*?)</title>', rp.text, re.IGNORECASE)
                if t_m:
                    p_title = unescape(t_m[0].split("»")[0].strip())
                    if p_title and p_title != "Tooted":
                        b_hint = "Määramata"
                        m_hint = "Määramata"
                        if "procare" in rp.text.lower():
                            b_hint = "ProCare"
                            m_hint = "DJO, LLC / Enovis (USA)"
                        elif "donjoy" in rp.text.lower():
                            b_hint = "DonJoy"
                            m_hint = "DJO, LLC / Enovis (USA)"
                        elif "aircast" in rp.text.lower():
                            b_hint = "Aircast"
                            m_hint = "DJO, LLC / Enovis (USA)"
                        
                        scanned_items.append({
                            "raw_name": p_title,
                            "source": p_url,
                            "source_name": "Eesti Ortoosikeskus",
                            "brand_hint": b_hint,
                            "mfg_hint": m_hint,
                            "category_hint": "Ortoosid ja tugisidemed"
                        })
            except Exception:
                pass
except Exception as e:
    print("Error scanning ortoosikeskus:", e)

# --- ALLIKAS 4: ortopro.ee ---
print("Scanning ortopro.ee...")
try:
    r = requests.get("https://www.ortopro.ee/hinnakiri", headers=headers, timeout=10)
    tables = re.findall(r'<table[^>]*>(.*?)</table>', r.text, re.DOTALL)
    if len(tables) >= 5:
        # Table 5 is specific branded products (Ottobock, Össur)
        rows5 = re.findall(r'<tr[^>]*>(.*?)</tr>', tables[4], re.DOTALL)
        for row in rows5:
            tds = [unescape(re.sub(r'<[^>]+>', '', td).strip()) for td in re.findall(r'<td[^>]*>(.*?)</td>', row, re.DOTALL)]
            if len(tds) >= 4 and tds[0] and tds[3]:
                name, code, l_type, brand = tds[0], tds[1], tds[2], tds[3]
                full_name = f"{brand} {name} {code} ({l_type})".strip()
                mfg = "Ottobock SE & Co. KGaA (Saksamaa)" if "OTTOBOCK" in brand.upper() else "Össur hf (Island)"
                scanned_items.append({
                    "raw_name": full_name,
                    "source": "https://www.ortopro.ee/hinnakiri",
                    "source_name": "Ortopro",
                    "brand_hint": brand.capitalize(),
                    "mfg_hint": mfg,
                    "category_hint": f"Proteesi sisevoodrid ({l_type})"
                })
except Exception as e:
    print("Error scanning ortopro:", e)

# --- ALLIKAS 5: meditsiiniseadmed.ee ---
print("Scanning meditsiiniseadmed.ee...")
try:
    for cat in ["uneapnoe", "trahheostoomi-filtrid"]:
        url = f"https://meditsiiniseadmed.ee/kategooria/{cat}/"
        r = requests.get(url, headers=headers, timeout=10)
        links = re.findall(r'<a\s+[^>]*href="(https://meditsiiniseadmed\.ee/toode/[^"]+)"[^>]*>(.*?)</a>', r.text, re.DOTALL)
        for h, t in links:
            clean = unescape(re.sub(r'<[^>]+>', '', t).strip())
            first_line = clean.split('\n')[0].strip()
            if first_line and len(first_line) > 3:
                b_hint = "Määramata"
                mfg_hint = "Määramata"
                if "resmed" in first_line.lower():
                    b_hint = "ResMed"
                    mfg_hint = "ResMed Inc. (USA/Austraalia)"
                elif "pürdoux" in first_line.lower():
                    b_hint = "Pürdoux"
                    mfg_hint = "Pürdoux Health"
                elif "hydro-trach" in first_line.lower():
                    b_hint = "Hydro-Trach"
                    mfg_hint = "Intersurgical Ltd (Ühendkuningriik)"
                
                scanned_items.append({
                    "raw_name": first_line,
                    "source": h,
                    "source_name": "Meditsiiniseadmed.ee",
                    "brand_hint": b_hint,
                    "mfg_hint": mfg_hint,
                    "category_hint": "Uneapnoe ja hingamisteede tarvikud"
                })
except Exception as e:
    print("Error scanning meditsiiniseadmed:", e)

print(f"\nTotal raw scanned items: {len(scanned_items)}")

# 2. ANALÜÜS JA VÕRDLUS TOOTEREGISTRIGA
unique_scanned = {}
for it in scanned_items:
    k = it["raw_name"].strip().upper()
    if k not in unique_scanned:
        unique_scanned[k] = it

print(f"Unique items after deduplication: {len(unique_scanned)}")

# Tuvasta uued vs olemasolevad vs duplikaadid
results = []
for k, it in unique_scanned.items():
    raw_name = it["raw_name"]
    brand_hint = it["brand_hint"]
    mfg_hint = it["mfg_hint"]
    source = it["source"]
    source_name = it["source_name"]
    category_hint = it["category_hint"]
    
    # Kontrolli olemasolu andmebaasis
    exact_match = db_product_map.get(raw_name.upper())
    
    best_ratio = 0
    best_candidate = None
    for db_name, db_info in db_product_map.items():
        ratio = fuzz.token_sort_ratio(raw_name.upper(), db_name)
        if ratio > best_ratio:
            best_ratio = ratio
            best_candidate = db_info
    
    # Hinda ISO vastavust määruse nr 74 alusel
    matching_isos = []
    
    # Reeglid ISO tuvastamiseks
    rn_lower = raw_name.lower()
    cat_lower = category_hint.lower()
    
    if "kuuldeaparaat" in rn_lower or "oticon" in rn_lower:
        if "cros" in rn_lower:
            matching_isos.append(("22.06.15.05", "teise kõrva heli ülekande süsteemid (CROS)", "Standardne CROS komplekt"))
        elif "zeal" in rn_lower or "intent" in rn_lower or "real" in rn_lower or "own" in rn_lower or "jet" in rn_lower:
            # Kuuldeaparaadid vastavad mitmele ISO koodile olenevalt patsiendi aktiivsusgrupist (I vs II) ja vanusest (laps vs täiskasvanu)
            matching_isos.append(("22.06.15.01", "kõrvatagused kuulmisabivahendid - aktiivsusgrupp I", "Kõrvatagune aparaat, aktiivsusgrupp I"))
            matching_isos.append(("22.06.15.02", "kõrvatagused kuulmisabivahendid - aktiivsusgrupp II", "Kõrvatagune aparaat, aktiivsusgrupp II"))
            matching_isos.append(("22.06.12.01", "kõrvasisesed kuulmisabivahendid - aktiivsusgrupp I", "Kõrvasisene aparaat, kui tegu on ITE/CIC mudeliga"))
    elif "filter" in rn_lower and "oticon" in cat_lower or "prowax" in rn_lower or "nowax" in rn_lower or "waxstop" in rn_lower:
        matching_isos.append(("22.06.21.03", "kuulmisimplantaadi / kuulmisabivahendi varuosad ja tarvikud", "Hooldustarvikud ja filtrid"))
    elif "patarei" in rn_lower and any(code in rn_lower for code in ["10", "13", "312", "675"]):
        matching_isos.append(("22.06.21.03", "kuulmisimplantaadi / kuuldeaparaadi patareid", "Kuuldeaparaatide spetsiaalsed tsink-õhk patareid"))
    elif "lainer" in rn_lower or "sisevooder" in cat_lower or "iceross" in rn_lower or "galeo" in rn_lower or "skeo" in rn_lower:
        if "tt" in rn_lower or "sääre" in cat_lower:
            matching_isos.append(("06.24.41.07", "Proteesi sisevooder (lainer) sääreproteesile", "Transtibiaalne (TT) lainer"))
        elif "tf" in rn_lower or "reie" in cat_lower:
            matching_isos.append(("06.24.41.08", "Proteesi sisevooder (lainer) põlve- ja reieproteesile", "Transfemoraalne (TF) lainer"))
        elif "käe" in rn_lower or "upper" in rn_lower:
            matching_isos.append(("06.18.00.02", "Proteesi sisevooder (lainer) ülajäsemeproteesile", "Ülajäseme proteesi lainer"))
        else:
            matching_isos.append(("06.24.41.07", "Proteesi sisevooder (lainer) sääreproteesile", "Lainer (täpsustamisel)"))
            matching_isos.append(("06.24.41.08", "Proteesi sisevooder (lainer) põlve- ja reieproteesile", "Lainer (täpsustamisel)"))
    elif "rulaator" in rn_lower:
        matching_isos.append(("12.06.06", "neljarattalised käimistoolid / rulaatorid", "Rulaator liikumise toeks"))
    elif "kompressioon" in rn_lower or "sukad" in rn_lower or "põlvikud" in rn_lower:
        matching_isos.append(("04.06.06", "ravikompressioontooted (sukad/põlvikud)", "Ravisukad veenihaiguste raviks"))
    elif "ortoos" in rn_lower or "rihm" in rn_lower or "patella" in rn_lower or "tugiside" in rn_lower or "fiksaator" in rn_lower:
        if "põlv" in rn_lower or "patella" in rn_lower:
            matching_isos.append(("06.12.06", "põlveortoosid", "Põlveliigest toetav ortoos"))
        elif "ranne" in rn_lower or "käsi" in rn_lower or "käsivars" in rn_lower:
            matching_isos.append(("06.06.03", "randme- ja käeortoosid", "Käe/randme toetav ortoos"))
        elif "hüppeliiges" in rn_lower or "jalg" in rn_lower:
            matching_isos.append(("06.12.03", "hüppeliigese ortoosid", "Hüppeliigest toetav ortoos"))
        elif "selg" in rn_lower:
            matching_isos.append(("06.03.09", "lülisambatoed / seljaortoosid", "Seljaortoos"))
        else:
            matching_isos.append(("06.12.06", "ortoosid (täpsustamisel)", "Ortoos"))
    elif "vanniaste" in rn_lower:
        matching_isos.append(("09.33.03", "vanni- ja dušitoolid / astmed", "Abivahend pesemisel"))
    elif "aluspesu" in rn_lower and "imav" in rn_lower:
        matching_isos.append(("09.30.24", "imavad tooted (uriinipidamatuse pesu)", "Korduvkasutatav imav pesu"))
    elif "resmed" in rn_lower or "cpap" in rn_lower or "uneapnoe" in cat_lower or "hydro-trach" in rn_lower:
        # Tervisekassa meditsiiniseadmete loetelu, MITTE SKA määrus 74
        matching_isos.append(("TERVISEKASSA", "Tervisekassa hüvitatav meditsiiniseade (CPAP/Hingamine)", "EI KUULU SKA määruse nr 74 loetellu"))

    # Määra kindlustase
    if exact_match:
        confidence = "DUPLIKAAT"
        status_desc = f"Toode on juba tooteregistris olemas (ID {exact_match[0]}: '{exact_match[1]}')"
    elif best_ratio >= 85:
        confidence = "VÕIMALIK ALIAS"
        status_desc = f"Väga sarnane olemasolevale tootele ({best_ratio}%): '{best_candidate[1]}' (Tootja: {best_candidate[3]})"
    elif len(matching_isos) == 1 and matching_isos[0][0] != "TERVISEKASSA":
        confidence = "KÕRGE KINDLUS"
        status_desc = f"Selge 1:1 vastavus määruse nr 74 klassile {matching_isos[0][0]} ({matching_isos[0][1]})"
    elif len(matching_isos) > 1:
        confidence = "ÜLEVAATUST VAJAV (MITU ISO-D)"
        iso_str = ", ".join([f"{iso[0]} ({iso[1]})" for iso in matching_isos])
        status_desc = f"Toode sobib mitmele ISO klassile: {iso_str}. Nõuab inimese määratlust vastavalt kliendi näidustusele."
    elif len(matching_isos) == 1 and matching_isos[0][0] == "TERVISEKASSA":
        confidence = "MADAL KINDLUS (TERVISEKASSA)"
        status_desc = "Tegemist on Tervisekassa kompenseeritava meditsiiniseadmega (CPAP/hingamisteraapia), mis ei kuulu SKA abivahendite määruse nr 74 alla."
    else:
        confidence = "MADAL KINDLUS"
        status_desc = "Ei leitud otsest vaste määruse nr 74 loetelust või vajab lisauurimist."

    results.append({
        "raw_name": raw_name,
        "source": source,
        "source_name": source_name,
        "brand": brand_hint,
        "manufacturer": mfg_hint,
        "category": category_hint,
        "matching_isos": matching_isos,
        "confidence": confidence,
        "status_desc": status_desc,
        "best_ratio": best_ratio,
        "best_candidate": best_candidate
    })

# Koondstatistika
new_prods = [r for r in results if r["confidence"] in ("KÕRGE KINDLUS", "ÜLEVAATUST VAJAV (MITU ISO-D)", "MADAL KINDLUS", "MADAL KINDLUS (TERVISEKASSA)")]
duplikaadid = [r for r in results if r["confidence"] == "DUPLIKAAT"]
aliased = [r for r in results if r["confidence"] == "VÕIMALIK ALIAS"]
manually_review = [r for r in results if "ÜLEVAATUST VAJAV" in r["confidence"] or "MADAL KINDLUS" in r["confidence"]]

new_brands = set(r["brand"] for r in new_prods if r["brand"] != "Määramata" and r["brand"].upper() not in db_brands)
new_mfgs = set(r["manufacturer"] for r in new_prods if r["manufacturer"] != "Määramata" and r["manufacturer"].upper() not in db_mfg)

print("\n=== SKANEERIMISE KOONDSTATISTIKA ===")
print(f"Kokku analüüsitud tooteid: {len(results)}")
print(f"Uusi tootekandidaate: {len(new_prods)}")
print(f" - Kõrge kindlusega: {len([r for r in new_prods if r['confidence'] == 'KÕRGE KINDLUS'])}")
print(f" - Ülevaatust vajavaid (mitu võimalikku ISO-d): {len([r for r in new_prods if 'MITU ISO-D' in r['confidence']])}")
print(f" - Madala kindlusega / Tervisekassa: {len([r for r in new_prods if 'MADAL KINDLUS' in r['confidence']])}")
print(f"Uusi tootjaid avastatud: {len(new_mfgs)} -> {new_mfgs}")
print(f"Uusi kaubamärke/brände avastatud: {len(new_brands)} -> {new_brands}")
print(f"Võimalikke duplikaate: {len(duplikaadid)}")
print(f"Võimalikke aliasnimesid olemasolevatele toodetele: {len(aliased)}")
print(f"Käsitsi kontrolli vajavaid kirjeid kokku: {len(manually_review)}")
