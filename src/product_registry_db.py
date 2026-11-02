"""
SQLite tooteregistri (tooteregister) liides ja optimeeritud päringuteenus.

Võimaldab:
1. Kiiret O(1) otsingut aliaste ja normaliseeritud nimede järgi
2. Brändipõhist kandidaatide filtreerimist
3. Riikliku klassifikaatori (Sotsiaalministeeriumi määrus nr 74) ISO koodide sidumist
4. Tooteregistri statistikat ja ülevaadet
"""

import sqlite3
import json
import os
import re
from typing import Dict, Any, List, Optional, Tuple
from src.normalizer import clean_text, normalize_name
from src.product_registry import MANUFACTURER_CATALOGUE

DEFAULT_DB_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "valideer.db")


def infer_iso_and_statutory_name(
    brand: str,
    name: str,
    p_type: str,
    ml: Optional[int] = None,
    drops: Optional[int] = None,
    size: Optional[str] = None
) -> Tuple[Optional[str], Optional[str]]:
    """Tuletab toote omaduste põhjal ametliku ISO koodi ja määrusejärgse nimetuse (Sotsiaalministeeriumi määrus nr 74)."""
    name_upper = (name or "").upper()
    type_lower = (p_type or "").lower()

    # 1. Meeste sidemed (eraldi ISO-koodid .11, .12, .13)
    is_men = bool(re.search(r'\b(MEN|MAN|MEESTE|MALE)\b', name_upper)) and not bool(re.search(r'\b(WOMEN|WOMAN|NAISTE|LADY)\b', name_upper))
    if is_men and any(x in type_lower for x in ["side", "pad", "inkontinentsiside"]):
        if ml:
            if ml <= 399:
                return "09.30.24.11", "inkontinentsisidemed meestele kuni 399 ml"
            elif 400 <= ml <= 599:
                return "09.30.24.12", "inkontinentsisidemed meestele 400 - 599 ml"
            else: # ml >= 600
                return "09.30.24.13", "inkontinentsisidemed meestele üle 600 ml"
        elif drops:
            if drops <= 2:
                return "09.30.24.11", "inkontinentsisidemed meestele kuni 399 ml"
            elif drops == 3:
                return "09.30.24.12", "inkontinentsisidemed meestele 400 - 599 ml"
            else:
                return "09.30.24.13", "inkontinentsisidemed meestele üle 600 ml"

    # 2. Naiste ja universaalsed inkontinentsisidemed (09.30.24.14 kuni .21)
    has_pad_name = (
        bool(re.search(r'\b(LADY|MINI|LIGHT|NORMAL|EXTRA|SUPER|MAXI)\b', name_upper)) or
        bool(re.search(r'\bSAN\s*([0-5]|1A)\b', name_upper)) or
        bool(re.search(r'\bPAD\s*([1-5]|1\.5)\b', name_upper))
    )
    if (any(x in type_lower for x in ["side", "pad", "inkontinentsiside"]) or has_pad_name) and not any(x in type_lower for x in ["püks", "pants", "pull-up", "slip", "vöö"]):
        if ml:
            if ml <= 299:
                return "09.30.24.14", "inkontinentsisidemed naistele 201- 299 ml"
            elif 300 <= ml <= 599:
                return "09.30.24.15", "inkontinentsisidemed naistele 300 - 599 ml"
            elif 600 <= ml <= 999:
                return "09.30.24.16", "inkontinentsisidemed naistele 600 - 999 ml"
            elif 1000 <= ml <= 1499:
                return "09.30.24.17", "inkontinentsisidemed naistele 1000 - 1499 ml"
            elif 1500 <= ml <= 1999:
                return "09.30.24.18", "inkontinentsisidemed naistele 1500 - 1999 ml"
            elif 2000 <= ml <= 2499:
                return "09.30.24.19", "inkontinentsisidemed naistele 2000 - 2499 ml"
            elif 2500 <= ml <= 2999:
                return "09.30.24.20", "inkontinentsisidemed naistele 2500 - 2999 ml"
            elif ml >= 3000:
                return "09.30.24.21", "inkontinentsisidemed naistele üle 3000 ml"

        # Mudelipõhine või tilgapõhine määramine, kui ml puudub
        if bool(re.search(r'\b(SAN\s*4|PAD\s*4)\b', name_upper)) or drops == 4:
            return "09.30.24.16", "inkontinentsisidemed naistele 600 - 999 ml"
        if bool(re.search(r'\b(SAN\s*3|PAD\s*3|LIGHT)\b', name_upper)) or drops == 3:
            return "09.30.24.15", "inkontinentsisidemed naistele 300 - 599 ml"
        if bool(re.search(r'\b(SAN\s*5|PAD\s*5)\b', name_upper)) or drops == 5:
            return "09.30.24.17", "inkontinentsisidemed naistele 1000 - 1499 ml"
        if drops == 2 or bool(re.search(r'\b(SAN\s*2|SAN\s*1|PAD\s*2|PAD\s*1)\b', name_upper)):
            return "09.30.24.14", "inkontinentsisidemed naistele 201- 299 ml"
        return "09.30.24.15", "inkontinentsisidemed naistele 300 - 599 ml"

    # 3. Vormmähkmed (09.30.24.22 kuni .29)
    is_vorm = any(x in type_lower for x in ["vorm", "vormmähe", "vormmähkmed"]) or bool(re.search(r'\bSAN\s*(6|7|8|9|10|11)\b', name_upper))
    if is_vorm and not any(x in type_lower for x in ["püks", "pants", "pull-up", "slip"]):
        if ml:
            if ml <= 299:
                return "09.30.24.22", "vormmähkmed 201- 299 ml"
            elif 300 <= ml <= 599:
                return "09.30.24.23", "vormmähkmed 300 - 599 ml"
            elif 600 <= ml <= 999:
                return "09.30.24.24", "vormmähkmed 600 - 999 ml"
            elif 1000 <= ml <= 1499:
                return "09.30.24.25", "vormmähkmed 1000 - 1499 ml"
            elif 1500 <= ml <= 1999:
                return "09.30.24.26", "vormmähkmed 1500 - 1999 ml"
            elif 2000 <= ml <= 2499:
                return "09.30.24.27", "vormmähkmed 2000 - 2499 ml"
            elif 2500 <= ml <= 2999:
                return "09.30.24.28", "vormmähkmed 2500 - 2999 ml"
            elif ml >= 3000:
                return "09.30.24.29", "vormmähkmed üle 3000 ml"

        if bool(re.search(r'\bSAN\s*(6|7)\b', name_upper)):
            return "09.30.24.26", "vormmähkmed 1500 - 1999 ml"
        if bool(re.search(r'\bSAN\s*(8|9|10)\b', name_upper)):
            return "09.30.24.28", "vormmähkmed 2500 - 2999 ml"
        if bool(re.search(r'\bSAN\s*11\b', name_upper)):
            return "09.30.24.29", "vormmähkmed üle 3000 ml"
        return "09.30.24.25", "vormmähkmed 1000 - 1499 ml"

    # Tuvasta suurus
    s_upper = (size or ("XXL" if "XXL" in name_upper else "XL" if "XL" in name_upper else "XS" if "XS" in name_upper else "S" if " S" in name_upper or "-S" in name_upper else "L" if " L" in name_upper or "-L" in name_upper else "M")).upper()

    # 4. Imavad püksid (pull-up / pants) - 09.30.24.81 kuni .96
    if any(x in type_lower for x in ["imavad püksid", "pants", "pull-up", "active"]) or ("PANTS" in name_upper or "MOBILE" in name_upper or "ACTIVE" in name_upper):
        if ml:
            if ml < 1400:
                if "XS" in s_upper or "S" in s_upper:
                    return "09.30.24.81", "imavad püksid kuni 1399 ml XS-S"
                elif "L" in s_upper and "XL" not in s_upper:
                    return "09.30.24.83", "imavad püksid kuni 1399 ml L"
                elif "XL" in s_upper:
                    return "09.30.24.84", "imavad püksid kuni 1399 ml XL"
                else:
                    return "09.30.24.82", "imavad püksid kuni 1399 ml M"
            elif 1400 <= ml <= 1699:
                if "XS" in s_upper or "S" in s_upper:
                    return "09.30.24.87", "imavad püksid 1400 - 1699 ml XS-S"
                elif "L" in s_upper and "XL" not in s_upper:
                    return "09.30.24.89", "imavad püksid 1400 - 1699 ml L"
                elif "XXL" in s_upper:
                    return "09.30.24.91", "imavad püksid 1400 - 1699 ml XXL"
                elif "XL" in s_upper:
                    return "09.30.24.90", "imavad püksid 1400 - 1699 ml XL"
                else:
                    return "09.30.24.88", "imavad püksid 1400 - 1699 ml M"
            else: # ml >= 1700
                if "XS" in s_upper or "S" in s_upper:
                    return "09.30.24.93", "imavad püksid üle 1700 ml XS-S"
                elif "L" in s_upper and "XL" not in s_upper:
                    return "09.30.24.95", "imavad püksid üle 1700 ml L"
                elif "XL" in s_upper or "XXL" in s_upper:
                    return "09.30.24.96", "imavad püksid üle 1700 ml XL - XXL"
                else:
                    return "09.30.24.94", "imavad püksid üle 1700 ml M"

        # Vaikimisi pants suurus M järgi
        return "09.30.24.88", "imavad püksid 1400 - 1699 ml M"

    # 5. Püksmähkmed (klassikalised avatud mähkmed / slip) - 09.30.24.30 kuni .54
    if any(x in type_lower for x in ["püksmähe", "püksmähkmed", "klassikaline", "slip"]) or "SLIP" in name_upper or "SUPREMFIT" in name_upper:
        if ml:
            if ml <= 1899:
                if "XS" in s_upper or "XXS" in s_upper:
                    return "09.30.24.30", "püksmähkmed kuni 1899 ml XXS-XS"
                elif "S" in s_upper:
                    return "09.30.24.31", "püksmähkmed kuni 1899 ml S"
                else:
                    return "09.30.24.32", "püksmähkmed kuni 1899 ml M"
            elif 1900 <= ml <= 2499:
                if "S" in s_upper and "XS" not in s_upper:
                    return "09.30.24.35", "püksmähkmed 1900 - 2499 ml S"
                elif "L" in s_upper and "XL" not in s_upper:
                    return "09.30.24.37", "püksmähkmed 1900 - 2499 ml L"
                elif "XL" in s_upper or "XXL" in s_upper:
                    return "09.30.24.38", "püksmähkmed 1900 - 2499 ml XL"
                else:
                    return "09.30.24.36", "püksmähkmed 1900 - 2499 ml M"
            elif 2500 <= ml <= 2999:
                if "S" in s_upper and "XS" not in s_upper:
                    return "09.30.24.41", "püksmähkmed 2500 - 2999 ml S"
                elif "L" in s_upper and "XL" not in s_upper:
                    return "09.30.24.43", "püksmähkmed 2500 - 2999 ml L"
                elif "XXL" in s_upper:
                    return "09.30.24.45", "püksmähkmed 2500 - 2999 ml XXL"
                elif "XL" in s_upper:
                    return "09.30.24.44", "püksmähkmed 2500 - 2999 ml XL"
                else:
                    return "09.30.24.42", "püksmähkmed 2500 - 2999 ml M"
            elif 3000 <= ml <= 3699:
                if "L" in s_upper and "XL" not in s_upper:
                    return "09.30.24.48", "püksmähkmed 3000 - 3699 ml L"
                elif "XL" in s_upper or "XXL" in s_upper:
                    return "09.30.24.49", "püksmähkmed 3000 - 3699 ml XL"
                else:
                    return "09.30.24.47", "püksmähkmed 3000 - 3699 ml M"
            else: # ml >= 3700
                if "L" in s_upper and "XL" not in s_upper:
                    return "09.30.24.53", "püksmähkmed üle 3700 ml L"
                elif "XL" in s_upper or "XXL" in s_upper:
                    return "09.30.24.54", "püksmähkmed üle 3700 ml XL"
                else:
                    return "09.30.24.52", "püksmähkmed üle 3700 ml M"

        return "09.30.24.36", "püksmähkmed 1900 - 2499 ml M"

    # 6. Vöömähkmed (09.30.24.55 kuni .78)
    if "vöö" in type_lower or any(w in name_upper for w in ["FLEX", "OPTIMA", "WING"]):
        if ml:
            if ml <= 1899:
                if "XS" in s_upper or "S" in s_upper:
                    return "09.30.24.55", "vöömähkmed kuni 1899 ml XS-S"
                elif "L" in s_upper:
                    return "09.30.24.59", "vöömähkmed kuni 1899 ml L"
                else:
                    return "09.30.24.58", "vöömähkmed kuni 1899 ml M"
            elif 1900 <= ml <= 2499:
                if "XS" in s_upper or "S" in s_upper:
                    return "09.30.24.62", "vöömähkmed 1900 - 2499 ml XS-S"
                elif "L" in s_upper:
                    return "09.30.24.64", "vöömähkmed 1900 - 2499 ml L"
                else:
                    return "09.30.24.63", "vöömähkmed 1900 - 2499 ml M"
            elif 2500 <= ml <= 2999:
                if "XS" in s_upper or "S" in s_upper:
                    return "09.30.24.67", "vöömähkmed 2500 - 2999 ml XS-S"
                elif "L" in s_upper and "XL" not in s_upper:
                    return "09.30.24.69", "vöömähkmed 2500 - 2999 ml L"
                elif "XL" in s_upper:
                    return "09.30.24.70", "vöömähkmed 2500 - 2999 ml XL"
                else:
                    return "09.30.24.68", "vöömähkmed 2500 - 2999 ml M"
            elif 3000 <= ml <= 3699:
                if "L" in s_upper and "XL" not in s_upper:
                    return "09.30.24.74", "vöömähkmed 3000 - 3699 ml L"
                elif "XL" in s_upper:
                    return "09.30.24.75", "vöömähkmed 3000 - 3699 ml XL"
                else:
                    return "09.30.24.73", "vöömähkmed 3000 - 3699 ml M"
            else: # ml >= 3700
                return "09.30.24.78", "vöömähkmed üle 3700 ml XL"

        return "09.30.24.63", "vöömähkmed 1900 - 2499 ml M"

    # Fikseerivad püksid
    if "fikseeriv" in type_lower or "fikseerivad" in type_lower:
        if "XXL" in s_upper:
            return "09.30.39.05", "püksid mähkmete fikseerimiseks XXL+"
        elif "XL" in s_upper:
            return "09.30.39.04", "püksid mähkmete fikseerimiseks XL"
        elif "L" in s_upper:
            return "09.30.39.03", "püksid mähkmete fikseerimiseks L"
        elif "S" in s_upper:
            return "09.30.39.01", "püksid mähkmete fikseerimiseks S"
        return "09.30.39.02", "püksid mähkmete fikseerimiseks M"

    # 7. Aluslinad ja voodikaitsed (09.30.00.01 kuni .06)
    if any(x in type_lower for x in ["lina", "voodikaitse", "bed mat", "underpad"]):
        if "40" in name_upper and "60" in name_upper:
            return "09.30.00.01", "ühekordsed imavad aluslinad 40 x 60 cm"
        elif "60" in name_upper and "90" in name_upper:
            return "09.30.00.03", "ühekordsed imavad aluslinad 60 x 90 cm"
        elif "60" in name_upper and ("60" in name_upper or "X60" in name_upper):
            return "09.30.00.02", "ühekordsed imavad aluslinad 60 x 60 cm"
        elif "210" in name_upper:
            return "09.30.00.05", "ühekordsed imavad aluslinad 70-90 x 210 cm"
        elif "140" in name_upper or "180" in name_upper:
            return "09.30.00.04", "ühekordsed imavad aluslinad 80-90 x 140-180 cm"
        return "09.30.00.03", "ühekordsed imavad aluslinad 60 x 90 cm"

    # 4. Ortoosid ja tallatoed
    if "ortoos" in type_lower or "tallatugi" in type_lower:
        if any(w in name_upper for w in ["TALLATUGI", "TALLATOED", "SISETALLAD", "POOLTALLAD", "JALATS", "SANDAAL", "KING"]):
            return "06.33.03", "individuaalsed tallatoed ja ortopeedilised jalatsid"
        elif any(w in name_upper for w in ["SELJA", "LUMBO", "VÖÖ"]):
            return "06.03.09", "seljaortoosid"
        elif any(w in name_upper for w in ["PÕLV", "GENU"]):
            return "06.12.06", "põlveortoosid"
        elif any(w in name_upper for w in ["RANNE", "KÄSI", "MANU"]):
            return "06.06.03", "randme- ja käeortoosid"
        elif any(w in name_upper for w in ["HÜPPE", "MALLEO"]):
            return "06.12.03", "hüppeliigeseortoosid"
        elif any(w in name_upper for w in ["KAEL", "KRAE"]):
            return "06.03.12", "kaelaortoosid"
        return "06.03.00", "ortoosid ja toed"

    # 5. Kompressioon
    if "kompressioon" in type_lower:
        return "04.06.06", "kompressioontooted (ravipõlvikud ja -sukad)"

    # 6. Liikumisabivahendid
    if "ratastool" in type_lower:
        if any(w in name_upper for w in ["ELEKTRILINE", "E60", "C40", "ROBOOTER", "PRIDE"]):
            return "12.23.03", "elektrilised ratastoolid"
        elif any(w in name_upper for w in ["AKTIIV", "PANTHERA", "ARIA"]):
            return "12.22.18", "aktiivratastoolid"
        return "12.22.03", "standardratastoolid"

    if "rulaator" in type_lower or "käimisraam" in type_lower:
        return "12.06.06", "rulaatorid ja käimisraamid"

    if "kark" in type_lower or "crutch" in type_lower:
        return "12.03.06", "küünarkargud"

    if "kepp" in type_lower or "cane" in type_lower:
        return "12.03.03", "kepid"

    if "kaldtee" in type_lower or "ramp" in type_lower:
        return "12.36.03", "teisaldatavad kaldteed ja rambid"

    # 7. Tualeti- ja vannitooted
    if "tualet" in type_lower or "vanni" in type_lower:
        if "kõrgendus" in name_upper or "korgendus" in name_upper:
            return "09.12.12", "tualetipoti kõrgendused ja käetoed"
        elif "duši" in name_upper or "vanni" in name_upper:
            return "09.33.03", "vanni- ja dušitoolid"
        return "09.12.03", "potitoolid ja tualetiabivahendid"

    # 8. Hooldusvoodid ja lamatiste ennetus
    if "voodi" in type_lower or "lamatis" in type_lower:
        if "madrats" in name_upper:
            return "04.33.06.01", "püsiva survejaotusega lamatisi ennetavad madratsid"
        elif "padi" in name_upper or "istmepadi" in name_upper:
            return "04.33.03.01", "istmepadjad lamatiste vältimiseks"
        elif "tõstuk" in name_upper or "raizer" in name_upper:
            return "12.36.03", "patsienditõstukid"
        return "18.12.10", "funktsionaalsed hooldusvoodid"

    # 9. Igapäevaelu abivahendid
    if "igapäev" in type_lower:
        if "haarats" in name_upper:
            return "24.09.06", "haaratsid"
        elif "prill" in name_upper or "luup" in name_upper:
            return "22.03.09", "luubid ja nägemise abivahendid"
        return "24.09.00", "igapäevaelu abivahendid"

    # 10. Nahahooldus ja hügieen (09.21.06 nahapesemisvahendid, 09.21.18 nahakaitsevahendid)
    if any(x in type_lower for x in ["nahahooldus", "nahapesu", "hügieen", "pesuvahend"]) or any(w in name_upper for w in ["TSINKSALV", "TSINKKREEM", "TSINKSPREI", "PESUVAHT", "PESUKREEM", "WASH MOUSSE", "WASH CREAM"]):
        if any(w in name_upper for w in ["TSINK", "TSINGI", "ZINC", "KAITSE", "BARRIER"]):
            return "09.21.18", "nahakaitsevahendid"
        elif any(w in name_upper for w in ["PESU", "WASH", "VAHT"]):
            return "09.21.06", "nahapesemisvahendid"
        return "09.21.18", "nahakaitsevahendid"

    # 11. Proteesi sisevoodrid (lainerid) (Sotsiaalministeeriumi määrus nr 74)
    if "lainer" in type_lower or "sisevooder" in type_lower or any(w in name_upper for w in ["LAINER", "ICEROSS", "GALEO", "SKEO"]):
        if any(w in name_upper for w in ["(TF)", " TF", "-TF", "TRANSFEMORAL", "REIE"]):
            return "06.24.41.08", "proteesi sisevoodrid (lainerid) põlve- ja reieproteesidele"
        elif any(w in name_upper for w in ["(TT)", " TT", "-TT", "TRANSTIBIAL", "SÄÄRE"]):
            return "06.24.41.07", "proteesi sisevoodrid (lainerid) sääreproteesidele"
        elif any(w in name_upper for w in ["KÄE", "UPPER", "ÜLAJÄSE"]):
            return "06.18.00.02", "proteesi sisevoodrid (lainerid) ülajäsemeproteesidele"
        return "06.24.41.07", "proteesi sisevoodrid (lainerid) sääreproteesidele"

    # 12. Kuulmisabivahendid (CROS heliülekandesüsteemid)
    if "cros" in name_upper or "cros" in type_lower:
        return "22.06.15.05", "teise kõrva heli ülekande süsteemid (CROS)"

    return None, None


class ProductRegistryDB:
    def __init__(self, db_path: str = DEFAULT_DB_PATH):
        self.db_path = db_path
        self._products: List[Dict[str, Any]] = []
        self._alias_to_product: Dict[str, Dict[str, Any]] = {}
        self._brand_to_products: Dict[str, List[Dict[str, Any]]] = {}
        self._loaded = False
        self._load()

    def _load(self):
        """Laeb tooteregistri SQLite tabelist mällu ja seob ametliku klassifikaatori andmetega."""
        self._products = []
        self._alias_to_product = {}
        self._brand_to_products = {}

        # 1. Laadi esmalt baaskataloog (MANUFACTURER_CATALOGUE) tootjate täpsete spetsifikatsioonidega
        for p in MANUFACTURER_CATALOGUE:
            item = dict(p)
            item['source_supplier'] = "Ametlik tootja kataloog"
            self._register_product(item)

        # 2. Laadi SQLite tooteregister (kui olemas)
        if os.path.exists(self.db_path):
            conn = sqlite3.connect(self.db_path, timeout=30.0)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='tooteregister';")
            if cursor.fetchone():
                cursor.execute("""
                    SELECT id, manufacturer, brand, product_family, official_product_name,
                           aliases, package_information, ml_capacity, drop_rating,
                           product_type, source_supplier, source_url
                    FROM tooteregister;
                """)
                rows = cursor.fetchall()
                for row in rows:
                    p = dict(row)
                    try:
                        aliases_list = json.loads(p['aliases']) if p['aliases'] else []
                    except Exception:
                        aliases_list = []
                    p['aliases'] = aliases_list
                    p['official_name'] = p['official_product_name']
                    p['full_name'] = f"{p['manufacturer']} {p['official_product_name']}"
                    p['product_line'] = p['product_family']
                    p['absorption_ml'] = p['ml_capacity']
                    p['drops'] = p['drop_rating']
                    p['category_type'] = p['product_type']

                    iso, stat = infer_iso_and_statutory_name(
                        p['brand'], p['official_product_name'], p['product_type'],
                        p['ml_capacity'], p['drop_rating']
                    )
                    p['suggested_iso'] = iso
                    p['suggested_statutory_name'] = stat

                    self._register_product(p)
            conn.close()

        self._loaded = True

    def _register_product(self, p: Dict[str, Any]):
        """Indekseerib toote ja selle aliased O(1) otsinguks."""
        self._products.append(p)

        norm_official = normalize_name(p['official_name'])
        self._alias_to_product[norm_official] = p
        
        clean_canon = re.sub(r'[^A-Z0-9]', '', norm_official)
        if clean_canon:
            self._alias_to_product[clean_canon] = p

        for alias in p.get('aliases', []):
            norm_al = normalize_name(alias)
            self._alias_to_product[norm_al] = p
            clean_al = re.sub(r'[^A-Z0-9]', '', norm_al)
            if clean_al:
                self._alias_to_product[clean_al] = p

        b_key = p['brand'].upper()
        if b_key not in self._brand_to_products:
            self._brand_to_products[b_key] = []
        self._brand_to_products[b_key].append(p)

    def get_all_products(self) -> List[Dict[str, Any]]:
        return self._products

    def get_by_brand(self, brand: str) -> List[Dict[str, Any]]:
        return self._brand_to_products.get(brand.upper(), [])

    def find_exact_alias(self, raw_or_norm_name: str) -> Optional[Dict[str, Any]]:
        """Otsib O(1) kiirusega täpset aliaset."""
        norm = normalize_name(raw_or_norm_name)
        if norm in self._alias_to_product:
            return self._alias_to_product[norm]
            
        clean = re.sub(r'[^A-Z0-9]', '', norm)
        if clean in self._alias_to_product:
            return self._alias_to_product[clean]

        return None

    def get_statistics(self) -> Dict[str, Any]:
        """Tagastab tooteregistri koondstatistika."""
        if not os.path.exists(self.db_path):
            return {
                "total_products": len(self._products),
                "manufacturers_count": 5,
                "top_manufacturers": [],
                "categories": [],
                "suppliers": [],
                "cross_supplier_count": 0
            }

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("SELECT count(*) FROM tooteregister;")
        total_products = cursor.fetchone()[0]

        cursor.execute("SELECT count(DISTINCT manufacturer) FROM tooteregister WHERE manufacturer != 'Määramata';")
        mfg_count = cursor.fetchone()[0]

        cursor.execute("SELECT manufacturer, count(*) FROM tooteregister WHERE manufacturer != 'Määramata' GROUP BY manufacturer ORDER BY count(*) DESC LIMIT 15;")
        top_mfgs = cursor.fetchall()

        cursor.execute("SELECT product_type, count(*) FROM tooteregister GROUP BY product_type ORDER BY count(*) DESC;")
        categories = cursor.fetchall()

        cursor.execute("SELECT source_supplier, count(*) FROM tooteregister GROUP BY source_supplier ORDER BY count(*) DESC LIMIT 10;")
        suppliers = cursor.fetchall()

        cursor.execute("SELECT count(*) FROM tooteregister WHERE source_supplier LIKE '%,%';")
        cross_supplier_count = cursor.fetchone()[0]

        conn.close()

        return {
            "total_products": total_products,
            "manufacturers_count": mfg_count,
            "top_manufacturers": top_mfgs,
            "categories": categories,
            "suppliers": suppliers,
            "cross_supplier_count": cross_supplier_count
        }


_REGISTRY_INSTANCE: Optional[ProductRegistryDB] = None

def get_product_registry_db() -> ProductRegistryDB:
    global _REGISTRY_INSTANCE
    if _REGISTRY_INSTANCE is None:
        _REGISTRY_INSTANCE = ProductRegistryDB()
    return _REGISTRY_INSTANCE
