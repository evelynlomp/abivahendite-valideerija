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


if __name__ == "__main__":
    unittest.main()
