"""Valideer — Abivahendite andmete kontroll & otsustustugi.

UX Sprint 2: Otsustamise lihtsustamine.
- Selge järgmine samm ja tegevusplokk pärast valideerimist
- Rahulik, mitteagressiivne värvipalett (punane ainult kriitilistele vigadele)
- Kasutajakeskne terminoloogia (otsuste kinnitamine, mitte süsteemi õpetamine)
- Madala kognitiivse koormusega probleemse kirje vaade
- Kahe-tasemeline Exceli raport (Spetsialisti vaade vs Tehniline audit)
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
from src.report import generate_validation_report, format_status_label, get_action_recommendation


# --- LEHE SEADISTUS ---
st.set_page_config(
    page_title="Valideer — Abivahendite andmete kontroll",
    page_icon="assets/valideer_icon.png",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- CVI & DISAINIPÕHIMÕTTED (VALIDEER DISAINISÜSTEEM 1.0 / DARK MODE WCAG 2.2 AA) ---
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@400;500;600&family=IBM+Plex+Sans:wght@400;500;600;700&display=swap');

:root {
  color-scheme: dark;
  /* Semantilised värvitokenid (valideer-disainisusteem-v1/tokens.json) */
  --canvas: #0B0F19;
  --surface: #112D32;
  --panel: #152430;
  --raised: #1B3340;
  --text: #F4F6F9;
  --muted: #B8C7D1;
  --border: #72909D;
  --divider: #344C59;
  --accent: #66C7B8;
  --accent-hover: #83D8CB;
  --accent-pressed: #4FB3A5;
  --link: #80D5E8;
  --focus: #48CAE4;
  --success: #8ED9B4;
  --warning: #F2CD7E;
  --error: #FFB4AB;
  --info: #A7D4F2;
  --ink: #0B0F19;
  --brand-teal: #2A9D8F;
  --font-sans: "IBM Plex Sans", -apple-system, BlinkMacSystemFont, "Segoe UI", Arial, sans-serif;
  --font-mono: "IBM Plex Mono", Consolas, monospace;
  --r-control: 4px;
  --r-panel: 6px;
  --r-badge: 3px;
}

/* 1. Üldine tüpograafia ja taustad */
html, body, p, h1, h2, h3, h4, h5, h6, label, input, textarea, select,
.stMarkdown, div[data-testid="stMarkdownContainer"], .stCaption {
  font-family: var(--font-sans) !important;
  color: var(--text) !important;
  -webkit-font-smoothing: antialiased;
}

.stApp {
  background-color: var(--canvas) !important;
}

[data-testid="stSidebar"] {
  background-color: var(--surface) !important;
  border-right: 1px solid var(--divider) !important;
}

/* 2. Ikoonide kaitse (AINULT tegelikud ikoonid, mitte üleslaadija teksti-spanid) */
.material-symbols-rounded,
.material-symbols-outlined,
[class*="material-symbols"],
[data-testid="stIconMaterial"],
[data-testid*="Icon"] {
  font-family: 'Material Symbols Rounded', 'Material Icons', sans-serif !important;
  font-weight: normal !important;
  font-style: normal !important;
  line-height: 1 !important;
  letter-spacing: normal !important;
  text-transform: none !important;
  display: inline-block !important;
  white-space: nowrap !important;
  word-wrap: normal !important;
  direction: ltr !important;
  -webkit-font-feature-settings: 'liga' !important;
  font-feature-settings: 'liga' !important;
  -webkit-font-smoothing: antialiased !important;
}

/* 3. Külgriba kokkupakkimisnupu viimistlus */
[data-testid="stSidebarCollapseButton"] {
  color: var(--muted) !important;
  background: transparent !important;
  border: none !important;
  padding: 4px 8px !important;
  border-radius: var(--r-control) !important;
  transition: all 0.15s ease-in-out !important;
}
[data-testid="stSidebarCollapseButton"]:hover {
  color: var(--accent) !important;
  background: var(--raised) !important;
}

/* 4. Täisekraani nupu peitmine piltidelt */
[data-testid="StyledFullScreenButton"],
button[title="View fullscreen"],
button[aria-label="View fullscreen"],
[data-testid="stImageActionButton"],
div[data-testid="stImage"] button {
  display: none !important;
  visibility: hidden !important;
  opacity: 0 !important;
  pointer-events: none !important;
  width: 0 !important;
  height: 0 !important;
}

/* 5. Külgriba bränd ja tõeallikate paneel */
.sidebar-brand-svg {
  width: 190px;
  max-width: 100%;
  margin-top: 4px;
  margin-bottom: 6px;
}
.sidebar-brand-svg svg {
  width: 100%;
  height: auto;
  display: block;
}
.sidebar-brand-sub {
  font-size: 0.8125rem;
  color: var(--muted);
  line-height: 1.4;
  margin-bottom: 16px;
}

[data-testid="stRadio"] label {
  font-size: 0.875rem !important;
  color: var(--text) !important;
}
[data-testid="stRadio"] > label {
  font-size: 0.8125rem !important;
  font-weight: 600 !important;
  color: var(--muted) !important;
  text-transform: uppercase !important;
  letter-spacing: 0.05em !important;
}

.sidebar-sources {
  background-color: var(--panel);
  border: 1px solid var(--divider);
  border-radius: var(--r-panel);
  padding: 12px 14px;
  margin-top: 8px;
}
.sidebar-sources-title {
  font-size: 0.75rem;
  font-weight: 600;
  letter-spacing: 0.06em;
  color: var(--accent);
  margin-bottom: 8px;
}
.sidebar-source-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 5px 0;
  border-bottom: 1px solid rgba(52, 76, 89, 0.4);
}
.sidebar-source-row:last-child {
  border-bottom: none;
  padding-bottom: 0;
}
.source-name {
  font-size: 0.8125rem;
  color: var(--muted);
}
.source-badge {
  font-size: 0.8125rem;
  font-weight: 500;
  color: var(--text);
  font-family: var(--font-mono);
}

/* 6. Avalehe 3 kaardi ruudustik (Võrdsed kõrgused!) */
.valideer-card-grid {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 20px;
  align-items: stretch;
  margin: 20px 0 32px 0;
}
@media (max-width: 900px) {
  .valideer-card-grid {
    grid-template-columns: 1fr;
  }
}
.valideer-card {
  background: var(--panel);
  border: 1px solid var(--divider);
  border-radius: var(--r-panel);
  padding: 24px;
  display: flex;
  flex-direction: column;
  box-sizing: border-box;
  height: 100%;
}
.valideer-card h3 {
  font-size: 1.125rem !important;
  line-height: 1.4 !important;
  font-weight: 600 !important;
  color: var(--text) !important;
  margin: 0 0 12px 0 !important;
}
.valideer-card p {
  font-size: 0.9375rem !important;
  line-height: 1.55 !important;
  color: var(--muted) !important;
  margin: 0 !important;
}
.valideer-card ul {
  margin: 0 !important;
  padding-left: 20px !important;
  font-size: 0.9375rem !important;
  line-height: 1.55 !important;
  color: var(--muted) !important;
}
.valideer-card li {
  margin-bottom: 6px !important;
}
.valideer-card li:last-child {
  margin-bottom: 0 !important;
}

/* 7. Faili üleslaadimise konteiner (Dropzone) */
[data-testid="stFileUploader"] {
  background-color: var(--panel) !important;
  border: 1px dashed var(--border) !important;
  border-radius: var(--r-panel) !important;
  padding: 24px !important;
  transition: border-color 0.15s ease-in-out;
}
[data-testid="stFileUploader"]:hover {
  border-color: var(--accent) !important;
}
[data-testid="stFileUploaderDropzone"] {
  background: transparent !important;
  border: none !important;
  padding: 0 !important;
}
[data-testid="stFileUploaderDropzoneInstructions"],
[data-testid="stFileUploader"] small,
[data-testid="stFileUploader"] span:not([class*="material-symbols"]):not([data-testid*="Icon"]) {
  font-family: var(--font-sans) !important;
  font-size: 0.875rem !important;
  color: var(--muted) !important;
  text-transform: none !important;
  letter-spacing: normal !important;
}
[data-testid="stFileUploader"] button {
  min-height: 44px !important;
  padding: 10px 18px !important;
  background-color: var(--accent) !important;
  border: 1px solid var(--accent) !important;
  color: var(--ink) !important;
  border-radius: var(--r-control) !important;
  font-family: var(--font-sans) !important;
  font-weight: 600 !important;
  font-size: 0.9375rem !important;
  cursor: pointer !important;
  transition: background-color 0.15s ease, border-color 0.15s ease !important;
}
[data-testid="stFileUploader"] button:hover {
  background-color: var(--accent-hover) !important;
  border-color: var(--accent-hover) !important;
  color: var(--ink) !important;
}

/* 8. Tüpograafiline skaala */
h1 {
  font-size: clamp(2rem, 1.6rem + 1vw, 2.5rem) !important;
  line-height: 1.2 !important;
  font-weight: 600 !important;
  letter-spacing: -0.02em !important;
  color: var(--text) !important;
  margin-bottom: 0.5rem !important;
}
h2 {
  font-size: clamp(1.5rem, 1.3rem + 0.5vw, 1.75rem) !important;
  line-height: 1.25 !important;
  font-weight: 600 !important;
  letter-spacing: -0.01em !important;
  color: var(--text) !important;
  margin-bottom: 0.5rem !important;
}
h3 {
  font-size: 1.25rem !important;
  line-height: 1.4 !important;
  font-weight: 600 !important;
  color: var(--text) !important;
}
h4 {
  font-size: 1.125rem !important;
  line-height: 1.4 !important;
  font-weight: 600 !important;
  color: var(--text) !important;
}

/* 9. Mõõdikud (Metrics) */
div[data-testid="stMetric"] {
  background-color: var(--panel) !important;
  border: 1px solid var(--divider) !important;
  border-radius: var(--r-panel) !important;
  padding: 14px 18px !important;
  box-shadow: none !important;
}
div[data-testid="stMetricLabel"] {
  color: var(--muted) !important;
  font-size: 0.8125rem !important;
  font-weight: 500 !important;
  text-transform: none !important;
  letter-spacing: normal !important;
}
div[data-testid="stMetricValue"] {
  color: var(--text) !important;
  font-family: var(--font-mono) !important;
  font-size: 1.85rem !important;
  font-weight: 600 !important;
  letter-spacing: -0.01em !important;
}

/* 10. Nupud */
.stButton > button {
  min-height: 44px !important;
  padding: 10px 18px !important;
  border-radius: var(--r-control) !important;
  border: 1px solid var(--border) !important;
  background-color: transparent !important;
  color: var(--text) !important;
  font-family: var(--font-sans) !important;
  font-size: 0.9375rem !important;
  font-weight: 600 !important;
  transition: all 0.15s ease-in-out !important;
}
.stButton > button:hover {
  background-color: var(--raised) !important;
  border-color: var(--accent) !important;
  color: var(--text) !important;
}
.stButton > button:focus-visible {
  outline: 3px solid var(--focus) !important;
  outline-offset: 3px !important;
}
.stButton > button[kind="primary"],
.stDownloadButton > button {
  background-color: var(--accent) !important;
  color: var(--ink) !important;
  border: 1px solid var(--accent) !important;
  font-weight: 600 !important;
}
.stButton > button[kind="primary"]:hover,
.stDownloadButton > button:hover {
  background-color: var(--accent-hover) !important;
  border-color: var(--accent-hover) !important;
  color: var(--ink) !important;
}

/* 11. Vahekaardid (Tabs) */
.stTabs [data-baseweb="tab-list"] {
  background-color: transparent !important;
  border-bottom: 1px solid var(--divider) !important;
  gap: 12px !important;
}
.stTabs [data-baseweb="tab"] {
  color: var(--muted) !important;
  font-size: 0.9375rem !important;
  font-weight: 600 !important;
  padding: 12px 18px !important;
}
.stTabs [aria-selected="true"] {
  color: var(--accent) !important;
  border-bottom: 2px solid var(--accent) !important;
}

/* 12. Laiendatavad paneelid (Expanders) */
div[data-testid="stExpander"] {
  background-color: var(--panel) !important;
  border: 1px solid var(--divider) !important;
  border-radius: var(--r-panel) !important;
  margin-bottom: 12px !important;
}
div[data-testid="stExpander"] summary {
  color: var(--text) !important;
  font-size: 0.9375rem !important;
  font-weight: 600 !important;
  padding: 12px 16px !important;
}
div[data-testid="stExpander"] summary:hover {
  color: var(--accent) !important;
}

/* 13. Tabelid */
div[data-testid="stDataFrame"] {
  border: 1px solid var(--border) !important;
  border-radius: var(--r-control) !important;
  background-color: var(--panel) !important;
}

/* 14. Teavituskastid (Alerts) */
div[data-testid="stAlert"] {
  background-color: var(--panel) !important;
  border: 1px solid var(--divider) !important;
  border-left: 3px solid var(--info) !important;
  border-radius: var(--r-panel) !important;
  color: var(--text) !important;
}

/* 15. Mono- ja koodimärgendid */
.mono {
  font-family: var(--font-mono) !important;
}
code {
  font-family: var(--font-mono) !important;
  background-color: var(--canvas) !important;
  color: var(--link) !important;
  border: 1px solid var(--divider) !important;
  border-radius: var(--r-control) !important;
  padding: 2px 6px !important;
  font-size: 0.85em !important;
}

hr {
  border-color: var(--divider) !important;
}
</style>
""", unsafe_allow_html=True)


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
    logo_svg_path = "assets/valideer-logo-flat.svg"
    if os.path.exists(logo_svg_path):
        with open(logo_svg_path, "r", encoding="utf-8") as f:
            logo_svg = f.read()
        st.markdown(f'<div class="sidebar-brand-svg">{logo_svg}</div>', unsafe_allow_html=True)
    elif os.path.exists("assets/valideer_logo.png"):
        st.image("assets/valideer_logo.png", width=190)
    else:
        st.title("Valideer")
    st.markdown('<div class="sidebar-brand-sub">Abivahendite tehinguridade kontroll</div>', unsafe_allow_html=True)
    st.divider()

    app_mode = st.radio(
        "Töökeskkond:",
        ["📋 Valideerimise töölaud", "📚 Registrid ja haldus"],
        index=0
    )

    st.divider()

    # Süsteemi lühistatistika (valideer-disainisusteem-v1 kompaktne paneel)
    st.markdown(f"""
    <div class="sidebar-sources">
      <div class="sidebar-sources-title">PÜSIVAD TÕEALLIKAD</div>
      <div class="sidebar-source-row">
        <span class="source-name">Määrus nr 74</span>
        <span class="source-badge mono">{class_count} ISO koodi</span>
      </div>
      <div class="sidebar-source-row">
        <span class="source-name">Tooteregister</span>
        <span class="source-badge mono">{reg_stats['total_products']:,} toodet</span>
      </div>
      <div class="sidebar-source-row">
        <span class="source-name">Kinnitatud reeglid</span>
        <span class="source-badge mono">{kb_count} reeglit</span>
      </div>
    </div>
    """.replace(",", " "), unsafe_allow_html=True)

    if st.session_state["df_input"] is not None:
        st.divider()
        st.markdown(f'<div style="font-size: 0.8125rem; color: var(--muted); margin-bottom: 8px;">Aktiivne fail: <strong style="color: var(--text);">{st.session_state["input_source_name"]}</strong></div>', unsafe_allow_html=True)
        if st.button("Uus fail / Tühjenda", use_container_width=True):
            st.session_state["df_input"] = None
            st.session_state["input_source_name"] = None
            st.session_state.pop("cached_validation_results", None)
            st.session_state.pop("last_validation_key", None)
            st.rerun()


# ==============================================================================
# HARU A: VALIDEERIMISE TÖÖLAUD (PÕHITÖÖVOOG)
# ==============================================================================
if app_mode == "📋 Valideerimise töölaud":

    # --- 1. AVALEHT ENNE FAILI LAADIMIST ---
    if st.session_state["df_input"] is None:
        st.title("Abivahendite andmete kontroll")
        st.caption("Sotsiaalministeeriumi määruse nr 74 tehinguridade automaatne vastavuskontroll")

        st.markdown("""
        <p style="color: var(--muted); font-size: 1rem; line-height: 1.5; max-width: 68ch; margin-top: 8px; margin-bottom: 24px;">
        See tööriist kontrollib igakuiseid abivahendite tehingufaile (Excel, CSV) ja tuvastab automaatselt vead ning mittevastavused enne arve esitamist või kinnitamist.
        </p>
        """, unsafe_allow_html=True)

        # Selgitavad väärtuskaardid esmakordsele kasutajale (3 võrdse kõrgusega kaarti!)
        st.markdown("""
        <div class="valideer-card-grid">
          <div class="valideer-card">
            <h3>Mis süsteemiga on tegu?</h3>
            <p>Automaatne reeglimootor, mis võrdleb tehinguridu Sotsiaalministeeriumi määruse nr 74 ametliku loetelu ja Eesti tarnijate ühendatud tooteregistriga.</p>
          </div>
          <div class="valideer-card">
            <h3>Mida kontrollitakse?</h3>
            <ul>
              <li>Toote tuvastamine ja 1:1 ISO koodi kehtivus</li>
              <li>Imavusmahtude (ml) vastavus nõuetele</li>
              <li>Määruse veergude C ja M kitsendused (tsinkoksiid jm)</li>
              <li>Ametliku määrusejärgse nimetuse klapp</li>
            </ul>
          </div>
          <div class="valideer-card">
            <h3>Millist kasu saad?</h3>
            <ul>
              <li>Käsitsitöö asendamine sekunditega</li>
              <li>Finantsiliste tagasinõuete ja tagasilükkamiste ennetamine</li>
              <li>Parandusettepanekutega kahe-tasemeline Exceli raport</li>
            </ul>
          </div>
        </div>
        """, unsafe_allow_html=True)

        st.divider()

        # HERO: Faili üleslaadimine (kõige silmapaistvam element lehel)
        st.subheader("Laadi tehingufail valideerimiseks")

        uploaded_file = st.file_uploader(
            "Vali või lohista siia igakuine Exceli või CSV fail (.xlsx, .xls, .csv)",
            type=["xlsx", "xls", "csv"],
            help="Fail peab sisaldama välju toote nimetuse, ISO koodi ja määrusejärgse nimetusega."
        )

        col_act1, col_act2 = st.columns([1, 2])
        with col_act1:
            load_sample = st.button("Proovi näidisfailiga (vigadega tehingud)", use_container_width=True)

        if uploaded_file is not None:
            try:
                if uploaded_file.name.lower().endswith(".csv"):
                    # Tuvastame automaatselt eraldaja (koma või semikoolon) ja toetame Eesti tähti (utf-8 / windows-1257)
                    try:
                        st.session_state["df_input"] = pd.read_csv(uploaded_file, sep=None, engine='python')
                    except Exception:
                        uploaded_file.seek(0)
                        st.session_state["df_input"] = pd.read_csv(uploaded_file, sep=None, engine='python', encoding='windows-1257')
                else:
                    st.session_state["df_input"] = pd.read_excel(uploaded_file)
                st.session_state["input_source_name"] = uploaded_file.name
                st.session_state.pop("cached_validation_results", None)
                st.session_state.pop("last_validation_key", None)
                st.rerun()
            except Exception as e:
                st.error(f"Viga faili lugemisel: {e}")

        elif load_sample:
            sample_path = "data/naidis_sisend_vigadega.xlsx"
            if os.path.exists(sample_path):
                st.session_state["df_input"] = pd.read_excel(sample_path)
                st.session_state["input_source_name"] = "naidis_sisend_vigadega.xlsx (näidis)"
                st.session_state.pop("cached_validation_results", None)
                st.session_state.pop("last_validation_key", None)
                st.rerun()
            else:
                st.warning("Näidisfaili ei leitud kataloogist data/.")

    # --- 2. TÖÖTLEMINE JA TULEMUSED (PÄRAST FAILI LAADIMIST) ---
    else:
        df_input = st.session_state["df_input"]

        # Tuvasta nõutud veerud paindlikult (sh eesti raamatupidamistarkvarade pealkirjad)
        col_map = {}
        for c in df_input.columns:
            c_clean = str(c).strip().lower()
            if any(term in c_clean for term in ["abivahend", "toote", "artikkel", "kirjeldus", "kaup", "teenus"]) or ("nimetus" in c_clean and "määrus" not in c_clean and "maaruse" not in c_clean):
                if "name" not in col_map:
                    col_map["name"] = c
            elif any(term in c_clean for term in ["iso", "kood", "klassifikaator"]):
                if "name" not in col_map or c != col_map.get("name"):
                    col_map["iso"] = c
            elif any(term in c_clean for term in ["määruse", "maaruse", "ametlik"]):
                col_map["statutory"] = c

        if "name" not in col_map or "iso" not in col_map:
            st.error(f"Exceli failist ei leitud kohustuslikke veerge (tootenimi, ISO kood)! Tuvastatud veerud: {list(df_input.columns)}")
            if st.button("Vali teine fail"):
                st.session_state["df_input"] = None
                st.session_state.pop("cached_validation_results", None)
                st.session_state.pop("last_validation_key", None)
                st.rerun()
            st.stop()

        name_col = col_map["name"]
        iso_col = col_map["iso"]
        stat_col = col_map.get("statutory")

        # Valideeri read (vahemäluga, et vältida tarbetut uuestiarvutust igal filtriklikil)
        cache_key = f"{st.session_state['input_source_name']}_{len(df_input)}_{kb_count}"
        if st.session_state.get("last_validation_key") == cache_key and "cached_validation_results" in st.session_state:
            validation_results = st.session_state["cached_validation_results"]
        else:
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
            st.session_state["cached_validation_results"] = validation_results
            st.session_state["last_validation_key"] = cache_key

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

        # Genereeri kahe-tasemeline Exceli raport (Spetsialisti vaade + Tehniline audit)
        report_bytes = generate_validation_report(validation_results)
        report_filename = f"valideerimise_raport_{datetime.now().strftime('%Y%m%d_%H%M')}.xlsx"

        # --- PÄIS: TULEMUSED JA RAPORTI NUPP ---
        st.title("Valideerimise kokkuvõte")
        st.caption(f"Töödeldud fail: **{st.session_state['input_source_name']}** ({total_rows} rida)")

        # ÜLEMISED KOONDMÕÕDIKUD JA CTA
        c_kpi1, c_kpi2, c_kpi3, c_cta = st.columns([1.5, 1.8, 1.8, 2.5])
        with c_kpi1:
            st.metric("Töödeldud ridu", total_rows)
        with c_kpi2:
            st.metric("Vastab reeglitele", valid_count, f"{int(valid_count/total_rows*100)}%" if total_rows else "")
        with c_kpi3:
            st.metric("Vajab ülevaatust", problem_count, f"{int(problem_count/total_rows*100)}%" if total_rows else "")
        with c_cta:
            st.write("")  # nihutus joondamiseks
            st.download_button(
                label="Laadi valideerimise raport (.xlsx)",
                data=report_bytes,
                file_name=report_filename,
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                use_container_width=True,
                help="Sisaldab spetsialisti kokkuvõtet ja täielikku tehnilist auditit."
            )

        # Probleemide rahulik, astmeline jaotus
        st.markdown("**Tähelepanu vajavate kirjete ülevaade:**")
        cp1, cp2, cp3, cp4, cp5 = st.columns(5)
        cp1.metric("Kitsenduse rikkumine", restriction_violations)
        cp2.metric("Vale ISO kood", wrong_iso)
        cp3.metric("Vale nimetus", wrong_stat)
        cp4.metric("Vale ISO ja nimetus", wrong_both)
        cp5.metric("Vajab kontrolli", needs_review + unknown)

        st.divider()

        # --- 1. TEGEVUSPLOKK: JÄRGMINE SAMM ILMSEKS ---
        if problem_count > 0:
            st.info(f"""
            ### 📋 Spetsialisti tegevusjuhis (Leitud {problem_count} otsustamist vajavat kirjet)
            
            Failis leiti lahknevusi ametliku klassifikaatoriga või määruse nr 74 kitsenduste rikkumisi.
            
            **Sinu järgmised sammud:**
            1. **Vaata üle vead:** Vahekaardil **"🔍 Probleemsete kirjete ülevaade"** on välja toodud täpne põhjus igale reale.
            2. **Kinnita või korrigeeri:** Vahekaardil **"✍️ Paranda ja kinnita kirjed"** saad süsteemi pakutud vasteid kinnitada või muuta.
            3. **Laadi alla raport:** Ülal asuvast nupust saad alla laadida parandustega Exceli raporti.
            4. **Süsteem jätab meelde:** Sinu kinnitatud kirjed salvestatakse ja järgmisel kuul lahenduvad need automaatselt.
            """)
        else:
            st.success(f"""
            ### ✅ Kõik {total_rows} rida vastavad nõuetele!
            Failis ei tuvastatud ühtegi viga ega määruse kitsenduste rikkumist. Fail on valmis kinnitamiseks ja arveldamiseks.
            """)

        # --- TÖÖLAUA VAHEKAARDID: PROBLEEMID JA KINNITAMINE ---
        unresolved = df_res[df_res["Valideerimise staatus"] != Validator.STATUS_MATCH]

        tab_prob, tab_queue = st.tabs([
            f"🔍 Probleemsete kirjete ülevaade ({problem_count})",
            f"✍️ Paranda ja kinnita kirjed ({len(unresolved)})"
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
            df_filtered = df_res[df_res["Valideerimise staatus"].isin(selected_status)].copy()
            df_filtered["Otsuse staatus"] = df_filtered["Valideerimise staatus"].apply(format_status_label)

            if not show_valid:
                st.caption(f"Kuvatakse ainult tähelepanu vajavad kirjed ({len(df_filtered)} rida).")
            else:
                st.caption(f"Kuvatakse kõik valitud staatustega kirjed ({len(df_filtered)} rida).")

            # Tabel otsustamiseks optimeeritud veergudega
            table_cols = [
                "Rida",
                "Otsuse staatus",
                "Selgitus",
                "Abivahendi nimetus (Excel)",
                "Tuvastatud ametlik toode",
                "Tootja",
                "ISO kood (Excel)",
                "Ametlik ISO kood",
                "Määrusejärgne nimetus (Excel)",
                "Ametlik määrusejärgne nimetus"
            ]
            valid_cols = [c for c in table_cols if c in df_filtered.columns]

            st.dataframe(
                df_filtered[valid_cols],
                use_container_width=True,
                height=450
            )

        # --- 4. PROBLEEMSETE KIRJETE LAHENDAMINE (TÕEALLIKA PÕHINE OTSUSTUSMUDEL) ---
        with tab_queue:
            st.subheader("✍️ Probleemsete kirjete lahendamine")
            st.caption(
                "Kinnita arvel esitatud kirjapildi vastavus ametlikule tootele. "
                "ISO kood, määrusejärgne nimetus ja kitsendused pärinevad alati tõeallikatest (tooteregister ja määrus nr 74), mitte arvelt."
            )

            if len(unresolved) == 0:
                st.success("Kõik tooted vastavad nõuetele! Ühtegi lahendamist vajavat kirjet ei ole.")
            else:
                st.info(f"Otsustamist ja toote seostamist vajab {len(unresolved)} kirjet.")

                for _, r in unresolved.iterrows():
                    st_label = format_status_label(r['Valideerimise staatus'])
                    row_id = r['Rida']
                    raw_name = r['Abivahendi nimetus (Excel)']
                    s_prod = r['Tuvastatud ametlik toode'] or "Tundmatu toode"
                    s_mfg = f" ({r['Tootja']})" if r.get('Tootja') else ""

                    with st.expander(f"Rida {row_id}: {raw_name}  —  [{st_label}]"):
                        # 4-ASTMELINE VÕRDLUSMUDEL
                        col_card1, col_card2 = st.columns(2)

                        with col_card1:
                            st.markdown("##### 1. 📄 Esitatud arvel (Kontrollitav väide)")
                            st.write(f"• **Arvel olev tootenimi:** {raw_name}")
                            st.write(f"• **Arvel esitatud ISO:** `{r['ISO kood (Excel)']}`")
                            st.write(f"• **Arvel esitatud nimetus:** {r['Määrusejärgne nimetus (Excel)']}")

                        with col_card2:
                            st.markdown("##### 2. 🏛️ Tõeallikas (Ametlik toode & klassifikatsioon)")
                            st.write(f"• **Tuvastatud toode:** **{s_prod}**{s_mfg}")
                            st.write(f"• **Tõeallika ametlik ISO:** `{r['Ametlik ISO kood'] or 'Määramata'}`")
                            st.write(f"• **Tõeallika ametlik nimetus:** *{r['Ametlik määrusejärgne nimetus'] or 'Määramata'}*")

                        st.divider()

                        # 3. LAHKNEVUSE PÕHJUS JA TEGEVUSJUHIS
                        rec_action = get_action_recommendation(
                            status=r['Valideerimise staatus'],
                            excel_iso=str(r.get('ISO kood (Excel)', '')),
                            official_iso=str(r.get('Ametlik ISO kood', '')),
                            excel_statutory=str(r.get('Määrusejärgne nimetus (Excel)', '')),
                            official_statutory=str(r.get('Ametlik määrusejärgne nimetus', '')),
                            official_product=str(r.get('Tuvastatud ametlik toode', '')),
                            restriction_warning=str(r.get('Selgitus', ''))
                        )

                        st.markdown(f"##### 3. 🔍 Tuvastatud lahknevus tõeallikaga")
                        st.write(f"**Põhjus:** {r.get('Selgitus')}")
                        st.caption(f"👉 **Soovitus menetlejale:** {rec_action}")

                        st.divider()

                        # 4. OTSUS: TOOTE IDENTITEEDI JA ALIASE KINNITAMINE
                        st.markdown("##### 4. 🎯 Sinu otsus: Toote vaste kinnitamine")
                        st.caption("Kinnitades toote vaste, õpib süsteem antud kirjapildi aliast. Ametlikku ISO-koodi ega nimetust käsitsi ei määrata — need rakenduvad automaatselt valitud toote tõeallikast.")

                        col_btn, col_change = st.columns([1.5, 1])
                        with col_change:
                            change_product = st.checkbox("🔍 Vali teine toode tooteregistrist", key=f"chg_{row_id}")

                        chosen_product_name = s_prod
                        chosen_iso = r["Ametlik ISO kood"]
                        chosen_stat = r["Ametlik määrusejärgne nimetus"]

                        if change_product:
                            all_prods = registry_db.get_all_products()
                            prod_options = [p['official_name'] for p in all_prods]
                            def_idx = prod_options.index(s_prod) if s_prod in prod_options else 0
                            selected_from_reg = st.selectbox(
                                "Otsi ja vali korrektne toode registrist:",
                                options=prod_options,
                                index=def_idx,
                                key=f"sel_p_{row_id}"
                            )
                            chosen_product_name = selected_from_reg
                            chosen_obj = registry_db.find_exact_alias(chosen_product_name)
                            if chosen_obj:
                                chosen_iso = chosen_obj.get("suggested_iso", "")
                                chosen_stat = chosen_obj.get("suggested_statutory_name", "")
                                st.info(f"Valitud toote ametlik ISO: **`{chosen_iso}`** | Määrusejärgne nimetus: **{chosen_stat}** (pärineb tooderegistrist)")
                        else:
                            chosen_obj = registry_db.find_exact_alias(s_prod)
                            if chosen_obj:
                                chosen_iso = chosen_obj.get("suggested_iso", r["Ametlik ISO kood"])
                                chosen_stat = chosen_obj.get("suggested_statutory_name", r["Ametlik määrusejärgne nimetus"])

                        with col_btn:
                            btn_label = f"✅ Kinnita toote vaste: '{raw_name}' ➔ '{chosen_product_name}'"
                            if st.button(btn_label, key=f"btn_confirm_{row_id}"):
                                kb.confirm_mapping(
                                    raw_name=raw_name,
                                    normalized_name=r.get("Normaliseeritud nimetus") or normalize_name(raw_name),
                                    official_product=chosen_product_name,
                                    iso_code=chosen_iso,
                                    statutory_name=chosen_stat,
                                    confidence=1.0
                                )
                                st.session_state.pop("cached_validation_results", None)
                                st.session_state.pop("last_validation_key", None)
                                st.toast(f"✅ Toote vaste kinnitatud: '{raw_name}' ➔ '{chosen_product_name}'!", icon="✅")
                                st.rerun()

                        # 5. KOKKUKLAPITAV TEHNILINE AUDITINFO
                        with st.expander("🔬 Vaata tehnilisi tuvastusandmeid (usaldusskoor, allikad, analüüs)"):
                            st.write(f"- Usaldusskoor: **{r.get('Usaldusskoor', 0)*100:.1f}%**")
                            st.write(f"- Tuvastuse allikas: {r.get('Tuvastuse allikas')}")
                            st.write(f"- Kitsenduse reeglikontroll: {r.get('Kitsenduse kontroll')}")
                            st.write(f"- Normaliseeritud nimetus: `{r.get('Normaliseeritud nimetus')}`")
                            if r.get("Põhjendus"):
                                st.write(f"- Agendi arutluskäik: {r.get('Põhjendus')}")


# ==============================================================================
# HARU B: REGISTRID JA HALDUS (ISESEISEV KESKKOND)
# ==============================================================================
else:
    st.title("Registrid ja haldus")
    st.caption("Püsivad tõeallikad ja andmebaasid. Kasutatavad igal ajal, ilma faili üleslaadimata.")

    tab_reg, tab_class, tab_kb, tab_admin = st.tabs([
        f"📦 Tooteregister ({reg_stats['total_products']:,} toodet)".replace(",", " "),
        f"🏛️ Riiklik klassifikaator ({class_count} ISO koodi)",
        f"🧠 Kinnitatud reeglid ({kb_count})",
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
        st.subheader("🏛️ Sotsiaalkindlustusameti ja määruse nr 74 loetelu (alates 01.10.2026)")
        st.caption("Ametlik tõeallikas koos valdkondade, liikide, tootekitsenduste ja piirhindadega.")

        search_q = st.text_input("Otsi klassifikaatorist (ISO kood, valdkond, liik või märksõna):", key="haldus_class_search")

        all_classes_data = classifier.get_all_classifications()
        if all_classes_data:
            df_classes = pd.DataFrame(all_classes_data)
            if search_q:
                q_up = search_q.upper()
                df_classes = df_classes[
                    df_classes["iso_kood"].str.upper().str.contains(q_up, na=False) |
                    df_classes["maarusejargne_nimetus"].str.upper().str.contains(q_up, na=False) |
                    df_classes["tapsustus"].str.upper().str.contains(q_up, na=False) |
                    df_classes.get("valdkond", pd.Series(dtype=str)).str.upper().str.contains(q_up, na=False) |
                    df_classes.get("liik", pd.Series(dtype=str)).str.upper().str.contains(q_up, na=False)
                ]

            show_cols = [
                "iso_kood",
                "valdkond",
                "liik",
                "maarusejargne_nimetus",
                "tapsustus",
                "kasutusaeg",
                "tehingu_liik",
                "piirlimiit",
                "piirmaar",
                "piirhind_muuk",
                "piirhind_uur",
                "omaosaluse_miinimum",
                "uhik",
                "hooldusteenus_h"
            ]
            valid_show = [c for c in show_cols if c in df_classes.columns]
            rename_classes = {
                "iso_kood": "ISO kood",
                "valdkond": "Valdkond",
                "liik": "Liik",
                "maarusejargne_nimetus": "Määrusejärgne nimetus",
                "tapsustus": "Kitsendus / Täpsustus (Veerg C)",
                "kasutusaeg": "Kasutusaeg",
                "tehingu_liik": "Tehingu liik",
                "piirlimiit": "Piirlimiit",
                "piirmaar": "Piirmäär",
                "piirhind_muuk": "Müügi piirhind (€)",
                "piirhind_uur": "Üüri piirhind (€/kuu)",
                "omaosaluse_miinimum": "Omaosaluse miinimum",
                "uhik": "Ühik",
                "hooldusteenus_h": "Hooldekodu piirang (H)"
            }
            st.dataframe(df_classes[valid_show].rename(columns=rename_classes), use_container_width=True, height=500)

    # 3. KINNITATUD REEGLID (ENDINE TEADMISTEBAAS)
    with tab_kb:
        st.subheader("🧠 Kinnitatud reeglid ja erandid")
        st.caption("Spetsialisti poolt kinnitatud reeglid, mida süsteem rakendab automaatselt eelisjärjekorras.")

        all_entries = kb.get_all()
        if not all_entries:
            st.info("Kinnitatud reegleid ei ole veel lisatud. Reeglid lisanduvad siia, kui kinnitate töölaual lahknevustega kirjeid.")
        else:
            kb_df = pd.DataFrame(all_entries)

            col_kb1, col_kb2 = st.columns([3, 1])
            with col_kb2:
                towrite_kb = io.BytesIO()
                kb_df.to_excel(towrite_kb, index=False, engine="openpyxl")
                towrite_kb.seek(0)
                st.download_button(
                    label="💾 Laadi reeglid alla (.xlsx)",
                    data=towrite_kb,
                    file_name="kinnitatud_reeglid.xlsx",
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
