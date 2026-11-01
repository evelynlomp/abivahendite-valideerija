"""Valideer - Abivahendite andmete kontroll & õppiv teadmistebaas.

Spetsialistile suunatud töölaud:
- Igakuiste Exceli failide valideerimine
- Tulemuste ülevaatus ja teadmistebaasi täiendamine
- Püsiva tooteregistri sirvimine
- Ametliku klassifikaatori vaade
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


# Lehe seadistus
st.set_page_config(
    page_title="Valideer — Abivahendite andmete kontroll",
    page_icon="🩺",
    layout="wide",
    initial_sidebar_state="expanded"
)


# Initsialiseeri komponendid
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


# --- KÜLGRIBA ---
with st.sidebar:
    st.image("https://img.icons8.com/fluency/96/medical-clipboard.png", width=64)
    st.title("Valideer")
    st.caption("Abivahendite andmete kontrollisüsteem")
    st.divider()

    # 1. PÜSIV TOOTEREGISTER
    st.subheader("📦 Tooteregister")
    st.metric("Kataloogi tooteid", f"{reg_stats['total_products']:,}".replace(",", " "))
    st.caption("Ühendatud tarnijate tootekataloog (Invaru, ITAK, Terviseabi, Invaabi, Invatooted).")

    with st.expander("🔍 Otsi tooteregistrist"):
        q_reg = st.text_input("Toote või brändi nimi:", key="sb_reg_search")
        if q_reg:
            found = [
                p for p in registry_db.get_all_products()
                if q_reg.upper() in p['official_name'].upper() or q_reg.upper() in p['brand'].upper()
            ][:5]
            if found:
                for f_p in found:
                    st.markdown(f"**{f_p['official_name']}**")
                    st.caption(f"Tootja: {f_p['manufacturer']} | {f_p.get('source_supplier')}")
            else:
                st.write("Vasteid ei leitud.")

    st.divider()

    # 2. PÜSIV SOTSIAALMINISTEERIUMI KLASSIFIKAATOR
    st.subheader("🏛️ Riiklik klassifikaator")
    st.metric("Ametlikke klassifikatsioone", class_count)
    st.caption("Sotsiaalministeeriumi määruse nr 74 abivahendite loetelu.")

    with st.expander("🔍 Otsi klassifikaatorist"):
        search_q = st.text_input("ISO-kood või nimetus:", key="sb_search")
        if search_q:
            found_items = classifier.search(search_q, limit=5)
            if found_items:
                for f_item in found_items:
                    st.markdown(f"**`{f_item['iso_kood']}`** — {f_item['maarusejargne_nimetus']}")
            else:
                st.write("Vasteid ei leitud.")

    st.divider()

    # 3. ÕPPIV TEADMISTEBAAS
    st.subheader("🧠 Teadmistebaas")
    kb_count = kb.count()
    st.metric("Kinnitatud seoseid", kb_count)
    st.caption("Spetsialisti kinnitatud reeglid rakendatakse esmajärjekorras.")

    if kb_count > 0:
        all_kb = kb.get_all()
        kb_df = pd.DataFrame(all_kb)
        towrite = io.BytesIO()
        kb_df.to_excel(towrite, index=False, engine="openpyxl")
        towrite.seek(0)
        st.download_button(
            label="💾 Laadi teadmistebaas alla (.xlsx)",
            data=towrite,
            file_name="valideer_teadmistebaas.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            use_container_width=True
        )


# Initsialiseeri Matcher ja Validator
matcher = ProductMatcher(
    classifier=classifier,
    knowledge_base=kb,
    product_agent=product_agent
)
validator = Validator(matcher=matcher)


# --- PÕHIVORM / HOMEPAGE ---
st.title("🩺 Valideer — Abivahendite andmete kontroll")

# TOP KPI KAARDID (alati lehe ülaosas nähtaval)
kpi1, kpi2, kpi3, kpi4 = st.columns(4)
kpi1.metric("Kataloogi tooteid", f"{reg_stats['total_products']:,}".replace(",", " "))
kpi2.metric("Kaetud tootjaid", reg_stats['manufacturers_count'])
kpi3.metric("Tootekategooriaid", len(reg_stats['categories']))
kpi4.metric("Ristmüügi tooteid", reg_stats['cross_supplier_count'])

st.divider()

# Faili valik / üleslaadimine spetsialistile
col_up1, col_up2 = st.columns([3, 1])

with col_up1:
    uploaded_file = st.file_uploader(
        "Vali töödeldav igakuine Exceli fail (.xlsx, .xls, .csv)",
        type=["xlsx", "xls", "csv"],
        help="Exceli fail peab sisaldama välju: Abivahendi nimetus, ISO kood, Määrusejärgne nimetus."
    )

with col_up2:
    st.write("Või proovi näidisfaili:")
    load_sample = st.button("🧪 Laadi näidisandmed (vigadega fail)", use_container_width=True)
    if st.button("🔄 Tühjenda vahemälu & taaskäivita", use_container_width=True):
        st.session_state.clear()
        st.rerun()

# Töötle faili või näidisandmeid
df_input = None

if uploaded_file is not None:
    try:
        if uploaded_file.name.endswith(".csv"):
            df_input = pd.read_csv(uploaded_file)
        else:
            df_input = pd.read_excel(uploaded_file)
        st.success(f"Fail edukalt laetud: {len(df_input)} rida.")
    except Exception as e:
        st.error(f"Viga faili lugemisel: {e}")

elif load_sample:
    sample_path = "data/naidis_sisend_vigadega.xlsx"
    if os.path.exists(sample_path):
        df_input = pd.read_excel(sample_path)
        st.success(f"Näidisfail laetud: {len(df_input)} rida.")
    else:
        st.warning("Näidisfaili ei leitud.")


# TÖÖTLUS JA TULEMUSED
if df_input is not None:
    # Kontrolli veerunimesid
    col_map = {}
    for c in df_input.columns:
        c_clean = str(c).strip().lower()
        if "abivahendi" in c_clean or "toote" in c_clean or "nimetus" in c_clean and "määrus" not in c_clean:
            if "name" not in col_map:
                col_map["name"] = c
        elif "iso" in c_clean:
            col_map["iso"] = c
        elif "määruse" in c_clean or "maaruse" in c_clean or "ametlik" in c_clean:
            col_map["statutory"] = c

    if "name" not in col_map or "iso" not in col_map:
        st.error(f"Exceli failist ei leitud kohustuslikke veerge! Tuvastatud veerud: {list(df_input.columns)}")
        st.stop()

    name_col = col_map["name"]
    iso_col = col_map["iso"]
    stat_col = col_map.get("statutory")

    with st.spinner("Valideerin andmeid..."):
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

    # --- TÖÖLAUA VAHEKAARDID ---
    tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs([
        "📊 Valideerimise tulemused",
        "✍️ Kinnita uued seosed",
        "🧠 Teadmistebaas",
        "🏛️ Ametlik klassifikaator",
        f"📦 Tooteregister ({reg_stats['total_products']:,} toodet)".replace(",", " "),
        "ℹ️ Süsteemi info"
    ])

    # TAB 1: VALIDEERIMISE TULEMUSED
    with tab1:
        st.subheader("Valideerimise koondtulemused")

        # Tulemuste mõõdikud
        status_counts = df_res["Valideerimise staatus"].value_counts()
        total_rows = len(df_res)
        valid_count = status_counts.get(Validator.STATUS_MATCH, 0)
        wrong_iso = status_counts.get(Validator.STATUS_WRONG_ISO, 0)
        wrong_stat = status_counts.get(Validator.STATUS_WRONG_NAME, 0)
        wrong_both = status_counts.get(Validator.STATUS_WRONG_BOTH, 0)
        unknown = status_counts.get(Validator.STATUS_UNKNOWN, 0)
        needs_review = status_counts.get(Validator.STATUS_REVIEW, 0)

        m1, m2, m3, m4, m5, m6 = st.columns(6)
        m1.metric("KOKKU RIDU", total_rows)
        m2.metric("✅ Vastab", valid_count, f"{int(valid_count/total_rows*100)}%" if total_rows else "")
        m3.metric("⚠️ Vale ISO", wrong_iso)
        m4.metric("⚠️ Vale nimetus", wrong_stat)
        m5.metric("❌ Vale mõlemad", wrong_both)
        m6.metric("❓ Käsitsi kontroll", needs_review + unknown)

        st.divider()

        # Filtreerimine
        selected_status = st.multiselect(
            "Filtreeri staatuse järgi:",
            options=list(df_res["Valideerimise staatus"].unique()),
            default=list(df_res["Valideerimise staatus"].unique())
        )
        df_filtered = df_res[df_res["Valideerimise staatus"].isin(selected_status)]

        # Tulemuste tabel
        st.dataframe(
            df_filtered[[
                "Rida",
                "Valideerimise staatus",
                "Abivahendi nimetus (Excel)",
                "Tuvastatud ametlik toode",
                "Tootja",
                "Usaldusskoor",
                "Tuvastuse allikas",
                "ISO kood (Excel)",
                "Ametlik ISO kood",
                "Määrusejärgne nimetus (Excel)",
                "Ametlik määrusejärgne nimetus"
            ]],
            use_container_width=True,
            height=400
        )

        # Laadi tulemused alla
        towrite_res = io.BytesIO()
        df_res.to_excel(towrite_res, index=False, engine="openpyxl")
        towrite_res.seek(0)
        st.download_button(
            label="📥 Laadi valideerimise raport alla (.xlsx)",
            data=towrite_res,
            file_name=f"valideerimise_raport_{datetime.now().strftime('%Y%m%d_%H%M')}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )

    # TAB 2: KINNITA UUED SEOSED (ÕPPIV KOMPONENT)
    with tab2:
        st.subheader("✍️ Kinnita uued seosed ja õpeta teadmistebaasi")
        st.write("Spetsialisti kinnitatud kirjed salvestatakse teadmistebaasi ja neid kasutatakse järgmistel kuudel automaatselt.")

        unresolved = df_res[df_res["Valideerimise staatus"].isin([
            Validator.STATUS_REVIEW,
            Validator.STATUS_UNKNOWN,
            Validator.STATUS_WRONG_ISO,
            Validator.STATUS_WRONG_NAME,
            Validator.STATUS_WRONG_BOTH
        ])]

        if len(unresolved) == 0:
            st.success("Kõik tooted vastavad või on juba teadmistebaasis kinnitatud!")
        else:
            st.info(f"Ülevaatust vajab {len(unresolved)} kirjet.")

            for i, r in unresolved.iterrows():
                with st.expander(f"Rida {r['Rida']}: {r['Abivahendi nimetus (Excel)']} [Staatus: {r['Valideerimise staatus']}]"):
                    col_e1, col_e2 = st.columns([1, 1])

                    with col_e1:
                        st.markdown("**Exceli andmed:**")
                        st.write(f"- Algne nimetus: **{r['Abivahendi nimetus (Excel)']}**")
                        st.write(f"- ISO kood: `{r['ISO kood (Excel)']}`")
                        st.write(f"- Nimetus: {r['Määrusejärgne nimetus (Excel)']}")
                        st.write(f"- Tuvastuse allikas: *{r.get('Tuvastuse allikas')}*")
                        if r.get("Põhjendus"):
                            st.caption(f"💡 **Tuvastuse arutluskäik:** {r['Põhjendus']}")

                    with col_e2:
                        st.markdown("**Kinnitatavad väärtused (Teadmistebaasi):**")
                        c_official = st.text_input(
                            "Ametlik toode:",
                            value=r["Tuvastatud ametlik toode"] or r["Abivahendi nimetus (Excel)"],
                            key=f"off_{r['Rida']}"
                        )
                        c_iso = st.text_input(
                            "Õige ISO kood:",
                            value=r["Ametlik ISO kood"] or r["ISO kood (Excel)"],
                            key=f"iso_{r['Rida']}"
                        )
                        c_stat = st.text_input(
                            "Õige määrusejärgne nimetus:",
                            value=r["Ametlik määrusejärgne nimetus"] or r["Määrusejärgne nimetus (Excel)"],
                            key=f"stat_{r['Rida']}"
                        )

                        if st.button(f"💾 Kinnita ja salvesta teadmistebaasi (Rida {r['Rida']})", key=f"btn_{r['Rida']}", type="primary"):
                            kb.confirm_mapping(
                                raw_name=r["Abivahendi nimetus (Excel)"],
                                normalized_name=r.get("Normaliseeritud nimetus") or normalize_name(r["Abivahendi nimetus (Excel)"]),
                                official_product=c_official,
                                iso_code=c_iso,
                                statutory_name=c_stat,
                                confidence=1.0
                            )
                            st.success("Salvestatud teadmistebaasi! Järgmisel töötlemisel võetakse arvesse.")
                            st.rerun()

    # TAB 3: TEADMISTEBAAS
    with tab3:
        st.subheader("🧠 Õppiv teadmistebaas")
        st.caption("Spetsialisti kinnitatud tooted ja seosed, mida kasutatakse uute failide valideerimisel esmajärjekorras.")
        all_entries = kb.get_all()
        if not all_entries:
            st.info("Teadmistebaas on hetkel tühi.")
        else:
            kb_table = pd.DataFrame(all_entries)
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
            st.dataframe(kb_table[[c for c in display_kb_cols if c in kb_table.columns]], use_container_width=True)

    # TAB 4: SOTSIAALMINISTEERIUMI REGISTER
    with tab4:
        st.subheader("🏛️ Sotsiaalministeeriumi abivahendite loetelu (Püsiv alus)")
        st.caption("Määruse nr 74 ametlik klassifikaator (326 kirjet).")
        all_classes_data = classifier.get_all_classifications()
        if all_classes_data:
            df_classes = pd.DataFrame(all_classes_data)
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
            st.dataframe(df_classes[valid_show], use_container_width=True, height=500)

    # TAB 5: TOOTEREGISTER
    with tab5:
        st.subheader(f"📦 Püsiv Tooteregister ({reg_stats['total_products']:,} toodet)".replace(",", " "))
        st.caption("Eesti abivahendite tarnijate tootekataloogidest ühendatud ja dublikaadivaba register.")

        col_f1, col_f2 = st.columns([2, 1])
        with col_f1:
            prod_search = st.text_input("Otsi tootenime, brändi või aliaset:", key="tab5_search")
        with col_f2:
            all_types = ["Kõik kategooriad"] + [c[0] for c in reg_stats['categories']]
            sel_type = st.selectbox("Filtreeri kategooria järgi:", options=all_types)

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

    # TAB 6: SÜSTEEMI INFO
    with tab6:
        st.subheader("ℹ️ Süsteemi ja arhitektuuri ülevaade")
        st.markdown("""
        - **Andmebaas:** SQLite (`data/valideer.db`)
        - **Püsivad tõeallikad:**
          1. `ametlik_klassifikaator`: Sotsiaalministeeriumi määruse nr 74 abivahendite loetelu (326 kirjet)
          2. `tooteregister`: 4 994 ühendatud toodet (Invaru, ITAK, Terviseabi, Invaabi, Invatooted)
          3. `teadmistebaas`: Spetsialisti kinnitatud seosed ja valideerimise ajalugu
        - **Privaatsuspõhimõte:** Üleslaaditud igakuiste Exceli failide sisu kettale ei salvestata; töötlemine toimub ainult mälus (RAM).
        """)

else:
    st.info("👆 Alustamiseks laadi üles igakuine Exceli fail või klõpsa nupule **'🧪 Laadi näidisandmed (vigadega fail)'**.")
