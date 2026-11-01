"""
Testscript tooteregistri andmekvaliteedi parendamiseks:
1. Duplikaattoodete liitmine
2. Tarnijaspetsiifiliste variantide koondamine kanooniliseks tooteks
3. Aliaste konfliktide lahendamine
4. Puuduvate brändide ja tootjate tuvastamine
5. 'Muu abivahend' kategooria vähendamine
6. Tootesarjade (product_family) täpsustamine
7. Riikliku ISO klassifikatsiooni usaldusväärsuse parandamine
"""

import sys
import os
import re
import json
import html
import sqlite3
from typing import Dict, Any, List, Optional, Tuple, Set
from collections import defaultdict, Counter

sys.stdout.reconfigure(encoding='utf-8')

DB_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "test_cleanup.db")

BRAND_MAP = {
    # Inkontinents & Hügieen
    'ABENA': ('ABENA', 'Abena Group (Taani)'),
    'ABRI': ('ABENA', 'Abena Group (Taani)'),
    'BAMBO': ('ABENA', 'Abena Group (Taani)'),
    'DELTA-FORM': ('ABENA', 'Abena Group (Taani)'),
    'DELTA-SAN': ('ABENA', 'Abena Group (Taani)'),
    'MOLICARE': ('MOLICARE', 'Paul Hartmann AG (Saksamaa)'),
    'HARTMANN': ('MOLICARE', 'Paul Hartmann AG (Saksamaa)'),
    'MENALIND': ('MOLICARE', 'Paul Hartmann AG (Saksamaa)'),
    'MOLINEA': ('MOLICARE', 'Paul Hartmann AG (Saksamaa)'),
    'TENA': ('TENA', 'Essity Hygiene and Health AB (Rootsi)'),
    'ESSITY': ('TENA', 'Essity Hygiene and Health AB (Rootsi)'),
    'SENI': ('SENI', 'TZMO SA (Poola)'),
    'TZMO': ('SENI', 'TZMO SA (Poola)'),
    'BELLA': ('SENI', 'TZMO SA (Poola)'),
    'LILLE': ('LILLE', 'Ontex Healthcare (Belgia)'),
    'ONTEX': ('LILLE', 'Ontex Healthcare (Belgia)'),
    'EURON': ('LILLE', 'Ontex Healthcare (Belgia)'),
    'SUPREMFIT': ('LILLE', 'Ontex Healthcare (Belgia)'),
    'ATTENDS': ('ATTENDS', 'Attends Healthcare Group (Rootsi/USA)'),
    'SUPRIMA': ('SUPRIMA', 'Suprima GmbH (Saksamaa)'),
    'CHEMI-PHARM': ('CHEMI-PHARM', 'AS Chemi-Pharm (Eesti)'),
    'OILLAN': ('OILLAN', 'Oceanic Sp. z o.o. (Poola)'),
    'SENSILIND': ('SENSILIND', 'Paul Hartmann AG / Sensilind (Saksamaa)'),
    'DUREX': ('DUREX', 'Reckitt Benckiser (UK)'),

    # Liikumine & Ratastoolid
    'VERMEIREN': ('VERMEIREN', 'Vermeiren Group (Belgia)'),
    'INVACARE': ('INVACARE', 'Invacare Corp. (USA/Saksamaa)'),
    'DIETZ': ('DIETZ', 'DIETZ GmbH (Saksamaa)'),
    'MEYRA': ('MEYRA', 'Meyra GmbH (Saksamaa)'),
    'OTTOBOCK': ('OTTOBOCK', 'Ottobock SE & Co. KGaA (Saksamaa)'),
    'PANTHERA': ('PANTHERA', 'Panthera AB (Rootsi)'),
    'ETAC': ('ETAC', 'Etac AB (Rootsi)'),
    'REBOTEC': ('REBOTEC', 'Rebotec Rehab GmbH (Saksamaa)'),
    'TOPRO': ('TOPRO', 'Topro Industri AS (Norra)'),
    'TRUST CARE': ('TRUST CARE', 'Trust Care AB (Rootsi)'),
    'ROLLZ': ('ROLLZ', 'Rollz International (Holland)'),
    'REHAFUND': ('REHAFUND', 'Rehafund Sp. z o.o. (Poola)'),
    'TIMAGO': ('TIMAGO', 'Timago International Group (Poola)'),
    'MOBILEX': ('MOBILEX', 'Mobilex A/S (Taani)'),
    'KMINA': ('KMINA', 'Kmina (Hispaania)'),
    'DRIVE': ('DRIVE', 'Drive DeVilbiss Healthcare (Saksamaa/USA)'),
    'DEVILBISS': ('DRIVE', 'Drive DeVilbiss Healthcare (Saksamaa/USA)'),
    'SUNRISE': ('SUNRISE MEDICAL', 'Sunrise Medical (Saksamaa/USA)'),
    'QUICKIE': ('SUNRISE MEDICAL', 'Sunrise Medical (Saksamaa/USA)'),
    'BREEZY': ('SUNRISE MEDICAL', 'Sunrise Medical (Saksamaa/USA)'),
    'EMPULSE': ('SUNRISE MEDICAL', 'Sunrise Medical (Saksamaa/USA)'),
    'SWERECO': ('SWERECO', 'Swereco Group (Rootsi)'),
    'SUNDO': ('SUNDO', 'Sundo Homecare GmbH (Saksamaa)'),
    'MORETTI': ('MORETTI', 'Moretti SpA (Itaalia)'),
    'HERDEGEN': ('HERDEGEN', 'Herdegen (Prantsusmaa)'),
    'GIMA': ('GIMA', 'Gima SpA (Itaalia)'),
    'PERMOBIL': ('PERMOBIL', 'Permobil AB (Rootsi)'),
    'ROHO': ('ROHO', 'Permobil AB (Rootsi)'),
    'ROBOOTER': ('ROBOOTER', 'Bangbang Robotics / Robooter (EL/Hiina)'),
    'PRIDE': ('PRIDE', 'Pride Mobility Products (USA)'),
    'ESLA': ('ESLA', 'E.S. Lahtinen Oy (Soome)'),
    'REHASENSE': ('REHASENSE', 'Rehasense Group (Taani/Saksamaa)'),
    'VITEACARE': ('VITEACARE', 'mdh Sp. z o.o. / Vitea Care (Poola)'),
    'QUOKKA': ('QUOKKA', 'Quokka (Belgia)'),
    'RAIZER': ('RAIZER', 'Liftup A/S (Taani)'),
    'ASTON': ('ASTON', 'Drive DeVilbiss Healthcare (Saksamaa)'),

    # Ortoosid, Tallatoed & Kompressioon
    'PEDAG': ('PEDAG', 'Schelchen GmbH (Saksamaa)'),
    'BAUERFEIND': ('BAUERFEIND', 'Bauerfeind AG (Saksamaa)'),
    'VENOTRAIN': ('BAUERFEIND', 'Bauerfeind AG (Saksamaa)'),
    'THUASNE': ('THUASNE', 'Thuasne Group (Prantsusmaa)'),
    'BORT': ('BORT', 'Bort Medical (Saksamaa)'),
    'PEDISOFT': ('BORT', 'Bort Medical (Saksamaa)'),
    'ORLIMAN': ('ORLIMAN', 'Orliman SLU (Hispaania)'),
    'MEDIVEN': ('MEDI', 'medi GmbH & Co. KG (Saksamaa)'),
    'MEDI': ('MEDI', 'medi GmbH & Co. KG (Saksamaa)'),
    'CIRCUMED': ('MEDI', 'medi GmbH & Co. KG (Saksamaa)'),
    'SIGVARIS': ('SIGVARIS', 'Sigvaris Group (Šveits)'),
    'JOBST': ('JOBST', 'Essity BSN medical (Saksamaa/Rootsi)'),
    'OFABAMBERG': ('OFA', 'Ofa Bamberg GmbH (Saksamaa)'),
    'OFA': ('OFA', 'Ofa Bamberg GmbH (Saksamaa)'),
    'MAXIS': ('MAXIS', 'Maxis a.s. (Tšehhi)'),
    'SVORTO': ('SVORTO', 'Svorto s.r.o. (Tšehhi)'),
    'SIDAS': ('SIDAS', 'Sidas SAS (Prantsusmaa)'),
    'REH4MAT': ('REH4MAT', 'Reh4Mat Sp. z o.o. (Poola)'),
    'QMED': ('QMED', 'mdh Sp. z o.o. (Poola)'),
    'MEMO': ('MEMO', 'mdh Sp. z o.o. (Poola)'),
    'ORTHOMOVEMENT': ('ORTHOMOVEMENT', 'Ortho Movement (Rootsi)'),
    'ORTHOCARE': ('ORTHOCARE', 'Orthocare (Türgi/Saksamaa)'),
    'OPPO': ('OPPO', 'Oppo Medical Inc. (USA)'),
    'PUSH': ('PUSH', 'Nea International bv (Holland)'),
    'DONJOY': ('DONJOY', 'Enovis / DJO Global (USA)'),
    'AIRCAST': ('DONJOY', 'Enovis / DJO Global (USA)'),
    'MUELLER': ('MUELLER', 'Mueller Sports Medicine (USA)'),
    'ZAMST': ('ZAMST', 'Nippon Sigmax Co., Ltd. (Jaapan)'),
    'YELLOWSPORT': ('YELLOWSPORT', 'Yellow Sport (Poola)'),
    'PULSAAR': ('PULSAAR', 'Pulsaar Nutrition (Šveits)'),
    'ESTCARBON': ('ESTCARBON', 'Estcarbon OÜ (Eesti)'),
    'CATELL': ('CATELL', 'Catell AB (Rootsi)'),
    'PRIM': ('PRIM', 'Prim S.A. (Hispaania)'),
    'TONUS ELAST': ('TONUS ELAST', 'Tonus Elast AS (Läti)'),

    # Taastusravi, Voodid & Hooldus
    'WINNCARE': ('WINNCARE', 'Winncare Group (Prantsusmaa)'),
    'HALEY’S JOY': ('HALEY\'S JOY', 'Haley\'s Joy (USA)'),
    'HALEYS JOY': ('HALEY\'S JOY', 'Haley\'s Joy (USA)'),
    'KTR': ('KTR', 'KTR Sp. z o.o. (Poola)'),
    'VETTEL': ('VETTEL', 'Vettel OÜ (Eesti)'),
    'SISSEL': ('SISSEL', 'Novacare GmbH (Saksamaa)'),
    'NOVACARE': ('NOVACARE', 'Novacare GmbH (Saksamaa)'),
    'BEURER': ('BEURER', 'Beurer GmbH (Saksamaa)'),
    'OMRON': ('OMRON', 'Omron Healthcare (Jaapan)'),
    'MICROLIFE': ('MICROLIFE', 'Microlife AG (Šveits)'),
    'ROSSMAX': ('ROSSMAX', 'Rossmax International (Šveits)'),
    'THERABAND': ('THERABAND', 'Performance Health (USA)'),
    'BLACKROLL': ('BLACKROLL', 'Blackroll AG (Šveits)'),
    'AIREX': ('AIREX', 'Airex AG (Šveits)'),
    'TOGU': ('TOGU', 'Togu GmbH (Saksamaa)'),
    'CANDO': ('CANDO', 'Fabrication Enterprises Inc. (USA)'),
    'ROLYAN': ('ROLYAN', 'Performance Health (USA)'),
    'KOST': ('KOST', 'Kost International (Saksamaa)'),
    'CONTACT PLUS': ('CONTACT PLUS', 'Contact Plus (Prantsusmaa)'),
    'CA-MI': ('CA-MI', 'CA-MI Srl (Itaalia)'),
    'MEDELA': ('MEDELA', 'Medela AG (Šveits)'),
    'PENNINE': ('PENNINE', 'Pennine Healthcare (Ühendkuningriik)'),
    'INCREDIWEAR': ('INCREDIWEAR', 'Incrediwear Inc. (USA)'),
    'MVS IN MOTION': ('MVS IN MOTION', 'MVS In Motion (Belgia)'),
    'MOVES': ('MVS IN MOTION', 'MVS In Motion (Belgia)'),
    'TUNTURI': ('TUNTURI', 'Tunturi New Fitness (Holland)'),
    'TFH': ('TFH', 'TFH Special Needs (Ühendkuningriik)'),
    'DR. LUIGI': ('DR. LUIGI', 'Dr. Luigi d.o.o. (Horvaatia)'),
    'VERICA': ('VERICA', 'Verica Ortopeedilised Jalatsid (EL)'),
}

CATEGORY_RULES = [
    ('püksmähe', [
        r'\bPANTS\b', r'\bPÜKSMÄH', r'\bPULL-UP', r'IMAVAD PÜKSID', r'MOLICARE MOBILE', r'TENA PANTS', r'SENI ACTIVE'
    ]),
    ('vormmähe', [
        r'\bVORMMÄH', r'\bSAN\b', r'\bFORM\b', r'\bCOMFORT\b'
    ]),
    ('vöömähkmed', [
        r'\bVÖÖTMÄH', r'\bVÖÖMÄH', r'\bFLEX\b', r'\bOPTIMA\b'
    ]),
    ('klassikaline mähe', [
        r'\bSLIP\b', r'\bMÄHKMED\b', r'\bALL-IN-ONE\b'
    ]),
    ('inkontinentsiside', [
        r'\bSIDE\b', r'\bSIDEMED\b', r'\bPAD\b', r'\bLADY\b', r'\bLIGHT\b', r'\bEXTRA\b', r'\bNORMAL\b', r'\bSUPER\b', r'\bMINI\b', r'\bMICRO\b', r'\bMEN\s+\d', r'INCONTINENCE', r'MOLICARE PAD', r'TENA LADY', r'TENA MEN', r'SENI LADY'
    ]),
    ('imav lina / voodikaitse', [
        r'\bLINA\b', r'\bALUSLINA\b', r'\bVOODIKAITSE\b', r'\bBED MAT\b', r'\bSUPERDRY\b', r'\bPESTAV LINA\b', r'\bKATTEMATT\b'
    ]),
    ('fikseerivad püksid', [
        r'\bFIKSEERIV', r'\bFIX\b', r'\bFIXPANTS\b', r'\bVÕRKPÜKS', r'\bSUPRIMA\b'
    ]),
    ('nahahooldus- ja hügieenivahend', [
        r'\bKREEM\b', r'\bVAHT\b', r'\bÕLI\b', r'\bSALV\b', r'\bGEEL\b', r'\bPUHASTUS', r'\bPESU', r'\bŠAMPOON\b', r'\bSAMPOON\b', r'\bIHUD\b', r'\bIHUPIIM\b', r'\bRÄTIK', r'\bKINNAS\b', r'\bKINDAD\b', r'\bINTIIM', r'\bTSINK', r'\bSEEP\b', r'\bDERM', r'\bDESINF', r'\bSENSILIND\b', r'\bOILLAN\b', r'\bSKINCARE\b', r'\bLIBESTI\b'
    ]),
    ('ortoos ja tallatugi', [
        r'\bORTOOS\b', r'\bTALLATUGI\b', r'\bTALLATOED\b', r'\bSISETALLAD\b', r'\bPOOLTALLAD\b', r'\bBANDAAŽ\b', r'\bBANDAAS\b', r'\bLAHAS\b', r'\bKORREKTOR\b', r'\bVARBA', r'\bKANNA', r'\bKAPUGA\b', r'\bTRAKSID\b', r'\bVÖÖ\b', r'\bKRAE\b', r'\bSONGAVÖÖ\b', r'\bTEIP\b', r'\bKINESIO', r'\bFIKSAATOR\b', r'\bTUGI\b', r'\bTUED\b', r'\bJALATS\b', r'\bJALATSID\b', r'\bKINGAD\b', r'\bSANDAALID\b', r'\bSUSSID\b', r'\bKORRIGEERIV\b', r'\bTERVISEJALATS\b', r'\bSVORTO\b', r'\bPEDAG\b', r'\bMEMO\b'
    ]),
    ('kompressioontoode', [
        r'\bKOMPRESSIOON', r'\bSUKAD\b', r'\bSUKK\b', r'\bPÕLVIKUD\b', r'\bPÕLVIK\b', r'\bSUKKPÜKSID\b', r'\bMEDIVEN\b', r'\bJOBST\b', r'\bVENOTRAIN\b', r'\bCCL1\b', r'\bCCL2\b', r'\bCCL3\b'
    ]),
    ('liikumisabivahend', [
        r'\bRATASTOOL\b', r'\bRULAATOR\b', r'\bKÄIMISRAAM\b', r'\bKÄIMISTOOL\b', r'\bKARK\b', r'\bKARGU', r'\bKEPP\b', r'\bKEPI', r'\bKÄIMISKEPP\b', r'\bTÕUKERATAS\b', r'\bSKUU?TER\b', r'\bROLLER\b', r'\bKALDTEE\b', r'\bRAMP\b', r'\bKÄSIPUU\b', r'\bRATAS\b', r'\bSISEKUMM\b', r'\bVÄLISKUMM\b', r'\bKUMMIOTSIK\b', r'\bVIHMASIRM\b', r'\bKORV\b', r'\bKOTT\b', r'\bKÄRU\b', r'\bKÄRUD\b', r'\bLAADIMISSILD\b', r'\bRATTOOLI\b', r'\bTREPIRONIJA\b'
    ]),
    ('tualeti- ja vannitoatoode', [
        r'\bPOTITOOL\b', r'\bPOTIKÕRGENDUS\b', r'\bDUŠITOOL\b', r'\bDUŠITOOLI\b', r'\bVANNIISTE\b', r'\bVANNI\b', r'\bTUALET', r'\bKÄETUGI\b', r'\bDUŠI\b', r'\bSIOBER\b', r'\bURIINIPUDEL\b', r'\bURIINIKOTT\b', r'\bKATEETER\b', r'\bKÄEPIDE\b', r'\bTUGIKÄEPIDE\b'
    ]),
    ('hooldusvoodi ja lamatiste ennetus', [
        r'\bVOODI\b', r'\bMADRATS\b', r'\bLAMATIS', r'\bISTMEPADI\b', r'\bPOSITSIONEER', r'\bPADJAKATE\b', r'\bVOODILAUD\b', r'\bVOODIPIIRE\b', r'\bTÕSTUK\b', r'\bTÕSTESEADE\b', r'\bLING\b', r'\bRAIZER\b', r'\bLIBILAUD\b', r'\bSIIRDUMISLAUD\b', r'\bPÖÖRDALUS\b', r'\bTRAVEX\b'
    ]),
    ('taastusravi- ja treeningvahend', [
        r'\bVÕIMLEMIS', r'\bTREENING', r'\bMASSAA', r'\bPALL', r'\bIPALL', r'\bLINT\b', r'\bKUMM\b', r'\bEXPANDER\b', r'\bTASAKAAL', r'\bRULL\b', r'\bTRENAŽÖÖR\b', r'\bKIIK\b', r'\bKIIGE', r'\bSENSOOR', r'\bHALEY', r'\bMVS IN MOTION\b', r'\bMOVES\b', r'\bSISSEL\b', r'\bTHERABAND\b', r'\bBLACKROLL\b', r'\bAIREX\b', r'\bTOGU\b', r'\bNAGADEGA\b'
    ]),
    ('igapäevaelu abivahend', [
        r'\bHAARATS\b', r'\bSOKIJALGAPAN', r'\bLUSIKAS\b', r'\bKAHVEL\b', r'\bNOAD\b', r'\bTALDRIK\b', r'\bTOPS\b', r'\bKRUUS\b', r'\bAVAJAD\b', r'\bLÕIKUR\b', r'\bTABLETI', r'\bNÖÖBI', r'\bLUGEMISPRILLID\b', r'\bLUUP\b', r'\bVALGUSTI\b', r'\bPRILLID\b', r'\bPATAREI\b', r'\bKUULDEAPARAAT\b', r'\bKÕRVATROPID\b', r'\bTERMOMEETER\b'
    ])
]


def clean_string(s: str) -> str:
    """Eemaldab HTML olemid ja üleliigsed sümbolid."""
    if not s:
        return ""
    t = html.unescape(s)
    t = re.sub(r'&#8211;', '–', t)
    t = re.sub(r'&#215;', '×', t)
    t = re.sub(r'[\r\n\t]+', ' ', t)
    t = re.sub(r'\s+', ' ', t).strip()
    t = re.sub(r'\s*[–\-,/]$', '', t).strip()
    return t


def run_cleanup():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()

    c.execute("SELECT * FROM tooteregister")
    records = [dict(r) for r in c.fetchall()]
    old_product_count = len(records)
    print(f"Old product count: {old_product_count}")

    # 1. Puhasta stringid ja eralda brändid/tootjad
    for r in records:
        r['official_product_name'] = clean_string(r['official_product_name'])
        try:
            aliases = json.loads(r['aliases']) if r['aliases'] else []
        except Exception:
            aliases = []
        aliases = [clean_string(a) for a in aliases if clean_string(a)]
        r['aliases'] = aliases

        # Kontrolli brändi
        full_text = f"{r['official_product_name']} {' '.join(aliases)}".upper()
        if r['brand'] == 'MÄÄRAMATA' or r['manufacturer'] == 'Määramata':
            for b_kw in sorted(BRAND_MAP.keys(), key=lambda x: -len(x)):
                if re.search(r'\b' + re.escape(b_kw.strip()) + r'\b', full_text):
                    b_brand, b_mfg = BRAND_MAP[b_kw]
                    r['brand'] = b_brand
                    r['manufacturer'] = b_mfg
                    break

        # Täpsusta kategooriat
        if r['product_type'] == 'muu abivahend':
            for cat_name, kw_patterns in CATEGORY_RULES:
                if any(re.search(p, full_text) for p in kw_patterns):
                    r['product_type'] = cat_name
                    break

        # Täpsusta product_family
        if r['brand'] != 'MÄÄRAMATA':
            if not r['product_family'] or r['product_family'] == 'Määramata' or r['product_family'].upper() in ['ELEKTRILINE RATASTOOL', 'MEMO LASTE', 'TALLATUGI PEDAG']:
                # Võta bränd ja järgmine oluline sõna
                fam_words = [w for w in r['official_product_name'].split() if w.upper() != r['brand'].upper()]
                if fam_words:
                    r['product_family'] = f"{r['brand'].title()} {fam_words[0].title()}"
                else:
                    r['product_family'] = r['brand'].title()

    # 2. Liida duplikaattooted ja variandid
    # Grupeeri kanoonilise tootenime ja brändi järgi
    groups = defaultdict(list)
    for r in records:
        clean_name = re.sub(r'[^A-Z0-9]', '', r['official_product_name'].upper())
        group_key = f"{r['brand'].upper()}::{clean_name}"
        groups[group_key].append(r)

    print(f"Distinct canonical groups: {len(groups)}")

    canonical_products = []
    for g_key, items in groups.items():
        primary = items[0]

        # Ühenda tarnijad
        all_suppliers = set()
        for it in items:
            for s in (it.get('source_supplier') or '').split(','):
                s_strip = s.strip()
                if s_strip:
                    all_suppliers.add(s_strip)
        unified_suppliers = ', '.join(sorted(all_suppliers))

        # Ühenda aliased
        all_aliases = set()
        for it in items:
            for a in it.get('aliases', []):
                all_aliases.add(a)

        # Vali parimad tehnilised parameetrid
        best_ml = next((it['ml_capacity'] for it in items if it['ml_capacity']), None)
        best_drop = next((it['drop_rating'] for it in items if it['drop_rating']), None)
        best_pkg = next((it['package_information'] for it in items if it['package_information']), None)
        best_type = next((it['product_type'] for it in items if it['product_type'] != 'muu abivahend'), primary['product_type'])
        best_family = next((it['product_family'] for it in items if it['product_family'] and it['product_family'] != 'Määramata'), primary['product_family'])
        best_url = next((it['source_url'] for it in items if it['source_url']), primary['source_url'])

        canonical_products.append({
            'manufacturer': primary['manufacturer'],
            'brand': primary['brand'],
            'product_family': best_family,
            'official_product_name': primary['official_product_name'],
            'aliases': list(all_aliases),
            'package_information': best_pkg,
            'ml_capacity': best_ml,
            'drop_rating': best_drop,
            'product_type': best_type,
            'source_supplier': unified_suppliers,
            'source_url': best_url,
            'created_at': primary.get('created_at', '')
        })

    new_product_count = len(canonical_products)
    print(f"New product count: {new_product_count}")

    # 3. Lahenda aliaste kollisioonid
    # Leia aliased, mis viitavad mitmele kanoonilisele tootele
    alias_to_prod_idx = defaultdict(set)
    for idx, p in enumerate(canonical_products):
        for a in p['aliases']:
            norm_a = re.sub(r'[^A-Z0-9]', '', a.upper())
            if norm_a:
                alias_to_prod_idx[norm_a].add(idx)

    colliding_alias_norms = {a for a, p_indices in alias_to_prod_idx.items() if len(p_indices) > 1}
    print(f"Colliding alias keys before resolution: {len(colliding_alias_norms)}")

    # Eemalda multi-product SKUd ja liiga üldised aliased, mis viitavad mitmele tootele
    cleaned_alias_count = 0
    for p in canonical_products:
        retained_aliases = []
        for a in p['aliases']:
            norm_a = re.sub(r'[^A-Z0-9]', '', a.upper())
            if norm_a in colliding_alias_norms:
                # Kui alias on SKU või lühike üldkood, eemalda see konfliktide lahendamiseks
                if re.match(r'^SKU\b', a, re.I) or len(norm_a) < 5 or norm_a == re.sub(r'[^A-Z0-9]', '', p['brand'].upper()):
                    cleaned_alias_count += 1
                    continue
                # Kui alias ei sisalda piisavalt unikaalset mudelit, eemalda
                cleaned_alias_count += 1
                continue
            retained_aliases.append(a)
        p['aliases'] = retained_aliases

    # Kontrolli kollisioone pärast puhastust
    alias_to_prod_idx_after = defaultdict(set)
    for idx, p in enumerate(canonical_products):
        for a in p['aliases']:
            norm_a = re.sub(r'[^A-Z0-9]', '', a.upper())
            if norm_a:
                alias_to_prod_idx_after[norm_a].add(idx)

    colliding_after = {a for a, p_indices in alias_to_prod_idx_after.items() if len(p_indices) > 1}
    print(f"Colliding alias keys after resolution: {len(colliding_after)}")

    # 4. Arvuta mõõdikud
    mfg_covered = sum(1 for p in canonical_products if p['manufacturer'] != 'Määramata')
    cat_specific = sum(1 for p in canonical_products if p['product_type'] != 'muu abivahend')

    dup_reduction = ((old_product_count - new_product_count) / old_product_count) * 100
    alias_conflict_reduction = ((len(colliding_alias_norms) - len(colliding_after)) / max(1, len(colliding_alias_norms))) * 100
    mfg_coverage = (mfg_covered / new_product_count) * 100
    cat_coverage = (cat_specific / new_product_count) * 100

    print("\n--- TULEMUSED ---")
    print(f"Vana toodete arv: {old_product_count}")
    print(f"Uus toodete arv: {new_product_count}")
    print(f"Duplikaatide vähenemine: {dup_reduction:.1f}%")
    print(f"Aliaste konfliktide vähenemine: {alias_conflict_reduction:.1f}%")
    print(f"Tootjate kaetus: {mfg_coverage:.1f}% ({mfg_covered}/{new_product_count})")
    print(f"Kategooriate kaetus (mitte 'muu'): {cat_coverage:.1f}% ({cat_specific}/{new_product_count})")


if __name__ == '__main__':
    run_cleanup()
