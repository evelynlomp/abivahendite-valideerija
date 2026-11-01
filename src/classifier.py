"""Sotsiaalministeeriumi abivahendite loetelu - püsiv klassifikaatori moodul."""

import os
import sqlite3
import openpyxl
from typing import Optional, List, Dict, Any
from src.normalizer import clean_text, normalize_iso, normalize_statutory_name


class MinistryClassifier:
    """
    Sotsiaalministeeriumi abivahendite loetelu (Püsiv tõeallikas / Source of Truth).
    
    Haldab ametlikke ISO-koode, määrusejärgseid nimetusi ja piiranguid.
    Laaditakse süsteemi andmebaasi (data/valideer.db) käivitamisel ja seda ei küsita kasutajalt igakuiselt.
    """

    FILE_PATH = "data/Sotsiaalministeeriumi abivahendite loetelu.xlsx"

    def __init__(self, db_path: str = "data/valideer.db"):
        self.db_path = db_path
        os.makedirs(os.path.dirname(os.path.abspath(db_path)), exist_ok=True)
        self._init_db()
        self.ensure_loaded()

    def _get_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self) -> None:
        """Loob klassifikaatori tabeli andmebaasis."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS ametlik_klassifikaator (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    iso_kood TEXT NOT NULL,
                    iso_kood_puhas TEXT NOT NULL,
                    maarusejargne_nimetus TEXT NOT NULL,
                    maarusejargne_nimetus_norm TEXT NOT NULL,
                    tapsustus TEXT,
                    kasutusaeg TEXT,
                    tehingu_liik TEXT,
                    piirlimiit TEXT,
                    piirmaar TEXT,
                    piirhind_uur REAL,
                    piirhind_muuk REAL,
                    uhik TEXT,
                    kirjeldus TEXT,
                    CONSTRAINT unikaalne_iso UNIQUE (iso_kood_puhas)
                )
            """)
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_klass_iso ON ametlik_klassifikaator(iso_kood_puhas)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_klass_nimetus ON ametlik_klassifikaator(maarusejargne_nimetus_norm)")
            conn.commit()

    def ensure_loaded(self) -> int:
        """
        Laadib ametliku klassifikaatori Exceli failist andmebaasi, kui tabel on tühi.
        Tagastab laaditud kirjete arvu.
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM ametlik_klassifikaator")
            count = cursor.fetchone()[0]
            if count > 0:
                return count

        if not os.path.exists(self.FILE_PATH):
            return 0

        # Laadi Exceli fail
        wb = openpyxl.load_workbook(self.FILE_PATH, data_only=True)
        ws = wb.active

        rows = list(ws.iter_rows(values_only=True))
        if not rows:
            return 0

        header_idx = -1
        for idx, row in enumerate(rows):
            if row and any("ISO-kood" in str(cell or "") for cell in row):
                header_idx = idx
                break

        if header_idx == -1:
            header_idx = 0

        data_rows = rows[header_idx + 1:]
        loaded = 0

        with self._get_connection() as conn:
            cursor = conn.cursor()

            for r in data_rows:
                if not r or not r[0]:
                    continue

                raw_iso = str(r[0]).strip()
                iso_clean = normalize_iso(raw_iso)
                if not iso_clean:
                    continue

                name = str(r[1]).strip() if len(r) > 1 and r[1] is not None else ""
                name_norm = normalize_statutory_name(name)
                tapsustus = str(r[2]).strip() if len(r) > 2 and r[2] is not None else ""
                kasutusaeg = str(r[3]).strip() if len(r) > 3 and r[3] is not None else ""
                tehingu_liik = str(r[4]).strip() if len(r) > 4 and r[4] is not None else ""
                piirlimiit = str(r[5]).strip() if len(r) > 5 and r[5] is not None else ""
                piirmaar = str(r[8]).strip() if len(r) > 8 and r[8] is not None else ""

                try:
                    piirhind_uur = float(str(r[9]).replace(",", ".")) if len(r) > 9 and r[9] else None
                except (ValueError, TypeError):
                    piirhind_uur = None

                try:
                    piirhind_muuk = float(str(r[10]).replace(",", ".")) if len(r) > 10 and r[10] else None
                except (ValueError, TypeError):
                    piirhind_muuk = None

                uhik = str(r[11]).strip() if len(r) > 11 and r[11] is not None else ""
                kirjeldus = str(r[12]).strip() if len(r) > 12 and r[12] is not None else ""

                cursor.execute("""
                    INSERT OR REPLACE INTO ametlik_klassifikaator (
                        iso_kood,
                        iso_kood_puhas,
                        maarusejargne_nimetus,
                        maarusejargne_nimetus_norm,
                        tapsustus,
                        kasutusaeg,
                        tehingu_liik,
                        piirlimiit,
                        piirmaar,
                        piirhind_uur,
                        piirhind_muuk,
                        uhik,
                        kirjeldus
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    raw_iso,
                    iso_clean,
                    name,
                    name_norm,
                    tapsustus,
                    kasutusaeg,
                    tehingu_liik,
                    piirlimiit,
                    piirmaar,
                    piirhind_uur,
                    piirhind_muuk,
                    uhik,
                    kirjeldus
                ))
                loaded += 1

            conn.commit()

        return loaded

    def count(self) -> int:
        """Tagastab klassifikaatoris olevate ametlike kirjete arvu."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM ametlik_klassifikaator")
            return cursor.fetchone()[0]

    def get_by_iso(self, raw_iso: str) -> Optional[Dict[str, Any]]:
        """Otsib ametlikku klassifikatsiooni ISO-koodi järgi."""
        clean_code = normalize_iso(raw_iso)
        if not clean_code:
            return None

        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM ametlik_klassifikaator WHERE iso_kood_puhas = ?", (clean_code,))
            row = cursor.fetchone()
            if row:
                return dict(row)
        return None

    def is_valid_iso(self, raw_iso: str) -> bool:
        """Kontrollib, kas ISO-kood eksisteerib Sotsiaalministeeriumi loetelus."""
        return self.get_by_iso(raw_iso) is not None

    def get_statutory_name(self, raw_iso: str) -> Optional[str]:
        """Tagastab ISO-koodile vastava ametliku määrusejärgse nimetuse."""
        res = self.get_by_iso(raw_iso)
        return res["maarusejargne_nimetus"] if res else None

    def get_all_classifications(self) -> List[Dict[str, Any]]:
        """Tagastab kõik klassifikaatori kirjed (rippmenüüde ja ülevaate jaoks)."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT * FROM ametlik_klassifikaator 
                WHERE LENGTH(iso_kood_puhas) >= 4
                ORDER BY iso_kood ASC
            """)
            return [dict(r) for r in cursor.fetchall()]

    def search(self, query: str, limit: int = 20) -> List[Dict[str, Any]]:
        """Otsib klassifikaatorist märksõna või koodi järgi."""
        q_clean = clean_text(query)
        if not q_clean:
            return []

        q_like = f"%{q_clean}%"
        q_iso = f"%{normalize_iso(query)}%"

        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT * FROM ametlik_klassifikaator 
                WHERE maarusejargne_nimetus_norm LIKE ? 
                   OR iso_kood_puhas LIKE ?
                   OR tapsustus LIKE ?
                ORDER BY iso_kood ASC
                LIMIT ?
            """, (q_like, q_iso, q_like, limit))
            return [dict(r) for r in cursor.fetchall()]
