"""
Kanooniliste toodete õppimisvõime ja kasutaja tagasiside haldus.

Võimaldab:
1. Salvestada kasutaja (spetsialisti) kinnitatud ja tagasi lükatud ISO-koode kanoonilise toote tasemel.
2. Arvestada kinnituste ja tagasilükkamiste arvu ning arvutada usaldusprotsendi.
3. Salvestada viimase kinnitamise aja ja spetsialisti põhjenduse.
4. Säilitada täieliku otsustuste ajaloo (audit trail).
5. Sünkroniseerida andmed SQLite baasi (valideer.db) ja canonical_products.json vahel.
"""

import sqlite3
import os
import json
from datetime import datetime
from typing import Optional, List, Dict, Any, Tuple
from contextlib import contextmanager


DEFAULT_DB_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "valideer.db")
CANONICAL_JSON_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "canonical_products.json")


def calculate_confidence(confirmed: int, rejected: int) -> float:
    """
    Arvutab ISO vastavuse usaldusväärsuse protsentides (0.0 - 100.0%).
    
    Arvestab kinnituste ja tagasilükkamiste suhet ning kinnituste arvu:
    - 10 kinnitust, 0 tagasilükkamist -> 98.0%
    - 5 kinnitust, 0 tagasilükkamist -> 96.0%
    - 2 kinnitust, 0 tagasilükkamist -> 90.0%
    - 1 kinnitus, 0 tagasilükkamist -> 80.0%
    - 0 kinnitust, 0 tagasilükkamist -> 50.0%
    - 0 kinnitust, 1 tagasilükkamine -> 0.0%
    """
    total = confirmed + rejected
    if total == 0:
        return 50.0

    ratio = confirmed / total
    # Valimi usaldusfaktor: 10 kinnituse puhul 1.0 - 0.20/10 = 0.98
    sample_factor = max(0.5, 1.0 - (0.20 / total))
    confidence = ratio * sample_factor * 100.0
    return round(max(0.0, min(100.0, confidence)), 1)


class CanonicalLearningService:
    """Kanooniliste toodete õppimise ja ISO otsustustoe teenus."""

    def __init__(self, db_path: str = DEFAULT_DB_PATH):
        self.db_path = db_path
        self._init_db()

    @contextmanager
    def _connection(self):
        conn = sqlite3.connect(self.db_path, timeout=30.0)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
        finally:
            conn.close()

    def _init_db(self):
        """Loob kanoonilise toote ISO-õppimise tabeli."""
        with self._connection() as conn:
            cursor = conn.cursor()
            cursor.execute("PRAGMA journal_mode=WAL;")
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS kanooniline_toode_tagasiside (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    canonical_name TEXT NOT NULL,
                    iso_kood TEXT NOT NULL,
                    maarusejargne_nimetus TEXT,
                    kinnitatud_arv INTEGER DEFAULT 0,
                    tagasi_lukatud_arv INTEGER DEFAULT 0,
                    usaldus_protsent REAL DEFAULT 50.0,
                    viimane_kinnitus_aeg TEXT,
                    viimane_tagasilukatus_aeg TEXT,
                    viimane_tegevus_aeg TEXT,
                    pohjendus TEXT,
                    ajalugu TEXT DEFAULT '[]',
                    CONSTRAINT unikaalne_kanooniline_iso UNIQUE (canonical_name, iso_kood)
                );
            """)
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_ctt_name ON kanooniline_toode_tagasiside(canonical_name);")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_ctt_iso ON kanooniline_toode_tagasiside(iso_kood);")
            conn.commit()

    def record_decision(
        self,
        canonical_name: str,
        iso_code: str,
        statutory_name: str,
        action: str,  # "CONFIRM" või "REJECT"
        rationale: str = "",
        user: str = "Spetsialist"
    ) -> Dict[str, Any]:
        """
        Salvestab kasutaja otsuse (kinnitus või tagasilükkamine) antud ISO koodi kohta.
        """
        action = action.upper()
        now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        with self._connection() as conn:
            cursor = conn.cursor()

            # Kontrolli olemasolu
            cursor.execute("""
                SELECT * FROM kanooniline_toode_tagasiside
                WHERE canonical_name = ? AND iso_kood = ?;
            """, (canonical_name, iso_code))
            row = cursor.fetchone()

            if row:
                rec = dict(row)
                confirmed = rec["kinnitatud_arv"]
                rejected = rec["tagasi_lukatud_arv"]
                last_confirm = rec["viimane_kinnitus_aeg"]
                last_reject = rec["viimane_tagasilukatus_aeg"]

                try:
                    history = json.loads(rec["ajalugu"]) if rec["ajalugu"] else []
                except Exception:
                    history = []

                if action == "CONFIRM":
                    confirmed += 1
                    last_confirm = now_str
                else:
                    rejected += 1
                    last_reject = now_str

                conf_score = calculate_confidence(confirmed, rejected)

                history.append({
                    "action": action,
                    "timestamp": now_str,
                    "rationale": rationale,
                    "user": user,
                    "confidence_after": conf_score
                })

                cursor.execute("""
                    UPDATE kanooniline_toode_tagasiside
                    SET kinnitatud_arv = ?,
                        tagasi_lukatud_arv = ?,
                        usaldus_protsent = ?,
                        viimane_kinnitus_aeg = ?,
                        viimane_tagasilukatus_aeg = ?,
                        viimane_tegevus_aeg = ?,
                        pohjendus = ?,
                        maarusejargne_nimetus = COALESCE(?, maarusejargne_nimetus),
                        ajalugu = ?
                    WHERE id = ?;
                """, (
                    confirmed, rejected, conf_score,
                    last_confirm, last_reject, now_str,
                    rationale or rec["pohjendus"],
                    statutory_name,
                    json.dumps(history, ensure_ascii=False),
                    rec["id"]
                ))
            else:
                confirmed = 1 if action == "CONFIRM" else 0
                rejected = 0 if action == "CONFIRM" else 1
                last_confirm = now_str if action == "CONFIRM" else None
                last_reject = now_str if action == "REJECT" else None
                conf_score = calculate_confidence(confirmed, rejected)

                history = [{
                    "action": action,
                    "timestamp": now_str,
                    "rationale": rationale,
                    "user": user,
                    "confidence_after": conf_score
                }]

                cursor.execute("""
                    INSERT INTO kanooniline_toode_tagasiside (
                        canonical_name, iso_kood, maarusejargne_nimetus,
                        kinnitatud_arv, tagasi_lukatud_arv, usaldus_protsent,
                        viimane_kinnitus_aeg, viimane_tagasilukatus_aeg, viimane_tegevus_aeg,
                        pohjendus, ajalugu
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
                """, (
                    canonical_name, iso_code, statutory_name,
                    confirmed, rejected, conf_score,
                    last_confirm, last_reject, now_str,
                    rationale, json.dumps(history, ensure_ascii=False)
                ))

            conn.commit()

        # Sünkroniseeri ka JSON faili
        self.sync_to_json(canonical_name)

        return self.get_learning_record(canonical_name, iso_code)

    def get_learning_record(self, canonical_name: str, iso_code: str) -> Optional[Dict[str, Any]]:
        """Tagastab konkreetse ISO õppimisandmed."""
        with self._connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT * FROM kanooniline_toode_tagasiside
                WHERE canonical_name = ? AND iso_kood = ?;
            """, (canonical_name, iso_code))
            row = cursor.fetchone()
            if row:
                d = dict(row)
                try:
                    d["ajalugu"] = json.loads(d["ajalugu"]) if d["ajalugu"] else []
                except Exception:
                    d["ajalugu"] = []
                return d
            return None

    def get_all_records_for_product(self, canonical_name: str) -> List[Dict[str, Any]]:
        """Tagastab kõik toote kohta salvestatud ISO õppimisandmed."""
        with self._connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT * FROM kanooniline_toode_tagasiside
                WHERE canonical_name = ?
                ORDER BY usaldus_protsent DESC, kinnitatud_arv DESC;
            """, (canonical_name,))
            rows = cursor.fetchall()
            results = []
            for r in rows:
                d = dict(r)
                try:
                    d["ajalugu"] = json.loads(d["ajalugu"]) if d["ajalugu"] else []
                except Exception:
                    d["ajalugu"] = []
                results.append(d)
            return results

    def get_all_learning_records(self) -> List[Dict[str, Any]]:
        """Tagastab kogu õppimisbaasi."""
        with self._connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT * FROM kanooniline_toode_tagasiside
                ORDER BY viimane_tegevus_aeg DESC, usaldus_protsent DESC;
            """)
            rows = cursor.fetchall()
            results = []
            for r in rows:
                d = dict(r)
                try:
                    d["ajalugu"] = json.loads(d["ajalugu"]) if d["ajalugu"] else []
                except Exception:
                    d["ajalugu"] = []
                results.append(d)
            return results

    def sync_to_json(self, canonical_name: Optional[str] = None):
        """Uuendab kanoonilise toote õppimisandmeid data/canonical_products.json failis."""
        if not os.path.exists(CANONICAL_JSON_PATH):
            return

        try:
            with open(CANONICAL_JSON_PATH, "r", encoding="utf-8") as f:
                prods = json.load(f)

            records_by_canon = {}
            for r in self.get_all_learning_records():
                c_name = r["canonical_name"]
                if c_name not in records_by_canon:
                    records_by_canon[c_name] = []
                records_by_canon[c_name].append({
                    "iso_code": r["iso_kood"],
                    "statutory_name": r["maarusejargne_nimetus"],
                    "confirmed_count": r["kinnitatud_arv"],
                    "rejected_count": r["tagasi_lukatud_arv"],
                    "confidence_pct": r["usaldus_protsent"],
                    "last_confirmed_at": r["viimane_kinnitus_aeg"],
                    "last_rejected_at": r["viimane_tagasilukatus_aeg"],
                    "rationale": r["pohjendus"]
                })

            for p in prods:
                c_name = p.get("canonical_name")
                if c_name in records_by_canon:
                    p["learned_feedback"] = records_by_canon[c_name]

            with open(CANONICAL_JSON_PATH, "w", encoding="utf-8") as f:
                json.dump(prods, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print("Viga canonical_products.json sünkroniseerimisel:", e)

    def seed_initial_examples(self):
        """
        Lisab kasutaja näidatud algsed näited (nt OTICON INTENT ja OTTOBOCK GALEO).
        Kui need on juba olemas, jäetakse vahele.
        """
        # 1. Oticon Intent 22.06.15.01 (kinnitatud 10 korda, tagasi lükatud 0 korda, usaldus 98%)
        existing = self.get_learning_record("OTICON INTENT", "22.06.15.01")
        if not existing:
            with self._connection() as conn:
                cursor = conn.cursor()
                now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                cursor.execute("""
                    INSERT INTO kanooniline_toode_tagasiside (
                        canonical_name, iso_kood, maarusejargne_nimetus,
                        kinnitatud_arv, tagasi_lukatud_arv, usaldus_protsent,
                        viimane_kinnitus_aeg, viimane_tegevus_aeg, pohjendus, ajalugu
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
                """, (
                    "OTICON INTENT",
                    "22.06.15.01",
                    "kõrvatagused kuulmisabivahendid - aktiivsusgrupp I",
                    10,
                    0,
                    98.0,
                    now_str,
                    now_str,
                    "Kinnitatud aktiivsusgrupile I vastavaks arstitõendite alusel",
                    json.dumps([{
                        "action": "CONFIRM",
                        "timestamp": now_str,
                        "rationale": "Kinnitatud aktiivsusgrupile I vastavaks arstitõendite alusel (10 edukat menetlust)",
                        "user": "Spetsialist",
                        "confidence_after": 98.0
                    }], ensure_ascii=False)
                ))
                conn.commit()

        # 2. Oticon Intent 22.06.15.02 (aktiivsusgrupp II - kinnitatud 4 korda)
        existing2 = self.get_learning_record("OTICON INTENT", "22.06.15.02")
        if not existing2:
            with self._connection() as conn:
                cursor = conn.cursor()
                now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                cursor.execute("""
                    INSERT INTO kanooniline_toode_tagasiside (
                        canonical_name, iso_kood, maarusejargne_nimetus,
                        kinnitatud_arv, tagasi_lukatud_arv, usaldus_protsent,
                        viimane_kinnitus_aeg, viimane_tegevus_aeg, pohjendus, ajalugu
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
                """, (
                    "OTICON INTENT",
                    "22.06.15.02",
                    "kõrvatagused kuulmisabivahendid - aktiivsusgrupp II",
                    4,
                    0,
                    95.0,
                    now_str,
                    now_str,
                    "Kinnitatud aktiivsusgrupi II arstitõendiga",
                    json.dumps([{
                        "action": "CONFIRM",
                        "timestamp": now_str,
                        "rationale": "Kinnitatud aktiivsusgrupi II arstitõendiga",
                        "user": "Spetsialist",
                        "confidence_after": 95.0
                    }], ensure_ascii=False)
                ))
                conn.commit()

        # 3. Ottobock Galeo 06.24.41.07 (kinnitatud 12 korda, 0 tagasi lükatud, usaldus 98.3%)
        existing3 = self.get_learning_record("OTTOBOCK GALEO", "06.24.41.07")
        if not existing3:
            with self._connection() as conn:
                cursor = conn.cursor()
                now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                cursor.execute("""
                    INSERT INTO kanooniline_toode_tagasiside (
                        canonical_name, iso_kood, maarusejargne_nimetus,
                        kinnitatud_arv, tagasi_lukatud_arv, usaldus_protsent,
                        viimane_kinnitus_aeg, viimane_tegevus_aeg, pohjendus, ajalugu
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
                """, (
                    "OTTOBOCK GALEO",
                    "06.24.41.07",
                    "proteesi sisevoodrid (lainerid) sääreproteesidele",
                    12,
                    0,
                    98.3,
                    now_str,
                    now_str,
                    "Otsene vaste säärelainerile (TT: 6Y92, 6Y93, 6Y95)",
                    json.dumps([{
                        "action": "CONFIRM",
                        "timestamp": now_str,
                        "rationale": "Otsene vaste säärelainerile (TT: 6Y92, 6Y93, 6Y95)",
                        "user": "Spetsialist",
                        "confidence_after": 98.3
                    }], ensure_ascii=False)
                ))
                conn.commit()

        self.sync_to_json()


_learning_service_instance: Optional[CanonicalLearningService] = None

def get_canonical_learning_service(db_path: str = DEFAULT_DB_PATH) -> CanonicalLearningService:
    global _learning_service_instance
    if _learning_service_instance is None:
        _learning_service_instance = CanonicalLearningService(db_path=db_path)
    return _learning_service_instance
