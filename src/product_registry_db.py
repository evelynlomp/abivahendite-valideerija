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


ID_BRAND_VALID_RE = re.compile(
    r"\b(?:ONTEX\s+ID|ID\s+(?:PANTS|SLIP|EXPERT|LIGHT|COMFY|FORM|SOFT|CARE|BELT|GREEN|PROTECT|INTIME|FOR\s+MEN|MEN|LADY|JUNIOR|ALUSLINA|MÄHE|MÄHKMED|LASTEMÄHE|IMAV|SIDEMED|VÖÖMÄHE))\b",
    re.IGNORECASE
)


def extract_size_token(name_upper: str, size: Optional[str] = None) -> str:
    """Tuvastab tootenimest suuruse tähise (sh M1-M4, L1-L4, XL1-XL4, S/M, LARGE jne)."""
    if size:
        return size.upper()
    if re.search(r"\bS\s*/\s*M\b", name_upper):
        return "M"
    if re.search(r"\bL\s*/\s*XL\b", name_upper):
        return "L"
    m = re.search(r"\b(XXXL|XXL|XL|XXS|XS|S|M|L)[0-9]?\b", name_upper)
    if m:
        return m.group(1).upper()
    if "EXTRA LARGE" in name_upper or "X-LARGE" in name_upper:
        return "XL"
    if "LARGE" in name_upper:
        return "L"
    if "MEDIUM" in name_upper:
        return "M"
    if "SMALL" in name_upper:
        return "S"
    return "M"


def infer_iso_and_statutory_name(
    brand: str,
    name: str,
    p_type: str,
    ml: Optional[int] = None,
    drops: Optional[int] = None,
    size: Optional[str] = None
) -> Tuple[Optional[str], Optional[str]]:
    """Tuletab toote omaduste põhjal ametliku ISO koodi ja määrusejärgse nimetuse (Sotsiaalministeeriumi määrus nr 74)."""
    name_upper = normalize_name(name or "")
    raw_upper = (name or "").upper()
    type_lower = (p_type or "").lower()
    combined_upper = f"{name_upper} {type_lower.upper()}"

    # 0A. Kuulmisabivahendite individuaalsed otsakud (22.06.12.04) ja Cochlear tarvikud (22.06.21.03)
    if re.search(r"\b(INDIVIDUAALNE|INDIV\.?|IND\.?)\s*(KÕRVAOTSIK|KÕRVAOTSAK|OTSAK|OTSIK|RIE\s+OTSIK|RIE\s+OTSAK)\b", raw_upper):
        return "22.06.12.04", "kuuldeaparaadi individuaalsed otsakud"
    if any(w in raw_upper for w in ["KUIVATUSBRIKET", "DRY BRIKETT", "DRY-BRIK", "MIKROFONI KATTED", "SAATJAPOOL"]):
        return "22.06.21.03", "kuulmisimplantaadi kõneprotsessorite varuosad"

    # 0B. Niisutatud salvrätid (09.33.30.01), pesukindad (09.33.30.02), peapesumütsid (09.33.30.03)
    if any(w in combined_upper for w in ["PEAPESUMÜTS", "JUUSTEPESUMÜTS", "PESUMÜTS", "SHAMPOO CAP"]):
        return "09.33.30.03", "peapesumütsid"
    if any(w in combined_upper for w in ["PESUKINNAS", "PESUKINDAD", "WASHGLOVE", "WASH GLOVE", "WASH CLOVE"]):
        return "09.33.30.02", "pesukindad"
    if any(w in combined_upper for w in [
        "SALVRÄT", "NIISUTATUD", "WET WIPES", "WET WIPE", "MOIST WIPES",
        "PUHASTUSRÄTIK", "PUHASTUSLAPID", "PESULAPID", "PESUSVAMM", "NIISKED INTIIM"
    ]) and not any(w in combined_upper for w in ["CPAP", "PÜRDOX", "PURDOUX"]):
        return "09.33.30.01", "niisutatud salvrätid"

    # Kui tootenimes endas on täpne ml (nt '2394ml', '1045ml', '267ml'), eelista seda üldisele registri ml-ile
    m_ml = re.search(r"\b(\d{3,4})\s*ML\b", raw_upper)
    if m_ml:
        ml = int(m_ml.group(1))
    m_dr = re.search(r"\b(\d+(?:[,\.]5)?)\s*(?:TILKA?|DROPS?)\b", raw_upper)
    if m_dr and drops is None:
        drops = int(float(m_dr.group(1).replace(",", ".")))

    # 0C. Veekindlad madratsikatted ja pestavad aluslinad (09.30.45)
    is_underpad = bool(re.search(r"\b(ALUSLINA|ALUSLINAD|VOODIKAITSE|VOODIKATE|MADRATSIKATE|MADRATSIKAITSE|BED\s*MAT|TENA\s+BED|ABRI\s*SOFT|SENI\s+SOFT|UNDERPAD|PROTECT\s+PLUS)\b", combined_upper))
    if any(w in combined_upper for w in ["MADRATSIKATE", "MADRATSIKAITSE", "BED MAT TEXTILE"]) or (
        is_underpad and (
            any(w in combined_upper for w in ["PESTAV", "KORDUVKASUTATAV", "TEXTILE"]) or
            bool(re.search(r"\b(75X85|85X75|85X90|90X85|70X90|90X70|75X90|90X75)\b", name_upper))
        )
    ):
        return "09.30.45", "veekindlad madratsikatted, sh pestavad aluslinad"

    # 0D. Ühekordsed imavad aluslinad (09.30.00.01 kuni .06) - kontrollitakse ENNE sidemeid, et 'Bed Plus/Normal/Super' ei läheks sidemeteks
    if is_underpad:
        if re.search(r"\b(40X60|60X40)\b", name_upper):
            return "09.30.00.01", "ühekordsed imavad aluslinad 40 x 60 cm"
        if re.search(r"\b60X60\b", name_upper):
            return "09.30.00.02", "ühekordsed imavad aluslinad 60 x 60 cm"
        if re.search(r"\b(60X90|90X60)\b", name_upper):
            return "09.30.00.03", "ühekordsed imavad aluslinad 60 x 90 cm"
        if re.search(r"\b(80X90|90X80)\b", name_upper):
            return "09.30.00.06", "ühekordsed imavad aluslinad 80 x 90 cm"
        if re.search(r"\b(70X210|80X210|90X210|210X90|210X80|210X70|210)\b", name_upper):
            return "09.30.00.05", "ühekordsed imavad aluslinad 70-90 x 210 cm"
        if re.search(r"\b(80X140|80X170|80X180|85X180|90X170|90X180|180X80|180X85|180X90|170X90|140|170|180|WINGS|TIIBAD)\b", name_upper):
            return "09.30.00.04", "ühekordsed imavad aluslinad 80-90 x 140-180 cm"
        return "09.30.00.03", "ühekordsed imavad aluslinad 60 x 90 cm"

    # Tuvasta suurus varakult
    s_upper = extract_size_token(name_upper, size)

    # 0E. Fikseerivad püksid (09.30.39.01 kuni .05) - kontrollitakse ENNE imavaid pükse, et 'Fixpants' ei läheks 'Pants' alla
    if any(w in combined_upper for w in ["FIKSEERIV", "FIXPANTS", "ABRI FIX", "ABENA FIX", "TENA FIX", "SENI FIX", "VÕRKPÜKSID"]):
        if "XXL" in s_upper or "XXXL" in s_upper:
            return "09.30.39.05", "püksid mähkmete fikseerimiseks XXL+"
        elif "XL" in s_upper:
            return "09.30.39.04", "püksid mähkmete fikseerimiseks XL"
        elif "L" in s_upper:
            return "09.30.39.03", "püksid mähkmete fikseerimiseks L"
        elif "S" in s_upper or "XS" in s_upper:
            return "09.30.39.01", "püksid mähkmete fikseerimiseks S"
        return "09.30.39.02", "püksid mähkmete fikseerimiseks M"

    # 0F. Laste mähkmed ja imavad püksid (09.30.24.09 ja 09.30.24.10)
    if any(w in combined_upper for w in ["BAMBO DREAMY", "DRYNITES", "DRY NITES", "LASTE IMAVAD PÜKSID", "LASTEMÄHE", "JUNIOR"]) or (
        "BAMBO" in combined_upper and any(w in combined_upper for w in ["DREAMY", "NIGHT PANTS", "PÜKSID"])
    ):
        if any(w in combined_upper for w in ["35", "50", "57", "8 15", "XXL", "L XL"]):
            return "09.30.24.10", "laste imavad püksid 27 - 57 kg"
        return "09.30.24.09", "laste imavad püksid XL 15 - 30 kg"

    # 1. Meeste sidemed (eraldi ISO-koodid .11, .12, .13)
    is_men = bool(re.search(r'\b(MEN|MAN|MEESTE|MALE)\b', name_upper)) and not bool(re.search(r'\b(WOMEN|WOMAN|NAISTE|LADY|PANTS|MOBILE|PÜKSID)\b', name_upper))
    if is_men and (any(x in type_lower for x in ["side", "pad", "inkontinentsiside"]) or any(w in name_upper for w in ["MEN", "PAD", "LEVEL", "GUARD", "SHIELD"])):
        if ml:
            if ml <= 399:
                return "09.30.24.11", "inkontinentsisidemed meestele kuni 399 ml"
            elif 400 <= ml <= 599:
                return "09.30.24.12", "inkontinentsisidemed meestele 400 - 599 ml"
            else: # ml >= 600
                return "09.30.24.13", "inkontinentsisidemed meestele üle 600 ml"
        elif drops:
            if drops <= 2 or "LEVEL 1" in name_upper:
                return "09.30.24.11", "inkontinentsisidemed meestele kuni 399 ml"
            elif drops in (3, 4) or "LEVEL 2" in name_upper:
                return "09.30.24.12", "inkontinentsisidemed meestele 400 - 599 ml"
            else:
                return "09.30.24.13", "inkontinentsisidemed meestele üle 600 ml"
        if "LEVEL 3" in name_upper or "SUPER" in name_upper:
            return "09.30.24.13", "inkontinentsisidemed meestele üle 600 ml"
        if "LEVEL 2" in name_upper:
            return "09.30.24.12", "inkontinentsisidemed meestele 400 - 599 ml"
        if "LEVEL 1" in name_upper:
            return "09.30.24.11", "inkontinentsisidemed meestele kuni 399 ml"

    # 2. Naiste ja universaalsed inkontinentsisidemed (09.30.24.14 kuni .21)
    has_pad_name = (
        bool(re.search(r'\b(LADY|DISCREET|COMFORT\s+MINI)\b', name_upper)) or
        bool(re.search(r'\bSAN\s*([0-4]|1A|3A)\b', name_upper)) or
        bool(re.search(r'\bPAD\s*([1-5]|1\.5)\b', name_upper))
    )
    is_not_diaper = not any(x in name_upper for x in [
        "PÜKS", "PANTS", "PULL-UP", "MOBILE", "ACTIVE", "SLIP", "ELASTIC", "FLEX", "OPTIMA", "WING", "FORM"
    ]) and ("COMFORT MINI" in name_upper or "COMFORT" not in name_upper)
    if (any(x in type_lower for x in ["side", "pad", "inkontinentsiside"]) or has_pad_name) and is_not_diaper:
        if bool(re.search(r'\bPAD\s*5\b', name_upper)) and (not ml or ml == 900):
            return "09.30.24.17", "inkontinentsisidemed naistele 1000 - 1499 ml"
        if bool(re.search(r'\bPAD\s*1\.5\b', name_upper)) or "1.5" in name_upper:
            return "09.30.24.14", "inkontinentsisidemed naistele 201- 299 ml"
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
        if bool(re.search(r'\b(SAN\s*5|PAD\s*5)\b', name_upper)) or drops == 5:
            return "09.30.24.17", "inkontinentsisidemed naistele 1000 - 1499 ml"
        if bool(re.search(r'\b(SAN\s*4|PAD\s*4|MAXI|EXTRA\s+PLUS|COMFORT\s+MINI\s+SUPER)\b', name_upper)) or drops == 4:
            return "09.30.24.16", "inkontinentsisidemed naistele 600 - 999 ml"
        if bool(re.search(r'\b(SAN\s*3|PAD\s*3|NORMAL|EXTRA)\b', name_upper)) or drops == 3:
            return "09.30.24.15", "inkontinentsisidemed naistele 300 - 599 ml"
        if drops in (1, 2) or bool(re.search(r'\b(SAN\s*2|SAN\s*1|PAD\s*2|PAD\s*1|MINI|SLIM\s+MINI|SLIM\s+ULTRA\s+MINI)\b', name_upper)):
            return "09.30.24.14", "inkontinentsisidemed naistele 201- 299 ml"
        return "09.30.24.15", "inkontinentsisidemed naistele 300 - 599 ml"

    # 3. Vormmähkmed (09.30.24.22 kuni .29)
    is_vorm = (any(x in type_lower for x in ["vorm", "vormmähe", "vormmähkmed"]) or bool(re.search(r'\b(SAN\s*(5|6|7|8|9|10|11)|MOLICARE\s+FORM|SENI\s+SAN|ID\s+EXPERT\s+FORM|TENA\s+COMFORT)\b', name_upper))) and "COMFORT MINI" not in name_upper
    if is_vorm and not any(x in name_upper for x in ["PÜKS", "PANTS", "PULL-UP", "SLIP", "ELASTIC"]):
        if bool(re.search(r'\bSAN\s*9\b', name_upper)):
            return "09.30.24.28", "vormmähkmed 2500 - 2999 ml"
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
        if bool(re.search(r'\bSAN\s*8\b', name_upper)):
            return "09.30.24.27", "vormmähkmed 2000 - 2499 ml"
        if bool(re.search(r'\bSAN\s*10\b', name_upper)):
            return "09.30.24.28", "vormmähkmed 2500 - 2999 ml"
        if bool(re.search(r'\bSAN\s*11\b', name_upper)):
            return "09.30.24.29", "vormmähkmed üle 3000 ml"
        return "09.30.24.25", "vormmähkmed 1000 - 1499 ml"

    # 4. Imavad püksid (pull-up / pants) - 09.30.24.81 kuni .96
    if (
        any(x in type_lower for x in ["imavad püksid", "pants", "pull-up", "active"])
        or any(w in name_upper for w in ["PANTS", "MOBILE", "SENI ACTIVE", "ABRI FLEX", "PÜKSID", "SILHOUETTE"])
    ) and "ELASTIC" not in name_upper and "SLIP" not in name_upper:
        # Kui ml puudub, tuleta seeria tasemest (nt M1/L1/XL1 -> <1400ml, M2/L2/Plus/6 tilka -> 1400-1699ml, M3/L3/Super/Maxi/8-10 tilka -> >=1700ml)
        eff_ml = ml
        if not eff_ml:
            if re.search(r"\b(XXS|XS|S|M|L|XL|XXL)1\b", name_upper) or any(w in name_upper for w in ["NORMAL", "DISCREET", "LIGHT", "5 DROPS", "5 TILKA"]):
                eff_ml = 1200
            elif re.search(r"\b(XXS|XS|S|M|L|XL|XXL)[34]\b", name_upper) or any(w in name_upper for w in ["MAXI", "SUPER", "NIGHT", "8 DROPS", "8 TILKA", "10 DROPS", "10 TILKA"]):
                eff_ml = 2000
            else:
                eff_ml = 1500

        if eff_ml < 1400:
            if s_upper in ("XXS", "XS", "S"):
                return "09.30.24.81", "imavad püksid kuni 1399 ml XS-S"
            elif s_upper == "L":
                return "09.30.24.83", "imavad püksid kuni 1399 ml L"
            elif s_upper in ("XL", "XXL", "XXXL"):
                return "09.30.24.84", "imavad püksid kuni 1399 ml XL"
            else:
                return "09.30.24.82", "imavad püksid kuni 1399 ml M"
        elif 1400 <= eff_ml <= 1699:
            if s_upper in ("XXS", "XS", "S"):
                return "09.30.24.87", "imavad püksid 1400 - 1699 ml XS-S"
            elif s_upper == "L":
                return "09.30.24.89", "imavad püksid 1400 - 1699 ml L"
            elif s_upper in ("XXL", "XXXL"):
                return "09.30.24.91", "imavad püksid 1400 - 1699 ml XXL"
            elif s_upper == "XL":
                return "09.30.24.90", "imavad püksid 1400 - 1699 ml XL"
            else:
                return "09.30.24.88", "imavad püksid 1400 - 1699 ml M"
        else: # eff_ml >= 1700
            if s_upper in ("XXS", "XS", "S"):
                return "09.30.24.93", "imavad püksid üle 1700 ml XS-S"
            elif s_upper == "L":
                return "09.30.24.95", "imavad püksid üle 1700 ml L"
            elif s_upper in ("XL", "XXL", "XXXL"):
                return "09.30.24.96", "imavad püksid üle 1700 ml XL - XXL"
            else:
                return "09.30.24.94", "imavad püksid üle 1700 ml M"

    # 5. Püksmähkmed (klassikalised avatud mähkmed / slip / MoliCare Elastic / Abri-Form) - 09.30.24.30 kuni .54
    if any(x in type_lower for x in ["püksmähe", "püksmähkmed", "klassikaline", "slip"]) or any(w in name_upper for w in ["SLIP", "SUPREMFIT", "MOLICARE ELASTIC", "ABRI FORM"]):
        eff_ml = ml
        if not eff_ml:
            if drops == 10 or any(w in name_upper for w in ["ULTIMA", "TRIO", "10 DROPS", "10 TILKA"]) or re.search(r"\b(S|M|L|XL)4\b", name_upper):
                eff_ml = 3800
            elif drops in (8, 9) or any(w in name_upper for w in ["MAXI", "SUPER PLUS", "8 DROPS", "8 TILKA", "9 DROPS", "9 TILKA"]) or re.search(r"\b(S|M|L|XL)3\b", name_upper):
                eff_ml = 3100
            elif drops == 7 or any(w in name_upper for w in ["SUPER", "7 DROPS", "7 TILKA"]) or re.search(r"\b(S|M|L|XL)2\b", name_upper):
                eff_ml = 2600
            elif drops in (4, 5) or re.search(r"\b(XS|S|M|L|XL)1\b", name_upper):
                eff_ml = 1600
            else:
                eff_ml = 2100

        if eff_ml <= 1899:
            if s_upper in ("XXS", "XS"):
                return "09.30.24.30", "püksmähkmed kuni 1899 ml XXS-XS"
            elif s_upper == "S":
                return "09.30.24.31", "püksmähkmed kuni 1899 ml S"
            elif s_upper == "L":
                return "09.30.24.37", "püksmähkmed 1900 - 2499 ml L"
            elif s_upper in ("XL", "XXL"):
                return "09.30.24.38", "püksmähkmed 1900 - 2499 ml XL"
            else:
                return "09.30.24.32", "püksmähkmed kuni 1899 ml M"
        elif 1900 <= eff_ml <= 2499:
            if s_upper in ("XXS", "XS", "S"):
                return "09.30.24.35", "püksmähkmed 1900 - 2499 ml S"
            elif s_upper == "L":
                return "09.30.24.37", "püksmähkmed 1900 - 2499 ml L"
            elif s_upper in ("XL", "XXL"):
                return "09.30.24.38", "püksmähkmed 1900 - 2499 ml XL"
            else:
                return "09.30.24.36", "püksmähkmed 1900 - 2499 ml M"
        elif 2500 <= eff_ml <= 2999:
            if s_upper in ("XXS", "XS", "S"):
                return "09.30.24.41", "püksmähkmed 2500 - 2999 ml S"
            elif s_upper == "L":
                return "09.30.24.43", "püksmähkmed 2500 - 2999 ml L"
            elif s_upper in ("XXL", "XXXL"):
                return "09.30.24.45", "püksmähkmed 2500 - 2999 ml XXL"
            elif s_upper == "XL":
                return "09.30.24.44", "püksmähkmed 2500 - 2999 ml XL"
            else:
                return "09.30.24.42", "püksmähkmed 2500 - 2999 ml M"
        elif 3000 <= eff_ml <= 3699:
            if s_upper in ("XXS", "XS", "S"):
                return "09.30.24.41", "püksmähkmed 2500 - 2999 ml S"
            elif s_upper == "L":
                return "09.30.24.48", "püksmähkmed 3000 - 3699 ml L"
            elif s_upper in ("XXL", "XXXL"):
                return "09.30.24.49", "püksmähkmed 3000 - 3699 ml XL"
            elif s_upper == "XL":
                return "09.30.24.49", "püksmähkmed 3000 - 3699 ml XL"
            else:
                return "09.30.24.47", "püksmähkmed 3000 - 3699 ml M"
        else: # eff_ml >= 3700
            if s_upper == "L":
                return "09.30.24.53", "püksmähkmed üle 3700 ml L"
            elif s_upper in ("XL", "XXL", "XXXL"):
                return "09.30.24.54", "püksmähkmed üle 3700 ml XL"
            else:
                return "09.30.24.52", "püksmähkmed üle 3700 ml M"

    # 6. Vöömähkmed (09.30.24.55 kuni .78)
    if "vöö" in type_lower or any(w in name_upper for w in ["TENA FLEX", "SENI OPTIMA", "ABENA WING", "ABRI WING", "ID EXPERT BELT"]):
        if ml:
            if ml <= 1899:
                if s_upper in ("XXS", "XS", "S"):
                    return "09.30.24.55", "vöömähkmed kuni 1899 ml XS-S"
                elif s_upper == "L":
                    return "09.30.24.59", "vöömähkmed kuni 1899 ml L"
                else:
                    return "09.30.24.58", "vöömähkmed kuni 1899 ml M"
            elif 1900 <= ml <= 2499:
                if s_upper in ("XXS", "XS", "S"):
                    return "09.30.24.62", "vöömähkmed 1900 - 2499 ml XS-S"
                elif s_upper == "L":
                    return "09.30.24.64", "vöömähkmed 1900 - 2499 ml L"
                elif s_upper in ("XL", "XXL"):
                    return "09.30.24.70", "vöömähkmed 2500 - 2999 ml XL"
                else:
                    return "09.30.24.63", "vöömähkmed 1900 - 2499 ml M"
            elif 2500 <= ml <= 2999:
                if s_upper in ("XXS", "XS", "S"):
                    return "09.30.24.67", "vöömähkmed 2500 - 2999 ml XS-S"
                elif s_upper == "L":
                    return "09.30.24.69", "vöömähkmed 2500 - 2999 ml L"
                elif s_upper in ("XL", "XXL"):
                    return "09.30.24.70", "vöömähkmed 2500 - 2999 ml XL"
                else:
                    return "09.30.24.68", "vöömähkmed 2500 - 2999 ml M"
            elif 3000 <= ml <= 3699:
                if s_upper == "L":
                    return "09.30.24.74", "vöömähkmed 3000 - 3699 ml L"
                elif s_upper in ("XL", "XXL"):
                    return "09.30.24.75", "vöömähkmed 3000 - 3699 ml XL"
                else:
                    return "09.30.24.73", "vöömähkmed 3000 - 3699 ml M"
            else: # ml >= 3700
                return "09.30.24.78", "vöömähkmed üle 3700 ml XL"

        return "09.30.24.63", "vöömähkmed 1900 - 2499 ml M"

    # 7. Liikumisabivahendid (rulaatorid ja käimisraamid enne ortoose, et 'tugiraam' ei läheks 'ortoos' alla)
    if any(x in type_lower for x in ["rulaator", "käimisraam", "tugiraam"]) or any(w in name_upper for w in ["RULAATOR", "KÄIMISRAAM", "TUGIRAAM", "ROLLATOR"]):
        if any(w in name_upper for w in ["KÄIMISRAAM", "TUGIRAAM"]) and "RULAATOR" not in name_upper and "ROLLATOR" not in name_upper:
            return "12.06.03", "käimisraamid"
        return "12.06.06", "rulaatorid"

    if any(w in name_upper for w in ["JALUTUSKEPP", "KEPP"]):
        return "12.03.03", "käimiskepid"

    # 8. Ortoosid ja ortopeedilised jalatsid
    if "ortoos" in type_lower or "tallatugi" in type_lower:
        if any(w in name_upper for w in ["JALATS", "SANDAAL", "KING"]):
            return "06.33.00.02", "ortopeedilised jalatsid - kategooria II (täiskasvanute ortopeedilised jalatsid)"
        return None, None

    # 5. Kompressioon (ei kuulu määruse nr 74 klassifikaatorisse)
    if "kompressioon" in type_lower:
        return None, None

    # 6. Liikumisabivahendid
    if "ratastool" in type_lower:
        if any(w in name_upper for w in ["ELEKTRILINE", "E60", "C40", "ROBOOTER", "PRIDE"]):
            return "12.23.06.01", "elektrilised ratastoolid - aktiivsusgrupp I"
        elif any(w in name_upper for w in ["AKTIIV", "PANTHERA", "ARIA"]):
            return "12.22.03.02", "kahekäeratastoolid - aktiivsusgrupp II"
        return "12.22.03.01", "kahekäeratastoolid - aktiivsusgrupp I"

    if "rulaator" in type_lower or "käimisraam" in type_lower:
        return "12.06.06", "rulaatorid"

    if "kark" in type_lower or "crutch" in type_lower:
        return "12.03.06", "küünarkargud"

    if "kepp" in type_lower or "cane" in type_lower:
        return "12.03.03", "käimiskepid"

    if "kaldtee" in type_lower or "ramp" in type_lower:
        return "18.30.15", "kaasaskantavad kaldteed"

    # 7. Tualeti- ja vannitooted
    if "tualet" in type_lower or "vanni" in type_lower:
        if "KÕRGENDUS" in name_upper or "KORGENDUS" in name_upper:
            return "09.12.15", "potikõrgendused"
        elif "DUŠI" in name_upper or "VANNI" in name_upper:
            return "09.33.03", "vanni- ja dušitoolid"
        return "09.12.03.01", "tualetitoolid"

    # 8. Hooldusvoodid ja lamatiste ennetus
    if "voodi" in type_lower or "lamatis" in type_lower:
        if "MADRATS" in name_upper:
            return "04.33.06.01", "püsiva survejaotusega lamatisi ennetavad madratsid"
        elif "PADI" in name_upper or "ISTMEPADI" in name_upper:
            return "04.33.03.01", "istmepadjad lamatiste vältimiseks"
        elif "TÕSTUK" in name_upper or "RAIZER" in name_upper:
            return "12.36.03", "lingtõstukid"
        return "18.12.10", "elektrilise reguleerimisega voodid"

    # 9. Igapäevaelu abivahendid
    if "igapäev" in type_lower:
        if "HAARATS" in name_upper:
            return "24.21.03", "haaramistangid"
        elif "PRILL" in name_upper or "LUUP" in name_upper:
            return "22.03.09", "suurendusklaasid"
        return None, None

    # 10. Nahahooldus ja hügieen (09.21.06 nahapesemisvahendid, 09.21.18 nahakaitsevahendid)
    if any(x in type_lower for x in ["nahahooldus", "nahapesu", "hügieen", "pesuvahend"]) or any(w in name_upper for w in [
        "TSINKSALV", "TSINKKREEM", "TSINKSPREI", "SUDOCREM", "SUDOCREAM", "PESUVAHT", "PUHASTUSVAHT", "PESUKREEM", "PESUEMULSIOON", "WASH MOUSSE", "WASH CREAM", "WASH LOTION"
    ]):
        if any(w in name_upper for w in ["PESU", "PUHASTUS", "WASH", "CLEANSING", "CLEAN"]) and not any(w in name_upper for w in ["TSINK", "TSINGI", "ZINC", "ZINK", "SUDOCRE"]):
            return "09.21.06", "nahapesemisvahendid"
        if any(w in name_upper for w in ["TSINK", "TSINGI", "ZINC", "ZINK", "SUDOCRE", "KAITSE", "BARRIER"]):
            return "09.21.18", "nahakaitsevahendid"
        if "VAHT" in name_upper:
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

    # 12. Kuulmisabivahendid
    if "CROS" in name_upper or "cros" in type_lower:
        return "22.06.15.05", "teise kõrva heli ülekande süsteemid (CROS)"
    if any(w in name_upper for w in ["OTICON OWN", "KEY ITC", "SIGNIA SILK", "SIGNIA INSIO", "PHONAK VIRTO"]) or "kõrvasisene" in type_lower:
        return "22.06.12.01", "kõrvasisesed kuulmisabivahendid - aktiivsusgrupp I"
    if "kuulmisabivahend" in type_lower or "kuuldeaparaat" in type_lower or any(w in name_upper for w in ["KUULDEAPARAAT", "OTICON", "RESOUND", "PHONAK", "SIGNIA", "BERNAFON", "STARKEY"]):
        return "22.06.15.01", "kõrvatagused kuulmisabivahendid - aktiivsusgrupp I"

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

        # 1. Laadi esmalt SQLite tooteregister (kui olemas)
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

                    # Puhasta valepositiivsed ID brändi kirjed (nt 'ID LAMATISTEVASTANE MADRATS')
                    if (p.get('brand') or '').upper() == 'ID':
                        combined_check = f"{p.get('official_product_name', '')} {' '.join(aliases_list[:3])}"
                        if not ID_BRAND_VALID_RE.search(combined_check):
                            p['brand'] = 'Määramata'
                            p['manufacturer'] = 'Määramata'
                            p['official_product_name'] = re.sub(r'^ID\s+', '', p.get('official_product_name', ''), flags=re.IGNORECASE).strip()
                            if p.get('product_family'):
                                p['product_family'] = re.sub(r'^ID\s+', '', p.get('product_family', ''), flags=re.IGNORECASE).strip()

                    p['aliases'] = aliases_list
                    p['official_name'] = p['official_product_name']
                    p['full_name'] = f"{p['manufacturer']} {p['official_product_name']}" if p.get('manufacturer') and p['manufacturer'] != 'Määramata' else p['official_product_name']
                    p['product_line'] = p['product_family']
                    p['absorption_ml'] = p['ml_capacity']
                    p['drops'] = p['drop_rating']
                    p['category_type'] = p['product_type']

                    dim_m = re.search(r"\b(\d{2,3}X\d{2,3})\b", normalize_name(p['official_name']))
                    if dim_m:
                        p['dimensions'] = dim_m.group(1)

                    iso, stat = infer_iso_and_statutory_name(
                        p['brand'], p['official_product_name'], p['product_type'],
                        p['ml_capacity'], p['drop_rating']
                    )
                    p['suggested_iso'] = iso
                    p['suggested_statutory_name'] = stat

                    self._register_product(p)
            conn.close()

        # 2. Laadi kureeritud baaskataloog (MANUFACTURER_CATALOGUE) teisena, et täpsed spetsifikatsioonid oleksid prioriteetsed
        for p in MANUFACTURER_CATALOGUE:
            item = dict(p)
            item['source_supplier'] = "Ametlik tootja kataloog"
            self._register_product(item, is_curated=True)

        self._loaded = True

    def _register_product(self, p: Dict[str, Any], is_curated: bool = False):
        """Indekseerib toote ja selle aliased O(1) otsinguks (säilitades mõõdupõhised variandid)."""
        self._products.append(p)

        norm_official = normalize_name(p['official_name'])
        if is_curated or norm_official not in self._alias_to_product:
            self._alias_to_product[norm_official] = p
        
        clean_canon = re.sub(r'[^A-Z0-9]', '', norm_official)
        if clean_canon and (is_curated or clean_canon not in self._alias_to_product):
            self._alias_to_product[clean_canon] = p

        b_key = p['brand'].upper()
        if b_key not in self._brand_to_products:
            self._brand_to_products[b_key] = []
        if is_curated:
            self._brand_to_products[b_key].insert(0, p)
        else:
            self._brand_to_products[b_key].append(p)

        dim_variants: Dict[str, Dict[str, Any]] = {}

        for alias in p.get('aliases', []):
            norm_al = normalize_name(alias)
            al_dim_m = re.search(r"\b(\d{2,3}X\d{2,3})\b", norm_al)
            target_p = p

            # Kui aliase sees on mõõt (nt 40X60), mida põhinimes pole, loo mõõdupõhine alamvariant
            if al_dim_m and not p.get('dimensions'):
                dim_str = al_dim_m.group(1)
                if dim_str not in dim_variants:
                    p_dim = dict(p)
                    p_dim['official_name'] = f"{p['official_name']} {dim_str}"
                    p_dim['full_name'] = f"{p.get('full_name', p['official_name'])} {dim_str}"
                    p_dim['dimensions'] = dim_str
                    p_dim['aliases'] = [a for a in p.get('aliases', []) if dim_str in normalize_name(a)]
                    iso_d, stat_d = infer_iso_and_statutory_name(
                        p_dim['brand'], p_dim['official_name'], p_dim.get('category_type', ''),
                        p_dim.get('absorption_ml'), p_dim.get('drops')
                    )
                    p_dim['suggested_iso'] = iso_d
                    p_dim['suggested_statutory_name'] = stat_d
                    dim_variants[dim_str] = p_dim
                    self._products.append(p_dim)
                    self._brand_to_products[b_key].append(p_dim)
                target_p = dim_variants[dim_str]

            if is_curated or norm_al not in self._alias_to_product:
                self._alias_to_product[norm_al] = target_p
            clean_al = re.sub(r'[^A-Z0-9]', '', norm_al)
            if clean_al and (is_curated or clean_al not in self._alias_to_product):
                self._alias_to_product[clean_al] = target_p

    def get_all_products(self) -> List[Dict[str, Any]]:
        return self._products

    def get_by_brand(self, brand: str) -> List[Dict[str, Any]]:
        return self._brand_to_products.get(brand.upper(), [])

    def find_exact_alias(self, raw_or_norm_name: str) -> Optional[Dict[str, Any]]:
        """Otsib O(1) kiirusega täpset aliaset (ning täpsustab üldkirje korral ISO konkreetse aliase atribuutide põhjal)."""
        norm = normalize_name(raw_or_norm_name)
        matched = None
        if norm in self._alias_to_product:
            matched = self._alias_to_product[norm]
        else:
            clean = re.sub(r'[^A-Z0-9]', '', norm)
            if clean in self._alias_to_product:
                matched = self._alias_to_product[clean]

        if matched is not None and matched.get("source_supplier") != "Ametlik tootja kataloog":
            iso_ref, stat_ref = infer_iso_and_statutory_name(
                matched.get("brand", ""),
                f"{matched.get('official_name', '')} {raw_or_norm_name}",
                matched.get("category_type", ""),
                matched.get("absorption_ml"),
                matched.get("drops")
            )
            if iso_ref and iso_ref != matched.get("suggested_iso"):
                refined = dict(matched)
                refined["suggested_iso"] = iso_ref
                refined["suggested_statutory_name"] = stat_ref
                return refined

        return matched

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
