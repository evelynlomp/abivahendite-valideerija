"""Valideerimise Exceli raporti generaator.

Loob kahe-tasemelise Exceli töövihiku:
1. 'Spetsialisti raport' — lühike, selge, tegevusele suunatud (otsustamiseks).
2. 'Tehniline audit' — täielik auditijälg (usaldusskoorid, tuvastusallikad, kandidaadid).

PÕHIPRINTSIIP:
Exceli arve andmed on esitatud väited.
Tõeallikad on kanooniline tooderegister ja Sotsiaalministeeriumi määrus nr 74.
Raport kõrvutab esitatud arve andmed tõeallikaga ja toob välja konkreetsed lahknevused.
"""

import io
import json
import pandas as pd
from typing import List, Dict, Any
import openpyxl
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter

from src.validator import Validator


def get_action_recommendation(
    status: str,
    excel_iso: str,
    official_iso: str,
    excel_statutory: str,
    official_statutory: str,
    official_product: str,
    restriction_warning: str = ""
) -> str:
    """Genereerib spetsialistile konkreetse inimkeelse tegevussoovituse."""
    if status == Validator.STATUS_RESTRICTION:
        if restriction_warning:
            return f"Mittehüvitatav (Määruse välistus). Lükka arverida tagasi. {restriction_warning}"
        return "Mittehüvitatav (Määruse kitsenduse rikkumine). Lükka arverida tagasi või nõua tarnijalt täpsustust."

    elif status == Validator.STATUS_WRONG_BOTH:
        return f"Vajab arvel parandamist: Toote ametlikud andmed tõeallikas on ISO '{official_iso}' ja nimetus '{official_statutory}'. Arvel esitatud andmed tuleb korrigeerida."

    elif status == Validator.STATUS_WRONG_ISO:
        return f"Vajab arvel parandamist: Toote ametlik kood tõeallikas on '{official_iso}'. Arvel esitatud ISO '{excel_iso}' ei vasta toote ametlikule klassifikatsioonile ja tuleb asendada."

    elif status == Validator.STATUS_WRONG_NAME:
        return f"Vajab arvel parandamist: Toote ametlik nimetus määruses nr 74 on '{official_statutory}'. Arvel esitatud nimetus tuleb korrigeerida."

    elif status == Validator.STATUS_REVIEW:
        return f"Vajab kontrolli: Tuvastati võimalik vaste '{official_product}' (ametlik ISO {official_iso}). Kinnita toote identiteet."

    elif status == Validator.STATUS_UNKNOWN:
        return "Tundmatu toode: Kirjet ei leitud tooderegistrist. Nõua tarnijalt toote täpne mudel ja tehnilised andmed."

    elif status == Validator.STATUS_MATCH:
        return "Nõuetele vastav: Arvel esitatud andmed klapivad tõeallikaga ja vastavad hüvitamise nõuetele."

    return "Vaata üle ja otsusta."


def format_status_label(status: str) -> str:
    """Tagastab puhta ja väärika staatuse sildi ilma emotikonideta."""
    mapping = {
        Validator.STATUS_MATCH: "Vastab nõuetele",
        Validator.STATUS_RESTRICTION: "Kitsenduse rikkumine",
        Validator.STATUS_WRONG_ISO: "Vale ISO kood",
        Validator.STATUS_WRONG_NAME: "Vale määrusejärgne nimetus",
        Validator.STATUS_WRONG_BOTH: "Vale ISO ja nimetus",
        Validator.STATUS_REVIEW: "Vajab ülevaatust",
        Validator.STATUS_UNKNOWN: "Tundmatu toode"
    }
    return mapping.get(status, status)


def format_tedi_badge(status: str) -> str:
    """Genereerib TEDI standardse ovaalse staatuse märgi (StatusBadge)."""
    if status == Validator.STATUS_MATCH:
        return '<span class="tedi-badge tedi-badge-success">Vastab nõuetele</span>'
    elif status == Validator.STATUS_RESTRICTION:
        return '<span class="tedi-badge tedi-badge-danger">Kitsenduse rikkumine</span>'
    elif status == Validator.STATUS_WRONG_BOTH:
        return '<span class="tedi-badge tedi-badge-danger">Vale ISO ja nimetus</span>'
    elif status in (Validator.STATUS_WRONG_ISO, Validator.STATUS_WRONG_NAME, Validator.STATUS_REVIEW):
        label = format_status_label(status)
        return f'<span class="tedi-badge tedi-badge-warning">{label}</span>'
    else:
        label = format_status_label(status)
        return f'<span class="tedi-badge tedi-badge-info">{label}</span>'


def generate_validation_report(results: List[Dict[str, Any]]) -> bytes:
    """
    Genereerib kahe lehega professionaalse Exceli raporti:
    1. Spetsialisti raport (Action-oriented)
    2. Tehniline audit (Audit trail)
    """
    # 1. Koosta Spetsialisti vaate andmed
    specialist_rows = []
    for r in results:
        raw_status = r.get("Valideerimise staatus", "")
        clean_status = format_status_label(raw_status)
        action = get_action_recommendation(
            status=raw_status,
            excel_iso=str(r.get("ISO kood (Excel)", "")),
            official_iso=str(r.get("Ametlik ISO kood", "")),
            excel_statutory=str(r.get("Määrusejärgne nimetus (Excel)", "")),
            official_statutory=str(r.get("Ametlik määrusejärgne nimetus", "")),
            official_product=str(r.get("Tuvastatud ametlik toode", "")),
            restriction_warning=str(r.get("Selgitus", ""))
        )

        specialist_rows.append({
            "Rida": r.get("Rida", 1),
            "Otsuse staatus": clean_status,
            "Arvel esitatud tootenimi": r.get("Abivahendi nimetus (Excel)", ""),
            "Arvel esitatud ISO": r.get("ISO kood (Excel)", ""),
            "Arvel esitatud nimetus": r.get("Määrusejärgne nimetus (Excel)", ""),
            "Tõeallikas: Tuvastatud toode": r.get("Tuvastatud ametlik toode", ""),
            "Tõeallikas: Tootja": r.get("Tootja", ""),
            "Tõeallikas: Ametlik ISO": r.get("Ametlik ISO kood", ""),
            "Tõeallikas: Ametlik nimetus": r.get("Ametlik määrusejärgne nimetus", ""),
            "Tuvastatud lahknevus ja põhjus": r.get("Selgitus", ""),
            "Soovitatav tegevus arve menetlejale": action
        })

    # 2. Koosta Tehnilise auditi andmed
    audit_rows = []
    for r in results:
        raw_status = r.get("Valideerimise staatus", "")
        cands = r.get("Kandidaadid", [])
        cands_str = json.dumps(cands, ensure_ascii=False) if isinstance(cands, list) else str(cands)

        audit_rows.append({
            "Rida": r.get("Rida", 1),
            "Valideerimise staatus": format_status_label(raw_status),
            "Usaldusskoor": r.get("Usaldusskoor", 0.0),
            "Tuvastuse allikas": r.get("Tuvastuse allikas", ""),
            "Kitsenduse kontroll": r.get("Kitsenduse kontroll", ""),
            "Kitsenduse selgitus": r.get("Kitsenduse selgitus", ""),
            "Arvel esitatud tootenimi": r.get("Abivahendi nimetus (Excel)", ""),
            "Normaliseeritud tootenimi": r.get("Normaliseeritud nimetus", ""),
            "Tuvastatud ametlik toode": r.get("Tuvastatud ametlik toode", ""),
            "Tootja": r.get("Tootja", ""),
            "Arvel esitatud ISO": r.get("ISO kood (Excel)", ""),
            "Ametlik ISO": r.get("Ametlik ISO kood", ""),
            "Arvel esitatud nimetus": r.get("Määrusejärgne nimetus (Excel)", ""),
            "Ametlik määrusejärgne nimetus": r.get("Ametlik määrusejärgne nimetus", ""),
            "Teadmistebaasis kinnitatud": "Jah" if r.get("Teadmistebaasis olemas") else "Ei",
            "Agendi arutluskäik": r.get("Põhjendus", ""),
            "Kandidaadid (JSON)": cands_str
        })

    # 3. Ehita Excel töövihik openpyxl abil
    wb = openpyxl.Workbook()

    # Sheet 1: Spetsialisti raport
    ws1 = wb.active
    ws1.title = "Spetsialisti raport"

    # Sheet 2: Tehniline audit
    ws2 = wb.create_sheet(title="Tehniline audit")

    # Stiilid
    header_font = Font(name="Calibri", size=11, bold=True, color="1F2937")
    header_fill_1 = PatternFill(start_color="E6F0FA", end_color="E6F0FA", fill_type="solid") # helesinine rahulik
    header_fill_2 = PatternFill(start_color="F3F4F6", end_color="F3F4F6", fill_type="solid") # hall
    thin_border = Border(
        left=Side(style='thin', color='E5E7EB'),
        right=Side(style='thin', color='E5E7EB'),
        top=Side(style='thin', color='E5E7EB'),
        bottom=Side(style='thin', color='E5E7EB')
    )

    def write_sheet(ws, rows, header_fill):
        if not rows:
            return
        headers = list(rows[0].keys())
        ws.append(headers)

        # Kujunda päis
        for col_idx in range(1, len(headers) + 1):
            cell = ws.cell(row=1, column=col_idx)
            cell.font = header_font
            cell.fill = header_fill
            cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
            cell.border = thin_border
        ws.row_dimensions[1].height = 26

        # Lisa andmed
        for row_idx, r in enumerate(rows, start=2):
            for col_idx, key in enumerate(headers, start=1):
                val = r[key]
                cell = ws.cell(row=row_idx, column=col_idx, value=val)
                cell.border = thin_border
                cell.font = Font(name="Calibri", size=10)
                if key == "Rida":
                    cell.alignment = Alignment(horizontal="center", vertical="top")
                elif key in ["Otsuse staatus", "Valideerimise staatus", "Arvel esitatud ISO", "Tõeallikas: Ametlik ISO", "Ametlik ISO"]:
                    cell.alignment = Alignment(horizontal="center", vertical="top")
                else:
                    cell.alignment = Alignment(horizontal="left", vertical="top", wrap_text=True)

        # Automaatne veeru laiuse määramine
        for col in ws.columns:
            max_len = 0
            col_letter = get_column_letter(col[0].column)
            col_name = str(col[0].value or "")
            for cell in col:
                val_str = str(cell.value or "")
                max_len = max(max_len, min(len(val_str), 55))
            calculated_width = max(max_len + 3, len(col_name) + 3, 10)
            ws.column_dimensions[col_letter].width = min(calculated_width, 65)

    write_sheet(ws1, specialist_rows, header_fill_1)
    write_sheet(ws2, audit_rows, header_fill_2)

    # Vaikimisi Sheet 1 aktiivne
    wb.active = ws1

    output = io.BytesIO()
    wb.save(output)
    output.seek(0)
    return output.getvalue()
