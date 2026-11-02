"""
AUTO_LEARN teadmiste, aliaste ja kahetasemeliste variandireeglite turvaline import
õppefailist 'data/Sept 15.09.xls' teadmistebaasi ('data/valideer.db').

Omadused:
- Teeb enne muutmist automaatse SQLite varukoopia.
- Impordib AINULT AUTO_LEARN kvalifitseeruvad kirjed (880 nimetust, 414 variandireeglit).
- Jätab LIKELY ja REVIEW kirjed täielikult vahele.
- Lisab tunnused:
    SOURCE = VERIFIED_HISTORICAL_DATA
    CONFIDENCE = CONFIRMED
    MODEL = FAMILY_VARIANT_RULE
- Ei loo dubleerivaid tooteperekondi: seob olemasolevate tooteperekondade ja kanooniliste toodetega.
- Salvestab täieliku auditijälje (JSON, Excel, Markdown ja SQLite tabel 'impordi_audit').
"""

import os
import sys
import json
import sqlite3
from datetime import datetime
from collections import Counter, defaultdict
import pandas as pd

ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, ROOT_DIR)

from src.normalizer import normalize_name, normalize_iso, format_iso_display
from src.classifier import MinistryClassifier
from src.restriction_engine import RestrictionEngine
from src.variant_classifier import VariantClassifier
from src.knowledge_base import KnowledgeBase
from src.product_registry_db import get_product_registry_db

BATCH_ID = "BATCH_SEPT_15_09_AUTO_LEARN"
SOURCE_FILE = "Sept 15.09.xls"
SOURCE_TAG = "VERIFIED_HISTORICAL_DATA"
CONFIDENCE_TAG = "CONFIRMED"
MODEL_TAG = "FAMILY_VARIANT_RULE"

SPECIALIST_PREFIXES = (
    "22.06.12.01", "22.06.12.02", "22.06.12.03",
    "22.06.15.01", "22.06.15.02", "22.06.15.03",
    "06.33.00", "06.24.", "06.18.", "06.30.",
    "12.22.", "12.23.", "18.09.21"
)

GENERIC_PLACEHOLDERS = {
    "ABIVAHEND", "ORTOOS", "ORTOOSID", "KUULDEAPARAAT", "RATASTOOL", "JALATS", "JALATSID",
    "TALLATUGI", "TALLATOED", "SISETALLAD", "VARUOSAD", "TARVIKUD", "REMONT", "HOOLDUS",
    "MÄHKMED", "ALUSLINA", "KARK", "KARGUD", "KEPP", "RULAATOR", "POTITOOL", "DUŠITOOL"
}


def create_db_backup(db_path: str, backup_dir: str) -> str:
    os.makedirs(backup_dir, exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = os.path.join(backup_dir, f"valideer_pre_auto_learn_{ts}.db")
    latest_path = os.path.join(backup_dir, "valideer_pre_auto_learn_latest.db")

    src_conn = sqlite3.connect(db_path)
    dst_conn = sqlite3.connect(backup_path)
    src_conn.backup(dst_conn)
    dst_conn.close()

    if not os.path.exists(latest_path):
        dst_latest = sqlite3.connect(latest_path)
        src_conn.backup(dst_latest)
        dst_latest.close()

    src_conn.close()
    return latest_path if os.path.exists(latest_path) else backup_path


def run_import():
    db_path = os.path.join(ROOT_DIR, "data", "valideer.db")
    xls_path = os.path.join(ROOT_DIR, "data", SOURCE_FILE)
    backup_dir = os.path.join(ROOT_DIR, "data", "backups")
    audit_dir = os.path.join(ROOT_DIR, "data", "audit_reports")
    os.makedirs(audit_dir, exist_ok=True)

    # 1. Varukoopia enne andmebaasi muutmist
    backup_path = create_db_backup(db_path, backup_dir)
    import_timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # 2. Laadi algfail ja abimoodulid
    df = pd.read_excel(xls_path, engine="xlrd")
    iso_col, stat_col, name_col = df.columns[0], df.columns[1], df.columns[2]

    raw_names = df[name_col].fillna("").astype(str).str.strip()
    raw_isos = df[iso_col].fillna("").astype(str).str.strip()
    raw_stats = df[stat_col].fillna("").astype(str).str.strip()

    norm_names = [normalize_name(n) for n in raw_names]
    norm_isos = [format_iso_display(normalize_iso(i)) for i in raw_isos]

    classifier = MinistryClassifier(db_path=db_path)
    reg_db = get_product_registry_db()
    kb = KnowledgeBase(db_path=db_path)

    # Puhasta võimalik varasem sama batch_id-ga proovikirje (idempotentsus)
    kb.rollback_import(BATCH_ID)

    # Vaatleme olemasolevaid tooteperekondi ja kanoonilisi tooteid
    existing_families_in_reg = set()
    for p in reg_db.get_all_products():
        pf = (p.get("product_line") or p.get("product_family") or "").strip().upper()
        on = (p.get("official_name") or "").strip().upper()
        if pf:
            existing_families_in_reg.add(pf)
        if on:
            existing_families_in_reg.add(on)

    norm_to_iso_counts = defaultdict(Counter)
    norm_to_stat_counts = defaultdict(Counter)
    norm_to_raw_counts = defaultdict(Counter)
    norm_to_raw_example = {}
    norm_to_stat_by_iso = {}

    for r_n, n_n, n_i, r_s in zip(raw_names, norm_names, norm_isos, raw_stats):
        if not n_n:
            continue
        norm_to_iso_counts[n_n][n_i] += 1
        norm_to_stat_counts[n_n][r_s.strip().lower()] += 1
        norm_to_raw_counts[n_n][r_n] += 1
        if n_n not in norm_to_raw_example:
            norm_to_raw_example[n_n] = r_n
        norm_to_stat_by_iso[(n_n, n_i)] = r_s

    norm_to_vc = {}
    variant_to_isos = defaultdict(Counter)
    for n_n, iso_c in norm_to_iso_counts.items():
        r_n = norm_to_raw_example[n_n]
        vc = VariantClassifier.analyze(r_n)
        norm_to_vc[n_n] = vc
        for iso_k, cnt in iso_c.items():
            variant_to_isos[vc["full_variant_key"]][iso_k] += cnt

    auto_learn_items = []
    skipped_items = []

    for n_n, iso_c in norm_to_iso_counts.items():
        r_n = norm_to_raw_example[n_n]
        vc = norm_to_vc[n_n]
        fam = vc["product_family"]
        var = vc["classifiable_variant"]
        fvk = vc["full_variant_key"]
        det = vc["determinant_type"]

        isos = list(iso_c.keys())
        top_iso, top_cnt = iso_c.most_common(1)[0]
        total_cnt = sum(iso_c.values())
        dom_purity = top_cnt / total_cnt if total_cnt > 0 else 1.0

        off_rec = classifier.get_by_iso(top_iso)
        stat_name = off_rec["maarusejargne_nimetus"] if off_rec else norm_to_stat_by_iso.get((n_n, top_iso), "")

        rest_ok, rest_msg, _ = RestrictionEngine.check_restrictions(top_iso, n_n)
        rest_fail = not rest_ok

        needs_specialist = any(top_iso.startswith(p) for p in SPECIALIST_PREFIXES) or "[SÕLTUB" in var
        is_generic = n_n in GENERIC_PLACEHOLDERS or len(n_n) < 4
        is_unspecified_variant = (
            any(u in var for u in ["MAHT TÄPSUSTAMATA", "MÕÕDUTA", "SUURUSETA"])
            or var in ("MEESTE SIDE", "NAISTE SIDE")
        )

        var_top_iso = variant_to_isos[fvk].most_common(1)[0][0]
        variant_iso_mismatch = (not needs_specialist) and (not is_unspecified_variant) and (top_iso != var_top_iso)

        is_clean_single = (len(isos) == 1 and len(norm_to_stat_counts[n_n]) == 1)
        is_high_purity_series = (total_cnt >= 20 and dom_purity >= 0.92 and top_iso == var_top_iso)

        if (
            not rest_fail
            and not variant_iso_mismatch
            and (is_clean_single or is_high_purity_series)
            and off_rec is not None
            and total_cnt >= 5
            and not needs_specialist
            and not is_generic
            and not is_unspecified_variant
        ):
            # Kontrollime, kas sama toode või tooteperekond juba eksisteerib
            exact_reg_match = reg_db.find_exact_alias(n_n)
            family_exists = (
                exact_reg_match is not None
                or fam.upper() in existing_families_in_reg
                or any(fam.upper() in ef or ef in fam.upper() for ef in existing_families_in_reg if len(ef) >= 5)
            )
            canonical_product = exact_reg_match["official_name"] if exact_reg_match else f"{fam} ({var})"

            auto_learn_items.append({
                "algne_nimetus": r_n,
                "normaliseeritud_nimetus": n_n,
                "ametlik_toode": canonical_product,
                "tooteperekond": fam,
                "klassifitseeritav_variant": var,
                "taielik_variandi_voti": fvk,
                "iso_kood": top_iso,
                "maarusejargne_nimetus": stat_name,
                "iso_maaramise_reegel": det,
                "esinemisi_failis": total_cnt,
                "kinnitatud_ridu": top_cnt,
                "unikaalseid_algseid_kirjapilte": len(norm_to_raw_counts[n_n]),
                "on_olemasolev_registris": exact_reg_match is not None,
                "on_olemasolev_pere": family_exists,
                "SOURCE": SOURCE_TAG,
                "CONFIDENCE": CONFIDENCE_TAG,
                "MODEL": MODEL_TAG,
                "import_batch_id": BATCH_ID,
            })
        else:
            status_skip = "REVIEW" if (rest_fail or variant_iso_mismatch or (len(isos) > 1 and not is_high_purity_series) or off_rec is None or is_generic) else "LIKELY"
            skipped_items.append({
                "algne_nimetus": r_n,
                "normaliseeritud_nimetus": n_n,
                "tooteperekond": fam,
                "klassifitseeritav_variant": var,
                "peamine_iso": top_iso,
                "esinemisi_failis": total_cnt,
                "vahelejatmise_staatus": status_skip,
            })

    auto_learn_items.sort(key=lambda x: (-x["esinemisi_failis"], x["tooteperekond"], x["klassifitseeritav_variant"]))

    # 3. Koonda variandireeglid (Tooteperekond + Klassifitseeritav variant -> ISO)
    variant_rules_map = {}
    for item in auto_learn_items:
        fvk = item["taielik_variandi_voti"]
        if fvk not in variant_rules_map:
            variant_rules_map[fvk] = {
                "tooteperekond": item["tooteperekond"],
                "klassifitseeritav_variant": item["klassifitseeritav_variant"],
                "taielik_variandi_voti": fvk,
                "iso_kood": item["iso_kood"],
                "maarusejargne_nimetus": item["maarusejargne_nimetus"],
                "iso_maaramise_reegel": item["iso_maaramise_reegel"],
                "kirjapiltide_arv": 0,
                "esinemisi_kokku": 0,
                "naide_nimetus": item["algne_nimetus"],
                "SOURCE": SOURCE_TAG,
                "CONFIDENCE": CONFIDENCE_TAG,
                "MODEL": MODEL_TAG,
                "import_batch_id": BATCH_ID,
            }
        variant_rules_map[fvk]["kirjapiltide_arv"] += 1
        variant_rules_map[fvk]["esinemisi_kokku"] += item["esinemisi_failis"]

    variant_rules_list = sorted(variant_rules_map.values(), key=lambda x: (-x["esinemisi_kokku"], x["tooteperekond"]))

    # 4. Salvesta teadmised, aliased ja variandireeglid SQLite andmebaasi
    added_new_knowledge = 0
    enriched_existing_knowledge = 0
    new_alias_links = 0
    alias_rows_audit = []

    seen_fvk_in_import = set()

    with kb._connection() as conn:
        cursor = conn.cursor()

        # Kontrolli, mis oli teadmistebaasis enne importi
        cursor.execute("SELECT normaliseeritud_nimetus, tooteperekond, klassifitseeritav_variant FROM teadmistebaas")
        pre_existing_norms = {r["normaliseeritud_nimetus"] for r in cursor.fetchall()}

        for item in auto_learn_items:
            n_n = item["normaliseeritud_nimetus"]
            fvk = item["taielik_variandi_voti"]
            conf_score = KnowledgeBase.calculate_confidence(item["kinnitatud_ridu"])

            # Kui sama varianditeadmine või registritoode oli juba olemas, loeme selle olemasoleva teadmise täiendamiseks
            if item["on_olemasolev_registris"] or n_n in pre_existing_norms or fvk in seen_fvk_in_import:
                enriched_existing_knowledge += 1
            else:
                added_new_knowledge += 1
            seen_fvk_in_import.add(fvk)

            history_entry = json.dumps([{
                "aeg": import_timestamp,
                "syndmus": "imporditud_ajaloolistest_andmetest",
                "allikas": SOURCE_FILE,
                "batch_id": BATCH_ID,
                "source": SOURCE_TAG,
                "confidence": CONFIDENCE_TAG,
                "model": MODEL_TAG,
                "esinemisi_failis": item["esinemisi_failis"],
            }], ensure_ascii=False)

            cursor.execute("""
                SELECT id FROM teadmistebaas WHERE normaliseeritud_nimetus = ?
            """, (n_n,))
            existing_kb = cursor.fetchone()

            if existing_kb:
                cursor.execute("""
                    UPDATE teadmistebaas SET
                        algne_nimetus = ?,
                        ametlik_toode = ?,
                        iso_kood = ?,
                        maarusejargne_nimetus = ?,
                        usaldustase = MAX(usaldustase, ?),
                        kinnituste_arv = kinnituste_arv + ?,
                        viimane_valideerimine = ?,
                        valideerimise_ajalugu = ?,
                        tooteperekond = ?,
                        klassifitseeritav_variant = ?,
                        source = ?,
                        confidence = ?,
                        model = ?,
                        import_batch_id = ?,
                        algfaili_esinemisi = ?
                    WHERE id = ?
                """, (
                    item["algne_nimetus"],
                    item["ametlik_toode"],
                    item["iso_kood"],
                    item["maarusejargne_nimetus"],
                    conf_score,
                    item["kinnitatud_ridu"],
                    import_timestamp,
                    history_entry,
                    item["tooteperekond"],
                    item["klassifitseeritav_variant"],
                    SOURCE_TAG,
                    CONFIDENCE_TAG,
                    MODEL_TAG,
                    BATCH_ID,
                    item["esinemisi_failis"],
                    existing_kb["id"],
                ))
            else:
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
                        valideerimise_ajalugu,
                        tooteperekond,
                        klassifitseeritav_variant,
                        source,
                        confidence,
                        model,
                        import_batch_id,
                        algfaili_esinemisi
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    item["algne_nimetus"],
                    n_n,
                    item["ametlik_toode"],
                    item["iso_kood"],
                    item["maarusejargne_nimetus"],
                    conf_score,
                    item["kinnitatud_ridu"],
                    import_timestamp,
                    history_entry,
                    item["tooteperekond"],
                    item["klassifitseeritav_variant"],
                    SOURCE_TAG,
                    CONFIDENCE_TAG,
                    MODEL_TAG,
                    BATCH_ID,
                    item["esinemisi_failis"],
                ))

            # Salvesta kõik unikaalsed algfaili kirjapildid (aliased) selle normaliseeritud nimetuse alla
            for raw_spelling, raw_cnt in norm_to_raw_counts[n_n].most_common():
                cursor.execute("""
                    INSERT OR REPLACE INTO teadmiste_aliased (
                        algne_kirjapilt,
                        normaliseeritud_nimetus,
                        tooteperekond,
                        klassifitseeritav_variant,
                        ametlik_toode,
                        iso_kood,
                        maarusejargne_nimetus,
                        esinemisi_failis,
                        source,
                        confidence,
                        model,
                        import_batch_id,
                        loodud_aeg
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    raw_spelling,
                    n_n,
                    item["tooteperekond"],
                    item["klassifitseeritav_variant"],
                    item["ametlik_toode"],
                    item["iso_kood"],
                    item["maarusejargne_nimetus"],
                    raw_cnt,
                    SOURCE_TAG,
                    CONFIDENCE_TAG,
                    MODEL_TAG,
                    BATCH_ID,
                    import_timestamp,
                ))
                new_alias_links += 1
                alias_rows_audit.append({
                    "algne_kirjapilt": raw_spelling,
                    "normaliseeritud_nimetus": n_n,
                    "tooteperekond": item["tooteperekond"],
                    "klassifitseeritav_variant": item["klassifitseeritav_variant"],
                    "ametlik_toode": item["ametlik_toode"],
                    "iso_kood": item["iso_kood"],
                    "maarusejargne_nimetus": item["maarusejargne_nimetus"],
                    "esinemisi_failis": raw_cnt,
                    "SOURCE": SOURCE_TAG,
                    "CONFIDENCE": CONFIDENCE_TAG,
                    "MODEL": MODEL_TAG,
                    "import_batch_id": BATCH_ID,
                })

        # Salvesta 414 variandireeglit
        for vr in variant_rules_list:
            cursor.execute("""
                INSERT OR REPLACE INTO variandireeglid (
                    tooteperekond,
                    klassifitseeritav_variant,
                    taielik_variandi_voti,
                    iso_kood,
                    maarusejargne_nimetus,
                    iso_maaramise_reegel,
                    kirjapiltide_arv,
                    esinemisi_kokku,
                    naide_nimetus,
                    source,
                    confidence,
                    model,
                    import_batch_id,
                    loodud_aeg
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                vr["tooteperekond"],
                vr["klassifitseeritav_variant"],
                vr["taielik_variandi_voti"],
                vr["iso_kood"],
                vr["maarusejargne_nimetus"],
                vr["iso_maaramise_reegel"],
                vr["kirjapiltide_arv"],
                vr["esinemisi_kokku"],
                vr["naide_nimetus"],
                SOURCE_TAG,
                CONFIDENCE_TAG,
                MODEL_TAG,
                BATCH_ID,
                import_timestamp,
            ))

        audit_json_path = os.path.join(audit_dir, "impordi_audit_jalg.json")
        cursor.execute("""
            INSERT OR REPLACE INTO impordi_audit (
                batch_id,
                impordi_kuupaev,
                allikas,
                imporditud_teadmiste_arv,
                taiendatud_teadmiste_arv,
                uute_aliaste_arv,
                imporditud_variandireeglite_arv,
                vahele_jaetud_kirjete_arv,
                varukoopia_rada,
                audit_json_rada,
                staatus
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'AKTIIVNE')
        """, (
            BATCH_ID,
            import_timestamp,
            SOURCE_FILE,
            len(auto_learn_items),
            enriched_existing_knowledge,
            new_alias_links,
            len(variant_rules_list),
            len(skipped_items),
            backup_path,
            audit_json_path,
        ))
        conn.commit()

    # 5. Salvesta täielik auditijälg failidesse (JSON, Excel, Markdown)
    exact_reg_enriched = sum(1 for x in auto_learn_items if x["on_olemasolev_registris"])
    brand_new_not_in_reg = len(auto_learn_items) - exact_reg_enriched
    skipped_likely = sum(1 for x in skipped_items if x["vahelejatmise_staatus"] == "LIKELY")
    skipped_review = sum(1 for x in skipped_items if x["vahelejatmise_staatus"] == "REVIEW")

    audit_payload = {
        "batch_id": BATCH_ID,
        "importimise_kuupaev": import_timestamp,
        "allikas": SOURCE_FILE,
        "tunnused": {
            "SOURCE": SOURCE_TAG,
            "CONFIDENCE": CONFIDENCE_TAG,
            "MODEL": MODEL_TAG,
        },
        "varukoopia_rada": backup_path,
        "kokkuvote": {
            "imporditud_auto_learn_nimetusi_kokku": len(auto_learn_items),
            "imporditud_auto_learn_ridu_kokku": sum(x["esinemisi_failis"] for x in auto_learn_items),
            "kinnitatud_puhtaid_ridu_kokku": sum(x["kinnitatud_ridu"] for x in auto_learn_items),
            "lisatud_uusi_teadmisi_registriga_vorreldes": brand_new_not_in_reg,
            "taiendatud_olemasolevaid_registris_teadmisi": exact_reg_enriched,
            "lisatud_uusi_kanoonilisi_varianditeadmisi": added_new_knowledge,
            "taiendatud_olemasolevaid_pere_ja_varianditeadmisi": enriched_existing_knowledge,
            "uusi_aliaste_seoseid_algkirjapiltidena": new_alias_links,
            "imporditud_variandireegleid": len(variant_rules_list),
            "unikaalseid_tooteperekondi": len({x["tooteperekond"] for x in auto_learn_items}),
            "vahele_jaetud_nimetusi_kokku": len(skipped_items),
            "vahele_jaetud_likely_nimetusi": skipped_likely,
            "vahele_jaetud_review_nimetusi": skipped_review,
            "vahele_jaetud_ridu_kokku": sum(x["esinemisi_failis"] for x in skipped_items),
        },
        "imporditud_variandireeglid": variant_rules_list,
        "imporditud_kirjete_loend": auto_learn_items,
    }

    with open(audit_json_path, "w", encoding="utf-8") as f:
        json.dump(audit_payload, f, ensure_ascii=False, indent=2)

    audit_xlsx_path = os.path.join(audit_dir, "impordi_audit_jalg.xlsx")
    with pd.ExcelWriter(audit_xlsx_path, engine="openpyxl") as writer:
        pd.DataFrame([audit_payload["kokkuvote"]]).to_excel(writer, sheet_name="Kokkuvote", index=False)
        pd.DataFrame(auto_learn_items).to_excel(writer, sheet_name="Imporditud_Teadmised_880", index=False)
        pd.DataFrame(variant_rules_list).to_excel(writer, sheet_name="Variandireeglid_414", index=False)
        pd.DataFrame(alias_rows_audit).to_excel(writer, sheet_name="Aliaste_Seosed_1031", index=False)
        pd.DataFrame(skipped_items).to_excel(writer, sheet_name="Vahele_Jaetud_1932", index=False)

    audit_md_path = os.path.join(audit_dir, "impordi_audit_aruanne.md")
    md_lines = [
        "# AUTO_LEARN impordi ametlik auditijälg",
        "",
        f"- **Impordi partii ID (`batch_id`):** `{BATCH_ID}`",
        f"- **Importimise kuupäev:** `{import_timestamp}`",
        f"- **Allikas:** `{SOURCE_FILE}`",
        f"- **Andmebaasi varukoopia:** `{backup_path}`",
        f"- **Tunnused:** `SOURCE = {SOURCE_TAG}`, `CONFIDENCE = {CONFIDENCE_TAG}`, `MODEL = {MODEL_TAG}`",
        "",
        "## Impordi koondkokkuvõte",
        "",
        f"- **Imporditud `AUTO_LEARN` teadmisi kokku:** **{len(auto_learn_items)}** normaliseeritud nimetust (**{sum(x['esinemisi_failis'] for x in auto_learn_items)}** rida failis)",
        f"  - sh täiesti uusi nimetusi (puudusid varem tooteregistris): **{brand_new_not_in_reg}**",
        f"  - sh olemasolevate registriteadmiste täiendusi: **{exact_reg_enriched}**",
        f"  - sh kanoonilise variandi tasemel esmakordseid teadmisi: **{added_new_knowledge}** ja olemasoleva pere/variandi täiendusi: **{enriched_existing_knowledge}**",
        f"- **Tekkinud aliaste seoseid:** **{len(auto_learn_items)}** normaliseeritud aliast (**{new_alias_links}** unikaalset algset kirjapilti failist)",
        f"- **Tekkinud kahetasemelisi variandireegleid (`Tooteperekond + Variant -> ISO`):** **{len(variant_rules_list)}** (üle **{len({x['tooteperekond'] for x in auto_learn_items})}** tooteperekonna)",
        f"- **Vahele jäetud kirjeid (`LIKELY` + `REVIEW`):** **{len(skipped_items)}** nimetust (**{sum(x['esinemisi_failis'] for x in skipped_items)}** rida), sh `{skipped_likely}` `LIKELY` ja `{skipped_review}` `REVIEW`",
        "",
        "## Tagasivõtmise (rollback) juhend",
        "",
        "Import on täielikult pööratav kahel viisil:",
        "1. **Programmatiivne tagasivõtmine partii ID alusel (`batch_id`):**",
        "   ```powershell",
        "   .\\.venv\\Scripts\\python.exe scripts\\rollback_auto_learn.py --batch-id BATCH_SEPT_15_09_AUTO_LEARN",
        "   ```",
        "2. **Täielik failipõhine taastamine varukoopiast:**",
        "   ```powershell",
        "   .\\.venv\\Scripts\\python.exe scripts\\rollback_auto_learn.py --restore-backup",
        "   ```",
    ]
    with open(audit_md_path, "w", encoding="utf-8") as f:
        f.write("\n".join(md_lines))

    print(json.dumps(audit_payload["kokkuvote"], indent=2, ensure_ascii=False))
    print(f"BACKUP_PATH={backup_path}")
    print(f"AUDIT_JSON={audit_json_path}")
    print(f"AUDIT_XLSX={audit_xlsx_path}")
    print(f"AUDIT_MD={audit_md_path}")


if __name__ == "__main__":
    run_import()
