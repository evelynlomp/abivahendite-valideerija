"""Õppiva teadmistebaasi (Knowledge Base) moodul.

PÕHIPRINTSIIP:
1. Reeglid on rangelt VAJADUSPÕHISED: reegel salvestatakse ainult siis, kui süsteemi automaatne
   tuvastuskindlus on madal ja vajab spetsialisti kinnitust. 100% klappivaid tooteid ei dubleerita.
2. Süsteem õpib AINULT aliasnimesid ja arvetel esinevaid ebatavalisi kirjapilte seoses ametliku tootega.
3. Süsteem EI ÕPI arvelt ISO-koode ega määrusejärgseid nimetusi: need pärinevad alati
   ametlikest tõeallikatest (ametlik_klassifikaator ja tooteregister).
"""

import sqlite3
import os
import json
from datetime import datetime
from typing import Optional, List, Dict, Any
from contextlib import contextmanager


class KnowledgeBase:
    """
    Haldab arvetel esinevate tootenimede ja kanooniliste toodete vahelisi seoseid (aliased).
    """

    def __init__(self, db_path: str = "data/valideer.db"):
        self.db_path = db_path
        os.makedirs(os.path.dirname(os.path.abspath(db_path)), exist_ok=True)
        self._init_db()

    @contextmanager
    def _connection(self):
        conn = sqlite3.connect(self.db_path, timeout=30.0)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
        finally:
            conn.close()

    def _init_db(self) -> None:
        """Loob teadmistebaasi tabeli ja indeksid, kui neid veel pole."""
        with self._connection() as conn:
            cursor = conn.cursor()
            cursor.execute("PRAGMA journal_mode=WAL;")
            cursor.execute("PRAGMA busy_timeout=30000;")
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS teadmistebaas (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    algne_nimetus TEXT NOT NULL,
                    normaliseeritud_nimetus TEXT NOT NULL,
                    ametlik_toode TEXT NOT NULL,
                    iso_kood TEXT NOT NULL,
                    maarusejargne_nimetus TEXT NOT NULL,
                    usaldustase REAL DEFAULT 0.85,
                    kinnituste_arv INTEGER DEFAULT 1,
                    viimane_valideerimine TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    valideerimise_ajalugu TEXT DEFAULT '[]',
                    CONSTRAINT unikaalne_kiri UNIQUE (normaliseeritud_nimetus, ametlik_toode)
                )
            """)
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_kb_norm ON teadmistebaas(normaliseeritud_nimetus)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_kb_algne ON teadmistebaas(algne_nimetus)")
            conn.commit()

    @staticmethod
    def calculate_confidence(confirmations: int) -> float:
        """
        Arvutab usaldustaseme kinnituste arvu põhjal (asümptootiliselt läheneb 1.0-le).
        1 kinnitus -> 0.85
        2 kinnitust -> 0.925
        3 kinnitust -> 0.95
        5+ kinnitust -> 0.98+
        """
        if confirmations <= 0:
            return 0.50
        confidence = 1.0 - (0.15 / confirmations)
        return round(min(1.0, max(0.50, confidence)), 3)

    def lookup(self, raw_name: str, normalized_name: str) -> Optional[Dict[str, Any]]:
        """
        Otsib toote seost (aliast) teadmistebaasist.
        Tagastab kirje, kus on näidatud seos ametliku tootega ('ametlik_toode').
        """
        if not normalized_name and not raw_name:
            return None

        with self._connection() as conn:
            cursor = conn.cursor()

            # 1. Otsing normaliseeritud nime järgi
            if normalized_name:
                cursor.execute("""
                    SELECT * FROM teadmistebaas 
                    WHERE normaliseeritud_nimetus = ? 
                    ORDER BY usaldustase DESC, kinnituste_arv DESC 
                    LIMIT 1
                """, (normalized_name,))
                row = cursor.fetchone()
                if row:
                    return dict(row)

            # 2. Otsing algse nime järgi
            if raw_name:
                cursor.execute("""
                    SELECT * FROM teadmistebaas 
                    WHERE algne_nimetus = ? 
                    ORDER BY usaldustase DESC, kinnituste_arv DESC 
                    LIMIT 1
                """, (raw_name.strip(),))
                row = cursor.fetchone()
                if row:
                    return dict(row)

        return None

    def confirm(
        self,
        algne_nimetus: str,
        normaliseeritud_nimetus: str,
        ametlik_toode: str,
        iso_kood: str = "",
        maarusejargne_nimetus: str = ""
    ) -> Dict[str, Any]:
        """
        Kinnitab arvel esitatud kirjapildi seose ametliku tootega (aliase õppimine).
        """
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        with self._connection() as conn:
            cursor = conn.cursor()

            cursor.execute("""
                SELECT id, kinnituste_arv, valideerimise_ajalugu FROM teadmistebaas
                WHERE normaliseeritud_nimetus = ? AND ametlik_toode = ?
            """, (normaliseeritud_nimetus, ametlik_toode))
            existing = cursor.fetchone()

            if existing:
                record_id = existing["id"]
                new_count = existing["kinnituste_arv"] + 1
                new_confidence = self.calculate_confidence(new_count)

                try:
                    history = json.loads(existing["valideerimise_ajalugu"] or "[]")
                except Exception:
                    history = []
                history.append({
                    "aeg": now,
                    "syndmus": "kinnitatud_spetsialisti_poolt",
                    "kinnitus_nr": new_count
                })

                cursor.execute("""
                    UPDATE teadmistebaas 
                    SET kinnituste_arv = ?, 
                        usaldustase = ?, 
                        iso_kood = ?,
                        maarusejargne_nimetus = ?,
                        viimane_valideerimine = ?,
                        valideerimise_ajalugu = ?
                    WHERE id = ?
                """, (
                    new_count,
                    new_confidence,
                    iso_kood or "",
                    maarusejargne_nimetus or "",
                    now,
                    json.dumps(history, ensure_ascii=False),
                    record_id
                ))
            else:
                new_count = 1
                new_confidence = self.calculate_confidence(new_count)
                history = [{
                    "aeg": now,
                    "syndmus": "esmane_seos_loodud",
                    "kinnitus_nr": 1
                }]

                cursor.execute("""
                    INSERT INTO teadmistebaas (
                        algne_nimetus, 
                        normaliseeritud_nimetus, 
                        ametlik_toode, 
                        iso_kood, 
                        maarusejargne_nimetus, 
                        usaldustase, 
                        kinnituste_arv, 
                        viimane_valideerimine,
                        valideerimise_ajalugu
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    algne_nimetus,
                    normaliseeritud_nimetus,
                    ametlik_toode,
                    iso_kood or "",
                    maarusejargne_nimetus or "",
                    new_confidence,
                    new_count,
                    now,
                    json.dumps(history, ensure_ascii=False)
                ))
                record_id = cursor.lastrowid

            conn.commit()

            cursor.execute("SELECT * FROM teadmistebaas WHERE id = ?", (record_id,))
            return dict(cursor.fetchone())

    def confirm_mapping(
        self,
        raw_name: str,
        normalized_name: str,
        official_product: str,
        iso_code: str = "",
        statutory_name: str = "",
        confidence: float = 1.0
    ) -> Dict[str, Any]:
        """Mugavusmeetod aliase kinnitamiseks."""
        return self.confirm(
            algne_nimetus=raw_name,
            normaliseeritud_nimetus=normalized_name,
            ametlik_toode=official_product,
            iso_kood=iso_code,
            maarusejargne_nimetus=statutory_name
        )

    def record_validation(self, record_id: int, status: str) -> None:
        """Salvestab valideerimise ajatempli ja sündmuse ajalukku."""
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        with self._connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT valideerimise_ajalugu FROM teadmistebaas WHERE id = ?", (record_id,))
            row = cursor.fetchone()
            if row:
                try:
                    history = json.loads(row["valideerimise_ajalugu"] or "[]")
                except Exception:
                    history = []
                history.append({"aeg": now, "syndmus": f"valideeritud_{status}"})
                history = history[-20:]

                cursor.execute("""
                    UPDATE teadmistebaas 
                    SET viimane_valideerimine = ?,
                        valideerimise_ajalugu = ?
                    WHERE id = ?
                """, (now, json.dumps(history, ensure_ascii=False), record_id))
                conn.commit()

    def get_all(self) -> List[Dict[str, Any]]:
        """Tagastab kõik teadmistebaasi kirjed (kuvamiseks ja ekspordiks)."""
        with self._connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM teadmistebaas ORDER BY viimane_valideerimine DESC")
            return [dict(r) for r in cursor.fetchall()]

    def count(self) -> int:
        """Tagastab kinnitatud aliaste koguarvu."""
        with self._connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM teadmistebaas")
            return cursor.fetchone()[0]

    def delete(self, record_id: int) -> bool:
        """Kustutab seose (vajalik ekslike kinnituste tühistamiseks)."""
        with self._connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM teadmistebaas WHERE id = ?", (record_id,))
            conn.commit()
            return cursor.rowcount > 0
