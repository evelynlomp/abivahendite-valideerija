"""Valideerimise ja reeglimootori moodul.

Teostab ajutise igakuise Exceli faili valideerimise mälus (andmeid kettale ei salvestata).
"""

import pandas as pd
from typing import Dict, Any, Tuple, Optional
from src.normalizer import compare_iso, compare_statutory_names, format_iso_display
from src.matcher import ProductMatcher
from src.restriction_engine import RestrictionEngine


class Validator:
    """
    Valideerib igakuiseid Exceli andmeridu:
    1. Tuvastab toote Tootetuvastuse agendi (või teadmistebaasi) abil.
    2. Tagab, et toode vastab alati täpselt ühele kanoonilisele ISO koodile.
    3. Kontrollib määruse veergude C ja M tootekitsendusi (koostis, välistused).
    4. Võrdleb esitatud Exceli väärtusi ja määrab staatuse.
    """

    STATUS_MATCH = "Vastab"
    STATUS_WRONG_ISO = "Vale ISO"
    STATUS_WRONG_NAME = "Vale määrusejärgne nimetus"
    STATUS_WRONG_BOTH = "Vale ISO ja määrusejärgne nimetus"
    STATUS_RESTRICTION = "Ei vasta määruse kitsendusele"
    STATUS_UNKNOWN = "Tundmatu toode"
    STATUS_REVIEW = "Vajab käsitsi kontrolli"


    def __init__(self, matcher: ProductMatcher):
        self.matcher = matcher

    def validate_row(
        self,
        excel_name: str,
        excel_iso: str,
        excel_statutory_name: str,
        row_index: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Valideerib ühe rea.
        """
        match_res = self.matcher.match(excel_name)

        status = self.STATUS_UNKNOWN
        explanation = ""
        official_product = match_res.get("official_product") or match_res.get("ametlik_toode")
        official_iso = match_res.get("iso_kood") or match_res.get("soovituslik_iso")
        official_statutory = match_res.get("maarusejargne_nimetus") or match_res.get("soovituslik_nimetus")
        confidence = match_res.get("confidence_score") or match_res.get("usaldusskoor", 0.0)
        source = match_res.get("allikas", "")
        in_kb = match_res.get("in_kb", False)
        manufacturer = match_res.get("manufacturer")
        reasoning = match_res.get("reasoning", "")
        evidence_sources = match_res.get("evidence_sources", [])
        alternative_matches = match_res.get("alternative_matches", [])

        # 0. Kontrolli toote tehnilist ja sisulist vastavust määruse kitsendustele (Tulbad C ja M)
        # Kasutatakse arve ISO-koodi või tuvastatud toote ametlikku koodi
        check_iso = excel_iso or official_iso
        is_compliant, restriction_warning, rule_code = RestrictionEngine.check_restrictions(
            iso_code=check_iso,
            product_name=excel_name,
            official_name=official_product or "",
            product_type=match_res.get("category_type") or match_res.get("product_type", "")
        )

        if not is_compliant:
            status = self.STATUS_RESTRICTION
            explanation = restriction_warning

        # 1. Kui toode tuvastati (kas teadmistebaasist või agendi poolt) ja kitsendust ei rikutud
        elif official_product and official_iso and official_statutory:
            iso_ok = compare_iso(excel_iso, official_iso)
            name_ok = compare_statutory_names(excel_statutory_name, official_statutory)

            if iso_ok and name_ok:
                if in_kb:
                    status = self.STATUS_MATCH
                    explanation = f"Kinnitatud toode '{official_product}': ISO-kood ja määrusejärgne nimetus on ametliku klassifikaatoriga kooskõlas ning vastab kitsendustele."
                else:
                    # Tuvastatud agendi poolt esmakordselt, klapib, vajab kinnitust teadmistebaasi lisamiseks
                    status = self.STATUS_MATCH
                    explanation = (
                        f"Agent tuvastas toote '{official_product}' ({int(confidence*100)}% usaldus). "
                        f"ISO-kood ja määrusejärgne nimetus klapivad esitatud andmetega ning vastavad kitsendustele."
                    )
            elif not iso_ok and name_ok:
                status = self.STATUS_WRONG_ISO
                explanation = f"Exceli ISO '{excel_iso}' ei vasta toote ainsale ametlikule koodile '{official_iso}'."
            elif iso_ok and not name_ok:
                status = self.STATUS_WRONG_NAME
                explanation = f"Exceli määrusejärgne nimetus ei vasta ametlikule nimetusele '{official_statutory}'."
            else:
                status = self.STATUS_WRONG_BOTH
                explanation = (
                    f"Vale ISO ('{excel_iso}' vs toote ametlik kood '{official_iso}') JA "
                    f"vale määrusejärgne nimetus ('{official_statutory}')."
                )

            # Salvesta valideerimise ajalugu teadmistebaasis, kui oli KB kirje
            kb_id = match_res.get("kb_id")
            if kb_id and hasattr(self.matcher, "kb") and self.matcher.kb:
                self.matcher.kb.record_validation(kb_id, status)

        # 2. Kui toode tuvastati kõrge usaldusväärsusega (>= 0.85), kuid puudus otsene ISO seos
        elif official_product and confidence >= 0.85:
            if self.matcher and hasattr(self.matcher, "classifier") and self.matcher.classifier and excel_iso:
                cand = self.matcher.classifier.get_by_iso(excel_iso)
                if cand:
                    status = self.STATUS_REVIEW
                    explanation = (
                        f"Toode '{official_product}' tuvastati kõrge usaldusväärsusega ({int(confidence*100)}%). "
                        f"Seos riikliku klassifikaatori koodiga '{excel_iso}' vajab spetsialisti kinnitust."
                    )
                else:
                    status = self.STATUS_WRONG_ISO
                    explanation = f"Toode tuvastati ('{official_product}'), kuid Exceli ISO '{excel_iso}' ei leidu riiklikus klassifikaatoris."
            else:
                status = self.STATUS_REVIEW
                explanation = f"Toode '{official_product}' tuvastati ({int(confidence*100)}%), kuid vajab spetsialisti ülevaatust."

        # 3. Kui toode tuvastati mõõduka usaldusväärsusega (>= 0.45)
        elif official_product and confidence >= 0.45:
            status = self.STATUS_REVIEW
            explanation = f"Vajab käsitsi kontrolli: toote tuvastamise usaldusskoor on {int(confidence*100)}%."

        # 4. Kui toote tuvastamine ebaõnnestus täielikult
        else:
            status = self.STATUS_UNKNOWN
            explanation = "Tundmatu toode. Toote tuvastamise agent ei suutnud toodet ega tootjat usaldusväärselt tuvastada."

        ret = {
            "Rida": row_index if row_index is not None else 1,
            "Valideerimise staatus": status,
            "Usaldusskoor": round(confidence, 3),
            "Tuvastatud ametlik toode": official_product or "",
            "Tootja": manufacturer or "",
            "Ametlik ISO kood": official_iso or "",
            "Ametlik määrusejärgne nimetus": official_statutory or "",
            "Tuvastuse allikas": source,
            "Põhjendus": reasoning,
            "Tõendite allikad": evidence_sources,
            "Alternatiivsed vasted": alternative_matches,
            "Selgitus": explanation,
            "Kandidaadid": match_res.get("kandidaadid", []),
            "Normaliseeritud nimetus": match_res.get("normaliseeritud_nimetus", ""),
            "Teadmistebaasis olemas": in_kb,
            "Kitsenduse kontroll": "Rikutud (Ei vasta määrusele)" if not is_compliant else "Nõuetele vastav",
            "Kitsenduse selgitus": restriction_warning or "",
            "Abivahendi nimetus (Excel)": excel_name,
            "ISO kood (Excel)": excel_iso,
            "Määrusejärgne nimetus (Excel)": excel_statutory_name
        }
        return ret

    def validate_dataframe(self, df: pd.DataFrame) -> Tuple[pd.DataFrame, Dict[str, str]]:
        """
        Valideerib terve DataFrame'i mälus (andmeid kettale ei salvestata).
        """
        name_col, iso_col, stat_col = None, None, None

        for col in df.columns:
            c_clean = str(col).strip().lower()
            if not name_col and ("abivahend" in c_clean or "toode" in c_clean or "toote nimetus" in c_clean or "nimetus" in c_clean):
                name_col = col
            elif not iso_col and "iso" in c_clean:
                iso_col = col
            elif not stat_col and ("määrus" in c_clean or "maarus" in c_clean or "teenus" in c_clean):
                stat_col = col

        cols = list(df.columns)
        if not name_col and len(cols) > 0:
            name_col = cols[0]
        if not iso_col and len(cols) > 1:
            iso_col = cols[1]
        if not stat_col and len(cols) > 2:
            stat_col = cols[2]

        col_info = {
            "name_col": name_col,
            "iso_col": iso_col,
            "stat_col": stat_col
        }

        results = []
        for _, row in df.iterrows():
            val_name = str(row[name_col]) if name_col and pd.notna(row[name_col]) else ""
            val_iso = str(row[iso_col]) if iso_col and pd.notna(row[iso_col]) else ""
            val_stat = str(row[stat_col]) if stat_col and pd.notna(row[stat_col]) else ""

            row_res = self.validate_row(val_name, val_iso, val_stat)
            results.append(row_res)

        res_df = pd.DataFrame(results)
        enriched_df = pd.concat([df.reset_index(drop=True), res_df], axis=1)
        return enriched_df, col_info
