"""Õppiva teadmistebaasi (Knowledge Base) moodul.

PÕHIPRINTSIIP:
1. Reeglid on rangelt VAJADUSPÕHISED: reegel salvestatakse ainult siis, kui süsteemi automaatne
   tuvastuskindlus on madal ja vajab spetsialisti kinnitust või pärineb eelkontrollitud
   ajaloolistest andmetest (SOURCE = VERIFIED_HISTORICAL_DATA).
2. Süsteem toetab kahetasemelist mudelit (MODEL = FAMILY_VARIANT_RULE):
   - Tase A: Tooteperekond (tooteperekond)
   - Tase B: Klassifitseeritav variant (klassifitseeritav_variant)
3. Kõik hulgimpordid on varustatud auditijäljega (import_batch_id) ja täielikult pööratavad.
"""

import sqlite3
import os
import json
from datetime import datetime
from typing import Optional, List, Dict, Any
from contextlib import contextmanager


class KnowledgeBase:
    """
    Haldab arvetel esinevate tootenimede, kanooniliste toodete, tooteperekondade
    ja variandireeglite vahelisi seoseid (aliased ja kahetasemelised reeglid).
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
        """Loob teadmistebaasi tabelid, lisab puuduvad veerud ja loob indeksid."""
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
                    tooteperekond TEXT DEFAULT '',
                    klassifitseeritav_variant TEXT DEFAULT '',
                    source TEXT DEFAULT 'SPECIALIST_CONFIRMATION',
                    confidence TEXT DEFAULT 'CONFIRMED',
                    model TEXT DEFAULT 'DIRECT_ALIAS',
                    import_batch_id TEXT DEFAULT NULL,
                    algfaili_esinemisi INTEGER DEFAULT 1,
                    CONSTRAINT unikaalne_kiri UNIQUE (normaliseeritud_nimetus, ametlik_toode)
                )
            """)

            # Ohutu skeemimigratsioon olemasolevale teadmistebaas tabelile
            cursor.execute("PRAGMA table_info(teadmistebaas)")
            existing_cols = {row["name"] for row in cursor.fetchall()}
            migrations = [
                ("tooteperekond", "TEXT DEFAULT ''"),
                ("klassifitseeritav_variant", "TEXT DEFAULT ''"),
                ("source", "TEXT DEFAULT 'SPECIALIST_CONFIRMATION'"),
                ("confidence", "TEXT DEFAULT 'CONFIRMED'"),
                ("model", "TEXT DEFAULT 'DIRECT_ALIAS'"),
                ("import_batch_id", "TEXT DEFAULT NULL"),
                ("algfaili_esinemisi", "INTEGER DEFAULT 1"),
            ]
            for col_name, col_def in migrations:
                if col_name not in existing_cols:
                    cursor.execute(f"ALTER TABLE teadmistebaas ADD COLUMN {col_name} {col_def}")

            # Kahetasemeliste variandireeglite tabel (Tooteperekond + Klassifitseeritav variant -> ISO)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS variandireeglid (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    tooteperekond TEXT NOT NULL,
                    klassifitseeritav_variant TEXT NOT NULL,
                    taielik_variandi_voti TEXT NOT NULL UNIQUE,
                    iso_kood TEXT NOT NULL,
                    maarusejargne_nimetus TEXT NOT NULL,
                    iso_maaramise_reegel TEXT DEFAULT '',
                    kirjapiltide_arv INTEGER DEFAULT 1,
                    esinemisi_kokku INTEGER DEFAULT 1,
                    naide_nimetus TEXT DEFAULT '',
                    source TEXT DEFAULT 'VERIFIED_HISTORICAL_DATA',
                    confidence TEXT DEFAULT 'CONFIRMED',
                    model TEXT DEFAULT 'FAMILY_VARIANT_RULE',
                    import_batch_id TEXT DEFAULT NULL,
                    loodud_aeg TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # Aliaste seoste tabel (kõik unikaalsed kirjapildid seotud tooteperekonna ja variandiga)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS teadmiste_aliased (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    algne_kirjapilt TEXT NOT NULL,
                    normaliseeritud_nimetus TEXT NOT NULL,
                    tooteperekond TEXT NOT NULL,
                    klassifitseeritav_variant TEXT NOT NULL,
                    ametlik_toode TEXT NOT NULL,
                    iso_kood TEXT NOT NULL,
                    maarusejargne_nimetus TEXT NOT NULL,
                    esinemisi_failis INTEGER DEFAULT 1,
                    source TEXT DEFAULT 'VERIFIED_HISTORICAL_DATA',
                    confidence TEXT DEFAULT 'CONFIRMED',
                    model TEXT DEFAULT 'FAMILY_VARIANT_RULE',
                    import_batch_id TEXT DEFAULT NULL,
                    loodud_aeg TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    CONSTRAINT unikaalne_alias UNIQUE (algne_kirjapilt, iso_kood)
                )
            """)

            # Impordi auditijälje tabel
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS impordi_audit (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    batch_id TEXT NOT NULL UNIQUE,
                    impordi_kuupaev TIMESTAMP NOT NULL,
                    allikas TEXT NOT NULL,
                    imporditud_teadmiste_arv INTEGER NOT NULL,
                    taiendatud_teadmiste_arv INTEGER NOT NULL,
                    uute_aliaste_arv INTEGER NOT NULL,
                    imporditud_variandireeglite_arv INTEGER NOT NULL,
                    vahele_jaetud_kirjete_arv INTEGER NOT NULL,
                    varukoopia_rada TEXT NOT NULL,
                    audit_json_rada TEXT NOT NULL,
                    staatus TEXT DEFAULT 'AKTIIVNE'
                )
            """)

            cursor.execute("CREATE INDEX IF NOT EXISTS idx_kb_norm ON teadmistebaas(normaliseeritud_nimetus)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_kb_algne ON teadmistebaas(algne_nimetus)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_kb_batch ON teadmistebaas(import_batch_id)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_kb_fam_var ON teadmistebaas(tooteperekond, klassifitseeritav_variant)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_vr_fvk ON variandireeglid(taielik_variandi_voti)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_al_norm ON teadmiste_aliased(normaliseeritud_nimetus)")
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

    def lookup_variant_rule(self, tooteperekond: str, klassifitseeritav_variant: str) -> Optional[Dict[str, Any]]:
        """Otsib kahetasemelise mudeli reeglit (Tooteperekond + Klassifitseeritav variant -> ISO)."""
        if not tooteperekond or not klassifitseeritav_variant:
            return None
        fvk = f"{tooteperekond} :: {klassifitseeritav_variant}"
        with self._connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT * FROM variandireeglid
                WHERE taielik_variandi_voti = ?
                LIMIT 1
            """, (fvk,))
            row = cursor.fetchone()
            return dict(row) if row else None

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

    def rollback_import(self, batch_id: Optional[str] = None) -> Dict[str, int]:
        """
        Võtab tagasi konkreetse hulgimpordi (või kõik VERIFIED_HISTORICAL_DATA kirjed, kui batch_id pole antud).
        """
        with self._connection() as conn:
            cursor = conn.cursor()
            if batch_id:
                cursor.execute("DELETE FROM teadmistebaas WHERE import_batch_id = ?", (batch_id,))
                del_kb = cursor.rowcount
                cursor.execute("DELETE FROM variandireeglid WHERE import_batch_id = ?", (batch_id,))
                del_vr = cursor.rowcount
                cursor.execute("DELETE FROM teadmiste_aliased WHERE import_batch_id = ?", (batch_id,))
                del_al = cursor.rowcount
                cursor.execute("UPDATE impordi_audit SET staatus = 'TAGASI_VOETUD' WHERE batch_id = ?", (batch_id,))
            else:
                cursor.execute("DELETE FROM teadmistebaas WHERE source = 'VERIFIED_HISTORICAL_DATA'")
                del_kb = cursor.rowcount
                cursor.execute("DELETE FROM variandireeglid WHERE source = 'VERIFIED_HISTORICAL_DATA'")
                del_vr = cursor.rowcount
                cursor.execute("DELETE FROM teadmiste_aliased WHERE source = 'VERIFIED_HISTORICAL_DATA'")
                del_al = cursor.rowcount
                cursor.execute("UPDATE impordi_audit SET staatus = 'TAGASI_VOETUD' WHERE staatus = 'AKTIIVNE'")
            conn.commit()
            return {
                "kustutatud_teadmisi": del_kb,
                "kustutatud_variandireegleid": del_vr,
                "kustutatud_aliaseid": del_al
            }

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
