import sys
import os
import unittest
import tempfile
import sqlite3

sys.path.insert(0, os.path.abspath("."))

from src.canonical_learning import CanonicalLearningService, calculate_confidence


class TestCanonicalLearning(unittest.TestCase):
    def setUp(self):
        self.tmp_dir = tempfile.TemporaryDirectory()
        self.db_path = os.path.join(self.tmp_dir.name, "test_learning.db")
        self.service = CanonicalLearningService(db_path=self.db_path)

    def tearDown(self):
        self.tmp_dir.cleanup()

    def test_calculate_confidence(self):
        # 10 kinnitust, 0 tagasi lükatud -> 98%
        self.assertEqual(calculate_confidence(10, 0), 98.0)
        # 1 kinnitus, 0 tagasi -> 80%
        self.assertEqual(calculate_confidence(1, 0), 80.0)
        # 0 kinnitust, 0 tagasi -> 50%
        self.assertEqual(calculate_confidence(0, 0), 50.0)
        # 0 kinnitust, 1 tagasi -> 0%
        self.assertEqual(calculate_confidence(0, 1), 0.0)

    def test_record_confirm_and_reject(self):
        # 1. Kinnita Oticon Intent 22.06.15.01
        for i in range(10):
            res = self.service.record_decision(
                canonical_name="OTICON INTENT",
                iso_code="22.06.15.01",
                statutory_name="kõrvatagused kuulmisabivahendid - aktiivsusgrupp I",
                action="CONFIRM",
                rationale="Sobib aktiivsusgrupp I nõuetele",
                user="Spetsialist"
            )

        self.assertEqual(res["kinnitatud_arv"], 10)
        self.assertEqual(res["tagasi_lukatud_arv"], 0)
        self.assertEqual(res["usaldus_protsent"], 98.0)
        self.assertEqual(len(res["ajalugu"]), 10)
        self.assertIsNotNone(res["viimane_kinnitus_aeg"])

        # 2. Lükka tagasi vale ISO (nt 09.30.24.11)
        res_rej = self.service.record_decision(
            canonical_name="OTICON INTENT",
            iso_code="09.30.24.11",
            statutory_name="inkontinentsisidemed",
            action="REJECT",
            rationale="Kuuldeaparaat ei ole mähkmed ega side",
            user="Spetsialist"
        )
        self.assertEqual(res_rej["kinnitatud_arv"], 0)
        self.assertEqual(res_rej["tagasi_lukatud_arv"], 1)
        self.assertEqual(res_rej["usaldus_protsent"], 0.0)
        self.assertIsNotNone(res_rej["viimane_tagasilukatus_aeg"])

    def test_get_candidate_products(self):
        sample_prods = [
            {
                "canonical_id": "CP-1",
                "canonical_name": "TEST LIKELY",
                "manufacturer": "Test Mfg",
                "brand": "Test Brand",
                "sources": [{"source_name": "Pood A"}],
                "aliases": ["Alias 1", "Alias 2"],
                "images": ["https://example.com/pilt.png"],
                "matching_isos": [["22.06.15.01", "kuuldeaparaadid", "kandidaat"]]
            },
            {
                "canonical_id": "CP-2",
                "canonical_name": "TEST UNCLASSIFIED",
                "manufacturer": "Test Mfg 2",
                "brand": "Test Brand 2",
                "sources": [],
                "aliases": ["Tarvik A"],
                "images": [],
                "matching_isos": []
            }
        ]

        cands = self.service.get_candidate_products(sample_prods)
        self.assertEqual(len(cands), 2)
        
        # Esimene peab olema LIKELY
        self.assertEqual(cands[0]["status"], "LIKELY")
        self.assertEqual(cands[0]["canonical_name"], "TEST LIKELY")
        self.assertEqual(cands[0]["sources_count"], 1)
        self.assertEqual(cands[0]["aliases_count"], 2)
        self.assertEqual(cands[0]["image"], "https://example.com/pilt.png")
        self.assertEqual(len(cands[0]["iso_candidates"]), 1)
        self.assertEqual(cands[0]["confidence_score"], 50.0)

        # Teine peab olema UNCLASSIFIED
        self.assertEqual(cands[1]["status"], "UNCLASSIFIED")
        self.assertEqual(cands[1]["sources_count"], 0)
        self.assertEqual(cands[1]["aliases_count"], 1)
        self.assertIsNone(cands[1]["image"])
        self.assertEqual(len(cands[1]["iso_candidates"]), 0)
        self.assertEqual(cands[1]["confidence_score"], 0.0)

    def test_change_iso(self):
        res = self.service.change_iso(
            canonical_name="OTICON TEST",
            new_iso_code="22.06.15.01",
            new_statutory_name="kõrvatagused kuulmisabivahendid",
            rationale="Spetsialisti määratud",
            user="Spetsialist"
        )
        self.assertEqual(res["iso_kood"], "22.06.15.01")
        self.assertEqual(res["kinnitatud_arv"], 1)
        self.assertEqual(res["usaldus_protsent"], 80.0)


if __name__ == "__main__":
    unittest.main()
