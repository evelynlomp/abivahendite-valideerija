"""Valideer — Abivahendite andmete kontroll & õppiv teadmistebaas.

Spetsialistile suunatud töölaud:
- Igakuiste Exceli/CSV failide kiire valideerimine
- Probleemsete kirjete analüüs ja määruse kitsenduste kontroll
- Valideerimise raporti kohene eksport
- Püsivate registrite sirvimine (iseseisev haldusala)
"""

import os
import io
import json
import pandas as pd
import streamlit as st
from datetime import datetime

from src.normalizer import (
    normalize_name,
    normalize_iso,
    format_iso_display,
    normalize_statutory_name
)
from src.classifier import MinistryClassifier
from src.knowledge_base import KnowledgeBase
from src.product_agent import ProductIdentificationAgent
from src.product_registry_db import get_product_registry_db
from src.matcher import ProductMatcher
from src.validator import Validator


# --- LEHE SEADISTUS ---
st.set_page_config(
    page_title="Valideer — Abivahendite andmete kontroll",
    page_icon="🩺",
    layout="wide",
    initial_sidebar_state="expanded"
)


# --- KOMPONENTIDE INITSIALISEERIMINE ---
@st.cache_resource
def get_classifier():
    return MinistryClassifier(db_path="data/valideer.db")


@st.cache_resource
def get_knowledge_base():
    return KnowledgeBase(db_path="data/valideer.db")


@st.cache_resource
def get_registry_db():
    return get_product_registry_db()


@st.cache_resource
def get_product_agent():
    return ProductIdentificationAgent()


classifier = get_classifier()
kb = get_knowledge_base()
registry_db = get_registry_db()
product_agent = get_product_agent()
reg_stats = registry_db.get_statistics()
class_count = classifier.count()
kb_count = kb.count()

matcher = ProductMatcher(
    classifier=classifier,
    knowledge_base=kb,
    product_agent=product_agent
)
validator = Validator(matcher=matcher)


# --- SESSIOONI OLEK ---
if "df_input" not in st.session_state:
    st.session_state["df_input"] = None
if "input_source_name" not in st.session_state:
    st.session_state["input_source_name"] = None


# --- KÜLGRIBA NAVIGATSIOON ---
with st.sidebar:
    st.image("https://img.icons8.com/fluency/96/medical-clipboard.png", width=56)
    st.title("Valideer")
    st.caption("Abivahendite tehinguridade kontrollisüsteem")
    st.divider()

    app_mode = st.radio(
        "Töökeskkond:",
        ["📋 Valideerimise töölaud", "📚 Registrid ja haldus"],
        index=0
    )

    st.divider()

    # Süsteemi lühistatistika
    st.caption("Püsivad tõeallikad:")
    st.markdown(f"- **Määrus nr 74:** {class_count} ISO koodi")
    st.markdown(f"- **Tooteregister:** {reg_stats['total_products']:,} toodet".replace(",", " "))
    st.markdown(f"- **Teadmistebaas:** {kb_count} reeglit")

    if st.session_state["df_input"] is not None:
        st.divider()
        st.caption(f"Aktiivne fail: **{st.session_state['input_source_name']}**")
        if st.button("🔄 Laadi uus fail / Tühjenda", use_container_width=True):
            st.session_state["df_input"] = None
            st.session_state["input_source_name"] = None
            st.rerun()


# ==============================================================================
# HARU A: VALIDEERIMISE TÖÖLAUD (PÕHITÖÖVOOG)
# ==============================================================================
if app_mode == "📋 Valideerimise töölaud":

    # --- 1. AVALEHT ENNE FAILI LAADIMIST ---
    if st.session_state["df_input"] is None:
        st.title("🩺 Abivahendite andmete kontroll")
        st.subheader("Sotsiaalministeeriumi määruse nr 74 tehinguridade automaatne vastavuskontroll")

        # Selgitav väärtuskaart esmakordsele kasutajale
        with st.container():
            st.markdown("""
            See tööriist kontrollib igakuiseid abivahendite tehingufaile (Excel, CSV) ja tuvastab automaatselt vead ning mittevastavused enne arve esitamist või kinnitamist.
            """)

            col_inf1, col_inf2, col_inf3 = st.columns(3)
            with col_inf1:
                st.markdown("#### 🎯 Mis süsteemiga on tegu?")
                st.caption(
                    "Automaatne reeglimootor, mis võrdleb tehinguridu Sotsiaalministeeriumi määruse nr 74 ametliku loetelu ja Eesti tarnijate ühendatud tooteregistriga."
                )
            with col_inf2:
                st.markdown("#### 🔍 Mida kontrollitakse?")
                st.caption(
                    "• Toote tuvastamine ja 1:1 ISO koodi kehtivus\n\n"
                    "• Imavusmahtude (ml) vastavus vahemikele\n\n"
                    "• Määruse veergude C ja M kitsendused (sh tsinkoksiidi nõue, välistatud tooted)\n\n"
                    "• Ametliku määrusejärgse nimetuse klapp"
                )
            with col_inf3:
                st.markdown("#### 💡 Millist kasu saad?")
                st.caption(
                    "• Tundidepikkuse käsitsitöö asendamine sekunditega\n\n"
                    "• Finantsiliste tagasinõuete ja tagasilükkamiste ennetamine\n\n"
                    "• Parandusettepanekutega allalaaditav Exceli raport"
                )

        st.divider()

        # HERO: Faili üleslaadimine (kõige silmapaistvam element lehel)
        st.subheader("📁 Laadi tehingufail valideerimiseks")

        uploaded_file = st.file_uploader(
            "Vali või lohista siia igakuine Exceli või CSV fail (.xlsx, .xls, .csv)",
            type=["xlsx", "xls", "csv"],
            help="Fail peab sisaldama välju toote nimetuse, ISO koodi ja määrusejärgse nimetusega."
        )

        col_act1, col_act2 = st.columns([1, 2])
        with col_act1:
            load_sample = st.button("🧪 Proovi kohe näidisfailiga (vigadega tehingud)", use_container_width=True, type="secondary")

        if uploaded_file is not None:
            try:
                if uploaded_file.name.endswith(".csv"):
                    st.session_state["df_input"] = pd.read_csv(uploaded_file)
                else:
                    st.session_state["df_input"] = pd.read_excel(uploaded_file)
                st.session_state["input_source_name"] = uploaded_file.name
                st.rerun()
            except Exception as e:
                st.error(f"Viga faili lugemisel: {e}")

        elif load_sample:
            sample_path = "data/naidis_sisend_vigadega.xlsx"
            if os.path.exists(sample_path):
                st.session_state["df_input"] = pd.read_excel(sample_path)
                st.session_state["input_source_name"] = "naidis_sisend_vigadega.xlsx (näidis)"
                st.rerun()
            else:
                st.warning("Näidisfaili ei leitud kataloogist data/.")

    # --- 2. TÖÖTLEMINE JA TULEMUSED (PÄRAST FAILI LAADIMIST) ---
    else:
        df_input = st.session_state["df_input"]

        # Tuvasta nõutud veerud paindlikult
        col_map = {}
        for c in df_input.columns:
            c_clean = str(c).strip().lower()
            if "abivahendi" in c_clean or "toote" in c_clean or ("nimetus" in c_clean and "määrus" not in c_clean):
                if "name" not in col_map:
                    col_map["name"] = c
            elif "iso" in c_clean:
                col_map["iso"] = c
            elif "määruse" in c_clean or "maaruse" in c_clean or "ametlik" in c_clean:
                col_map["statutory"] = c

        if "name" not in col_map or "iso" not in col_map:
            st.error(f"Exceli failist ei leitud kohustuslikke veerge (tootenimi, ISO kood)! Tuvastatud veerud: {list(df_input.columns)}")
            if st.button("Vali teine fail"):
                st.session_state["df_input"] = None
                st.rerun()
            st.stop()

        name_col = col_map["name"]
        iso_col = col_map["iso"]
        stat_col = col_map.get("statutory")

        # Valideeri read
        validation_results = []
        for idx, row in df_input.iterrows():
            raw_name = str(row[name_col]) if pd.notna(row[name_col]) else ""
            raw_iso = str(row[iso_col]) if pd.notna(row[iso_col]) else ""
            raw_stat = str(row[stat_col]) if stat_col and pd.notna(row[stat_col]) else ""

            res = validator.validate_row(
                excel_name=raw_name,
                excel_iso=raw_iso,
                excel_statutory_name=raw_stat,
                row_index=idx + 1
            )
            validation_results.append(res)

        df_res = pd.DataFrame(validation_results)

        # Arvuta koondmõõdikud
        status_counts = df_res["Valideerimise staatus"].value_counts()
        total_rows = len(df_res)
        valid_count = status_counts.get(Validator.STATUS_MATCH, 0)
        wrong_iso = status_counts.get(Validator.STATUS_WRONG_ISO, 0)
        wrong_stat = status_counts.get(Validator.STATUS_WRONG_NAME, 0)
        wrong_both = status_counts.get(Validator.STATUS_WRONG_BOTH, 0)
        restriction_violations = status_counts.get(Validator.STATUS_RESTRICTION, 0)
        unknown = status_counts.get(Validator.STATUS_UNKNOWN, 0)
        needs_review = status_counts.get(Validator.STATUS_REVIEW, 0)

        problem_count = total_rows - valid_count

        # Valmista ette Exceli raport allalaadimiseks
        towrite_res = io.BytesIO()
        df_res.to_excel(towrite_res, index=False, engine="openpyxl")
        towrite_res.seek(0)
        report_filename = f"valideerimise_raport_{datetime.now().strftime('%Y%m%d_%H%M')}.xlsx"

        # --- PÄIS: TULEMUSED JA RAPORTI NUPP ---
        st.title("📊 Valideerimise kokkuvõte")
        st.caption(f"Töödeldud fail: **{st.session_state['input_source_name']}** ({total_rows} rida)")

        # ÜLEMISED KOONDMÕÕDIKUD JA CTA (Raport kohe mõõdikute kõrval)
        c_kpi1, c_kpi2, c_kpi3, c_cta = st.columns([1.5, 1.5, 1.8, 2.5])
        with c_kpi1:
            st.metric("Töödeldud ridu", total_rows)
        with c_kpi2:
            st.metric("✅ Kõik korras", valid_count, f"{int(valid_count/total_rows*100)}%" if total_rows else "")
        with c_kpi3:
            st.metric("⚠️ Vajab tähelepanu", problem_count, f"{int(problem_count/total_rows*100)}%" if total_rows else "", delta_color="inverse")
        with c_cta:
            st.write("")  # nihutus joondamiseks
            st.download_button(
                label="📥 Laadi valideerimise raport alla (.xlsx)",
                data=towrite_res,
                file_name=report_filename,
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                type="primary",
                use_container_width=True
            )

        # Probleemide detailne jaotus
        st.markdown("**Probleemide detailne jaotus:**")
        cp1, cp2, cp3, cp4, cp5 = st.columns(5)
        cp1.metric("🛑 Ei vasta kitsendusele", restriction_violations)
        cp2.metric("⚠️ Vale ISO", wrong_iso)
        cp3.metric("⚠️ Vale nimetus", wrong_stat)
        cp4.metric("❌ Vale mõlemad", wrong_both)
        cp5.metric("❓ Käsitsi kontroll / Tundmatu", needs_review + unknown)

        st.divider()

        # --- TÖÖLAUA VAHEKAARDID: PROBLEEMID JA KINNITAMINE ---
        tab_prob, tab_queue = st.tabs([
            f"🔍 Probleemsete kirjete analüüs ({problem_count})",
            f"✍️ Lahenda kirjed ja õpeta teadmistebaasi ({len(df_res[df_res['Valideerimise staatus'] != Validator.STATUS_MATCH])})"
        ])

        with tab_prob:
            col_f1, col_f2 = st.columns([1, 2])
            with col_f1:
                show_valid = st.checkbox(f"Kuva tabelis ka nõuetele vastavad read ({valid_count} rida)", value=False)
            with col_f2:
                available_statuses = list(df_res["Valideerimise staatus"].unique())
                if not show_valid and Validator.STATUS_MATCH in available_statuses:
                    default_selected = [s for s in available_statuses if s != Validator.STATUS_MATCH]
                else:
                    default_selected = available_statuses

                selected_status = st.multiselect(
                    "Filtreeri staatuse järgi:",
                    options=available_statuses,
                    default=default_selected
                )

            # Filtreeritud read
            df_filtered = df_res[df_res["Valideerimise staatus"].isin(selected_status)]

            if not show_valid:
                st.caption(f"Kuvatakse ainult tähelepanu vajavad kirjed ({len(df_filtered)} rida).")
            else:
                st.caption(f"Kuvatakse kõik valitud staatustega kirjed ({len(df_filtered)} rida).")

            # Tabel otsustamiseks optimeeritud veergudega
            table_cols = [
                "Rida",
                "Valideerimise staatus",
                "Kitsenduse kontroll",
                "Selgitus",
                "Abivahendi nimetus (Excel)",
                "Tuvastatud ametlik toode",
                "Tootja",
                "ISO kood (Excel)",
                "Ametlik ISO kood",
                "Määrusejärgne nimetus (Excel)",
                "Ametlik määrusejärgne nimetus",
                "Usaldusskoor"
            ]
            valid_cols = [c for c in table_cols if c in df_filtered.columns]

            st.dataframe(
                df_filtered[valid_cols],
                use_container_width=True,
                height=450
            )

        with tab_queue:
            st.subheader("✍️ Kinnita uued seosed ja lahenda kahtlased kirjed")
            st.write("Spetsialisti kinnitatud otsused salvestatakse teadmistebaasi ja süsteem jätab need tulevikuks meelde.")

            unresolved = df_res[df_res["Valideerimise staatus"].isin([
                Validator.STATUS_RESTRICTION,
                Validator.STATUS_REVIEW,
                Validator.STATUS_UNKNOWN,
                Validator.STATUS_WRONG_ISO,
                Validator.STATUS_WRONG_NAME,
                Validator.STATUS_WRONG_BOTH
            ])]

            if len(unresolved) == 0:
                st.success("Kõik tooted vastavad nõuetele! Käsitsi ülevaatust vajavaid kirjeid ei ole.")
            else:
                st.info(f"Ülevaatust ja otsustamist vajab {len(unresolved)} kirjet.")

                for _, r in unresolved.iterrows():
                    with st.expander(f"Rida {r['Rida']}: {r['Abivahendi nimetus (Excel)']} [Staatus: {r['Valideerimise staatus']}]"):
                        col_e1, col_e2 = st.columns([1, 1])

                        with col_e1:
                            st.markdown("**Arve andmed:**")
                            st.write(f"- Esitatud nimetus: **{r['Abivahendi nimetus (Excel)']}**")
                            st.write(f"- Esitatud ISO: `{r['ISO kood (Excel)']}`")
                            st.write(f"- Esitatud nimetus: {r['Määrusejärgne nimetus (Excel)']}")
                            st.write(f"- Kitsenduse kontroll: **{r.get('Kitsenduse kontroll')}**")
                            if r.get("Selgitus"):
                                st.caption(f"💡 **Reegli selgitus:** {r['Selgitus']}")

                        with col_e2:
                            st.markdown("**Kinnitatavad väärtused (Teadmistebaasi):**")
                            c_official = st.text_input(
                                "Ametlik toode:",
                                value=r["Tuvastatud ametlik toode"] or r["Abivahendi nimetus (Excel)"],
                                key=f"q_off_{r['Rida']}"
                            )
                            c_iso = st.text_input(
                                "Õige ISO kood:",
                                value=r["Ametlik ISO kood"] or r["ISO kood (Excel)"],
                                key=f"q_iso_{r['Rida']}"
                            )
                            c_stat = st.text_input(
                                "Õige määrusejärgne nimetus:",
                                value=r["Ametlik määrusejärgne nimetus"] or r["Määrusejärgne nimetus (Excel)"],
                                key=f"q_stat_{r['Rida']}"
                            )

                            if st.button(f"💾 Kinnita ja salvesta teadmistebaasi (Rida {r['Rida']})", key=f"q_btn_{r['Rida']}", type="primary"):
                                kb.confirm_mapping(
                                    raw_name=r["Abivahendi nimetus (Excel)"],
                                    normalized_name=r.get("Normaliseeritud nimetus") or normalize_name(r["Abivahendi nimetus (Excel)"]),
                                    official_product=c_official,
                                    iso_code=c_iso,
                                    statutory_name=c_stat,
                                    confidence=1.0
                                )
                                st.success("Kirje salvestatud teadmistebaasi! Järgmisel töötlemisel võetakse arvesse.")
                                st.rerun()


# ==============================================================================
# HARU B: REGISTRID JA HALDUS (ISESEISEV KESKKOND)
# ==============================================================================
else:
    st.title("📚 Registrid ja haldus")
    st.caption("Püsivad tõeallikad ja andmebaasid. Kasutatavad igal ajal, ilma faili üleslaadimata.")

    tab_reg, tab_class, tab_kb, tab_admin = st.tabs([
        f"📦 Tooteregister ({reg_stats['total_products']:,} toodet)".replace(",", " "),
        f"🏛️ Riiklik klassifikaator ({class_count} ISO koodi)",
        f"🧠 Õppiv teadmistebaas ({kb_count} reeglit)",
        "⚙️ Haldus ja süsteemiinfo"
    ])

    # 1. TOOTEREGISTER
    with tab_reg:
        st.subheader("📦 Püsiv Tooteregister")
        st.caption("Eesti abivahendite tarnijate kataloogidest ühendatud ja dublikaadivaba toodete baas.")

        rkpi1, rkpi2, rkpi3 = st.columns(3)
        rkpi1.metric("Tooteid registris", f"{reg_stats['total_products']:,}".replace(",", " "))
        rkpi2.metric("Tootjaid", reg_stats['manufacturers_count'])
        rkpi3.metric("Kategooriaid", len(reg_stats['categories']))

        st.divider()

        col_rf1, col_rf2 = st.columns([2, 1])
        with col_rf1:
            prod_search = st.text_input("Otsi tootenime, brändi või aliaset:", key="haldus_reg_search")
        with col_rf2:
            all_types = ["Kõik kategooriad"] + [c[0] for c in reg_stats['categories']]
            sel_type = st.selectbox("Filtreeri kategooria järgi:", options=all_types, key="haldus_reg_cat")

        all_reg_prods = registry_db.get_all_products()
        filtered_reg = []
        for p in all_reg_prods:
            if sel_type != "Kõik kategooriad" and p.get('category_type') != sel_type:
                continue
            if prod_search:
                s_up = prod_search.upper()
                if s_up not in p['official_name'].upper() and s_up not in p['brand'].upper() and not any(s_up in a.upper() for a in p.get('aliases', [])):
                    continue
            filtered_reg.append(p)

        st.caption(f"Kuvatakse {len(filtered_reg)} toodet.")
        df_reg_view = pd.DataFrame(filtered_reg)
        if not df_reg_view.empty:
            view_cols = ["official_name", "brand", "manufacturer", "category_type", "absorption_ml", "drops", "package_information", "source_supplier"]
            valid_v_cols = [c for c in view_cols if c in df_reg_view.columns]
            rename_map = {
                "official_name": "Ametlik tootenimi",
                "brand": "Bränd",
                "manufacturer": "Tootja",
                "category_type": "Kategooria",
                "absorption_ml": "Imavus (ml)",
                "drops": "Tilgad / Tase",
                "package_information": "Pakendi info",
                "source_supplier": "Tarnijad"
            }
            st.dataframe(df_reg_view[valid_v_cols].rename(columns=rename_map), use_container_width=True, height=500)

    # 2. RIIKLIK KLASSIFIKAATOR
    with tab_class:
        st.subheader("🏛️ Sotsiaalministeeriumi määruse nr 74 loetelu")
        st.caption("Ametlik klassifikaator koos veergude C ja M tootekitsenduste ja kirjeldustega.")

        search_q = st.text_input("Otsi klassifikaatorist (ISO kood või märksõna):", key="haldus_class_search")

        all_classes_data = classifier.get_all_classifications()
        if all_classes_data:
            df_classes = pd.DataFrame(all_classes_data)
            if search_q:
                q_up = search_q.upper()
                df_classes = df_classes[
                    df_classes["iso_kood"].str.upper().str.contains(q_up, na=False) |
                    df_classes["maarusejargne_nimetus"].str.upper().str.contains(q_up, na=False) |
                    df_classes["tapsustus"].str.upper().str.contains(q_up, na=False)
                ]

            show_cols = [
                "iso_kood",
                "maarusejargne_nimetus",
                "tapsustus",
                "kasutusaeg",
                "tehingu_liik",
                "piirlimiit",
                "piirhind_uur",
                "piirhind_muuk",
                "uhik"
            ]
            valid_show = [c for c in show_cols if c in df_classes.columns]
            rename_classes = {
                "iso_kood": "ISO kood",
                "maarusejargne_nimetus": "Määrusejärgne nimetus",
                "tapsustus": "Kitsendus / Täpsustus (Veerg C)",
                "kasutusaeg": "Kasutusaeg",
                "tehingu_liik": "Tehingu liik",
                "piirlimiit": "Piirlimiit",
                "piirhind_uur": "Üüri piirhind",
                "piirhind_muuk": "Müügi piirhind",
                "uhik": "Ühik"
            }
            st.dataframe(df_classes[valid_show].rename(columns=rename_classes), use_container_width=True, height=500)

    # 3. TEADMISTEBAAS
    with tab_kb:
        st.subheader("🧠 Õppiv teadmistebaas")
        st.caption("Spetsialisti poolt käsitsi kinnitatud reeglid ja erandid, mida rakendatakse eelisjärjekorras.")

        all_entries = kb.get_all()
        if not all_entries:
            st.info("Teadmistebaas on hetkel tühi. Reeglid lisanduvad siia, kui kinnitate töölaual lahknevustega kirjeid.")
        else:
            kb_df = pd.DataFrame(all_entries)

            col_kb1, col_kb2 = st.columns([3, 1])
            with col_kb2:
                towrite_kb = io.BytesIO()
                kb_df.to_excel(towrite_kb, index=False, engine="openpyxl")
                towrite_kb.seek(0)
                st.download_button(
                    label="💾 Laadi teadmistebaas alla (.xlsx)",
                    data=towrite_kb,
                    file_name="valideer_teadmistebaas.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    use_container_width=True
                )

            display_kb_cols = [
                "id",
                "algne_nimetus",
                "normaliseeritud_nimetus",
                "ametlik_toode",
                "iso_kood",
                "maarusejargne_nimetus",
                "usaldustase",
                "kinnituste_arv",
                "viimane_valideerimine"
            ]
            valid_kb = [c for c in display_kb_cols if c in kb_df.columns]
            st.dataframe(kb_df[valid_kb], use_container_width=True, height=450)

    # 4. HALDUS JA SÜSTEEMIINFO
    with tab_admin:
        st.subheader("⚙️ Haldus ja süsteemiinfo")
        st.caption("Tehnilised parameetrid ja arhitektuuri ülevaade administraatorile.")

        st.markdown("""
        ### Süsteemi arhitektuur ja andmeallikad
        - **Andmebaas:** Lokaalne SQLite (`data/valideer.db`)
        - **Põhilised tõeallikad:**
          1. `ametlik_klassifikaator`: Sotsiaalministeeriumi määruse nr 74 ametlik loetelu (327 kirjet koos veergude C ja M kitsendustega).
          2. `tooteregister`: 4 115 kanoonilist toodet koos aliaste, imavusmahtude ja tarnijate infoga.
          3. `teadmistebaas`: Spetsialisti kinnitatud seosed (õppiv kiht).
        
        ### Valideerimise reeglimootor
        - **1:1 determinism:** Iga toode registris vastab eranditult ühele kindlale ISO koodile.
        - **RestrictionEngine:** Kontrollib toote füüsikalist ja keemilist vastavust määruse kitsendustele (nt tsinkoksiidi nõue, välistatud tootekategooriad).
        - **Privaatsuspõhimõte:** Kasutaja üleslaaditud faile ega arveridu kettale ei salvestata; kogu valideerimine toimub turvaliselt sessioonimälus (RAM).
        """)
