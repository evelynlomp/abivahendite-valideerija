"""Tooteregister ja tootjate spetsifikatsioonid toote tuvastamise agendile (Product Identification Agent)."""

from typing import Dict, Any, List, Optional


# Tuntud abivahendite tootjate ja kaubanduslike tootesarjade register
MANUFACTURER_CATALOGUE: List[Dict[str, Any]] = [
    # ABENA
    {
        "brand": "ABENA",
        "manufacturer": "Abena Group (Taani)",
        "product_line": "Abena San",
        "official_name": "ABENA SAN 4",
        "full_name": "Abena San Premium 4",
        "aliases": ["ABENA SAN 4", "ABRI-SAN 4", "ABENA SAN PREMIUM 4", "ABRI SAN 4"],
        "category_type": "inkontinentsiside / anatoomiline vormmähe",
        "absorption_ml": 800,
        "capacity_range": "600 - 999 ml",
        "target_group": "Naistele / Unisex",
        "suggested_iso": "09.30.24.16",
        "suggested_statutory_name": "inkontinentsisidemed naistele 600 - 999 ml",
        "evidence_notes": "Abena ametlik kataloog: Anatoomiline vormmähe mõõduka pidamatuse jaoks, imavus 800 ml (ISO 11948-1)."
    },
    {
        "brand": "ABENA",
        "manufacturer": "Abena Group (Taani)",
        "product_line": "Abena San",
        "official_name": "ABENA SAN 3",
        "full_name": "Abena San Premium 3",
        "aliases": ["ABENA SAN 3", "ABRI-SAN 3", "ABENA SAN PREMIUM 3", "ABRI SAN 3"],
        "category_type": "inkontinentsiside",
        "absorption_ml": 500,
        "capacity_range": "300 - 599 ml",
        "target_group": "Naistele / Unisex",
        "suggested_iso": "09.30.24.15",
        "suggested_statutory_name": "inkontinentsisidemed naistele 300 - 599 ml",
        "evidence_notes": "Abena ametlik kataloog: Imavus 500 ml."
    },
    {
        "brand": "ABENA",
        "manufacturer": "Abena Group (Taani)",
        "product_line": "Abena Pants",
        "official_name": "ABENA PANTS M3",
        "full_name": "Abena Pants Premium M3",
        "aliases": ["ABENA PANTS M3", "ABRI-FLEX M3", "ABENA PANTS MEDIUM 3"],
        "category_type": "imavad püksid",
        "absorption_ml": 2400,
        "capacity_range": "1900 - 2499 ml",
        "size": "M",
        "target_group": "Unisex",
        "suggested_iso": "09.30.24.36",
        "suggested_statutory_name": "püksmähkmed 1900 - 2499 ml M",
        "evidence_notes": "Abena pants imavad püksid suurus M, imavusmaht 2400 ml."
    },

    # HARTMANN / MOLICARE
    {
        "brand": "MOLICARE",
        "manufacturer": "Paul Hartmann AG (Saksamaa)",
        "product_line": "MoliCare Pad",
        "official_name": "MOLICARE PAD 4",
        "full_name": "MoliCare Premium Lady Pad 4 Drops / MoliCare Pad 4",
        "aliases": ["MOLICARE PAD 4", "MOLICARE PAD 4 TILKA", "MOLICARE PAD LADY 4", "MOLICARE PREMIUM PAD 4"],
        "category_type": "inkontinentsiside / anatoomiline padjake",
        "absorption_ml": 865,
        "capacity_range": "600 - 999 ml",
        "target_group": "Naistele / Unisex",
        "drops": 4,
        "suggested_iso": "09.30.24.16",
        "suggested_statutory_name": "inkontinentsisidemed naistele 600 - 999 ml",
        "evidence_notes": "Hartmann spetsifikatsioon: 4 tilka imavusaste = 865 ml, pH 5.5 nahasõbralik pealispind."
    },
    {
        "brand": "MOLICARE",
        "manufacturer": "Paul Hartmann AG (Saksamaa)",
        "product_line": "MoliCare Pad",
        "official_name": "MOLICARE PAD 3",
        "full_name": "MoliCare Premium Lady Pad 3 Drops",
        "aliases": ["MOLICARE PAD 3", "MOLICARE PAD 3 TILKA", "MOLICARE PAD LADY 3"],
        "category_type": "inkontinentsiside",
        "absorption_ml": 505,
        "capacity_range": "300 - 599 ml",
        "target_group": "Naistele",
        "drops": 3,
        "suggested_iso": "09.30.24.15",
        "suggested_statutory_name": "inkontinentsisidemed naistele 300 - 599 ml",
        "evidence_notes": "Hartmann spetsifikatsioon: 3 tilka imavusaste = 505 ml."
    },
    {
        "brand": "MOLICARE",
        "manufacturer": "Paul Hartmann AG (Saksamaa)",
        "product_line": "MoliCare Mobile",
        "official_name": "MOLICARE MOBILE 6 DROPS M",
        "full_name": "MoliCare Premium Mobile 6 Drops M",
        "aliases": ["MOLICARE MOBILE 6 DROPS M", "MOLICARE MOBILE 6 M", "MOLICARE MOBILE M 6 TILKA"],
        "category_type": "imavad püksid",
        "absorption_ml": 1470,
        "capacity_range": "1400 - 1699 ml",
        "size": "M",
        "drops": 6,
        "suggested_iso": "09.30.24.88",
        "suggested_statutory_name": "imavad püksid 1400 - 1699 ml M",
        "evidence_notes": "Hartmann tootekataloog: 6 tilka imavad püksid suurus M (1470 ml)."
    },

    # ONTEX / LILLE
    {
        "brand": "LILLE",
        "manufacturer": "Ontex Healthcare (Belgia / Prantsusmaa)",
        "product_line": "Lille Supreme Light",
        "official_name": "LILLE SUPREME LIGHT NORMAL 340ML",
        "full_name": "Lille Supreme Light Normal 340ml",
        "aliases": [
            "LILLE SUPREME LIGHT NORMAL 340ML",
            "LILLE SUPREME LIGHT NORMAL",
            "LILLE LIGHT NORMAL 340ML",
            "LILLE SUPREME LIGHT 340ML"
        ],
        "category_type": "inkontinentsiside",
        "absorption_ml": 340,
        "capacity_range": "300 - 599 ml",
        "target_group": "Naistele / Unisex",
        "suggested_iso": "09.30.24.15",
        "suggested_statutory_name": "inkontinentsisidemed naistele 300 - 599 ml",
        "evidence_notes": "Ontex spetsifikatsioon: Lille Supreme Light Normal anatoomiline side mahutavusega 340 ml."
    },
    {
        "brand": "LILLE",
        "manufacturer": "Ontex Healthcare (Belgia / Prantsusmaa)",
        "product_line": "Lille Supreme Light",
        "official_name": "LILLE SUPREME LIGHT EXTRA 600ML",
        "full_name": "Lille Supreme Light Extra 600ml",
        "aliases": ["LILLE SUPREME LIGHT EXTRA 600ML", "LILLE SUPREME LIGHT EXTRA"],
        "category_type": "inkontinentsiside",
        "absorption_ml": 600,
        "capacity_range": "600 - 999 ml",
        "target_group": "Naistele / Unisex",
        "suggested_iso": "09.30.24.16",
        "suggested_statutory_name": "inkontinentsisidemed naistele 600 - 999 ml",
        "evidence_notes": "Ontex spetsifikatsioon: Lille Supreme Light Extra anatoomiline side mahutavusega 600 ml."
    },

    # TENA / ESSITY
    {
        "brand": "TENA",
        "manufacturer": "Essity Hygiene and Health AB (Rootsi)",
        "product_line": "Tena Pants",
        "official_name": "TENA PANTS PLUS M",
        "full_name": "TENA Pants Plus Medium",
        "aliases": ["TENA PANTS PLUS M", "TENA PANTS PLUS MEDIUM", "TENA PANTS M PLUS"],
        "category_type": "imavad püksid",
        "absorption_ml": 1440,
        "capacity_range": "1400 - 1699 ml",
        "size": "M",
        "suggested_iso": "09.30.24.88",
        "suggested_statutory_name": "imavad püksid 1400 - 1699 ml M",
        "evidence_notes": "Essity TENA tootekataloog: TENA Pants Plus Medium imavus 1440 ml (ISO 11948-1)."
    },
    {
        "brand": "TENA",
        "manufacturer": "Essity Hygiene and Health AB (Rootsi)",
        "product_line": "Tena Lady",
        "official_name": "TENA LADY DISCREET NORMAL",
        "full_name": "TENA Lady Discreet Normal",
        "aliases": ["TENA LADY DISCREET NORMAL", "TENA LADY NORMAL", "TENA DISCREET NORMAL"],
        "category_type": "inkontinentsiside naistele",
        "absorption_ml": 300,
        "capacity_range": "300 - 599 ml",
        "target_group": "Naistele",
        "suggested_iso": "09.30.24.15",
        "suggested_statutory_name": "inkontinentsisidemed naistele 300 - 599 ml",
        "evidence_notes": "Essity TENA spetsifikatsioon: TENA Lady Discreet Normal imavus 300 ml."
    },

    # LIIKUMISABIVAHENDID
    {
        "brand": "CRISTALLO",
        "manufacturer": "Drive DeVilbiss Healthcare",
        "product_line": "Cristallo Rollator",
        "official_name": "RULAATOR CRISTALLO",
        "full_name": "Rulaator Cristallo 4-rattaline",
        "aliases": ["RULAATOR CRISTALLO", "RULAATOR 4-RATTALINE CRISTALLO", "CRISTALLO ROLLATOR"],
        "category_type": "käimisraam / rulaator",
        "suggested_iso": "12.06.06",
        "suggested_statutory_name": "rulaatorid",
        "evidence_notes": "Drive DeVilbiss meditsiiniseade: kokkupandav terasraamiga 4-rattaline rulaator korvi ja kandikuga."
    },
    {
        "brand": "ERGODYNAMIC",
        "manufacturer": "FDI France Medical",
        "product_line": "Ergodynamic Crutch",
        "official_name": "KÜÜNARKARK ERGODYNAMIC",
        "full_name": "Küünarkark Ergodynamic amortisaatoriga",
        "aliases": ["KÜÜNARKARK ERGODYNAMIC", "KARK ERGODYNAMIC", "ERGODYNAMIC KÜÜNARKARK"],
        "category_type": "küünarkark",
        "suggested_iso": "12.03.06",
        "suggested_statutory_name": "küünarkargud",
        "evidence_notes": "FDI France Medical tootekataloog: patenteeritud integreeritud löögisummutussüsteemiga küünarkark."
    }
]
