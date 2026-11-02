"""Automaattestid Valideer süsteemi toote tuvastamise agendi ja püsiva arhitektuuri kontrollimiseks."""

import os
import sys
import stat
import shutil
import sqlite3
import unittest
import tempfile

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.normalizer import normalize_name, normalize_iso, compare_iso, compare_statutory_names
from src.classifier import MinistryClassifier
from src.knowledge_base import KnowledgeBase
from src.product_agent import ProductIdentificationAgent
from src.product_registry_db import ProductRegistryDB
from src.canonical_learning import CanonicalLearningService
from src.matcher import ProductMatcher
from src.validator import Validator
from src.restriction_engine import RestrictionEngine


def test_normalization():
    examples = {
        "MOLICARE PAD 4": "MOLICARE PAD 4",
        "MOLICARE PAD 4 TILKA": "MOLICARE PAD 4",
        "MOLICARE PAD LADY 4": "MOLICARE PAD 4",
        "MOLICARE PAD 4 N30": "MOLICARE PAD 4",
        "LILLE SUPREME LIGHT NORMAL 340ML N28": "LILLE SUPREME LIGHT NORMAL 340ML",
        # ETAPP 1.1: Mõõdud säilivad, pakend eemaldatakse
        "TENA Bed Plus 40x60 cm N35": "TENA BED PLUS 40X60",
        "TENA Bed Plus 60x90 cm (30tk)": "TENA BED PLUS 60X90",
        "Molicare Bed Mat 75x85": "MOLICARE BED MAT 75X85",
        # ETAPP 1.2: ISO koodi sabad eemaldatakse
        "CHEMI-PHARM ITAK puhastusvaht 750ml*09.21.06": "CHEMI PHARM ITAK PUHASTUSVAHT 750ML",
        "Seni Active Trio L*09.30.24.95": "SENI ACTIVE TRIO L",
    }
    for raw, expected in examples.items():
        assert normalize_name(raw) == expected, f"Viga: {raw} -> {normalize_name(raw)}, oodati {expected}"


def test_etapp1_rules():
    agent = ProductIdentificationAgent()

    # 1. Mõõtude eristamine klassifitseerimises (40x60 vs 60x90)
    b40 = agent.identify_product("TENA Bed Plus 40x60")
    b90 = agent.identify_product("TENA Bed Plus 60x90")
    assert b40["suggested_iso"] == "09.30.00.01", f"40x60 ISO viga: {b40['suggested_iso']}"
    assert b90["suggested_iso"] == "09.30.00.03", f"60x90 ISO viga: {b90['suggested_iso']}"

    # 3. ID brändi sõnapiiri- ja kontekstipõhine tuvastus
    for false_id in ["INDIVIDUAALNE OTSAK", "INDIV OTSAK", "INDIVIDUAALNE KÕRVAOTSIK", "LAPID", "PESUSVAMMID"]:
        feat = agent.extract_features(false_id)
        assert feat["brand"] not in ("ID", "LILLE"), f"Valepositiivne ID bränd sõnale {false_id}: {feat['brand']}"
        res = agent.identify_product(false_id)
        assert not (res["official_product"] and res["official_product"].startswith("ID ")), f"Valepositiivne ID toode: {res['official_product']}"

    for valid_id in ["iD Pants Plus L", "iD Slip Super M", "iD Expert Form"]:
        feat = agent.extract_features(valid_id)
        assert feat["brand"] in ("ID", "LILLE"), f"Tuvastamata iD bränd: {valid_id} -> {feat['brand']}"

    # Individuaalne otsak peab tuvastama 22.06.12.04
    r_otsak = agent.identify_product("INDIVIDUAALNE KÕRVAOTSIK")
    assert r_otsak["official_product"] == "KUULDEAPARAADI INDIVIDUAALNE OTSAK"
    assert r_otsak["suggested_iso"] == "22.06.12.04"

    # 4. Kuulmisabivahendite mudelite koondumine
    for variant in ["Linx Quattro RE777-DWT", "GN ReSound RE777", "RE777-DWT"]:
        r_ha = agent.identify_product(variant)
        assert r_ha["identified"] is True, f"Tuvastamata kuuldeaparaat: {variant}"
        assert r_ha["official_product"] == "GN RESOUND LINX QUATTRO RE777", f"Vale kanooniline mudel '{variant}' jaoks: {r_ha['official_product']}"


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
    with tempfile.TemporaryDirectory() as tmpdir:
        test_db = os.path.join(tmpdir, "test_valideer.db")
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


def test_auto_learn_knowledge_base_and_restrictions():
    classifier = MinistryClassifier()
    kb = KnowledgeBase()
    agent = ProductIdentificationAgent()
    matcher = ProductMatcher(classifier=classifier, knowledge_base=kb, product_agent=agent)
    validator = Validator(matcher=matcher)

    assert kb.count() >= 880, f"Teadmistebaasis oodati >= 880 kirjet, leiti {kb.count()}"

    # 1. AUTO_LEARN otse-lookup (Serenity pesukinnas)
    r_kb = validator.validate_row(
        excel_name="Serenity care washglove NW/PE Wh/Blue 60",
        excel_iso="09.33.30.02",
        excel_statutory_name="pesukindad"
    )
    assert r_kb["Valideerimise staatus"] == Validator.STATUS_MATCH
    assert r_kb["Ametlik ISO kood"] == "09.33.30.02"

    # 2. Variandireegli (FAMILY_VARIANT_RULE) lookup (TENA Pants Maxi L 2550ml)
    r_vr = validator.validate_row(
        excel_name="TENA Pants Maxi L 2550ml uus partiikirje",
        excel_iso="09.30.24.95",
        excel_statutory_name="imavad püksid üle 1700 ml L"
    )
    assert r_vr["Valideerimise staatus"] == Validator.STATUS_MATCH
    assert r_vr["Ametlik ISO kood"] == "09.30.24.95"

    # 3. Määruse kitsenduse kontroll (09.21.18 nõuab tsinkoksiidi)
    ok_zinc, _, _ = RestrictionEngine.check_restrictions("09.21.18", "Seni Care tsinksalv 100ml")
    fail_no_zinc, _, _ = RestrictionEngine.check_restrictions("09.21.18", "Tavaline kätekreem kummeliga 100ml")
    assert ok_zinc is True
    assert fail_no_zinc is False


def test_readonly_db_and_cloud_security():
    # 1. Kontrolli, et data/valideer.db ei ole WAL režiimis (mis nõuaks -wal/-shm kirjutamist read-only kettale)
    conn = sqlite3.connect("data/valideer.db")
    j_mode = conn.execute("PRAGMA journal_mode;").fetchone()[0].lower()
    conn.close()
    assert j_mode == "delete", f"Oodati journal_mode=delete, leiti {j_mode}"

    # 2. Kontrolli rangelt read-only (S_IREAD) andmebaasifailiga kõigi teenuste tööd
    with tempfile.TemporaryDirectory() as tmpdir:
        ro_db = os.path.join(tmpdir, "readonly_valideer.db")
        shutil.copy2("data/valideer.db", ro_db)
        os.chmod(ro_db, stat.S_IREAD)
        try:
            clf_ro = MinistryClassifier(db_path=ro_db)
            kb_ro = KnowledgeBase(db_path=ro_db)
            reg_ro = ProductRegistryDB(db_path=ro_db)
            learn_ro = CanonicalLearningService(db_path=ro_db)

            assert clf_ro.count() == 250
            assert kb_ro.count() >= 880
            assert reg_ro.get_statistics()["total_products"] >= 3300
            assert learn_ro.get_candidate_products([]) == []
        finally:
            os.chmod(ro_db, stat.S_IWRITE | stat.S_IREAD)

    # 3. Kontrolli noindex/nofollow ja APP_PASSWORD kaitset app.py sees
    with open("app.py", "r", encoding="utf-8") as f:
        app_src = f.read()
    assert "noindex, nofollow" in app_src, "noindex, nofollow kaitse puudub app.py failist"
    assert "APP_PASSWORD" in app_src and "compare_digest" in app_src, "APP_PASSWORD kaitse puudub app.py failist"


class TestValideerSuite(unittest.TestCase):
    def test_1_normalization(self):
        test_normalization()

    def test_2_etapp1_rules(self):
        test_etapp1_rules()

    def test_3_product_identification_agent(self):
        test_product_identification_agent()

    def test_4_full_pipeline_with_agent(self):
        test_full_pipeline_with_agent()

    def test_5_auto_learn_kb_and_restrictions(self):
        test_auto_learn_knowledge_base_and_restrictions()

    def test_6_readonly_db_and_cloud_security(self):
        test_readonly_db_and_cloud_security()


if __name__ == "__main__":
    unittest.main()
