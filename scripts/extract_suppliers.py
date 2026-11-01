"""
Tarnijate tootekataloogide väljavõte, normaliseerimine, dublikaatide tuvastamine
ja ühtse SQLite tooteregistri (tooteregister) loomine.

Allikad:
1. Invaru (https://www.invaru.ee)
2. ITAK (https://www.itak.ee)
3. Terviseabi (https://terviseabi.ee)
4. Invaabi (https://invaabi.ee)
5. Invatooted (https://pood.invatooted.ee)
"""

import sys
import os
import re
import json
import html
import sqlite3
from typing import Dict, Any, List, Optional, Tuple, Set
from collections import defaultdict
import requests

sys.stdout.reconfigure(encoding='utf-8')

DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "data")
DB_PATH = os.path.join(DATA_DIR, "valideer.db")
RAW_CACHE_PATH = os.path.join(DATA_DIR, "raw_supplier_products.json")
VARIANT_CACHE_PATH = os.path.join(DATA_DIR, "invaru_variant_cache.json")

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Accept': 'application/json, text/plain, */*'
}

MANUFACTURER_MAP = {
    # Inkontinentsitooted
    "ABENA": "Abena Group (Taani)",
    "ABRI": "Abena Group (Taani)",
    "BAMBO": "Abena Group (Taani)",
    "MOLICARE": "Paul Hartmann AG (Saksamaa)",
    "HARTMANN": "Paul Hartmann AG (Saksamaa)",
    "MENALIND": "Paul Hartmann AG (Saksamaa)",
    "MOLINEA": "Paul Hartmann AG (Saksamaa)",
    "TENA": "Essity Hygiene and Health AB (Rootsi)",
    "ESSITY": "Essity Hygiene and Health AB (Rootsi)",
    "SENI": "TZMO SA (Poola)",
    "TZMO": "TZMO SA (Poola)",
    "LILLE": "Ontex Healthcare (Belgia)",
    "ONTEX": "Ontex Healthcare (Belgia)",
    "ID": "Ontex Healthcare (Belgia)",
    "EURON": "Ontex Healthcare (Belgia)",
    "ATTENDS": "Attends Healthcare Group (Rootsi/USA)",
    "SUPRIMA": "Suprima GmbH (Saksamaa)",

    # Ortoosid, sidemed ja kompressioon
    "BAUERFEIND": "Bauerfeind AG (Saksamaa)",
    "THUASNE": "Thuasne Group (Prantsusmaa)",
    "BORT": "Bort Medical (Saksamaa)",
    "ORLIMAN": "Orliman SLU (Hispaania)",
    "MEDI": "medi GmbH & Co. KG (Saksamaa)",
    "MEDIVEN": "medi GmbH & Co. KG (Saksamaa)",
    "SIGVARIS": "Sigvaris Group (Šveits)",
    "MAXIS": "Maxis a.s. (Tšehhi)",
    "OFA": "Ofa Bamberg GmbH (Saksamaa)",
    "CATELL": "Catell AB (Rootsi)",
    "SIDAS": "Sidas SAS (Prantsusmaa)",
    "ZAMST": "Nippon Sigmax Co., Ltd. (Jaapan)",
    "REH4MAT": "Reh4Mat Sp. z o.o. (Poola)",
    "QMED": "mdh Sp. z o.o. (Poola)",
    "SVORTO": "Svorto s.r.o. (Tšehhi)",
    "PULSAAR": "Pulsaar Nutrition (Šveits)",
    "YELLOWSPORT": "Yellow Sport (Poola)",
    "MUELLER": "Mueller Sports Medicine (USA)",
    "REHBAND": "Otto Bock HealthCare (Saksamaa)",
    "DONJOY": "Enovis / DJO Global (USA)",
    "PUSH": "Nea International bv (Holland)",
    "AIRCAST": "Enovis / DJO Global (USA)",

    # Liikumisabivahendid ja ratastoolid
    "VERMEIREN": "Vermeiren Group (Belgia)",
    "ETAC": "Etac AB (Rootsi)",
    "REBOTEC": "Rebotec Rehab GmbH (Saksamaa)",
    "INVACARE": "Invacare Corp. (USA/Saksamaa)",
    "DIETZ": "DIETZ GmbH (Saksamaa)",
    "MEYRA": "Meyra GmbH (Saksamaa)",
    "SUNRISE MEDICAL": "Sunrise Medical (Saksamaa/USA)",
    "QUICKIE": "Sunrise Medical (Saksamaa/USA)",
    "BREEZY": "Sunrise Medical (Saksamaa/USA)",
    "OTTOBOCK": "Ottobock SE & Co. KGaA (Saksamaa)",
    "TOPRO": "Topro Industri AS (Norra)",
    "TRUST CARE": "Trust Care AB (Rootsi)",
    "ROLLZ": "Rollz International (Holland)",
    "SWERECO": "Swereco Group (Rootsi)",
    "KMINA": "Kmina (Hispaania)",
    "RUSSKA": "Ludwig Bertram GmbH (Saksamaa)",
    "DRIVE": "Drive DeVilbiss Healthcare (Saksamaa/USA)",
    "TIMAGO": "Timago International Group (Poola)",
    "MOBILEX": "Mobilex A/S (Taani)",
    "DERBY": "Derby (Saksamaa)",
    "SUNDO": "Sundo Homecare GmbH (Saksamaa)",
    "ROHO": "Permobil AB (Rootsi)",
    "PERMOBIL": "Permobil AB (Rootsi)",

    # Tervisetooted, taastusravi ja diagnostika
    "BEURER": "Beurer GmbH (Saksamaa)",
    "OMRON": "Omron Healthcare (Jaapan)",
    "MICROLIFE": "Microlife AG (Šveits)",
    "MVS IN MOTION": "MVS In Motion (Belgia)",
    "SISSEL": "Novacare GmbH (Saksamaa)",
    "THERABAND": "Performance Health (USA)",
    "CANDO": "Fabrication Enterprises Inc. (USA)",
    "ROLYAN": "Performance Health (USA)",
    "AIREX": "Airex AG (Šveits)",
    "TOGU": "Togu GmbH (Saksamaa)",
    "BLACKROLL": "Blackroll AG (Šveits)",
    "INCREDIWEAR": "Incrediwear Inc. (USA)",
    "PENNINE": "Pennine Healthcare (Ühendkuningriik)",
    "MEDELA": "Medela AG (Šveits)",
    "CA-MI": "CA-MI Srl (Itaalia)"
}

KNOWN_FAMILIES = [
    # Abena
    ("ABENA", "Abena San", ["ABENA SAN", "ABRI-SAN", "ABRI SAN"]),
    ("ABENA", "Abena Pants", ["ABENA PANTS", "ABRI-FLEX", "ABRI FLEX"]),
    ("ABENA", "Abena Slip", ["ABENA SLIP", "ABRI-FORM", "ABRI FORM"]),
    ("ABENA", "Abena Light", ["ABENA LIGHT", "ABRI-LIGHT", "ABRI LIGHT"]),
    ("ABENA", "Abena Man", ["ABENA MAN", "ABRI-MAN", "ABRI MAN"]),
    ("ABENA", "Abri-Soft", ["ABRI-SOFT", "ABENA SOFT", "ABRI SOFT"]),
    ("ABENA", "Abena Fix", ["ABENA FIX", "ABRI-FIX", "ABRI FIX"]),
    ("ABENA", "Abena Skincare", ["ABENA PESUKREEM", "ABENA PESUVAHT", "ABENA TSINKSPREI", "ABENA KREEM"]),
    ("ABENA", "Abena Delta", ["DELTA-FORM", "DELTA FORM", "DELTA-SAN"]),
    
    # Hartmann / MoliCare
    ("MOLICARE", "MoliCare Pad", ["MOLICARE PAD", "MOLICARE LADY PAD", "MOLICARE MEN PAD", "MOLICARE PREMIUM PAD"]),
    ("MOLICARE", "MoliCare Mobile", ["MOLICARE MOBILE", "MOLICARE PREMIUM MOBILE", "MOLICARE ELASTIC"]),
    ("MOLICARE", "MoliCare Slip", ["MOLICARE SLIP", "MOLICARE PREMIUM SLIP"]),
    ("MOLICARE", "MoliCare Form", ["MOLICARE FORM", "MOLICARE PREMIUM FORM"]),
    ("MOLICARE", "MoliCare Fixpants", ["MOLICARE FIXPANTS", "MOLICARE FIX"]),
    ("MOLICARE", "MoliCare Bed Mat", ["MOLICARE BED MAT", "MOLINEA"]),
    ("MOLICARE", "MoliCare Skin", ["MENALIND", "MOLICARE SKIN"]),
    
    # TENA
    ("TENA", "Tena Lady", ["TENA LADY", "TENA DISCREET"]),
    ("TENA", "Tena Men", ["TENA MEN"]),
    ("TENA", "Tena Pants", ["TENA PANTS"]),
    ("TENA", "Tena Slip", ["TENA SLIP"]),
    ("TENA", "Tena Comfort", ["TENA COMFORT"]),
    ("TENA", "Tena Flex", ["TENA FLEX"]),
    ("TENA", "Tena Bed", ["TENA BED"]),
    ("TENA", "Tena Fix", ["TENA FIX"]),
    
    # Seni
    ("SENI", "Seni Lady", ["SENI LADY"]),
    ("SENI", "Seni Man", ["SENI MAN"]),
    ("SENI", "Seni Active", ["SENI ACTIVE"]),
    ("SENI", "Super Seni", ["SUPER SENI"]),
    ("SENI", "San Seni", ["SAN SENI"]),
    ("SENI", "Seni Optima", ["SENI OPTIMA"]),
    ("SENI", "Seni Soft", ["SENI SOFT"]),
    ("SENI", "Seni Care", ["SENI CARE"]),
    
    # Lille / Ontex
    ("LILLE", "Lille Supreme Light", ["LILLE SUPREME LIGHT", "SUPREME LIGHT", "ID LIGHT"]),
    ("LILLE", "Lille Supreme Pants", ["LILLE SUPREME PANTS", "SUPREME PANTS", "ID PANTS"]),
    ("LILLE", "Lille Supreme Fit", ["LILLE SUPREME FIT", "SUPREME FIT", "ID SLIP", "ID EXPERT SLIP"]),
    ("LILLE", "Lille Supreme Form", ["LILLE SUPREME FORM", "SUPREME FORM", "ID FORM"]),
    ("LILLE", "Lille Classic Bed", ["LILLE BED", "ID EXPERT PROTECT"])
]


def clean_html(raw_html: str) -> str:
    """Eemaldab HTML tagid ja unescape-ib erisümbolid."""
    if not raw_html:
        return ""
    text = re.sub(r'<[^>]+>', ' ', raw_html)
    text = html.unescape(text)
    return ' '.join(text.split())


def extract_product_features(title: str, desc: str = "", cats: List[str] = None, attrs: Dict[str, Any] = None) -> Dict[str, Any]:
    """Tuvastab toote nimetusest ja atribuutidest struktureeritud omadused."""
    title_clean = clean_html(title).strip()
    full_text = f"{title_clean} {desc}".upper()
    
    # 1. Tuvasta bränd
    brand = None
    if attrs and attrs.get('brand'):
        cand_b = str(attrs['brand']).strip().upper()
        if cand_b in MANUFACTURER_MAP:
            brand = cand_b
        elif any(cand_b.startswith(k) for k in MANUFACTURER_MAP.keys()):
            for k in MANUFACTURER_MAP.keys():
                if cand_b.startswith(k):
                    brand = k
                    break
        else:
            brand = cand_b

    if not brand:
        for b in sorted(MANUFACTURER_MAP.keys(), key=lambda x: -len(x)):
            if re.search(r'\b' + re.escape(b) + r'\b', full_text):
                if b == "HARTMANN" and "MOLICARE" in full_text:
                    brand = "MOLICARE"
                elif b == "ABRI" and "ABENA" in full_text:
                    brand = "ABENA"
                elif b == "ONTEX" and "LILLE" in full_text:
                    brand = "LILLE"
                elif b == "TZMO" and "SENI" in full_text:
                    brand = "SENI"
                else:
                    brand = b
                break

    manufacturer = MANUFACTURER_MAP.get(brand, f"{brand} (Tootja)" if brand and brand != "MÄÄRAMATA" else "Määramata")

    # 2. Tuvasta tootesari
    product_family = None
    if brand:
        for f_brand, f_name, f_aliases in KNOWN_FAMILIES:
            if brand == f_brand or (brand in ["HARTMANN", "MOLICARE"] and f_brand == "MOLICARE"):
                for al in f_aliases:
                    if re.search(r'\b' + re.escape(al) + r'\b', full_text):
                        product_family = f_name
                        break
            if product_family:
                break

    if not product_family:
        words = title_clean.split()
        if len(words) >= 2:
            product_family = f"{words[0]} {words[1]}"
        else:
            product_family = title_clean

    # 3. Tuvasta maht ml
    ml_capacity = None
    ml_match = re.search(r'\b(\d{2,4})\s*ML\b', full_text)
    if ml_match:
        ml_capacity = int(ml_match.group(1))

    # 4. Tuvasta tilgad (drops)
    drops = None
    drop_match = re.search(r'\b(\d+)\s*(TILKA?|DROPS?)\b', full_text)
    if drop_match:
        drops = int(drop_match.group(1))
    else:
        dec_drop = re.search(r'\b(\d+)[,\.]5\s*(TILKA?|DROPS?)\b', full_text)
        if dec_drop:
            drops = int(dec_drop.group(1))

    # 5. Tuvasta tase (level)
    level = None
    lvl_match = re.search(r'\b(?:SAN|PAD|LIGHT|LEVEL|PLUS|SUPER|MAXI|EXTRA)\s*(\d+)\b', full_text)
    if lvl_match:
        level = int(lvl_match.group(1))
    elif not drops:
        # Otsi numbrit sarja järel
        fam_escaped = re.escape(product_family.upper())
        fam_lvl = re.search(fam_escaped + r'\s*(\d+)\b', full_text)
        if fam_lvl:
            level = int(fam_lvl.group(1))
        else:
            single_num = re.search(r'\b([0-9])\b', title_clean)
            if single_num:
                level = int(single_num.group(1))

    # 6. Tuvasta suurus
    size = None
    combo_match = re.search(r'\b(XXS|XS|S|M|L|XL|XXL|XXXL)(\d)\b', full_text)
    if combo_match:
        size = combo_match.group(1).upper()
        if not level:
            level = int(combo_match.group(2))
    else:
        size_match = re.search(r'\b(XXS|XS|S|M|L|XL|XXL|XXXL)\b', full_text)
        if size_match:
            size = size_match.group(1).upper()

    # 7. Tuvasta pakendi info
    pkg_info = None
    pkg_match = re.search(r'\bN\s*(\d+)\b', full_text)
    if pkg_match:
        pkg_info = f"N{pkg_match.group(1)}"
    else:
        tk_match = re.search(r'\b(\d+)\s*(TK|PCS|PK)\b', full_text)
        if tk_match:
            pkg_info = f"{tk_match.group(1)} tk"

    # 8. Tuvasta toote tüüp (product_type)
    cats_str = " ".join(cats or []).lower()
    full_lower = full_text.lower()
    if any(x in full_lower or x in cats_str for x in ['püksmäh', 'pants', 'pull-up', 'imavad püksid']):
        product_type = "püksmähe"
    elif any(x in full_lower or x in cats_str for x in ['vormmäh', 'san ', 'form ']) and not any(x in full_lower for x in ['kreem', 'vaht']):
        product_type = "vormmähe"
    elif any(x in full_lower or x in cats_str for x in ['vöötmäh', 'flex', 'optima']):
        product_type = "vöömähkmed"
    elif any(x in full_lower or x in cats_str for x in ['mähkmed täiskasvanutele', 'slip', 'all-in-one']):
        product_type = "klassikaline mähe"
    elif any(x in full_lower or x in cats_str for x in ['side', 'sidemed', 'pad', 'lady', 'men']) and not any(x in full_lower for x in ['kreem', 'pesu', 'ratastoolipadi']):
        product_type = "inkontinentsiside"
    elif any(x in full_lower or x in cats_str for x in ['lina', 'aluslina', 'voodikaitse', 'bed mat']):
        product_type = "imav lina / voodikaitse"
    elif any(x in full_lower or x in cats_str for x in ['ratastool', 'wheelchair']):
        product_type = "ratastool"
    elif any(x in full_lower or x in cats_str for x in ['kark', 'kepp', 'crutch', 'cane', 'küünarkark']):
        product_type = "kark / käimiskepp"
    elif any(x in full_lower or x in cats_str for x in ['rulaator', 'käimisraam', 'rollator', 'walker']):
        product_type = "rulaator / käimisraam"
    elif any(x in full_lower or x in cats_str for x in ['ortoos', 'lahas', 'tugi', 'bandaaž']):
        product_type = "ortoos"
    elif any(x in full_lower or x in cats_str for x in ['kompressioon', 'sukad', 'põlvikud', 'mediven', 'ccl1', 'ccl2']):
        product_type = "kompressioontoode"
    elif any(x in full_lower or x in cats_str for x in ['dušitool', 'vanniiste', 'potitool', 'tualett', 'potikõrgendus']):
        product_type = "tualeti- ja vannitoatoode"
    elif any(x in full_lower or x in cats_str for x in ['pesukreem', 'kaitsekreem', 'nahahooldus', 'puhastusvaht', 'salv', 'kreem']):
        product_type = "nahahooldusvahend"
    else:
        product_type = "muu abivahend"

    # 9. Kanoniseeritud tootenimi
    canon_parts = []
    if brand and brand != "MÄÄRAMATA":
        canon_parts.append(brand.upper())
        if product_family:
            fam_clean = re.sub(r'^\s*' + re.escape(brand) + r'\s*', '', product_family, flags=re.I).strip()
            if fam_clean:
                canon_parts.append(fam_clean.upper())
    elif product_family:
        canon_parts.append(product_family.upper())

    if size and level:
        if "PANTS" in " ".join(canon_parts) or product_type == "püksmähe":
            canon_parts.append(f"{size}{level}")
        else:
            canon_parts.append(str(level))
            canon_parts.append(size)
    elif level is not None:
        canon_parts.append(str(level))
    elif drops is not None:
        canon_parts.append(f"{drops} TILKA")
    elif size:
        canon_parts.append(size)

    if ml_capacity and not level and not drops:
        canon_parts.append(f"{ml_capacity}ML")

    if canon_parts:
        official_name = " ".join(canon_parts).strip()
    else:
        clean_name = re.sub(r'^(Vormmähkmed|Vormmähe|Mähkmed täiskasvanutele|Mähkmed|Imavad püksid|Sidemed|Side naistele|Side meestele|Aluslinad|Pestav imav lina)\s+', '', title_clean, flags=re.IGNORECASE)
        clean_name = re.sub(r'\s+N\d+.*$', '', clean_name, flags=re.IGNORECASE)
        clean_name = re.sub(r'\s+\d+\s*tk.*$', '', clean_name, flags=re.IGNORECASE)
        official_name = clean_name.strip().upper()

    return {
        "title": title_clean,
        "brand": brand or "MÄÄRAMATA",
        "manufacturer": manufacturer,
        "product_family": product_family or title_clean,
        "official_product_name": official_name,
        "ml_capacity": ml_capacity,
        "drop_rating": drops or level,
        "size": size,
        "package_information": pkg_info,
        "product_type": product_type
    }


def get_all_raw_products() -> List[Dict[str, Any]]:
    """Laeb tooted vahemälust ja lisab Invaru variantide vahemälust täpsed suurused ja imavused."""
    if not os.path.exists(RAW_CACHE_PATH):
        raise RuntimeError("raw_supplier_products.json not found!")
        
    with open(RAW_CACHE_PATH, "r", encoding="utf-8") as f:
        raw_items = json.load(f)

    variant_cache = {}
    if os.path.exists(VARIANT_CACHE_PATH):
        with open(VARIANT_CACHE_PATH, "r", encoding="utf-8") as f:
            variant_cache = json.load(f)

    print(f"Loaded {len(raw_items)} raw items and {len(variant_cache)} cached variant pages.")
    
    final_items = []
    expanded_count = 0
    
    for it in raw_items:
        url = it.get('source_url')
        if url in variant_cache and len(variant_cache[url]) > 0:
            variants = variant_cache[url]
            expanded_count += len(variants)
            for v in variants:
                feat = extract_product_features(v, "")
                feat['source_supplier'] = it.get('source_supplier', 'Invaru')
                feat['source_url'] = url
                feat['raw_name'] = v
                feat['sku'] = it.get('sku', '')
                final_items.append(feat)
        else:
            final_items.append(it)

    print(f"Total supplier records after variant integration: {len(final_items)} (expanded +{expanded_count})")
    return final_items


def deduplicate_and_build_registry(all_items: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Tuvastab erinevate tarnijate samad tooted ja ühendab need ühtseks tooteregistriks."""
    print(f"\nDeduplicating and unifying {len(all_items)} total supplier records...")
    
    reparsed_items = []
    for it in all_items:
        raw_name = it.get('raw_name') or it.get('title', '')
        sku = it.get('sku', '')
        supp = it.get('source_supplier', '')
        url = it.get('source_url', '')
        attrs = {'sku': sku}
        if it.get('brand') and it.get('brand') != "MÄÄRAMATA":
            attrs['brand'] = it['brand']
            
        feat = extract_product_features(raw_name, "", attrs=attrs)
        feat['source_supplier'] = supp
        feat['source_url'] = url
        feat['raw_name'] = raw_name
        feat['sku'] = sku
        reparsed_items.append(feat)

    groups: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
    
    for item in reparsed_items:
        brand = item.get('brand', 'MÄÄRAMATA')
        family = item.get('product_family', '')
        drop = item.get('drop_rating') or ''
        size = item.get('size') or ''
        vol = item.get('ml_capacity') or ''
        sku = item.get('sku') or ''
        
        if brand != "MÄÄRAMATA" and family:
            group_key = f"{brand}::{family}::{drop}::{size}::{vol}".upper()
        elif sku:
            group_key = f"SKU::{sku}".upper()
        else:
            norm_name = re.sub(r'[^A-Z0-9]', '', item.get('official_product_name', '').upper())
            group_key = f"NAME::{norm_name}"
            
        groups[group_key].append(item)

    print(f"Created {len(groups)} distinct unified product clusters.")
    canonical_products: List[Dict[str, Any]] = []
    
    for key, items in groups.items():
        primary = items[0]
        
        aliases_set: Set[str] = set()
        suppliers_set: Set[str] = set()
        urls_set: Set[str] = set()
        
        best_name = primary['official_product_name']
        best_vol = None
        best_drop = None
        best_size = None
        best_pkg = None
        best_type = primary['product_type']
        
        for it in items:
            raw = it.get('raw_name')
            if raw:
                aliases_set.add(raw.strip())
                clean_variant = re.sub(r'[\r\n\t]+', ' ', raw).strip()
                aliases_set.add(clean_variant)
            if it.get('title'):
                aliases_set.add(it['title'])
            if it.get('sku'):
                aliases_set.add(f"SKU {it['sku']}")
                
            suppliers_set.add(it['source_supplier'])
            if it.get('source_url'):
                urls_set.add(it['source_url'])
                
            if not best_vol and it.get('ml_capacity'):
                best_vol = it['ml_capacity']
            if not best_drop and it.get('drop_rating'):
                best_drop = it['drop_rating']
            if not best_size and it.get('size'):
                best_size = it['size']
            if not best_pkg and it.get('package_information'):
                best_pkg = it['package_information']
            if best_type == "muu abivahend" and it.get('product_type') != "muu abivahend":
                best_type = it['product_type']

        aliases_set.add(best_name)
        
        canonical_products.append({
            "manufacturer": primary['manufacturer'],
            "brand": primary['brand'],
            "product_family": primary['product_family'],
            "official_product_name": best_name,
            "aliases": json.dumps(sorted(list(aliases_set)), ensure_ascii=False),
            "package_information": best_pkg,
            "ml_capacity": best_vol,
            "drop_rating": best_drop,
            "product_type": best_type,
            "source_supplier": ", ".join(sorted(list(suppliers_set))),
            "source_url": ", ".join(sorted(list(urls_set))[:3]),
            "item_count": len(items)
        })
        
    return canonical_products


def save_to_sqlite(canonical_products: List[Dict[str, Any]]):
    """Salvestab kanoniseeritud tooted valideer.db tabelisse 'tooteregister'."""
    print(f"\nSaving {len(canonical_products)} products to SQLite table 'tooteregister' in {DB_PATH}...")
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS tooteregister (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        manufacturer TEXT NOT NULL,
        brand TEXT NOT NULL,
        product_family TEXT,
        official_product_name TEXT NOT NULL,
        aliases TEXT NOT NULL,
        package_information TEXT,
        ml_capacity INTEGER,
        drop_rating INTEGER,
        product_type TEXT,
        source_supplier TEXT,
        source_url TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    """)
    
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_tooteregister_brand ON tooteregister(brand);")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_tooteregister_name ON tooteregister(official_product_name);")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_tooteregister_type ON tooteregister(product_type);")
    
    cursor.execute("DELETE FROM tooteregister;")
    
    insert_sql = """
    INSERT INTO tooteregister (
        manufacturer, brand, product_family, official_product_name,
        aliases, package_information, ml_capacity, drop_rating,
        product_type, source_supplier, source_url
    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """
    
    rows = [
        (
            p['manufacturer'],
            p['brand'],
            p['product_family'],
            p['official_product_name'],
            p['aliases'],
            p['package_information'],
            p['ml_capacity'],
            p['drop_rating'],
            p['product_type'],
            p['source_supplier'],
            p['source_url']
        )
        for p in canonical_products
    ]
    
    cursor.executemany(insert_sql, rows)
    conn.commit()
    
    cursor.execute("SELECT count(*) FROM tooteregister;")
    total_saved = cursor.fetchone()[0]
    
    cursor.execute("SELECT count(DISTINCT manufacturer) FROM tooteregister WHERE manufacturer != 'Määramata';")
    mfg_known = cursor.fetchone()[0]

    cursor.execute("SELECT manufacturer, count(*) FROM tooteregister WHERE manufacturer != 'Määramata' GROUP BY manufacturer ORDER BY count(*) DESC LIMIT 20;")
    mfg_counts = cursor.fetchall()
    
    cursor.execute("SELECT product_type, count(*) FROM tooteregister GROUP BY product_type ORDER BY count(*) DESC;")
    cat_counts = cursor.fetchall()
    
    cursor.execute("SELECT count(*) FROM tooteregister WHERE source_supplier LIKE '%,%';")
    cross_supplier_count = cursor.fetchone()[0]
    
    conn.close()
    
    print(f"\n================ IMPORT COMPLETE ================")
    print(f"Total unified products stored in tooteregister: {total_saved}")
    print(f"Identified manufacturers: {mfg_known}")
    print(f"Cross-supplier products (sold by 2+ stores): {cross_supplier_count}")
    
    print("\n--- TOP MANUFACTURERS COVERED ---")
    for m, c in mfg_counts:
        print(f"  {m}: {c} products")
        
    print("\n--- CATEGORY / PRODUCT TYPE COVERAGE ---")
    for ct, c in cat_counts:
        print(f"  {ct}: {c} products")
    print(f"=================================================\n")


def main():
    print("=== STARTING PRODUCT REGISTRY BUILD ===")
    raw_products = get_all_raw_products()
    canonical = deduplicate_and_build_registry(raw_products)
    save_to_sqlite(canonical)


if __name__ == "__main__":
    main()
