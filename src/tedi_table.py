"""
TEDI (TEHIK / Veera) Semantilise HTML5 Tabeli Generaator.
Vastab TEDI Table.txt ja Table.pdf spetsifikatsioonidele.
"""

import html
import math
from typing import List, Dict, Any, Optional
import pandas as pd


def render_tedi_table(
    df: pd.DataFrame,
    columns_config: List[Dict[str, Any]],
    current_page: int = 1,
    page_size: int = 20,
    table_id: str = "tedi_table"
) -> str:
    """
    Genereerib TEDI nõuetele 100% vastava semantilise HTML5 tabeli.
    
    columns_config struktuur:
    [
        {"key": "Rida", "label": "Rida", "type": "mono", "width": "60px"},
        {"key": "Valideerimise staatus", "label": "Otsuse staatus", "type": "badge", "width": "180px"},
        {"key": "Abivahendi nimetus (Excel)", "label": "Tootenimi arvel", "type": "text"},
        {"key": "Tuvastatud ametlik toode", "label": "Tuvastatud toode", "type": "bold"},
        {"key": "ISO kood (Excel)", "label": "Esitatud ISO", "type": "code", "width": "110px"},
        {"key": "Ametlik ISO kood", "label": "Ametlik ISO", "type": "code_highlight", "width": "110px"},
        {"key": "Määrusejärgne nimetus", "label": "Määrusejärgne nimetus", "type": "text"},
        {"key": "Selgitus", "label": "Lahknevuse selgitus", "type": "muted"}
    ]
    """
    total_rows = len(df)
    if total_rows == 0:
        return """
        <div class="tedi-table-container" style="padding: 32px; text-align: center; color: var(--tedi-text-secondary);">
          Ühtegi kirjet ei vasta valitud filtrile.
        </div>
        """
    
    total_pages = max(1, math.ceil(total_rows / page_size))
    current_page = max(1, min(current_page, total_pages))
    
    start_idx = (current_page - 1) * page_size
    end_idx = min(start_idx + page_size, total_rows)
    df_page = df.iloc[start_idx:end_idx]
    
    # Päise koostamine
    th_html = []
    for col in columns_config:
        w_style = f"width: {col['width']};" if "width" in col else ""
        th_html.append(f'<th style="{w_style}">{html.escape(col["label"])}</th>')
    
    # Ridade koostamine
    tr_html = []
    for _, row in df_page.iterrows():
        td_html = []
        for col in columns_config:
            key = col["key"]
            raw_val = row.get(key, "")
            val_str = "" if pd.isna(raw_val) else str(raw_val).strip()
            c_type = col.get("type", "text")
            
            if c_type == "badge":
                # Olekumärgis TEDI standardi järgi
                from src.report import format_tedi_badge
                formatted_cell = format_tedi_badge(val_str)
            elif c_type == "mono":
                formatted_cell = f'<span class="cell-mono">{html.escape(val_str)}</span>'
            elif c_type == "code":
                formatted_cell = f'<code class="mono">{html.escape(val_str)}</code>' if val_str else '<span class="cell-muted">—</span>'
            elif c_type == "code_highlight":
                formatted_cell = f'<code class="mono" style="color: var(--tedi-text-link); font-weight: 700;">{html.escape(val_str)}</code>' if val_str else '<span class="cell-muted">—</span>'
            elif c_type == "bold":
                formatted_cell = f'<strong>{html.escape(val_str)}</strong>' if val_str else '<span class="cell-muted">—</span>'
            elif c_type == "muted":
                formatted_cell = f'<span class="cell-muted">{html.escape(val_str)}</span>' if val_str else '<span class="cell-muted">—</span>'
            else:
                formatted_cell = html.escape(val_str) if val_str else '<span class="cell-muted">—</span>'
            
            td_html.append(f"<td>{formatted_cell}</td>")
        
        tr_html.append(f"<tr>{''.join(td_html)}</tr>")
    
    pagination_info = f"Näitan <strong>{start_idx + 1}–{end_idx}</strong> kirjet (kokku <strong>{total_rows}</strong>)"
    page_counter = f"Leht <strong>{current_page}</strong> / <strong>{total_pages}</strong>"
    
    table_markup = f"""
    <div class="tedi-table-container" id="{table_id}">
      <table class="tedi-table">
        <thead>
          <tr>
            {''.join(th_html)}
          </tr>
        </thead>
        <tbody>
          {''.join(tr_html)}
        </tbody>
      </table>
      <div class="tedi-pagination-container">
        <div>{pagination_info}</div>
        <div>{page_counter}</div>
      </div>
    </div>
    """
    return table_markup
