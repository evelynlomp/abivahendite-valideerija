"""Valideer — Abivahendite andmete kontroll ja otsustustugi.

TEDI (TEHIK / Veera) Disainisüsteemil põhinev kasutajaliides.
Visuaalne tõeallikas: assets/TEDI spetsifikatsioonid.
"""

import os
import io
import hmac
import json
import math
import html
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
from src.report import (
    generate_validation_report,
    format_status_label,
    get_action_recommendation,
    format_tedi_badge
)
from src.tedi_table import render_tedi_table
from src.canonical_learning import get_canonical_learning_service, calculate_confidence


# --- LEHE SEADISTUS ---
st.set_page_config(
    page_title="Valideer — Abivahendite andmete kontroll",
    page_icon="assets/valideer_icon.png",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- NOINDEX / NOFOLLOW KAITSE OTSINGUMOOTORITE JA INDEKSEERIJATE VASTU ---
st.markdown(
    '<meta name="robots" content="noindex, nofollow, noarchive, nosnippet">'
    '<meta name="googlebot" content="noindex, nofollow, noarchive, nosnippet">',
    unsafe_allow_html=True
)

# --- CVI & DISAINIPÕHIMÕTTED (TEDI / TEHIK DISAINISÜSTEEM — DARK MODE) ---
css_path = os.path.join(os.path.dirname(__file__), "assets", "tedi-dark.css")
if os.path.exists(css_path):
    with open(css_path, "r", encoding="utf-8") as f:
        st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)


def _get_configured_app_password() -> str:
    """Loeb APP_PASSWORD väärtuse keskkonnamuutujast või Streamlit secrets konfiguratsioonist."""
    env_pw = os.environ.get("APP_PASSWORD", "").strip()
    if env_pw:
        return env_pw
    try:
        if "APP_PASSWORD" in st.secrets:
            return str(st.secrets["APP_PASSWORD"]).strip()
    except Exception:
        pass
    return ""


def _enforce_password_gate() -> bool:
    """Nõuab sisselogimist, kui APP_PASSWORD on seadistatud. Tagastab True, kui paroolikaitse on aktiivne."""
    expected_pw = _get_configured_app_password()
    if not expected_pw:
        return False

    if st.session_state.get("authenticated") is True:
        return True

    st.markdown(
        '<div style="max-width: 440px; margin: 64px auto 16px auto;">'
        '<div class="valideer-card">'
        '<h3>Valideer — Kaitstud ligipääs</h3>'
        '<p style="color: var(--tedi-text-secondary); font-size: 0.9rem;">'
        'Rakenduse kasutamiseks sisesta ligipääsuparool.'
        '</p>'
        '</div></div>',
        unsafe_allow_html=True
    )
    col_l, col_c, col_r = st.columns([1, 1.4, 1])
    with col_c:
        entered_pw = st.text_input("Ligipääsuparool", type="password", key="login_password_input")
        login_clicked = st.button("Logi sisse", type="primary", use_container_width=True)
        if login_clicked or entered_pw:
            if hmac.compare_digest(entered_pw.encode("utf-8"), expected_pw.encode("utf-8")):
                st.session_state["authenticated"] = True
                st.rerun()
            elif login_clicked:
                st.error("Vale ligipääsuparool.")
    st.stop()
    return True


_password_gate_active = _enforce_password_gate()


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
learning_service = get_canonical_learning_service()

def load_canonical_catalog():
    c_path = "data/canonical_products.json"
    if os.path.exists(c_path):
        with open(c_path, "r", encoding="utf-8") as f:
            return json.load(f)
    return []

canonical_products = load_canonical_catalog()

@st.cache_data
def get_statutory_iso_options():
    classes = classifier.get_all_classifications()
    return [f"{c['iso_kood']} — {c['maarusejargne_nimetus']}" for c in classes]

all_iso_options = get_statutory_iso_options()

class_count = classifier.count()
kb_count = kb.count()
reg_stats = registry_db.get_statistics()

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
if "page_val" not in st.session_state:
    st.session_state["page_val"] = 1
if "page_reg" not in st.session_state:
    st.session_state["page_reg"] = 1
if "page_class" not in st.session_state:
    st.session_state["page_class"] = 1
if "page_kb" not in st.session_state:
    st.session_state["page_kb"] = 1
if "page_canon" not in st.session_state:
    st.session_state["page_canon"] = 1
if "page_cands" not in st.session_state:
    st.session_state["page_cands"] = 1


# --- KÜLGRIBA NAVIGATSIOON (TEDI Sidenav spetsifikatsioon) ---
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
        ["Valideerimise töölaud", "Kandidaattoodete töölaud", "Registrid ja haldus"],
        index=0
    )

    st.divider()

    # Süsteemi lühistatistika (TEDI Card formaadis paneel)
    all_cands_count = len(canonical_products)
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
        <span class="source-name">Kandidaattooted</span>
        <span class="source-badge mono">{all_cands_count} toodet</span>
      </div>
      <div class="sidebar-source-row">
        <span class="source-name">Kinnitatud reeglid</span>
        <span class="source-badge mono">{kb_count} reeglit</span>
      </div>
    </div>
    """.replace(",", " "), unsafe_allow_html=True)

    if st.session_state["df_input"] is not None:
        st.divider()
        st.markdown(f'<div style="font-size: 0.8125rem; color: var(--tedi-text-secondary); margin-bottom: 8px;">Aktiivne fail: <strong style="color: var(--tedi-text-primary);">{st.session_state["input_source_name"]}</strong></div>', unsafe_allow_html=True)
        if st.button("Uus fail / Tühjenda", use_container_width=True):
            st.session_state["df_input"] = None
            st.session_state["input_source_name"] = None
            st.session_state.pop("cached_validation_results", None)
            st.session_state.pop("last_validation_key", None)
            st.session_state["page_val"] = 1
            st.rerun()

    if _password_gate_active:
        st.divider()
        if st.button("Logi välja", use_container_width=True):
            st.session_state["authenticated"] = False
            st.rerun()


# ==============================================================================
# HARU A: VALIDEERIMISE TÖÖLAUD (PÕHITÖÖVOOG)
# ==============================================================================
if app_mode == "Valideerimise töölaud":

    # --- 1. AVALEHT ENNE FAILI LAADIMIST ---
    if st.session_state["df_input"] is None:
        st.title("Abivahendite andmete kontroll")
        st.caption("Sotsiaalministeeriumi määruse nr 74 tehinguridade automaatne vastavuskontroll")

        st.markdown("""
        <p style="color: var(--tedi-text-secondary); font-size: 1rem; line-height: 1.5; max-width: 68ch; margin-top: 8px; margin-bottom: 24px;">
        See tööriist kontrollib igakuiseid abivahendite tehingufaile (Excel, CSV) ja tuvastab automaatselt vead ning mittevastavused enne arve esitamist või kinnitamist.
        </p>
        """, unsafe_allow_html=True)

        # Selgitavad väärtuskaardid (TEDI Card ruudustik)
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

        # HERO: Faili üleslaadimine (TEDI Dropzone)
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
                st.session_state["page_val"] = 1
                st.rerun()
            except Exception as e:
                st.markdown(f'<div class="tedi-alert tedi-alert-danger"><div class="tedi-alert-title">Viga faili lugemisel</div><div class="tedi-alert-body">{html.escape(str(e))}</div></div>', unsafe_allow_html=True)

        elif load_sample:
            sample_path = "data/naidis_sisend_vigadega.xlsx"
            if os.path.exists(sample_path):
                st.session_state["df_input"] = pd.read_excel(sample_path)
                st.session_state["input_source_name"] = "naidis_sisend_vigadega.xlsx (näidis)"
                st.session_state.pop("cached_validation_results", None)
                st.session_state.pop("last_validation_key", None)
                st.session_state["page_val"] = 1
                st.rerun()
            else:
                st.markdown('<div class="tedi-alert tedi-alert-warning"><div class="tedi-alert-title">Näidisfail puudub</div><div class="tedi-alert-body">Näidisfaili ei leitud kataloogist data/.</div></div>', unsafe_allow_html=True)

    # --- 2. TÖÖTLEMINE JA TULEMUSED (PÄRAST FAILI LAADIMIST) ---
    else:
        df_input = st.session_state["df_input"]

        # Tuvasta nõutud veerud paindlikult
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
            st.markdown(f"""
            <div class="tedi-alert tedi-alert-danger">
              <div class="tedi-alert-title">Kohustuslikud veerud puuduvad</div>
              <div class="tedi-alert-body">
                Exceli failist ei leitud tootenime ja ISO koodi veerge! Tuvastatud veerud failis: <code>{html.escape(str(list(df_input.columns)))}</code>.
              </div>
            </div>
            """, unsafe_allow_html=True)
            if st.button("Vali teine fail"):
                st.session_state["df_input"] = None
                st.session_state.pop("cached_validation_results", None)
                st.session_state.pop("last_validation_key", None)
                st.rerun()
            st.stop()

        name_col = col_map["name"]
        iso_col = col_map["iso"]
        stat_col = col_map.get("statutory")

        # Valideeri read vahemäluga
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

        # Genereeri kahe-tasemeline Exceli raport
        report_bytes = generate_validation_report(validation_results)
        report_filename = f"valideerimise_raport_{datetime.now().strftime('%Y%m%d_%H%M')}.xlsx"

        # --- PÄIS: TULEMUSED JA RAPORTI NUPP ---
        st.title("Valideerimise kokkuvõte")
        st.caption(f"Töödeldud fail: **{st.session_state['input_source_name']}** ({total_rows} rida)")

        # ÜLEMISED KOONDMÕÕDIKUD (TEDI SUMMARY CARDS) JA CTA NUPP
        c_kpi_wrap, c_cta = st.columns([3, 1])
        with c_kpi_wrap:
            st.markdown(f"""
            <div class="tedi-summary-grid" style="margin: 0;">
              <div class="tedi-summary-card primary">
                <div class="tedi-summary-label">Töödeldud kirjeid kokku</div>
                <div class="tedi-summary-value-row">
                  <span class="tedi-summary-value">{total_rows}</span>
                  <span class="tedi-summary-sub">rida</span>
                </div>
              </div>
              <div class="tedi-summary-card success">
                <div class="tedi-summary-label">Vastab nõuetele</div>
                <div class="tedi-summary-value-row">
                  <span class="tedi-summary-value">{valid_count}</span>
                  <span class="tedi-summary-sub">({int(valid_count/total_rows*100) if total_rows else 0}%)</span>
                </div>
              </div>
              <div class="tedi-summary-card {'danger' if problem_count > 0 else 'success'}">
                <div class="tedi-summary-label">Vajab ülevaatust / Vigu</div>
                <div class="tedi-summary-value-row">
                  <span class="tedi-summary-value">{problem_count}</span>
                  <span class="tedi-summary-sub">({int(problem_count/total_rows*100) if total_rows else 0}%)</span>
                </div>
              </div>
            </div>
            """, unsafe_allow_html=True)

        with c_cta:
            st.write("")
            st.write("")
            st.download_button(
                label="Laadi valideerimise raport (.xlsx)",
                data=report_bytes,
                file_name=report_filename,
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                use_container_width=True,
                help="Sisaldab spetsialisti kokkuvõtet ja täielikku tehnilist auditit."
            )

        # Probleemide jaotus TEDI Summary Cards kujul
        if problem_count > 0:
            st.markdown(f"""
            <div style="font-family: var(--font-family); font-size: 13px; font-weight: 700; color: var(--tedi-text-secondary); margin-top: 20px; margin-bottom: 8px; text-transform: uppercase; letter-spacing: 0.05em;">Tähelepanu vajavate kirjete jaotus:</div>
            <div class="tedi-summary-grid" style="grid-template-columns: repeat(auto-fit, minmax(130px, 1fr)); margin-top: 4px; margin-bottom: 20px;">
              <div class="tedi-summary-card danger" style="padding: 12px 14px;">
                <div class="tedi-summary-label">Kitsenduse rikkumine</div>
                <div class="tedi-summary-value" style="font-size: 24px;">{restriction_violations}</div>
              </div>
              <div class="tedi-summary-card warning" style="padding: 12px 14px;">
                <div class="tedi-summary-label">Vale ISO kood</div>
                <div class="tedi-summary-value" style="font-size: 24px;">{wrong_iso}</div>
              </div>
              <div class="tedi-summary-card warning" style="padding: 12px 14px;">
                <div class="tedi-summary-label">Vale nimetus</div>
                <div class="tedi-summary-value" style="font-size: 24px;">{wrong_stat}</div>
              </div>
              <div class="tedi-summary-card danger" style="padding: 12px 14px;">
                <div class="tedi-summary-label">Vale ISO ja nimetus</div>
                <div class="tedi-summary-value" style="font-size: 24px;">{wrong_both}</div>
              </div>
              <div class="tedi-summary-card primary" style="padding: 12px 14px;">
                <div class="tedi-summary-label">Vajab kontrolli</div>
                <div class="tedi-summary-value" style="font-size: 24px;">{needs_review + unknown}</div>
              </div>
            </div>
            """, unsafe_allow_html=True)

        # Tegevusjuhised (TEDI Alert)
        if problem_count > 0:
            st.markdown(f"""
            <div class="tedi-alert tedi-alert-info">
              <div class="tedi-alert-title">Spetsialisti tegevusjuhis (Leitud {problem_count} otsustamist vajavat kirjet)</div>
              <div class="tedi-alert-body">
                Failis leiti lahknevusi ametliku klassifikaatoriga või määruse nr 74 kitsenduste rikkumisi.
                <ol>
                  <li><strong>Vaata üle vead:</strong> Vahekaardil <strong>"Probleemsete kirjete ülevaade"</strong> on välja toodud iga kirje täpne staatus ja lahknevuse selgitus.</li>
                  <li><strong>Kinnita või korrigeeri:</strong> Vahekaardil <strong>"Paranda ja kinnita kirjed"</strong> saab süsteemi pakutud vasteid kinnitada või muuta.</li>
                  <li><strong>Laadi alla raport:</strong> Ülal asuvast nupust saab alla laadida parandustega ametliku kahe-tasemelise Exceli raporti.</li>
                  <li><strong>Õppiv teadmistebaas:</strong> Sinu kinnitatud kirjed salvestatakse ja järgmisel kuul lahenduvad need automaatselt.</li>
                </ol>
              </div>
            </div>
            """, unsafe_allow_html=True)
        else:
            st.markdown(f"""
            <div class="tedi-alert tedi-alert-success">
              <div class="tedi-alert-title">Kõik {total_rows} rida vastavad nõuetele</div>
              <div class="tedi-alert-body">
                Failis ei tuvastatud ühtegi viga ega määruse kitsenduste rikkumist. Fail on valmis kinnitamiseks ja arveldamiseks.
              </div>
            </div>
            """, unsafe_allow_html=True)

        # --- TÖÖLAUA VAHEKAARDID: PROBLEEMID JA KINNITAMINE ---
        unresolved = df_res[df_res["Valideerimise staatus"] != Validator.STATUS_MATCH]

        tab_prob, tab_queue = st.tabs([
            f"Probleemsete kirjete ülevaade ({problem_count})",
            f"Paranda ja kinnita kirjed ({len(unresolved)})"
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

                status_labels_map = {s: format_status_label(s) for s in available_statuses}
                selected_status_labels = st.multiselect(
                    "Filtreeri staatuse järgi:",
                    options=list(status_labels_map.values()),
                    default=[status_labels_map[s] for s in default_selected if s in status_labels_map]
                )
                selected_status = [k for k, v in status_labels_map.items() if v in selected_status_labels]

            df_filtered = df_res[df_res["Valideerimise staatus"].isin(selected_status)].copy()

            if not show_valid:
                st.caption(f"Kuvatakse ainult tähelepanu vajavad kirjed ({len(df_filtered)} rida).")
            else:
                st.caption(f"Kuvatakse kõik valitud staatustega kirjed ({len(df_filtered)} rida).")

            # Leheküljestamise loogika
            val_page_size = 20
            total_val_rows = len(df_filtered)
            total_val_pages = max(1, math.ceil(total_val_rows / val_page_size))
            if st.session_state["page_val"] > total_val_pages:
                st.session_state["page_val"] = 1

            table_config = [
                {"key": "Rida", "label": "Rida", "type": "mono", "width": "50px"},
                {"key": "Valideerimise staatus", "label": "Otsuse staatus", "type": "badge", "width": "180px"},
                {"key": "Abivahendi nimetus (Excel)", "label": "Tootenimi arvel", "type": "text"},
                {"key": "Tuvastatud ametlik toode", "label": "Tuvastatud toode", "type": "bold"},
                {"key": "ISO kood (Excel)", "label": "Esitatud ISO", "type": "code", "width": "100px"},
                {"key": "Ametlik ISO kood", "label": "Ametlik ISO", "type": "code_highlight", "width": "100px"},
                {"key": "Ametlik määrusejärgne nimetus", "label": "Määrusejärgne nimetus", "type": "text"},
                {"key": "Selgitus", "label": "Lahknevuse selgitus", "type": "muted"}
            ]

            # Autentne TEDI Semantiline HTML5 Tabel
            tedi_html = render_tedi_table(
                df=df_filtered,
                columns_config=table_config,
                current_page=st.session_state["page_val"],
                page_size=val_page_size,
                table_id="tedi_validation_table"
            )
            st.markdown(tedi_html, unsafe_allow_html=True)

            # Leheküljestamise nupud
            if total_val_pages > 1:
                col_vp1, col_vp2, col_vp3 = st.columns([1, 2, 1])
                with col_vp1:
                    if st.button("Eelmine leht", disabled=(st.session_state["page_val"] <= 1), key="btn_vp_prev", use_container_width=True):
                        st.session_state["page_val"] -= 1
                        st.rerun()
                with col_vp3:
                    if st.button("Järgmine leht", disabled=(st.session_state["page_val"] >= total_val_pages), key="btn_vp_next", use_container_width=True):
                        st.session_state["page_val"] += 1
                        st.rerun()

        # --- 4. PROBLEEMSETE KIRJETE LAHENDAMINE (TEDI VORMID JA SISEKAARDID) ---
        with tab_queue:
            st.subheader("Probleemsete kirjete lahendamine")
            st.caption(
                "Kinnita arvel esitatud kirjapildi vastavus ametlikule tootele. "
                "ISO kood, määrusejärgne nimetus ja kitsendused pärinevad alati tõeallikatest (tooteregister ja määrus nr 74), mitte arvelt."
            )

            if len(unresolved) == 0:
                st.markdown('<div class="tedi-alert tedi-alert-success"><div class="tedi-alert-title">Kõik tooted vastavad nõuetele</div><div class="tedi-alert-body">Ühtegi lahendamist vajavat kirjet ei ole.</div></div>', unsafe_allow_html=True)
            else:
                st.markdown(f'<div style="font-size: 14px; color: var(--tedi-text-secondary); margin-bottom: 16px;">Otsustamist ja toote seostamist vajab <strong>{len(unresolved)}</strong> kirjet.</div>', unsafe_allow_html=True)

                for _, r in unresolved.iterrows():
                    st_clean = format_status_label(r['Valideerimise staatus'])
                    row_id = r['Rida']
                    raw_name = r['Abivahendi nimetus (Excel)']
                    s_prod = r['Tuvastatud ametlik toode'] or "Tundmatu toode"
                    s_mfg = f" ({r['Tootja']})" if r.get('Tootja') else ""

                    with st.expander(f"Rida {row_id}: {raw_name}  —  [{st_clean}]"):
                        # 4-ASTMELINE VÕRDLUSMUDEL (TEDI Card.txt sisekaardid)
                        col_card1, col_card2 = st.columns(2)

                        with col_card1:
                            st.markdown(f"""
                            <div class="tedi-inner-card">
                              <h5>1. Esitatud arvel (Kontrollitav väide)</h5>
                              <div style="margin-bottom: 4px;">• <strong>Arvel olev tootenimi:</strong> {html.escape(raw_name)}</div>
                              <div style="margin-bottom: 4px;">• <strong>Arvel esitatud ISO:</strong> <code class="mono">{html.escape(str(r['ISO kood (Excel)']))}</code></div>
                              <div>• <strong>Arvel esitatud nimetus:</strong> {html.escape(str(r['Määrusejärgne nimetus (Excel)']))}</div>
                            </div>
                            """, unsafe_allow_html=True)

                        with col_card2:
                            off_iso = r['Ametlik ISO kood'] or 'Määramata'
                            off_stat = r['Ametlik määrusejärgne nimetus'] or 'Määramata'
                            st.markdown(f"""
                            <div class="tedi-inner-card">
                              <h5>2. Tõeallikas (Ametlik toode ja klassifikatsioon)</h5>
                              <div style="margin-bottom: 4px;">• <strong>Tuvastatud toode:</strong> <strong>{html.escape(s_prod)}</strong>{html.escape(s_mfg)}</div>
                              <div style="margin-bottom: 4px;">• <strong>Tõeallika ametlik ISO:</strong> <code class="mono">{html.escape(str(off_iso))}</code></div>
                              <div>• <strong>Tõeallika ametlik nimetus:</strong> <em>{html.escape(str(off_stat))}</em></div>
                            </div>
                            """, unsafe_allow_html=True)

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

                        st.markdown(f"""
                        <div class="tedi-inner-card" style="border-left: 4px solid var(--tedi-status-warning-border);">
                          <h5>3. Tuvastatud lahknevus tõeallikaga</h5>
                          <div style="margin-bottom: 6px;"><strong>Põhjus:</strong> {html.escape(str(r.get('Selgitus')))}</div>
                          <div style="color: var(--tedi-text-link);"><strong>Soovitus menetlejale:</strong> {html.escape(rec_action)}</div>
                        </div>
                        """, unsafe_allow_html=True)

                        # 4. OTSUS: TOOTE IDENTITEEDI JA ALIASE KINNITAMINE
                        st.markdown("""
                        <div class="tedi-inner-card" style="border-left: 4px solid var(--tedi-primary); margin-bottom: 8px;">
                          <h5>4. Otsus: Toote vaste kinnitamine</h5>
                          <div style="font-size: 13px; color: var(--tedi-text-secondary);">
                            Kinnitades toote vaste, õpib süsteem antud kirjapildi aliast. Reegleid salvestatakse vajaduspõhiselt (ainult madala süsteemikindluse või lahknevuse korral). Ametlikku ISO-koodi käsitsi ei määrata — see rakendub automaatselt valitud toote tõeallikast.
                          </div>
                        </div>
                        """, unsafe_allow_html=True)

                        col_btn, col_change = st.columns([1.5, 1])
                        with col_change:
                            change_product = st.checkbox("Vali teine toode tooteregistrist", key=f"chg_{row_id}")

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
                                st.markdown(f'<div class="tedi-alert tedi-alert-info" style="margin: 8px 0; padding: 10px 14px;"><div class="tedi-alert-body">Valitud toote ametlik ISO: <strong><code class="mono">{chosen_iso}</code></strong> | Määrusejärgne nimetus: <strong>{chosen_stat}</strong></div></div>', unsafe_allow_html=True)
                        else:
                            chosen_obj = registry_db.find_exact_alias(s_prod)
                            if chosen_obj:
                                chosen_iso = chosen_obj.get("suggested_iso", r["Ametlik ISO kood"])
                                chosen_stat = chosen_obj.get("suggested_statutory_name", r["Ametlik määrusejärgne nimetus"])

                        with col_btn:
                            btn_label = f"Kinnita toote vaste: '{raw_name}' -> '{chosen_product_name}'"
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
                                st.toast(f"Toote vaste kinnitatud: '{raw_name}' -> '{chosen_product_name}'")
                                st.rerun()

                        # 5. KOKKUKLAPITAV TEHNILINE AUDITINFO
                        with st.expander("Tehnilised tuvastusandmed (usaldusskoor, allikad, analüüs)"):
                            st.write(f"- Usaldusskoor: **{r.get('Usaldusskoor', 0)*100:.1f}%**")
                            st.write(f"- Tuvastuse allikas: {r.get('Tuvastuse allikas')}")
                            st.write(f"- Kitsenduse reeglikontroll: {r.get('Kitsenduse kontroll')}")
                            st.write(f"- Normaliseeritud nimetus: `{r.get('Normaliseeritud nimetus')}`")
                            if r.get("Põhjendus"):
                                st.write(f"- Otsuse selgitus: {r.get('Põhjendus')}")


# ==============================================================================
# HARU B: KANDIDAATTOODETE TÖÖLAUD (LIKELY JA UNCLASSIFIED TOOTED)
# ==============================================================================
elif app_mode == "Kandidaattoodete töölaud":
    st.title("Kandidaattoodete töölaud")
    st.caption("Veebiallikatest tuvastatud uute toodete läbivaatus, ISO-vastavuse kinnitamine ja õppimine.")

    # 1. Pärime kandidaattooted: ainult LIKELY ja UNCLASSIFIED
    candidate_products = learning_service.get_candidate_products(canonical_products)
    likely_candidates = [c for c in candidate_products if c["status"] == "LIKELY"]
    unclass_candidates = [c for c in candidate_products if c["status"] == "UNCLASSIFIED"]

    # KPI kokkuvõte (TEDI Summary Grid)
    all_learned_recs = learning_service.get_all_learning_records()
    total_confirms = sum(r.get("kinnitatud_arv", 0) for r in all_learned_recs)
    total_rejects = sum(r.get("tagasi_lukatud_arv", 0) for r in all_learned_recs)

    st.markdown(f"""
    <div class="tedi-summary-grid">
      <div class="tedi-summary-card primary">
        <div class="tedi-summary-label">Kandidaate töölaual</div>
        <div class="tedi-summary-value">{len(candidate_products)}</div>
      </div>
      <div class="tedi-summary-card">
        <div class="tedi-summary-label">LIKELY (ISO kandidaadiga)</div>
        <div class="tedi-summary-value">{len(likely_candidates)}</div>
      </div>
      <div class="tedi-summary-card">
        <div class="tedi-summary-label">UNCLASSIFIED (liigitamata)</div>
        <div class="tedi-summary-value">{len(unclass_candidates)}</div>
      </div>
      <div class="tedi-summary-card">
        <div class="tedi-summary-label">Kasutaja kinnitusi</div>
        <div class="tedi-summary-value">{total_confirms}</div>
      </div>
    </div>
    """, unsafe_allow_html=True)

    # Filtri ja otsingu riba
    col_fil1, col_fil2 = st.columns([1, 2])
    with col_fil1:
        cand_filter = st.selectbox(
            "Kuvatakse kategooria:",
            [
                f"Kõik kandidaadid ({len(candidate_products)})",
                f"Ainult LIKELY ({len(likely_candidates)})",
                f"Ainult UNCLASSIFIED ({len(unclass_candidates)})"
            ],
            key="cand_wk_filter"
        )
    with col_fil2:
        cand_search = st.text_input(
            "Otsi tootenime, brändi, tootja või mudeli järgi:",
            key="cand_wk_search",
            placeholder="Nt Oticon Intent, Real, Own, Prowax, Fresco..."
        )

    # Filtreerimine
    filtered_cands = []
    for c in candidate_products:
        if "LIKELY" in cand_filter and c["status"] != "LIKELY":
            continue
        if "UNCLASSIFIED" in cand_filter and c["status"] != "UNCLASSIFIED":
            continue
        if cand_search:
            s_up = cand_search.upper()
            match = (
                s_up in c["canonical_name"].upper() or
                s_up in c["manufacturer"].upper() or
                s_up in c["brand"].upper() or
                any(s_up in str(a).upper() for a in c.get("aliases", []))
            )
            if not match:
                continue
        filtered_cands.append(c)

    st.caption(f"Kuvatakse {len(filtered_cands)} toodet.")

    if not filtered_cands:
        st.markdown('<div class="tedi-alert tedi-alert-info"><div class="tedi-alert-title">Kandidaattooteid ei leitud</div><div class="tedi-alert-body">Otsingu või filtri tingimustele vastavaid tooteid töölaual ei leidu.</div></div>', unsafe_allow_html=True)
    else:
        # Leheküljestamine (10 toodet lehel)
        cands_page_size = 10
        total_cands_pages = max(1, math.ceil(len(filtered_cands) / cands_page_size))
        if st.session_state["page_cands"] > total_cands_pages:
            st.session_state["page_cands"] = 1

        start_c = (st.session_state["page_cands"] - 1) * cands_page_size
        end_c = min(start_c + cands_page_size, len(filtered_cands))
        page_cands = filtered_cands[start_c:end_c]

        for c in page_cands:
            c_id = c["canonical_id"]
            c_name = c["canonical_name"]
            mfg = c["manufacturer"]
            brand = c["brand"]
            sources_count = c["sources_count"]
            aliases_count = c["aliases_count"]
            aliases = c["aliases"]
            image_url = c["image"]
            iso_candidates = c["iso_candidates"]
            confidence_score = c["confidence_score"]
            status = c["status"]

            # Staatusbadge
            if status == "LIKELY":
                status_badge = '<span class="tedi-badge tedi-badge-warning">LIKELY</span>'
                border_col = "var(--tedi-status-warning-border)"
            else:
                status_badge = '<span class="tedi-badge tedi-badge-info">UNCLASSIFIED</span>'
                border_col = "var(--tedi-border)"

            # Usaldusbadge
            if confidence_score >= 90.0:
                conf_badge = f'<span class="tedi-badge tedi-badge-success">Usaldus: {confidence_score:.0f}%</span>'
            elif confidence_score >= 50.0:
                conf_badge = f'<span class="tedi-badge tedi-badge-warning">Usaldus: {confidence_score:.0f}%</span>'
            else:
                conf_badge = '<span class="tedi-badge tedi-badge-info">Usaldus: Määramata</span>'

            # Toote kaardi ümbris
            st.markdown(f"""
            <div class="tedi-inner-card" style="margin-bottom: 24px; border-left: 4px solid {border_col}; padding: 20px;">
              <div style="display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 10px;">
                <div>
                  <h3 style="margin: 0 0 4px 0; font-size: 19px; font-weight: 700; color: var(--tedi-text-primary);">{html.escape(c_name)}</h3>
                  <div style="font-size: 14px; color: var(--tedi-text-secondary);">
                    <strong>Tootja:</strong> {html.escape(mfg)} &nbsp;|&nbsp; <strong>Bränd:</strong> {html.escape(brand)}
                  </div>
                </div>
                <div style="display: flex; gap: 8px; align-items: center;">
                  {status_badge}
                  {conf_badge}
                </div>
              </div>
              <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(160px, 1fr)); gap: 12px; margin: 12px 0; padding: 10px 14px; background-color: var(--tedi-canvas); border-radius: var(--tedi-radius-md); font-size: 13px;">
                <div>Allikate arv: <strong style="color: var(--tedi-text-primary);">{sources_count} allikat</strong></div>
                <div>Aliaste arv: <strong style="color: var(--tedi-text-primary);">{aliases_count} aliast</strong></div>
                <div>Hind: <strong style="color: var(--tedi-text-primary);">{html.escape(c.get('price_str', 'Täpsustamisel'))}</strong></div>
              </div>
            </div>
            """, unsafe_allow_html=True)

            # Kaardi sisu ja interaktsioon
            col_main, col_side = st.columns([3, 1])

            with col_side:
                if image_url:
                    st.image(image_url, caption=c_name, use_container_width=True)
                else:
                    st.markdown("<div style='border: 1px dashed var(--tedi-border); border-radius: var(--tedi-radius-md); padding: 30px 10px; text-align: center; color: var(--tedi-text-muted); font-size: 13px;'>Pilt puudub</div>", unsafe_allow_html=True)

            with col_main:
                if aliases:
                    alias_preview = " ".join([f"<code>{html.escape(str(a))}</code>" for a in aliases[:6]])
                    if len(aliases) > 6:
                        alias_preview += f" <span style='color: var(--tedi-text-muted);'>+{len(aliases)-6} veel</span>"
                    st.markdown(f"<div style='margin-bottom: 10px; font-size: 13px;'><strong>Tuvastatud aliased ({len(aliases)} tk):</strong><br/>{alias_preview}</div>", unsafe_allow_html=True)

                # ISO kandidaatide kuvamine ja valik
                chosen_iso = None
                chosen_stat = None

                if iso_candidates:
                    st.markdown("<strong>ISO kandidaadid ja reeglisoovitused:</strong>", unsafe_allow_html=True)
                    if len(iso_candidates) == 1:
                        cand0 = iso_candidates[0]
                        chosen_iso = cand0["iso_code"]
                        chosen_stat = cand0["statutory_name"]
                        st.markdown(f"<div style='margin: 6px 0; font-size: 14px;'><code>{chosen_iso}</code> — <strong>{chosen_stat}</strong> <span style='color: var(--tedi-text-muted); font-size: 12px;'>({cand0.get('note', '')})</span></div>", unsafe_allow_html=True)
                    else:
                        cand_opts = [f"{cd['iso_code']} — {cd['statutory_name']} (Usaldus: {cd['confidence']:.0f}%)" for cd in iso_candidates]
                        sel_cand = st.radio(
                            "Vali kinnitatav kandidaat:",
                            options=cand_opts,
                            key=f"cand_radio_{c_id}",
                            label_visibility="collapsed"
                        )
                        chosen_iso = sel_cand.split(" — ")[0].strip()
                        chosen_stat = sel_cand.split(" — ")[1].split(" (")[0].strip() if " — " in sel_cand else ""
                else:
                    st.markdown("<div style='color: var(--tedi-text-muted); font-size: 13px; margin: 6px 0;'>ISO kandidaat: <em>Klassifitseerimata (puudub)</em></div>", unsafe_allow_html=True)

                # Ühe-kliki toimingud: [Kinnita] [Lükka tagasi] [Muuda ISO-d]
                col_btn1, col_btn2, col_btn3 = st.columns([1, 1, 1])

                with col_btn1:
                    confirm_label = f"Kinnita ({chosen_iso})" if chosen_iso else "Kinnita"
                    if st.button(confirm_label, key=f"act_conf_{c_id}", type="primary", disabled=(chosen_iso is None), use_container_width=True):
                        learning_service.record_decision(
                            canonical_name=c_name,
                            iso_code=chosen_iso,
                            statutory_name=chosen_stat,
                            action="CONFIRM",
                            rationale="Kinnitatud kandidaattoodete töölaualt",
                            user="Spetsialist"
                        )
                        st.toast(f"Toode '{c_name}' kinnitatud ISO koodile {chosen_iso}!")
                        st.rerun()

                with col_btn2:
                    reject_label = "Lükka tagasi"
                    if st.button(reject_label, key=f"act_rej_{c_id}", use_container_width=True):
                        if chosen_iso:
                            learning_service.record_decision(
                                canonical_name=c_name,
                                iso_code=chosen_iso,
                                statutory_name=chosen_stat,
                                action="REJECT",
                                rationale="Tagasi lükatud kandidaattoodete töölaualt",
                                user="Spetsialist"
                            )
                            st.toast(f"ISO {chosen_iso} lükatud tagasi tootele '{c_name}'!")
                        else:
                            st.toast(f"Toode '{c_name}' märgitud määruseväliseks kaubaks.")
                        st.rerun()

                with col_btn3:
                    show_iso_change = st.toggle("Muuda ISO-d", key=f"toggle_iso_{c_id}")

                # Kui kasutaja soovib ISO-d muuta
                if show_iso_change:
                    st.markdown("<div style='margin-top: 10px; padding: 12px; background-color: var(--tedi-surface-raised); border-radius: var(--tedi-radius-md); border: 1px solid var(--tedi-border);'>", unsafe_allow_html=True)
                    col_ch1, col_ch2 = st.columns([3, 1])
                    with col_ch1:
                        picked_iso_full = st.selectbox(
                            "Vali määruse nr 74 ametlik klassifikaator:",
                            options=all_iso_options,
                            key=f"sel_change_{c_id}",
                            label_visibility="collapsed"
                        )
                        change_rationale = st.text_input(
                            "Põhjendus:",
                            key=f"input_ch_reason_{c_id}",
                            placeholder="Nt spetsialisti määratud täpsem aktiivsustase",
                            label_visibility="collapsed"
                        )
                    with col_ch2:
                        if st.button("Kinnita uus ISO", key=f"btn_save_iso_{c_id}", type="primary", use_container_width=True):
                            new_c_iso = picked_iso_full.split(" — ")[0].strip()
                            new_c_stat = picked_iso_full.split(" — ")[1].strip() if " — " in picked_iso_full else ""
                            learning_service.change_iso(
                                canonical_name=c_name,
                                new_iso_code=new_c_iso,
                                new_statutory_name=new_c_stat,
                                rationale=change_rationale or "Spetsialisti määratud uus ISO",
                                user="Spetsialist"
                            )
                            st.toast(f"Tootele '{c_name}' määratud ja kinnitatud uus ISO {new_c_iso}!")
                            st.rerun()
                    st.markdown("</div>", unsafe_allow_html=True)

            st.markdown("---")

        # Leheküljestamise juhtnupud
        if total_cands_pages > 1:
            col_cp1, col_cp2, col_cp3 = st.columns([1, 2, 1])
            with col_cp1:
                if st.button("Eelmine leht (Kandidaadid)", disabled=(st.session_state["page_cands"] <= 1), key="btn_cands_prev", use_container_width=True):
                    st.session_state["page_cands"] -= 1
                    st.rerun()
            with col_cp2:
                st.markdown(f"<div style='text-align: center; color: var(--tedi-text-secondary); padding-top: 8px;'>Lehekülg <strong>{st.session_state['page_cands']} / {total_cands_pages}</strong> (kokku {len(filtered_cands)} kandidaati)</div>", unsafe_allow_html=True)
            with col_cp3:
                if st.button("Järgmine leht (Kandidaadid)", disabled=(st.session_state["page_cands"] >= total_cands_pages), key="btn_cands_next", use_container_width=True):
                    st.session_state["page_cands"] += 1
                    st.rerun()


# ==============================================================================
# HARU C: REGISTRID JA HALDUS (ISESEISEV KESKKOND)
# ==============================================================================
else:
    st.title("Registrid ja haldus")
    st.caption("Püsivad tõeallikad ja andmebaasid. Kasutatavad igal ajal, ilma faili üleslaadimata.")

    tab_canon, tab_reg, tab_class, tab_kb, tab_admin = st.tabs([
        f"Õppiv tootekataloog ({len(canonical_products)})",
        f"Tooteregister ({reg_stats['total_products']:,} toodet)".replace(",", " "),
        f"Riiklik klassifikaator ({class_count} ISO koodi)",
        f"Kinnitatud reeglid ({kb_count})",
        "Haldus ja süsteemiinfo"
    ])

    # 0. ÕPPIV KANOONILINE TOOTEKATALOOG
    with tab_canon:
        st.subheader("Õppiv Kanooniline Tootekataloog")
        st.caption("Deduplitseeritud tooted, koondatud aliased ning spetsialisti poolt kinnitatud ja tagasi lükatud ISO-koodide usaldusbaas.")

        all_learned = learning_service.get_all_learning_records()
        total_confirms = sum(r.get("kinnitatud_arv", 0) for r in all_learned)
        total_rejects = sum(r.get("tagasi_lukatud_arv", 0) for r in all_learned)

        st.markdown(f"""
        <div class="tedi-summary-grid">
          <div class="tedi-summary-card primary">
            <div class="tedi-summary-label">Kanoonilisi tooteid</div>
            <div class="tedi-summary-value">{len(canonical_products)}</div>
          </div>
          <div class="tedi-summary-card">
            <div class="tedi-summary-label">Kinnitatud ISO seoseid</div>
            <div class="tedi-summary-value">{total_confirms}</div>
          </div>
          <div class="tedi-summary-card">
            <div class="tedi-summary-label">Tagasi lükatud seoseid</div>
            <div class="tedi-summary-value">{total_rejects}</div>
          </div>
          <div class="tedi-summary-card">
            <div class="tedi-summary-label">Õpitud reegleid baasis</div>
            <div class="tedi-summary-value">{len(all_learned)}</div>
          </div>
        </div>
        """, unsafe_allow_html=True)

        col_cf1, col_cf2 = st.columns([2, 1])
        with col_cf1:
            canon_search = st.text_input("Otsi kanoonilist toodet, mudelit või aliaset:", key="canon_search_input", placeholder="Nt Oticon Intent, Galeo, Skeo, ResMed...")
        with col_cf2:
            canon_filter = st.selectbox(
                "Filtreeri staatuse järgi:",
                [
                    "Kõik tooted",
                    "Ainult tagasisidega / õpitud tooted",
                    "Ülevaatust vajavad kuulmisaparaadid",
                    "Kõrge kindlusega SKA tooted",
                    "Tervisekassa meditsiiniseadmed"
                ],
                key="canon_filter_sel"
            )

        learned_canon_names = set(r["canonical_name"] for r in all_learned)

        filtered_canon = []
        for p in canonical_products:
            c_name = p.get("canonical_name", "")
            brand = p.get("brand", "")
            mfg = p.get("manufacturer", "")
            aliases = p.get("aliases", [])
            conf_status = p.get("confidence", "")

            # Filtri kontroll
            if canon_filter == "Ainult tagasisidega / õpitud tooted" and c_name not in learned_canon_names:
                continue
            elif canon_filter == "Ülevaatust vajavad kuulmisaparaadid" and "ÜLEVAATUST" not in conf_status:
                continue
            elif canon_filter == "Kõrge kindlusega SKA tooted" and conf_status != "KÕRGE KINDLUS":
                continue
            elif canon_filter == "Tervisekassa meditsiiniseadmed" and "TERVISEKASSA" not in conf_status:
                continue

            # Tekstiotsing
            if canon_search:
                s_up = canon_search.upper()
                match = (
                    s_up in c_name.upper() or
                    s_up in brand.upper() or
                    s_up in mfg.upper() or
                    any(s_up in str(a).upper() for a in aliases)
                )
                if not match:
                    continue

            filtered_canon.append(p)

        st.caption(f"Kuvatakse {len(filtered_canon)} kanoonilist toodet.")

        if not filtered_canon:
            st.markdown('<div class="tedi-alert tedi-alert-info"><div class="tedi-alert-title">Tooteid ei leitud</div><div class="tedi-alert-body">Valitud otsingule või filtrile vastavaid tooteid ei leitud.</div></div>', unsafe_allow_html=True)
        else:
            # Leheküljestamine kanoonilistele toodetele (10 tk lehel)
            c_page_size = 10
            total_c_rows = len(filtered_canon)
            total_c_pages = max(1, math.ceil(total_c_rows / c_page_size))
            if st.session_state["page_canon"] > total_c_pages:
                st.session_state["page_canon"] = 1

            start_idx = (st.session_state["page_canon"] - 1) * c_page_size
            end_idx = min(start_idx + c_page_size, total_c_rows)
            page_products = filtered_canon[start_idx:end_idx]

            for p in page_products:
                c_name = p.get("canonical_name", "")
                c_id = p.get("canonical_id", c_name.replace(" ", "_"))
                mfg = p.get("manufacturer", "Määramata")
                brand = p.get("brand", "Määramata")
                cat = p.get("category", "")
                aliases = p.get("aliases", [])
                matching_isos = p.get("matching_isos", [])
                descriptions = p.get("descriptions", [])
                price_str = p.get("price_range_str", "")
                images = p.get("images", [])
                conf_level = p.get("confidence", "")

                # Seotud õppimisandmed sellele tootele
                learned_recs = {r["iso_kood"]: r for r in learning_service.get_all_records_for_product(c_name)}

                with st.expander(f"{c_name} — {brand} ({mfg})", expanded=(canon_search != "" or len(filtered_canon) <= 3)):
                    col_info1, col_info2 = st.columns([3, 1])
                    with col_info1:
                        st.markdown(f"**Tootja:** {mfg} &nbsp;|&nbsp; **Bränd:** {brand} &nbsp;|&nbsp; **Kategooria:** {cat}")
                        if price_str:
                            st.markdown(f"**Hinnainfo:** {price_str}")
                        if aliases:
                            alias_badges = " ".join([f"<code>{html.escape(str(a))}</code>" for a in aliases])
                            st.markdown(f"<div style='margin: 8px 0;'><strong>Koondatud aliased ({len(aliases)} tk):</strong><br/>{alias_badges}</div>", unsafe_allow_html=True)
                        if descriptions:
                            st.markdown("**Tõendid ja omadused:**")
                            for d in descriptions:
                                st.markdown(f"- {d}")
                    with col_info2:
                        if images:
                            st.image(images[0], caption=c_name, use_container_width=True)

                    st.markdown("---")
                    st.markdown("##### Sotsiaalkindlustusameti määruse nr 74 ISO vastavus ja õppimine")

                    # Kui tootel on ISO kandidaate
                    if not matching_isos and not learned_recs:
                        st.markdown(f"<div class='tedi-alert tedi-alert-info'><div class='tedi-alert-body'>Sellel tootel puudub määruse nr 74 ISO seos ({conf_level}).</div></div>", unsafe_allow_html=True)
                    else:
                        # Koondame kõik ISO koodid (nii kandidaadid kui juba õpitud)
                        all_iso_entries = []
                        seen_isos = set()

                        for iso_item in matching_isos:
                            iso_code = iso_item[0]
                            iso_name = iso_item[1] if len(iso_item) > 1 else ""
                            note = iso_item[2] if len(iso_item) > 2 else ""
                            all_iso_entries.append((iso_code, iso_name, note))
                            seen_isos.add(iso_code)

                        for iso_kood, r_item in learned_recs.items():
                            if iso_kood not in seen_isos:
                                all_iso_entries.append((iso_kood, r_item.get("maarusejargne_nimetus", ""), "Spetsialisti lisatud"))
                                seen_isos.add(iso_kood)

                        for iso_code, iso_name, note in all_iso_entries:
                            rec = learned_recs.get(iso_code)
                            if rec:
                                conf_count = rec.get("kinnitatud_arv", 0)
                                rej_count = rec.get("tagasi_lukatud_arv", 0)
                                conf_pct = rec.get("usaldus_protsent", 50.0)
                                last_action = rec.get("viimane_kinnitus_aeg") or rec.get("viimane_tagasilukatus_aeg") or "Puudub"
                                cur_rationale = rec.get("pohjendus") or note
                                hist = rec.get("ajalugu", [])
                            else:
                                conf_count = 0
                                rej_count = 0
                                conf_pct = 50.0
                                last_action = "Puudub"
                                cur_rationale = note
                                hist = []

                            # Värv ja badge usaldusskoorile
                            if conf_pct >= 90.0:
                                badge_html = f'<span class="tedi-badge tedi-badge-success">Usaldus: {conf_pct:.0f}%</span>'
                                border_col = "var(--tedi-status-success-border)"
                            elif conf_pct >= 60.0:
                                badge_html = f'<span class="tedi-badge tedi-badge-warning">Usaldus: {conf_pct:.0f}%</span>'
                                border_col = "var(--tedi-status-warning-border)"
                            else:
                                badge_html = f'<span class="tedi-badge tedi-badge-danger">Usaldus: {conf_pct:.0f}%</span>'
                                border_col = "var(--tedi-status-danger-border)"

                            st.markdown(f"""
                            <div class="tedi-inner-card" style="margin-top: 10px; border-left: 4px solid {border_col};">
                              <div style="display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 8px;">
                                <div>
                                  <span style="font-size: 15px; font-weight: 700; color: var(--tedi-text-primary);">Pakutud ISO: </span>
                                  <code style="font-size: 14px; font-weight: 700;">{iso_code}</code>
                                  <span style="color: var(--tedi-text-secondary); margin-left: 6px;">— {iso_name}</span>
                                </div>
                                <div>
                                  {badge_html}
                                </div>
                              </div>
                              <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(180px, 1fr)); gap: 12px; margin: 10px 0; font-size: 13px;">
                                <div>Kinnitatud kasutaja poolt: <strong style="color: #64B5F6;">{conf_count} korda</strong></div>
                                <div>Tagasi lükatud: <strong style="color: #EF5350;">{rej_count} korda</strong></div>
                                <div>Viimase otsuse aeg: <strong style="color: var(--tedi-text-primary);">{last_action}</strong></div>
                              </div>
                              {f'<div style="font-size: 13px; color: var(--tedi-text-muted); margin-top: 6px;">Põhjendus: <span style="color: var(--tedi-text-secondary);">{cur_rationale}</span></div>' if cur_rationale else ''}
                            </div>
                            """, unsafe_allow_html=True)

                            col_act1, col_act2, col_act3 = st.columns([2, 1, 1])
                            with col_act1:
                                input_reason = st.text_input(
                                    f"Põhjendus ({iso_code}):",
                                    key=f"reason_{c_id}_{iso_code}",
                                    placeholder="Nt arstitõendi aktiivsusgrupp I",
                                    label_visibility="collapsed"
                                )
                            with col_act2:
                                if st.button(f"Kinnita ISO {iso_code}", key=f"btn_c_{c_id}_{iso_code}", use_container_width=True):
                                    learning_service.record_decision(
                                        canonical_name=c_name,
                                        iso_code=iso_code,
                                        statutory_name=iso_name,
                                        action="CONFIRM",
                                        rationale=input_reason or f"Kinnitatud kasutaja poolt tootele {c_name}",
                                        user="Spetsialist"
                                    )
                                    st.toast(f"ISO {iso_code} kinnitatud tootele '{c_name}'!")
                                    st.rerun()
                            with col_act3:
                                if st.button(f"Lükka tagasi", key=f"btn_r_{c_id}_{iso_code}", use_container_width=True):
                                    learning_service.record_decision(
                                        canonical_name=c_name,
                                        iso_code=iso_code,
                                        statutory_name=iso_name,
                                        action="REJECT",
                                        rationale=input_reason or f"Tagasi lükatud kasutaja poolt tootele {c_name}",
                                        user="Spetsialist"
                                    )
                                    st.toast(f"ISO {iso_code} tagasi lükatud tootele '{c_name}'!")
                                    st.rerun()

                            if hist:
                                with st.expander(f"Otsustuste ajalugu (audit): {len(hist)} kannet"):
                                    for h in reversed(hist):
                                        act_label = "Kinnitatud" if h.get("action") == "CONFIRM" else "Tagasi lükatud"
                                        st.write(f"- **{h.get('timestamp')}** | {act_label} ({h.get('user', 'Spetsialist')}): {h.get('rationale', '-')} -> Usaldus: {h.get('confidence_after', '-')}%")

            # Kanoonilise kataloogi lehevahetus
            if total_c_pages > 1:
                col_c1, col_c2, col_c3 = st.columns([1, 2, 1])
                with col_c1:
                    if st.button("Eelmine leht (Kataloog)", disabled=(st.session_state["page_canon"] <= 1), key="btn_cp_c_prev", use_container_width=True):
                        st.session_state["page_canon"] -= 1
                        st.rerun()
                with col_c3:
                    if st.button("Järgmine leht (Kataloog)", disabled=(st.session_state["page_canon"] >= total_c_pages), key="btn_cp_c_next", use_container_width=True):
                        st.session_state["page_canon"] += 1
                        st.rerun()

    # 1. TOOTEREGISTER
    with tab_reg:
        st.subheader("Püsiv Tooteregister")
        st.caption("Eesti abivahendite tarnijate kataloogidest ühendatud ja dublikaadivaba toodete baas.")

        st.markdown(f"""
        <div class="tedi-summary-grid">
          <div class="tedi-summary-card primary">
            <div class="tedi-summary-label">Tooteid registris</div>
            <div class="tedi-summary-value">{reg_stats['total_products']:,}</div>
          </div>
          <div class="tedi-summary-card">
            <div class="tedi-summary-label">Tootjaid kokku</div>
            <div class="tedi-summary-value">{reg_stats['manufacturers_count']}</div>
          </div>
          <div class="tedi-summary-card">
            <div class="tedi-summary-label">Tootekategooriaid</div>
            <div class="tedi-summary-value">{len(reg_stats['categories'])}</div>
          </div>
        </div>
        """.replace(",", " "), unsafe_allow_html=True)

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
            reg_page_size = 25
            total_reg_rows = len(df_reg_view)
            total_reg_pages = max(1, math.ceil(total_reg_rows / reg_page_size))
            if st.session_state["page_reg"] > total_reg_pages:
                st.session_state["page_reg"] = 1

            reg_columns_config = [
                {"key": "official_name", "label": "Ametlik tootenimi", "type": "bold"},
                {"key": "brand", "label": "Bränd", "type": "text"},
                {"key": "manufacturer", "label": "Tootja", "type": "text"},
                {"key": "category_type", "label": "Kategooria", "type": "badge"},
                {"key": "absorption_ml", "label": "Imavus (ml)", "type": "mono"},
                {"key": "drops", "label": "Tilgad / Tase", "type": "mono"},
                {"key": "source_supplier", "label": "Tarnijad", "type": "muted"}
            ]

            tedi_reg_html = render_tedi_table(
                df=df_reg_view,
                columns_config=reg_columns_config,
                current_page=st.session_state["page_reg"],
                page_size=reg_page_size,
                table_id="tedi_registry_table"
            )
            st.markdown(tedi_reg_html, unsafe_allow_html=True)

            if total_reg_pages > 1:
                col_rp1, col_rp2, col_rp3 = st.columns([1, 2, 1])
                with col_rp1:
                    if st.button("Eelmine leht", disabled=(st.session_state["page_reg"] <= 1), key="btn_rp_prev", use_container_width=True):
                        st.session_state["page_reg"] -= 1
                        st.rerun()
                with col_rp3:
                    if st.button("Järgmine leht", disabled=(st.session_state["page_reg"] >= total_reg_pages), key="btn_rp_next", use_container_width=True):
                        st.session_state["page_reg"] += 1
                        st.rerun()

    # 2. RIIKLIK KLASSIFIKAATOR
    with tab_class:
        st.subheader("Sotsiaalkindlustusameti ja määruse nr 74 loetelu (alates 01.10.2026)")
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

            class_page_size = 25
            total_class_rows = len(df_classes)
            total_class_pages = max(1, math.ceil(total_class_rows / class_page_size))
            if st.session_state["page_class"] > total_class_pages:
                st.session_state["page_class"] = 1

            class_columns_config = [
                {"key": "iso_kood", "label": "ISO kood", "type": "code_highlight", "width": "110px"},
                {"key": "valdkond", "label": "Valdkond", "type": "text"},
                {"key": "liik", "label": "Liik", "type": "text"},
                {"key": "maarusejargne_nimetus", "label": "Määrusejärgne nimetus", "type": "bold"},
                {"key": "tapsustus", "label": "Kitsendus / Täpsustus (Veerg C)", "type": "muted"},
                {"key": "tehingu_liik", "label": "Tehingu liik", "type": "text"},
                {"key": "piirhind_muuk", "label": "Müügi piirhind (€)", "type": "mono"},
                {"key": "piirhind_uur", "label": "Üüri piirhind (€/kuu)", "type": "mono"},
                {"key": "piirlimiit", "label": "Piirlimiit", "type": "text"}
            ]

            tedi_class_html = render_tedi_table(
                df=df_classes,
                columns_config=class_columns_config,
                current_page=st.session_state["page_class"],
                page_size=class_page_size,
                table_id="tedi_classifier_table"
            )
            st.markdown(tedi_class_html, unsafe_allow_html=True)

            if total_class_pages > 1:
                col_cp1, col_cp2, col_cp3 = st.columns([1, 2, 1])
                with col_cp1:
                    if st.button("Eelmine leht", disabled=(st.session_state["page_class"] <= 1), key="btn_cp_prev", use_container_width=True):
                        st.session_state["page_class"] -= 1
                        st.rerun()
                with col_cp3:
                    if st.button("Järgmine leht", disabled=(st.session_state["page_class"] >= total_class_pages), key="btn_cp_next", use_container_width=True):
                        st.session_state["page_class"] += 1
                        st.rerun()

    # 3. KINNITATUD REEGLID (VAJADUSPÕHINE KIHT)
    with tab_kb:
        st.subheader("Kinnitatud reeglid ja erandid")
        st.caption("Vajaduspõhine õppiv kiht: Siia salvestatakse ainult need kirjapildid ja aliased, kus süsteemi automaatne tuvastuskindlus oli madal või vajas inimese kinnitust. 100% klappivaid tooteid siia ei dubleerita.")

        all_entries = kb.get_all()
        if not all_entries:
            st.markdown('<div class="tedi-alert tedi-alert-info"><div class="tedi-alert-title">Kinnitatud reeglid puuduvad</div><div class="tedi-alert-body">Reeglid lisanduvad siia vajaduspõhiselt, kui kinnitate töölaual madala kindlusega või lahknevustega kirjeid.</div></div>', unsafe_allow_html=True)
        else:
            kb_df = pd.DataFrame(all_entries)

            col_kb1, col_kb2 = st.columns([3, 1])
            with col_kb2:
                towrite_kb = io.BytesIO()
                kb_df.to_excel(towrite_kb, index=False, engine="openpyxl")
                towrite_kb.seek(0)
                st.download_button(
                    label="Laadi reeglid alla (.xlsx)",
                    data=towrite_kb,
                    file_name="kinnitatud_reeglid.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    use_container_width=True
                )

            kb_columns_config = [
                {"key": "id", "label": "ID", "type": "mono", "width": "50px"},
                {"key": "algne_nimetus", "label": "Arvel esitatud kirjapilt", "type": "text"},
                {"key": "ametlik_toode", "label": "Kinnitatud ametlik toode", "type": "bold"},
                {"key": "iso_kood", "label": "ISO kood", "type": "code_highlight", "width": "110px"},
                {"key": "maarusejargne_nimetus", "label": "Määrusejärgne nimetus", "type": "text"},
                {"key": "usaldustase", "label": "Usaldustase", "type": "mono", "width": "100px"},
                {"key": "viimane_valideerimine", "label": "Kinnitamise aeg", "type": "muted"}
            ]

            tedi_kb_html = render_tedi_table(
                df=kb_df,
                columns_config=kb_columns_config,
                current_page=st.session_state["page_kb"],
                page_size=20,
                table_id="tedi_kb_table"
            )
            st.markdown(tedi_kb_html, unsafe_allow_html=True)

    # 4. HALDUS JA SÜSTEEMIINFO
    with tab_admin:
        st.subheader("Haldus ja süsteemiinfo")
        st.caption("Tehnilised parameetrid ja arhitektuuri ülevaade administraatorile.")

        st.markdown("""
        <div class="tedi-inner-card" style="margin-top: 16px;">
          <h5>Süsteemi arhitektuur ja andmeallikad</h5>
          <div style="margin-bottom: 6px;">• <strong>Andmebaas:</strong> Lokaalne SQLite (<code>data/valideer.db</code>)</div>
          <div style="margin-bottom: 6px;">• <strong>Põhilised tõeallikad:</strong>
            <ul style="margin-top: 4px; padding-left: 20px;">
              <li><code>ametlik_klassifikaator</code>: Sotsiaalministeeriumi määruse nr 74 ametlik loetelu (alates 01.10.2026, 250 kirjet koos piirmäärade ja kitsendustega).</li>
              <li><code>tooteregister</code>: 4 115 kanoonilist toodet koos aliaste, imavusmahtude ja tarnijate infoga.</li>
              <li><code>teadmistebaas</code>: Spetsialisti kinnitatud seosed (vajaduspõhine õppiv kiht madala tuvastuskindluse korral).</li>
            </ul>
          </div>
          <div>• <strong>Valideerimise reeglimootor:</strong> 1:1 determinism (iga toode vastab ühele ISO koodile) ja RestrictionEngine määruse veergude C ja M kontrolliks. Kasutaja arveid kettale ei salvestata.</div>
        </div>
        """, unsafe_allow_html=True)
