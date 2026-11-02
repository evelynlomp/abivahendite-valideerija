"""Sotsiaalkindlustusameti ja Sotsiaalministeeriumi määruse nr 74 abivahendite loetelu - ametlik klassifikaator (Tõeallikas)."""

import os
import re
import sqlite3
import openpyxl
from contextlib import contextmanager
from typing import Optional, List, Dict, Any
from src.normalizer import clean_text, normalize_iso, normalize_statutory_name


class MinistryClassifier:
    """
    Sotsiaalkindlustusameti ja Sotsiaalministeeriumi määruse nr 74 ametlik loetelu (Püsiv tõeallikas / Source of Truth).
    
    Seisuga: alates 01.10.2026 (Abivahendite otsimootor).
    Haldab ametlikke ISO-koode, määrusejärgseid nimetusi, valdkondi, liike, piirhindu ja piiranguid.
    Laaditakse süsteemi andmebaasi (data/valideer.db) ja seda ei küsita kasutajalt igakuiselt.
    """

    FILE_PATH = "data/Abivahendite_otsimootor_al.01.10.2026.xlsx"
    XLSB_PATH = "data/Abivahendite_otsimootor_al.01.10.2026.xlsb"

    def __init__(self, db_path: str = "data/valideer.db"):
        self.db_path = db_path
        self._iso_cache: Dict[str, Dict[str, Any]] = {}
        os.makedirs(os.path.dirname(os.path.abspath(db_path)), exist_ok=True)
        self._init_db()
        self.ensure_loaded()
        self._refresh_cache()

    def _refresh_cache(self) -> None:
        self._iso_cache = {}
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM ametlik_klassifikaator")
            for row in cursor.fetchall():
                d = dict(row)
                self._iso_cache[d["iso_kood_puhas"]] = d

    @contextmanager
    def _get_connection(self):
        conn = sqlite3.connect(self.db_path, timeout=30.0)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
            conn.commit()
        finally:
            conn.close()

    def _init_db(self) -> None:
        """Loob klassifikaatori tabeli andmebaasis täieliku 22-veerulise struktuuriga."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            # Kontrollime, kas olemasolev tabel vajab uuendamist
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='ametlik_klassifikaator'")
            if cursor.fetchone():
                cursor.execute("PRAGMA table_info(ametlik_klassifikaator)")
                cols = [r["name"] for r in cursor.fetchall()]
                if "valdkond" not in cols:
                    cursor.execute("DROP TABLE ametlik_klassifikaator")

            cursor.execute("""
                CREATE TABLE IF NOT EXISTS ametlik_klassifikaator (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    iso_kood TEXT NOT NULL,
                    iso_kood_puhas TEXT NOT NULL,
                    maarusejargne_nimetus TEXT NOT NULL,
                    maarusejargne_nimetus_norm TEXT NOT NULL,
                    valdkond TEXT,
                    liik TEXT,
                    tapsustus TEXT,
                    kasutusaeg TEXT,
                    tehingu_liik TEXT,
                    piirlimiit TEXT,
                    piirmaar TEXT,
                    piirhind_uur REAL,
                    piirhind_muuk REAL,
                    omaosaluse_miinimum TEXT,
                    uhik TEXT,
                    kirjeldus TEXT,
                    eelduskood TEXT,
                    valistav_kood TEXT,
                    hooldus_sagedus TEXT,
                    vajaduse_tuvastaja TEXT,
                    individuaalne_i TEXT,
                    hooldusteenus_h TEXT,
                    CONSTRAINT unikaalne_iso UNIQUE (iso_kood_puhas)
                )
            """)
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_klass_iso ON ametlik_klassifikaator(iso_kood_puhas)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_klass_nimetus ON ametlik_klassifikaator(maarusejargne_nimetus_norm)")
            conn.commit()

    def ensure_loaded(self, force: bool = False) -> int:
        """
        Laadib ametliku klassifikaatori failist andmebaasi, kui tabel on tühi või force=True.
        Tagastab laaditud kirjete arvu.
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM ametlik_klassifikaator")
            count = cursor.fetchone()[0]
            # Kontrollime ka, kas tabelis on olemas uus 'valdkond' veerg
            cursor.execute("PRAGMA table_info(ametlik_klassifikaator)")
            cols = [r["name"] for r in cursor.fetchall()]
            has_valdkond = "valdkond" in cols
            if count > 0 and has_valdkond and not force:
                return count

        return self.reload_from_file()

    def reload_from_file(self) -> int:
        """Laadib uue tõeallika faili (Abivahendite otsimootor) andmebaasi."""
        target_path = self.FILE_PATH if os.path.exists(self.FILE_PATH) else self.XLSB_PATH
        if not os.path.exists(target_path):
            return 0

        # Kui tegu on XLSX failiga, loeme openpyxl-iga
        if target_path.endswith(".xlsx"):
            wb = openpyxl.load_workbook(target_path, data_only=True)
            ws_andmed = wb["Määruse andmed"] if "Määruse andmed" in wb.sheetnames else wb.active
            ws_abi = wb["Abivahendid"] if "Abivahendid" in wb.sheetnames else None

            tax_map = {}
            if ws_abi:
                for r in list(ws_abi.iter_rows(values_only=True))[1:]:
                    if r and len(r) >= 4 and r[3]:
                        iso_k = str(r[3]).strip()
                        tax_map[iso_k] = (str(r[0] or "").strip(), str(r[1] or "").strip())

            rows = list(ws_andmed.iter_rows(values_only=True))
        else:
            # XLSB fallback
            import pandas as pd
            df_andmed = pd.read_excel(target_path, sheet_name="Määruse andmed", header=None, engine="pyxlsb")
            df_abi = pd.read_excel(target_path, sheet_name="Abivahendid", engine="pyxlsb")
            tax_map = {}
            for _, r in df_abi.iterrows():
                if pd.notna(r.iloc[3]):
                    tax_map[str(r.iloc[3]).strip()] = (str(r.iloc[0] or "").strip(), str(r.iloc[1] or "").strip())
            rows = [list(r) for _, r in df_andmed.iterrows()]

        header_idx = -1
        for idx, r in enumerate(rows):
            if r and any("ISO-kood" in str(c or "") for c in r):
                header_idx = idx
                break

        if header_idx == -1:
            header_idx = 3

        data_rows = rows[header_idx + 1:]
        loaded = 0

        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM ametlik_klassifikaator")

            for r in data_rows:
                if not r or not r[0]:
                    continue

                raw_iso = str(r[0]).strip()
                iso_clean = normalize_iso(raw_iso)
                if not iso_clean:
                    continue

                name = str(r[1]).strip() if len(r) > 1 and r[1] is not None else ""
                name_norm = normalize_statutory_name(name)
                valdkond, liik = tax_map.get(raw_iso, ("", ""))
                tapsustus = str(r[2]).strip() if len(r) > 2 and r[2] is not None else ""
                kasutusaeg = str(r[3]).strip() if len(r) > 3 and r[3] is not None else ""

                tehing_raw = str(r[4]).strip() if len(r) > 4 and r[4] is not None else ""
                if "osta ja" in tehing_raw.lower():
                    tehing_liik = "M/Ü"
                elif "vaid osta" in tehing_raw.lower():
                    tehing_liik = "M"
                elif "vaid üür" in tehing_raw.lower() or "vaid r" in tehing_raw.lower():
                    tehing_liik = "Ü"
                else:
                    tehing_liik = tehing_raw

                piirlimiit = str(r[5]).strip() if len(r) > 5 and r[5] is not None else ""
                piirmaar = str(r[6]).strip() if len(r) > 6 and r[6] is not None else ""

                uur_text = str(r[7]).strip() if len(r) > 7 and r[7] is not None else ""
                u_match = re.search(r"kuni\s*(\d+(?:[,\.]\d+)?)\s*eurot", uur_text, re.I)
                piirhind_uur = float(u_match.group(1).replace(",", ".")) if u_match else None

                muuk_text = str(r[8]).strip() if len(r) > 8 and r[8] is not None else ""
                m_match = re.search(r"kuni\s*(\d+(?:[,\.]\d+)?)\s*eurot", muuk_text, re.I)
                piirhind_muuk = float(m_match.group(1).replace(",", ".")) if m_match else None

                omaosalus_min = str(r[9]).strip() if len(r) > 9 and r[9] is not None else ""
                uhik = str(r[10]).strip() if len(r) > 10 and r[10] is not None else ""
                kirjeldus = str(r[11]).strip() if len(r) > 11 and r[11] is not None else ""
                eelduskood = str(r[12]).strip() if len(r) > 12 and r[12] is not None else ""
                valistav_kood = str(r[13]).strip() if len(r) > 13 and r[13] is not None else ""
                hooldus_sagedus = str(r[14]).strip() if len(r) > 14 and r[14] is not None else ""
                vajaduse_tuvastaja = str(r[15]).strip() if len(r) > 15 and r[15] is not None else ""
                individuaalne_i = str(r[16]).strip() if len(r) > 16 and r[16] is not None else ""
                hooldusteenus_h = str(r[17]).strip() if len(r) > 17 and r[17] is not None else ""

                cursor.execute("""
                    INSERT OR REPLACE INTO ametlik_klassifikaator (
                        iso_kood, iso_kood_puhas, maarusejargne_nimetus, maarusejargne_nimetus_norm,
                        valdkond, liik, tapsustus, kasutusaeg, tehingu_liik, piirlimiit, piirmaar,
                        piirhind_uur, piirhind_muuk, omaosaluse_miinimum, uhik, kirjeldus,
                        eelduskood, valistav_kood, hooldus_sagedus, vajaduse_tuvastaja,
                        individuaalne_i, hooldusteenus_h
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    raw_iso, iso_clean, name, name_norm,
                    valdkond, liik, tapsustus, kasutusaeg, tehing_liik, piirlimiit, piirmaar,
                    piirhind_uur, piirhind_muuk, omaosalus_min, uhik, kirjeldus,
                    eelduskood, valistav_kood, hooldus_sagedus, vajaduse_tuvastaja,
                    individuaalne_i, hooldusteenus_h
                ))
                loaded += 1

            conn.commit()

        self._refresh_cache()
        return loaded

    def count(self) -> int:
        """Tagastab klassifikaatoris olevate ametlike kirjete arvu."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM ametlik_klassifikaator")
            return cursor.fetchone()[0]

    def get_by_iso(self, raw_iso: str) -> Optional[Dict[str, Any]]:
        """Otsib ametlikku klassifikatsiooni ISO-koodi järgi (O(1) mälupuhvriga)."""
        clean_code = normalize_iso(raw_iso)
        if not clean_code:
            return None

        if clean_code in self._iso_cache:
            return self._iso_cache[clean_code]

        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM ametlik_klassifikaator WHERE iso_kood_puhas = ?", (clean_code,))
            row = cursor.fetchone()
            if row:
                d = dict(row)
                self._iso_cache[clean_code] = d
                return d
        return None

    def is_valid_iso(self, raw_iso: str) -> bool:
        """Kontrollib, kas ISO-kood eksisteerib Sotsiaalkindlustusameti loetelus."""
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
                   OR valdkond LIKE ?
                   OR liik LIKE ?
                ORDER BY iso_kood ASC
                LIMIT ?
            """, (q_like, q_iso, q_like, q_like, q_like, limit))
            return [dict(r) for r in cursor.fetchall()]
