"""Automaattestid Valideer süsteemi toote tuvastamise agendi ja püsiva arhitektuuri kontrollimiseks."""

import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.normalizer import normalize_name, normalize_iso, compare_iso, compare_statutory_names
from src.classifier import MinistryClassifier
from src.knowledge_base import KnowledgeBase
from src.product_agent import ProductIdentificationAgent
from src.matcher import ProductMatcher
from src.validator import Validator


def test_normalization():
    examples = {
        "MOLICARE PAD 4": "MOLICARE PAD 4",
        "MOLICARE PAD 4 TILKA": "MOLICARE PAD 4",
        "MOLICARE PAD LADY 4": "MOLICARE PAD 4",
        "MOLICARE PAD 4 N30": "MOLICARE PAD 4",
        "LILLE SUPREME LIGHT NORMAL 340ML N28": "LILLE SUPREME LIGHT NORMAL 340ML",
    }
    for raw, expected in examples.items():
        assert normalize_name(raw) == expected, f"Viga: {raw} -> {normalize_name(raw)}, oodati {expected}"


def test_product_identification_agent():
    agent = ProductIdentificationAgent()

    # Näidis 1: ABENA SAN 4
    r1 = agent.identify_product("ABENA SAN 4")
    assert r1["identified"] is True
    assert r1["official_product"] == "ABENA SAN 4"
    assert r1["confidence_score"] >= 0.85
    assert r1["suggested_iso"] == "09.30.24.16"
    assert "Abena Group" in r1["manufacturer"]
    assert len(r1["evidence_sources"]) >= 2
    assert len(r1["reasoning"]) > 20
    assert len(r1["alternative_matches"]) >= 1

    # Näidis 2: MOLICARE PAD 4 TILKA N30
    r2 = agent.identify_product("MOLICARE PAD 4 TILKA N30")
    assert r2["identified"] is True
    assert "MOLICARE PAD 4" in r2["official_product"]
    assert r2["confidence_score"] >= 0.85
    assert r2["suggested_iso"] == "09.30.24.16"
    assert "Paul Hartmann" in r2["manufacturer"]
    assert len(r2["evidence_sources"]) >= 2

    # Näidis 3: LILLE SUPREME LIGHT NORMAL 340ML N28
    r3 = agent.identify_product("LILLE SUPREME LIGHT NORMAL 340ML N28")
    assert r3["identified"] is True
    assert r3["official_product"] == "LILLE SUPREME LIGHT NORMAL 340ML"
    assert r3["confidence_score"] >= 0.85
    assert r3["suggested_iso"] == "09.30.24.15"
    assert "Ontex" in r3["manufacturer"]


def test_full_pipeline_with_agent():
    test_db = "data/test_valideer.db"
    classifier = MinistryClassifier(db_path=test_db)
    kb = KnowledgeBase(db_path=test_db)
    agent = ProductIdentificationAgent()
    matcher = ProductMatcher(classifier=classifier, knowledge_base=kb, product_agent=agent)
    validator = Validator(matcher=matcher)

    # 1. Kontrolli Abena San 4
    r_abena = validator.validate_row(
        excel_name="ABENA SAN 4",
        excel_iso="09.30.24.16",
        excel_statutory_name="inkontinentsisidemed naistele 600 - 999 ml"
    )
    assert r_abena["Tuvastatud ametlik toode"] == "ABENA SAN 4"
    assert r_abena["Valideerimise staatus"] == Validator.STATUS_MATCH
    assert r_abena["Ametlik ISO kood"] == "09.30.24.16"
    assert "Abena Group" in r_abena["Tootja"]
    assert len(r_abena["Tõendite allikad"]) >= 1

    # 2. Kontrolli Lille Supreme Light Normal 340ML vale ISO-ga
    r_lille_wrong_iso = validator.validate_row(
        excel_name="LILLE SUPREME LIGHT NORMAL 340ML N28",
        excel_iso="12.03.06",  # Vale ISO
        excel_statutory_name="inkontinentsisidemed naistele 300 - 599 ml"
    )
    assert r_lille_wrong_iso["Tuvastatud ametlik toode"] == "LILLE SUPREME LIGHT NORMAL 340ML"
    assert r_lille_wrong_iso["Valideerimise staatus"] == Validator.STATUS_WRONG_ISO
    assert r_lille_wrong_iso["Ametlik ISO kood"] == "09.30.24.15"

    print("Kõik Product Identification Agendi testid läbisid edukalt!")


if __name__ == "__main__":
    test_db = "data/test_valideer.db"
    try:
        if os.path.exists(test_db):
            os.remove(test_db)
    except Exception:
        pass

    test_normalization()
    test_product_identification_agent()
    test_full_pipeline_with_agent()

    try:
        if os.path.exists(test_db):
            os.remove(test_db)
    except Exception:
        pass
