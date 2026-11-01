"""Õppiva teadmistebaasi (Knowledge Base) moodul.

Säilitab AINULT kasutaja kinnitatud teadmised ja valideerimise ajaloo,
mitte töödeldud Exceli ridu ega isikuandmeid.
"""

import sqlite3
import os
import json
from datetime import datetime
from typing import Optional, List, Dict, Any
from contextlib import contextmanager


class KnowledgeBase:
    """
    Haldab kinnitatud toodete seoseid ja õppimise ajalugu.
    """

    def __init__(self, db_path: str = "data/valideer.db"):
        self.db_path = db_path
        os.makedirs(os.path.dirname(os.path.abspath(db_path)), exist_ok=True)
        self._init_db()

    @contextmanager
    def _connection(self):
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
        finally:
            conn.close()

    def _init_db(self) -> None:
        """Loob teadmistebaasi tabeli ja indeksid, kui neid veel pole."""
        with self._connection() as conn:
            cursor = conn.cursor()
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
                    CONSTRAINT unikaalne_kiri UNIQUE (normaliseeritud_nimetus, ametlik_toode, iso_kood)
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
        Otsib seost teadmistebaasist enne uut otsingut.
        Eelistusjärjestus:
        1. Täpne normaliseeritud vaste
        2. Täpne algne vaste
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
        iso_kood: str,
        maarusejargne_nimetus: str
    ) -> Dict[str, Any]:
        """
        Salvestab spetsialisti poolt kinnitatud uue seose või uuendab olemasolevat.
        Salvestab valideerimise ajaloo ja tõstab usaldustaset.
        """
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        with self._connection() as conn:
            cursor = conn.cursor()

            # Kontrollime, kas kirje juba eksisteerib
            cursor.execute("""
                SELECT id, kinnituste_arv, valideerimise_ajalugu FROM teadmistebaas
                WHERE normaliseeritud_nimetus = ? AND ametlik_toode = ? AND iso_kood = ?
            """, (normaliseeritud_nimetus, ametlik_toode, iso_kood))
            existing = cursor.fetchone()

            if existing:
                record_id = existing["id"]
                new_count = existing["kinnituste_arv"] + 1
                new_confidence = self.calculate_confidence(new_count)

                # Lisa ajaloo kirje
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
                        maarusejargne_nimetus = ?,
                        viimane_valideerimine = ?,
                        valideerimise_ajalugu = ?
                    WHERE id = ?
                """, (
                    new_count,
                    new_confidence,
                    maarusejargne_nimetus,
                    now,
                    json.dumps(history, ensure_ascii=False),
                    record_id
                ))
            else:
                new_count = 1
                new_confidence = self.calculate_confidence(new_count)
                history = [{
                    "aeg": now,
                    "syndmus": "esmane_kinnitus_loodud",
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
                    iso_kood,
                    maarusejargne_nimetus,
                    new_confidence,
                    new_count,
                    now,
                    json.dumps(history, ensure_ascii=False)
                ))
                record_id = cursor.lastrowid

            conn.commit()

            cursor.execute("SELECT * FROM teadmistebaas WHERE id = ?", (record_id,))
            return dict(cursor.fetchone())

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
                # Säilitame viimased 20 sündmust
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
        """Tagastab teadmistebaasis olevate kirjete koguarvu."""
        with self._connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM teadmistebaas")
            return cursor.fetchone()[0]

    def delete(self, record_id: int) -> bool:
        """Kustutab konkreetse kirje (vajalik ekslike kinnituste tühistamiseks)."""
        with self._connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM teadmistebaas WHERE id = ?", (record_id,))
            conn.commit()
            return cursor.rowcount > 0
