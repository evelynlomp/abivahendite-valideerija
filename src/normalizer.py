"""Teksti, ISO-koodide ja määrusejärgsete nimetuste normaliseerimise moodul."""

import re
from typing import Tuple


def clean_text(text: str) -> str:
    """Eemaldab liigsed tühikud ja viib teksti suurtähtedesse."""
    if not text:
        return ""
    text = str(text).strip().upper()
    # Asenda reavahetused ja tabulaatorid tühikutega
    text = re.sub(r"[\r\n\t]+", " ", text)
    # Asenda mitmekordsed tühikud
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def normalize_name(raw_name: str) -> str:
    """
    Normaliseerib abivahendi nimetuse kanoonilisele kujule.
    
    Näited:
    - 'MOLICARE PAD 4' -> 'MOLICARE PAD 4'
    - 'MOLICARE PAD 4 TILKA' -> 'MOLICARE PAD 4'
    - 'MOLICARE PAD LADY 4' -> 'MOLICARE PAD 4'
    - 'MOLICARE PAD 4 N30' -> 'MOLICARE PAD 4'
    - 'TENA PANTS MAXI M 10TK' -> 'TENA PANTS MAXI M'
    """
    if not raw_name:
        return ""

    text = clean_text(raw_name)

    # 1. Eemalda tootekoodid / EAN sulgudes, nt (168101), [4052199]
    text = re.sub(r"[\(\[\{]\s*\d+\s*[\)\]\}]", " ", text)

    # 2. Eemalda apteegi / kassa spetsiifilised märked
    noise_tags = [
        r"\bSOODUSTUSEGA\b",
        r"\bSOODUS\b",
        r"\bKLIENDIKAART\b",
        r"\bSKK\b",
        r"\bRETSEPTIGA\b",
        r"\bRETSEPT\b",
    ]
    for pattern in noise_tags:
        text = re.sub(pattern, " ", text, flags=re.IGNORECASE)

    # 3. Eemalda pakendi kogusetähised:
    # N30, N 30, N-30, N14, N100 jne
    text = re.sub(r"\bN\s*[-–—]?\s*\d+\b", " ", text, flags=re.IGNORECASE)
    # 30TK, 30 TK, 30 TÜKKI, 30PCS, 30 PK, 30 PACK jne
    text = re.sub(r"\b\d+\s*(TK|TÜKKI|TUKKI|PCS|PC|PK|PACK|PAKK)\b", " ", text, flags=re.IGNORECASE)
    # 10X30, 4X14 jne
    text = re.sub(r"\b\d+\s*[X*×]\s*\d+\b", " ", text, flags=re.IGNORECASE)

    # 4. Eemalda redundantsed tilga- ja imavussõnad (säilitades numbri):
    # nt "4 TILKA" -> "4", "3 TILK" -> "3", "5 DROPS" -> "5"
    text = re.sub(r"\bTILKA?\b", " ", text, flags=re.IGNORECASE)
    text = re.sub(r"\bDROPS?\b", " ", text, flags=re.IGNORECASE)

    # 5. Eemalda mittespetsiifilised soo-/bränditäiendid, kui need sageli varieeruvad
    # nt 'LADY' või 'MEN' üldmähkmetel/sidemetel, kui tootesarjas on need samaväärsed
    # Märkus: asendame ainult siis, kui see ei ole toote ainus sõna
    tokens = text.split()
    cleaned_tokens = []
    for token in tokens:
        # Säilitame põhiterminid, eemaldame pehmed vahesõnad
        if token in ("LADY", "MEN") and len(tokens) > 2:
            continue
        cleaned_tokens.append(token)
    text = " ".join(cleaned_tokens)

    # 6. Eemalda kirjavahemärgid, mis ei ole numbrite või tähtede vahel olulised
    # Asendame sümbolid nagu / + , - _ . tühikutega, kui need ei kuulu tootenimesse
    text = re.sub(r"[,;:\-_/\\\"'#*~]+", " ", text)

    # 7. Viimane tühikute ja ääriste puhastus
    text = re.sub(r"\s+", " ", text).strip()
    return text


def normalize_iso(raw_iso: str) -> str:
    """
    Normaliseerib ISO-koodi ühtsele kujule.
    Eemaldab punktid, tühikud, sidekriipsud ja kaldkriipsud.
    
    Näited:
    - '09.30.04.01' -> '09300401'
    - '09 30 04' -> '093004'
    - ' 09-30-04 ' -> '093004'
    """
    if not raw_iso:
        return ""
    # Eemalda kõik mitte-tähed ja mitte-numbrid
    cleaned = re.sub(r"[^0-9A-Za-z]", "", str(raw_iso)).upper()
    return cleaned


def format_iso_display(iso_clean: str) -> str:
    """
    Vormindab puhta ISO koodi standardseks punktidega vaateks (nt 09.30.04.01).
    """
    if not iso_clean:
        return ""
    # Kui on 6 või 8 numbrit, tükeldame paarikaupa
    if len(iso_clean) in (6, 8) and iso_clean.isdigit():
        parts = [iso_clean[i:i+2] for i in range(0, len(iso_clean), 2)]
        return ".".join(parts)
    return iso_clean


def normalize_statutory_name(raw_name: str) -> str:
    """
    Normaliseerib määrusejärgse nimetuse võrdluseks:
    - Suurtähed
    - Eemaldab liigsed kirjavahemärgid ja tühikud
    """
    if not raw_name:
        return ""
    text = clean_text(raw_name)
    # Eemalda lõpupunktid või komad
    text = re.sub(r"[\.,;:!\?]+$", "", text)
    # Eemalda topelttühikud
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def compare_iso(iso1: str, iso2: str) -> bool:
    """Võrdleb kahte ISO-koodi normaliseeritud kujul."""
    norm1 = normalize_iso(iso1)
    norm2 = normalize_iso(iso2)
    if not norm1 or not norm2:
        return False
    return norm1 == norm2


def compare_statutory_names(name1: str, name2: str) -> bool:
    """Võrdleb kahte määrusejärgset nimetust normaliseeritud kujul."""
    norm1 = normalize_statutory_name(name1)
    norm2 = normalize_statutory_name(name2)
    if not norm1 or not norm2:
        return False
    return norm1 == norm2
