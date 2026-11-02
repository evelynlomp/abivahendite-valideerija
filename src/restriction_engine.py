"""Sotsiaalkaitseministri määruse nr 74 kitsenduste ja välistuste mootor (Tulbad C ja M).

Kontrollib toote füüsiliste ja tehniliste omaduste vastavust määruse nõuetele.
Kuna patsiendi terviseandmed puuduvad, kontrollitakse AINULT toote enese omadusi,
koostist, funktsionaalsust ning määruses sätestatud otseseid välistusi.
"""

import re
from typing import Dict, Any, Optional, Tuple


class RestrictionEngine:
    """Määruse lisa veergude C ja M tootekitsenduste ja välistuste reeglimootor."""

    @staticmethod
    def check_restrictions(
        iso_code: str,
        product_name: str,
        official_name: str = "",
        product_type: str = "",
        details: Optional[Dict[str, Any]] = None
    ) -> Tuple[bool, Optional[str], Optional[str]]:
        """
        Kontrollib, kas toode vastab antud ISO koodi tehnilistele kitsendustele.

        Tagastab:
            (is_compliant, warning_message, rule_code)
            is_compliant: True kui toode vastab või kitsendust ei rikuta,
                          False kui toode rikub otseselt määruse tehnilist kitsendust.
            warning_message: Täpne viide määruse tulbale C/M ja selgitus.
            rule_code: Lühikood vea identifitseerimiseks.
        """
        if not iso_code:
            return True, None, None

        clean_iso = iso_code.strip()
        combined_text = f"{product_name} {official_name} {product_type}".upper()

        # 1. ISO 09.21.18: Nahakaitsevahendid (AINULT tsinkoksiidi põhised)
        if clean_iso.startswith("09.21.18") or clean_iso.replace(".", "").startswith("092118"):
            # Peab sisaldama tsinkoksiidi (sh käänetes: tsinkoksiidiga, tsingiga, tsinkkreem, Sudocrem 15.25% ZnO jne)
            has_zinc = bool(re.search(r'\b(TSINK|TSING|ZINC|ZINK|SUDOCRE)\w*', combined_text))
            
            # Kui tootenimes või tüübis on otseselt nahahooldus ilma tsingita (nt barjäärkreem, õli, talk, ihupiim)
            is_skin_care = any(w in combined_text for w in ["KREEM", "SALV", "CREAM", "VAHT", "ÕLI", "OLI", "OIL", "TALK", "VASELIIN", "IHULIHV", "PALSAM", "NAHAHOOLDUS"])
            
            if not has_zinc and is_skin_care:
                return (
                    False,
                    "Määruse kitsendus (Tulp C): ISO 09.21.18 alla kuuluvad AINULT tsinkoksiidi põhised vahendid. Tuvastatud toode ei sisalda tsinkoksiidi (nt tavaline hoolduskreem/õli/talk) ning ei kuulu selle koodi all hüvitamisele.",
                    "ZINC_OXIDE_REQUIRED"
                )
            elif not has_zinc:
                # Kui tootes pole üldse mainitud tsinki
                return (
                    False,
                    "Määruse kitsendus (Tulp C): ISO 09.21.18 nõuab tsinkoksiidi baasil toodet. Tuvastatud toote andmetes puudub tsinkoksiidi märge.",
                    "ZINC_OXIDE_REQUIRED"
                )

        # 2. ISO 09.21.06: Nahapesemisvahendid (veevabad kreemid/vahud, VÄLISTATUD seebid, šampoonid, dušigeelid)
        if clean_iso.startswith("09.21.06") or clean_iso.replace(".", "").startswith("092106"):
            prohibited_wash = [
                (r'\b(ŠAMPOON|SAMPOON|SHAMPOO)\b', "šampoonid"),
                (r'\b(DUŠIGEEL|DUSHIGEEL|DUŠIÕLI|DUSHIOLI|SHOWER GEL|BATH)\b', "dušigeelid ja dušiõlid"),
                (r'\b(TUALETTSEEP|KÄTESEEP|KATESEEP|VEDELSEEP)\b', "veega mahapestavad seebid")
            ]
            for pattern, label in prohibited_wash:
                if re.search(pattern, combined_text):
                    return (
                        False,
                        f"Määruse kitsendus (Tulp C): ISO 09.21.06 välistab otseselt hüvitamiselt: {label}. Lubatud on AINULT veevabad uriinipidamatuse pesuvahendid (pesukreem ja -vaht pH 5.5).",
                        "EXCLUDED_WASH_PRODUCT"
                    )

        # 3. ISO 18.30.15: Kaasaskantavad kaldteed (VÄLISTATUD lävepaku kaldteed)
        if clean_iso.startswith("18.30.15") or clean_iso.replace(".", "").startswith("183015"):
            if re.search(r'\b(LÄVEPAKK|LÄVEPAKUKALDTEE|LÄVEPAKULE|LAVEPAKK|LAVEPAKULE|THRESHOLD)\b', combined_text):
                return (
                    False,
                    "Määruse kitsendus (Tulp C): ISO 18.30.15 sätestab otseselt: 'hüvitamisele ei kuulu lävepaku kaldteed'. Lävepaku kaldteed ei kuulu selle koodi all riiklikule hüvitamisele.",
                    "EXCLUDED_THRESHOLD_RAMP"
                )

        # 4. ISO 04.33.06.01: Lamatisi ennetavad madratsid (VÄLISTATUD standardsed poroloonmadratsid)
        if clean_iso.startswith("04.33.06.01") or clean_iso.replace(".", "").startswith("04330601"):
            if re.search(r'\b(STANDARDS?E?D? POROLOON|TAVALINE POROLOON|POROLOONMADRATS)\b', combined_text):
                if not any(w in combined_text for w in ["SEKTSIOON", "PROFILISEERITUD", "LAMATIS", "HR-POROLOON", "VISKO"]):
                    return (
                        False,
                        "Määruse kitsendus (Tulp C): ISO 04.33.06.01 sätestab otseselt: 'hüvitamisele ei kuulu standardsed poroloonmadratsid'. Lubatud on vaid püsiva survejaotusega geel-, helme-, õhk- või spetsiaalsed sektsioonmadratsid.",
                        "EXCLUDED_STANDARD_FOAM"
                    )

        # 5. ISO 18.03.15: Voodilauad (VÄLISTATUD voodikandikud ja voodikapid)
        if clean_iso.startswith("18.03.15") or clean_iso.replace(".", "").startswith("180315"):
            if re.search(r'\b(VOODIKANDIK|KANDIK|VOODIKAPP|ÖÖKAPP|OOKAPP|ÖÖKAPIKE)\b', combined_text):
                return (
                    False,
                    "Määruse kitsendus (Tulp C): ISO 18.03.15 sätestab otseselt: 'hüvitamisele ei kuulu voodikandikud, voodikapid'. Lubatud on vaid reguleeritavad voodilauad.",
                    "EXCLUDED_BED_TRAY_OR_CABINET"
                )

        # 6. ISO 09.33.03: Vanni- ja dušitoolid (VÄLISTATUD vannid, vanniliftid, vanni astmed)
        if clean_iso.startswith("09.33.03") or clean_iso.replace(".", "").startswith("093303"):
            if re.search(r'\b(VANNI ASTE|VANNI ASTMED|VANNI LIFT|VANNILIFT|VANNI ISTE ASTE)\b', combined_text):
                return (
                    False,
                    "Määruse kitsendus (Tulp C): ISO 09.33.03 sätestab otseselt: 'hüvitamisele ei kuulu vannid, vanniliftid, vanni astmed'.",
                    "EXCLUDED_BATH_ACCESSORY"
                )

        # 7. ISO 04.48.08.02: Täiskasvanute seisuraamid (VÄLISTATUD trenažöörid)
        if clean_iso.startswith("04.48.08.02") or clean_iso.replace(".", "").startswith("04480802"):
            if re.search(r'\b(TRENAŽÖÖR|TRENAŽOOR|TRENAZOOR|TREENINGSEADE|JALGRATTATRENAŽÖÖR)\b', combined_text):
                return (
                    False,
                    "Määruse kitsendus (Tulp C): ISO 04.48.08.02 sätestab otseselt: 'hüvitamisele ei kuulu trenažöörid ja treeningseadmed'.",
                    "EXCLUDED_TRAINING_DEVICE"
                )

        # 8. ISO 09.33.30.01: Niisutatud salvrätid (alkoholi- ja lõhnaainetevabad)
        if clean_iso.startswith("09.33.30.01") or clean_iso.replace(".", "").startswith("09333001"):
            if re.search(r'\b(LÕHNASTATUD|PARFÜÜM|PERFUMED|ALKOHOLIGA)\b', combined_text):
                return (
                    False,
                    "Määruse kitsendus (Tulp C): ISO 09.33.30.01 nõuab, et salvrätikud peavad olema 'alkoholi- ja lõhnaainetevabad intiimpiirkonna puhastamiseks'.",
                    "FRAGRANCE_OR_ALCOHOL_EXCLUDED"
                )

        # 9. ISO 22.12.12: Punktkirjavarustus (VÄLISTATUD printerid)
        if clean_iso.startswith("22.12.12") or clean_iso.replace(".", "").startswith("221212"):
            if re.search(r'\bPRINTER\b', combined_text):
                return (
                    False,
                    "Määruse kitsendus (Tulp C): ISO 22.12.12 sätestab otseselt: 'hüvitamisele ei kuulu printerid'.",
                    "EXCLUDED_PRINTER"
                )

        # 10. ISO 06.30.03: Parukad (pikkus kuni 40cm)
        if clean_iso.startswith("06.30.03") or clean_iso.replace(".", "").startswith("063003"):
            match_len = re.search(r'(\d+)\s*(?:CM|SENTIMEETRIT)', combined_text)
            if match_len:
                length_cm = int(match_len.group(1))
                if length_cm > 40:
                    return (
                        False,
                        f"Määruse kitsendus (Tulp C): ISO 06.30.03 lubab parukaid juuste pikkusega kuni 40cm (tuvastatud toote pikkus: {length_cm} cm).",
                        "PARUKAS_OVER_40CM"
                    )

        return True, None, None
