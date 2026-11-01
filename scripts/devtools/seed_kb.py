"""Initsialiseerib teadmistebaasi algsed kinnitatud seosed testimiseks."""

import os
from src.knowledge_base import KnowledgeBase
from src.normalizer import normalize_name


def seed_knowledge_base():
    db_path = "data/valideer.db"
    kb = KnowledgeBase(db_path=db_path)

    # Uuenda MoliCare Pad 4 õigele ISO-koodile 09.30.24.16 (865 ml, naistele 600-999 ml)
    kb.confirm(
        algne_nimetus="MOLICARE PAD 4",
        normaliseeritud_nimetus=normalize_name("MOLICARE PAD 4"),
        ametlik_toode="MOLICARE PAD 4",
        iso_kood="09.30.24.16",
        maarusejargne_nimetus="inkontinentsisidemed naistele 600 - 999 ml"
    )

    # Lisa Tena Pants Plus M (1440 ml -> 09.30.24.88)
    kb.confirm(
        algne_nimetus="TENA PANTS PLUS M",
        normaliseeritud_nimetus=normalize_name("TENA PANTS PLUS M"),
        ametlik_toode="TENA PANTS PLUS M",
        iso_kood="09.30.24.88",
        maarusejargne_nimetus="imavad püksid 1400 - 1699 ml M"
    )

    # Lisa Rulaator Cristallo
    kb.confirm(
        algne_nimetus="RULAATOR CRISTALLO 4-RATTALINE",
        normaliseeritud_nimetus=normalize_name("RULAATOR CRISTALLO 4-RATTALINE"),
        ametlik_toode="RULAATOR CRISTALLO",
        iso_kood="12.06.06",
        maarusejargne_nimetus="rulaatorid"
    )

    # Lisa Küünarkark
    kb.confirm(
        algne_nimetus="KÜÜNARKARK ERGODYNAMIC",
        normaliseeritud_nimetus=normalize_name("KÜÜNARKARK ERGODYNAMIC"),
        ametlik_toode="KÜÜNARKARK ERGODYNAMIC",
        iso_kood="12.03.06",
        maarusejargne_nimetus="küünarkargud"
    )

    print(f"Teadmistebaas initsialiseeritud! Kirjeid: {kb.count()}")


if __name__ == "__main__":
    seed_knowledge_base()
