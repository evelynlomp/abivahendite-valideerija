"""
Kahetasemeline toodete ja variantide klassifitseerija (Tooteperekond + Klassifitseeritav Variant).

Eraldab kaks taset:
A. TOOTEPEREKOND (nt 'TENA PANTS MAXI', 'MOLICARE MOBILE 8 TILKA', 'ABENA SLIP', 'SENI LADY', 'SENI CARE')
B. KLASSIFITSEERITAV VARIANT (nt 'M + >=1700ML', 'L + >=1700ML', 'L3 + 3000-3699ML', '60X90', 'NIISUTATUD SALVRÄTID')

Võimaldab tuvastada:
1. Millised tehnilised tunnused (suurus, imavus ml, tilgad, sugu, mõõdud, alamtüüp) määravad ISO koodi.
2. Kas sama klassifitseeritav variant viitab alati samale ISO koodile.
"""

import re
from typing import Dict, Any, Optional, Tuple
from src.normalizer import normalize_name
from src.product_registry_db import ID_BRAND_VALID_RE


class VariantClassifier:
    """Eraldab tootenimetusest tooteperekonna (Level A) ja klassifitseeritava variandi (Level B)."""

    INCO_BRANDS = {
        "TENA", "MOLICARE", "SENI", "ABENA", "ATTENDS", "FORMA-CARE",
        "ONTEX iD", "LILLE", "EGOSAN", "AMD", "DAILEE", "SENSILIND",
        "BETTERDRY", "HUGGIES"
    }

    BRAND_PATTERNS = [
        ("TENA", r"\bTENA\b|\bTENAVAN\b"),
        ("MOLICARE", r"\bMOLICARE\b|\bMOLI\s*CARE\b|\bMOLIMED\b|\bMOLIFORM\b|\bMOLIPANTS\b"),
        ("SENI", r"\bSENI\b"),
        ("ABENA", r"\bABENA\b|\bABRI\b|\bBAMBO\b"),
        ("ATTENDS", r"\bATTENDS\b"),
        ("FORMA-CARE", r"\bFORMA[\s\-]*CARE\b"),
        ("ONTEX iD", None),  # Handled via ID_BRAND_VALID_RE
        ("LILLE", r"\bLILLE\b|\bONTEX\b"),
        ("EGOSAN", r"\bEGOSAN\w*\b"),
        ("AMD", r"\bAMD\b"),
        ("DAILEE", r"\bDAILEE\b"),
        ("SENSILIND", r"\bSENSILIND\b"),
        ("BETTERDRY", r"\bBETTERDRY\b"),
        ("HUGGIES", r"\bHUGGIES\b|\bDRYNITES\b|\bDRY\s+NITES\b"),
        ("CHEMI-PHARM", r"\bCHEMI[\s\-]*PHARM\b|\bFRESH\s+FOAM\b|\bECOSOFT\b"),
        ("SUDOCREM", r"\bSUDOCREA?M\b"),
        ("DISPOTECH", r"\bDISPOTECH\b|\bDISPO\b|\bDISPOWIPE\b"),
        ("SERENITY", r"\bSERENITY\b"),
        ("ROMED", r"\bROMED\b"),
        ("MED-COVER", r"\bMED[\s\-]*COVER\b"),
        ("GANTNET", r"\bGANTNET\b"),
        ("SELEFA", r"\bSELEFA\b"),
        ("VALACLEAN", r"\bVALACLEAN\b"),
        ("PURACLOTH", r"\bPURACLOTH\b"),
        ("HANDSOFT", r"\bHANDSOFT\b"),
        ("HYGER", r"\bHYGER\b"),
        ("INELLI", r"\bINELLI\b"),
        ("HELMI", r"\bHELMI\b"),
        ("KID-MAN", r"\bKID[\s\-]*MAN\b"),
        ("TUKIMET", r"\bTUKIMET\b"),
        ("GN RESOUND", r"\bRESOUND\b|\bLINX\s+QUATTRO\b|\bRE[\s\-]*[579]\d{2}\b|\bKE[\s\-]*[234]\d{2}\b|\bKEY[\s\-]*[234]\d{2}\b|\bRU[\s\-]*[4579]\d{2}\b|\bNX[\s\-]*[4579]\d{2}S?\b"),
        ("OTICON", r"\bOTICON\b|\bZIRCON\b|\bJET\s*[12]\b"),
        ("PHONAK", r"\bPHONAK\b|\bAUDEO\b|\bNAIDA\b"),
        ("SIGNIA", r"\bSIGNIA\b|\bINTUIS\b|\bXTM\b"),
        ("BERNAFON", r"\bBERNAFON\b|\bENTRA\b|\bENCANTA\b"),
        ("STARKEY", r"\bSTARKEY\b|\bEVOLV\b"),
        ("COCHLEAR", r"\bCOCHLEAR\b"),
        ("VAROMED", r"\bVAROMED\b"),
        ("FINNCOMFORT", r"\bFINN\s*COMFORT\b"),
        ("MEMO", r"\bMEMO\b"),
        ("HERGOS", r"\bHERGOS\b"),
        ("DR ORTO", r"\bDR\.?\s*ORTO\b"),
        ("TIMAGO", r"\bTIMAGO\b"),
        ("VERMEIREN", r"\bVERMEIREN\b"),
        ("ETAC", r"\bETAC\b"),
        ("INVACARE", r"\bINVACARE\b"),
        ("SWERECO", r"\bSWERECO\b"),
        ("SUNDO", r"\bSUNDO\b"),
        ("OSSENBERG", r"\bOSSENBERG\b"),
        ("DIETZ", r"\bDIETZ\b|\bTAIMA\b"),
        ("THUASNE", r"\bTHUASNE\b"),
        ("OTTOBOCK", r"\bOTTOBOCK\b|\bOTTO\s+BOCK\b"),
        ("BAUERFEIND", r"\bBAUERFEIND\b"),
        ("MEDI", r"\bMEDI\b"),
        ("ORLIMAN", r"\bORLIMAN\b"),
    ]

    @classmethod
    def extract_brand(cls, raw_name: str, norm_name: str) -> str:
        raw_up = raw_name.upper()
        if ID_BRAND_VALID_RE.search(raw_up):
            return "ONTEX iD"
        for brand, pat in cls.BRAND_PATTERNS:
            if pat and re.search(pat, raw_up):
                return brand
        return "MUU BRÄND"

    @classmethod
    def analyze(cls, raw_name: str) -> Dict[str, Any]:
        norm = normalize_name(raw_name)
        raw_up = raw_name.upper()
        brand = cls.extract_brand(raw_name, norm)

        # 1. Dimensions (e.g. 40X60, 60X60, 60X90, 80X180)
        dim_match = re.search(r"\b(\d{1,3}(?:\.\d+)?X\d{1,3}(?:\.\d+)?)\b", norm)
        dimensions = dim_match.group(1) if dim_match else None
        if dimensions:
            parts = dimensions.split("X")
            try:
                d1, d2 = float(parts[0]), float(parts[1])
                if (int(d1), int(d2)) in {(60, 40), (90, 60), (180, 80), (170, 80), (180, 70), (210, 90)}:
                    dimensions = f"{int(min(d1, d2))}X{int(max(d1, d2))}"
            except ValueError:
                pass

        # 2. Volume in ML
        ml_match = re.search(r"\b(\d{2,4})\s*ML\b", raw_up)
        if not ml_match:
            paren_ml = re.search(r"\((\d{3,4})\s*(?:ML)?\)", raw_up)
            if paren_ml and not re.search(r"\b(ART|KOOD|MSA|EAN)\b", raw_up):
                val = int(paren_ml.group(1))
                if 200 <= val <= 5000 and val not in {1000, 1065, 1070, 1124, 1562, 2071, 2074, 2075, 2077, 2078, 2079, 4041, 4046, 4051, 4056, 6595, 6657}:
                    ml_match = paren_ml
        volume_ml = int(ml_match.group(1)) if ml_match else None

        # 3. Drops (tilka)
        drops = None
        drops_match = re.search(r"\b(\d+(?:[.,]\d+)?)\s*(?:TILKA|TILK|DROPS)\b", raw_up)
        if drops_match:
            drops = float(drops_match.group(1).replace(",", "."))

        # 4. Combined size+level token (S2, S4, M1..M4, M10, L0..L4, L8, XL1..XL4, XL10, XXL1, XXL2)
        combo_match = re.search(r"\b(XS|S|M|L|XL|XXL)(10|[0-48])\b", raw_up)
        combo_code = f"{combo_match.group(1)}{combo_match.group(2)}" if combo_match else None

        # 5. Size (XS, S, M, L, XL, XXL, XXXL)
        size = None
        if combo_match:
            size = combo_match.group(1)
        else:
            sm_match = re.search(r"\b(S\s*/\s*M|L\s*/\s*XL)\b", raw_up)
            if sm_match:
                size = sm_match.group(1).replace(" ", "")
            else:
                sz_exact = re.search(
                    r"\b(XXXL|XX[\s\-]*LARGE|XXL|EXTRA\s+LARGE|X[\s\-]*LARGE|XLARGE|XL|XS)\b",
                    raw_up
                )
                if sz_exact:
                    s_tok = re.sub(r"[\s\-]+", " ", sz_exact.group(1).strip())
                    s_map = {
                        "X LARGE": "XL",
                        "XLARGE": "XL",
                        "EXTRA LARGE": "XL",
                        "XX LARGE": "XXL",
                    }
                    size = s_map.get(s_tok, s_tok)
                else:
                    sz_m = re.search(r"\b(SMALL|MEDIUM|LARGE|S|M|L)\b", raw_up)
                    if sz_m:
                        s_tok = sz_m.group(1)
                        s_map = {"SMALL": "S", "MEDIUM": "M", "LARGE": "L"}
                        size = s_map.get(s_tok, s_tok)
                    else:
                        att_m = re.search(r"\b([89]|10)(XS|S|M|L|XL|XXL)\b", raw_up)
                        if att_m:
                            size = att_m.group(2)

        # 6. Tier / Series modifier
        tiers = []
        for t_tok in ["BASIC", "MINI", "NORMAL", "EXTRA", "PLUS", "SUPER", "MAXI", "ULTIMA", "QUATRO", "TRIO", "NIGHT"]:
            if re.search(r"\b" + t_tok + r"\b", raw_up):
                tiers.append(t_tok)
        tier_str = " ".join(tiers) if tiers else None

        # 7. Level / Formula / Number
        level_code = None
        lvl_m = re.search(r"\b(?:LEVEL|FORMULA|L)\s*([0-4])\b", raw_up)
        if lvl_m:
            level_code = f"LEVEL {lvl_m.group(1)}"
        elif re.search(r"\bSAN\s*(\d+[A]?)\b", raw_up):
            san_m = re.search(r"\bSAN\s*(\d+[A]?)\b", raw_up)
            level_code = f"SAN {san_m.group(1)} BASIC" if "BASIC" in raw_up else f"SAN {san_m.group(1)}"
        elif re.search(r"\bSOFT\s*([0-7])\b", raw_up):
            sft_m = re.search(r"\bSOFT\s*([0-7])\b", raw_up)
            level_code = f"SOFT {sft_m.group(1)} {tier_str}" if tier_str else f"SOFT {sft_m.group(1)}"
        elif re.search(r"\b([89]|10)(?:XS|S|M|L|XL|XXL)\b", raw_up):
            att_lvl = re.search(r"\b([89]|10)(?:XS|S|M|L|XL|XXL)\b", raw_up)
            level_code = f"TASE {att_lvl.group(1)}"
        elif re.search(r"\bNR\.?\s*([1-5])\b", raw_up):
            nr_m = re.search(r"\bNR\.?\s*([1-5])\b", raw_up)
            level_code = f"NR {nr_m.group(1)}"

        # 8. Gender / Age group
        gender = None
        if brand != "KID-MAN" and any(w in raw_up for w in ["LASTE", "JUNIOR", "BAMBO", "DRYNITES", "DRY NITES", "BABY", "4-7A", "8-15A", "8-13A"]):
            gender = "LASTE"
        elif brand != "KID-MAN" and re.search(r"\b(MEN|MAN|MEESTE|MEESTELE|ACTIVE\s+FIT)\b", raw_up):
            gender = "MEESTE"
        elif re.search(r"\b(LADY|WOMAN|WOMEN|NAISTE|NAISTELE|DISCREET|SILHOUETTE)\b", raw_up):
            gender = "NAISTE"

        family, variant, det_type = cls._build_family_and_variant(
            raw_up, norm, brand, size, combo_code, tier_str, level_code, volume_ml, drops, gender, dimensions
        )

        return {
            "brand": brand,
            "product_family": family,
            "classifiable_variant": variant,
            "full_variant_key": f"{family} :: {variant}",
            "determinant_type": det_type,
            "attributes": {
                "size": size,
                "combo_code": combo_code,
                "tier": tier_str,
                "level_code": level_code,
                "volume_ml": volume_ml,
                "drops": drops,
                "gender": gender,
                "dimensions": dimensions,
            }
        }

    @classmethod
    def _build_family_and_variant(
        cls, raw_up: str, norm: str, brand: str, size: Optional[str], combo_code: Optional[str],
        tier_str: Optional[str], level_code: Optional[str], volume_ml: Optional[int],
        drops: Optional[float], gender: Optional[str], dimensions: Optional[str]
    ) -> Tuple[str, str, str]:

        # --- 1. PESUKINDAD (09.33.30.02) ---
        if any(w in raw_up for w in ["PESUKINNAS", "PESUKINDAD", "WASHGLOVE", "WASH GLOVE", "WASH CLOVE"]):
            fam = f"{brand} PESUKINNAS" if brand != "MUU BRÄND" else "PESUKINNAS (ÜLD)"
            coating = "KILEGA" if "KILEGA" in raw_up or "FILM" in raw_up or "PE" in raw_up else ("KILETA" if "KILETA" in raw_up else "STANDARD")
            return fam, f"PESUKINNAS ({coating})", "Tootetüüp (pesukindad -> 09.33.30.02)"

        # --- 2. PEAPESUMÜTSID (09.33.30.03) ---
        if any(w in raw_up for w in ["PEAPESUMÜTS", "JUUSTEPESUMÜTS", "PESUMÜTS", "SHAMPOO CAP"]):
            fam = f"{brand} PEAPESUMÜTS" if brand != "MUU BRÄND" else "PEAPESUMÜTS (ÜLD)"
            return fam, "PEAPESUMÜTS", "Tootetüüp (peapesumütsid -> 09.33.30.03)"

        # --- 3. NIISUTATUD SALVRÄTID / PUHASTUSLAPID (09.33.30.01) ---
        if any(w in raw_up for w in ["SALVRÄT", "PUHASTUSRÄT", "PUHASTUSLAP", "WET WIPE", "ABRI-WET", "ABRI WET", "PESUSVAMM"]):
            fam = f"{brand} NIISKED SALVRÄTID" if brand != "MUU BRÄND" else "NIISKED SALVRÄTID (ÜLD)"
            v_dim = f" {dimensions}" if dimensions else ""
            return fam, f"NIISUTATUD SALVRÄTID{v_dim}", "Tootetüüp (niisutatud salvrätid -> 09.33.30.01)"

        # --- 4. NAHAPESEMISVAHENDID (09.21.06) ---
        if any(w in raw_up for w in ["PESUVAHT", "PUHASTUSVAHT", "PUHASTAV VAHT", "NAHAHOOLDUSVAHT", "PESUKREEM", "PESUGEEL", "PESUEMULSIOON", "PESUÕLI", "WASH CREAM", "WASH LOTION", "WASH MOUSSE", "FRESH FOAM", "3IN1", "3 IN 1"]):
            fam = f"{brand} NAHAPESUVAHEND" if brand != "MUU BRÄND" else "NAHAPESUVAHEND (ÜLD)"
            sub = "PESUVAHT" if "VAHT" in raw_up or "FOAM" in raw_up or "MOUSSE" in raw_up else ("PESUKREEM" if "KREEM" in raw_up or "CREAM" in raw_up else "PESUGEEL/EMULSIOON")
            return fam, sub, "Tootetüüp (nahapesemisvahendid -> 09.21.06)"

        # --- 5. NAHAKAITSEVAHENDID (09.21.18) ---
        if any(w in raw_up for w in ["KAITSEKREEM", "KEHAKREEM", "MÄHKMEALUNE", "SUDOCREM", "SUDOCREAM", "BARRIER", "ARGINIIN", "TSINK", "ZINC", "RASVATALK", "KAITSEVAHT"]):
            fam = f"{brand} NAHAKAITSEVAHEND" if brand != "MUU BRÄND" else "NAHAKAITSEVAHEND (ÜLD)"
            has_zn = any(w in raw_up for w in ["TSINK", "ZINC", "ZNO", "SUDOCREM", "SUDOCREAM", "ARGINIIN", "SININE"])
            zn_tag = "TSINKOKSIIDIGA/ARGINIINIGA" if has_zn else "ILMA TSINGIMÄRKETA"
            return fam, zn_tag, "Tootetüüp + koostis (nahakaitsevahendid -> 09.21.18)"

        # --- 6. VEEKINDLAD MADRATSIKATTED JA PESTAVAD ALUSLINAD (09.30.45) ---
        if (
            any(w in raw_up for w in ["MADRATSIKAITSE", "MADRATSIKATE", "VOODIKATE"])
            or (
                ("ALUSLINA" in raw_up or "IMAV LINA" in raw_up or "BED MAT TEXTILE" in raw_up)
                and any(w in raw_up for w in ["PESTAV", "KORDUVKASUTATAV", "TEXTILE", "75X85", "85X90", "90X115"])
            )
        ) and "LAMATIST" not in raw_up:
            fam = f"{brand} PESTAV ALUSLINA / MADRATSIKATE" if brand != "MUU BRÄND" else "PESTAV ALUSLINA / MADRATSIKATE"
            v_dim = dimensions or "STANDARDMÕÕT"
            return fam, f"PESTAV/VEEKINDEL ({v_dim})", "Tootetüüp (pestavad aluslinad ja madratsikatted -> 09.30.45)"

        # --- 7. ÜHEKORDSED IMAVAD ALUSLINAD (09.30.00.01 - 09.30.00.06) ---
        if any(w in raw_up for w in ["ALUSLINA", "IMAV LINA", "BED PLUS", "BED NORMAL", "BED SUPER", "BED MAT", "ABRI-SOFT", "ABRI SOFT", "SENI SOFT", "VOODIKAITSE", "COVER-DRI"]):
            if brand == "TENA":
                fam = "TENA BED"
            elif brand == "MOLICARE":
                fam = "MOLICARE BED MAT"
            elif brand == "ABENA":
                fam = "ABENA ABRI-SOFT"
            elif brand == "SENI":
                fam = "SENI SOFT"
            elif brand == "ATTENDS":
                fam = "ATTENDS ALUSLINA"
            elif brand == "FORMA-CARE":
                fam = "FORMA-CARE ALUSLINA"
            else:
                fam = f"{brand} ALUSLINA"
            v_dim = dimensions or "MÕÕDUTA"
            if v_dim in ("70X180", "80X170", "90X170", "90X180", "85X180"):
                v_dim = f"80-90X140-180 ({v_dim})"
            return fam, f"MÕÕT {v_dim}", "Mõõdud cm x cm (ühekordsed aluslinad -> 09.30.00.01–06)"

        # --- 8. FIKSEERIVAD PÜKSID (09.30.39.01 - 09.30.39.05) ---
        if any(w in raw_up for w in ["FIXPANTS", "FIX PANTS", "PREMIUM FIX", "ABRI-FIX", "ABRI FIX", "FIKS.PÜKSID", "FIKSEERIVAD PÜKSID", "VÕRKPÜKSID"]):
            if brand == "MOLICARE":
                fam = "MOLICARE FIXPANTS"
            elif brand == "TENA":
                fam = "TENA FIX"
            elif brand == "ABENA":
                fam = "ABENA ABRI-FIX"
            else:
                fam = f"{brand} FIKSEERIVAD PÜKSID"
            v_sz = size or "SUURUSETA"
            return fam, f"SUURUS {v_sz}", "Suurus S/M/L/XL/XXL (fikseerivad püksid -> 09.30.39.01–05)"

        # --- 9. LASTE MÄHKMED JA IMAVAD PÜKSID (09.30.24.06 - 09.30.24.10) ---
        if gender == "LASTE":
            fam = f"{brand} LASTE MÄHKMED"
            if any(w in raw_up for w in ["35-50", "27-57", "8-15", "8-13", "30-50"]):
                wt = "ÜLE 30KG (8-15A)"
            elif any(w in raw_up for w in ["17-30", "17-27", "15-30", "15-35", "16-30", "4-7A", "SIZE 6", "NR 6", "XL"]):
                wt = "15-30KG (XL / JUNIOR)"
            else:
                wt = norm
            return fam, wt, "Vanuse- ja kaalugrupp (laste mähkmed -> 09.30.24.06–10)"

        # --- 10. KUULMISABIVAHENDID JA OTSAKUD (22.06.*) ---
        if re.search(r"\b(INDIVIDUAALNE|INDIV\.?|IND\.?)\s*(KÕRVAOTSIK|KÕRVAOTSAK|OTSAK|OTSIK|RIE\s+OTSIK|RIE\s+OTSAK)\b", raw_up):
            return "KUULDEAPARAADI OTSAKUD", "INDIVIDUAALNE OTSAK", "Tootetüüp (individuaalne otsak -> 22.06.12.04)"
        if brand == "COCHLEAR" or "KUIVATUSBRIKET" in raw_up:
            return "COCHLEAR SISEKÕRVAIMPLANTAADI TARVIKUD", "VARUOSAD / TARVIKUD", "Tootetüüp (implantaadi varuosad -> 22.06.21.03)"
        if brand in ("GN RESOUND", "OTICON", "PHONAK", "SIGNIA", "BERNAFON", "STARKEY") or "KUULDEAPARAAT" in raw_up:
            fam = f"{brand} KUULDEAPARAAT"
            hte_type = "ITE/ITC (KÕRVASISENE)" if any(w in raw_up for w in ["ITE", "ITC", "CIC", "OWN", "SILK", "INSIO"]) else "BTE/RIE (KÕRVATAGUNE)"
            return fam, f"{hte_type} [SÕLTUB AKTIIVSUSGRUPIST]", "Patsiendi aktiivsusgrupp I/II/III (22.06.12/15.01–03)"

        # --- 11. ORTOPEEDILISED JALATSID (06.33.00.*) ---
        if brand in ("VAROMED", "FINNCOMFORT", "MEMO", "HERGOS", "DR ORTO") or "JALATS" in raw_up or "KINGAD" in raw_up or "SAAPAD" in raw_up:
            fam = f"{brand} ORTOPEEDILINE JALATS" if brand != "MUU BRÄND" else "ORTOPEEDILINE JALATS"
            return fam, "ORTOPEEDILINE JALATS [SÕLTUB KATEGOORIAST I-V]", "Jalatsi kategooria I–V (06.33.00.01–05)"

        # --- 12. VÖÖMÄHKMED (BELTED DIAPERS -> 09.30.24.59 - .80) ---
        if any(w in raw_up for w in ["TENA FLEX", "SENI OPTIMA", "EXPERT BELT", "ATTENDS FLEX", "VÖÖMÄHE", "VÖÖMÄHKMED"]):
            if brand == "TENA":
                fam = f"TENA FLEX {tier_str}" if tier_str else "TENA FLEX"
            elif brand == "SENI":
                fam = f"SENI OPTIMA {tier_str}" if tier_str else "SENI OPTIMA"
            elif brand == "ONTEX iD":
                fam = f"ID EXPERT BELT {tier_str}" if tier_str else "ID EXPERT BELT"
            else:
                fam = f"{brand} VÖÖMÄHE"
            ml_bucket = cls._diaper_ml_bucket(volume_ml, tier_str, drops, combo_code)
            v_parts = [p for p in [size or "SUURUSETA", ml_bucket] if p]
            return fam, " + ".join(v_parts), "Suurus + imavus ml (vöömähkmed -> 09.30.24.59–80)"

        # --- 13. IMAVAD PÜKSID (PULL-UP PANTS -> 09.30.24.81 - .96) ---
        if any(w in raw_up for w in ["PANTS", "MOBILE", "SENI ACTIVE", "PULL-ONS", "PULL ONS", "IMAVAD PÜKSID", "PÜKSID", "SILHOUETTE"]):
            if brand == "TENA":
                if "SILHOUETTE" in raw_up:
                    fam = "TENA SILHOUETTE"
                elif gender == "MEESTE":
                    fam = "TENA MEN PANTS"
                else:
                    t_main = next((t for t in ["MAXI", "SUPER", "PLUS", "EXTRA", "NORMAL"] if t in (tier_str or "")), "")
                    fam = f"TENA PANTS {t_main}".strip()
            elif brand == "MOLICARE":
                dr_str = f" {int(drops) if drops and drops.is_integer() else drops} TILKA" if drops else ""
                fam = f"MOLICARE MOBILE{dr_str}"
            elif brand == "SENI":
                t_main = next((t for t in ["PLUS", "SUPER", "CLASSIC", "NORMAL"] if t in (tier_str or "")), "")
                fam = f"SENI ACTIVE {t_main}".strip()
            elif brand == "ABENA":
                fam = "ABENA PANTS"
            elif brand in ("ONTEX iD", "LILLE"):
                fam = "ID / LILLE PANTS"
            elif brand == "FORMA-CARE":
                fam = "FORMA-CARE PANTS"
            elif brand == "EGOSAN":
                fam = "EGOSAN PANTS"
            else:
                fam = f"{brand} IMAVAD PÜKSID"

            ml_bucket = cls._pants_ml_bucket(volume_ml, drops, combo_code, tier_str)
            v_tokens = []
            if combo_code:
                v_tokens.append(combo_code)
            elif size:
                v_tokens.append(size)
            if drops and "TILKA" not in fam:
                v_tokens.append(f"{int(drops) if drops.is_integer() else drops} TILKA")
            v_tokens.append(ml_bucket)
            return fam, " + ".join(v_tokens) if v_tokens else "STANDARD", "Suurus + imavus/tilgad (imavad püksid -> 09.30.24.81–96)"

        # --- 14. PÜKSMÄHKMED (SLIP / ELASTIC / SUPER SENI -> 09.30.24.30 - .57) ---
        if any(w in raw_up for w in ["SLIP", "ELASTIC", "PÜKSMÄHE", "PÜKSMÄHKMED", "SUPER SENI", "SENI SUPER"]):
            if brand == "TENA":
                t_main = next((t for t in ["ULTIMA", "MAXI", "SUPER", "PLUS"] if t in (tier_str or "")), "")
                fam = f"TENA SLIP {t_main}".strip()
            elif brand == "MOLICARE":
                sub_f = "ELASTIC" if "ELASTIC" in raw_up else "SLIP"
                dr_str = f" {int(drops) if drops and drops.is_integer() else drops} TILKA" if drops else ""
                fam = f"MOLICARE {sub_f}{dr_str}"
            elif brand == "SENI":
                t_main = next((t for t in ["QUATRO", "TRIO", "PLUS"] if t in (tier_str or "")), "STANDARD")
                fam = f"SUPER SENI {t_main}".strip()
            elif brand == "ABENA":
                fam = "ABENA SLIP"
            elif brand in ("ONTEX iD", "LILLE"):
                fam = "ID SLIP"
            elif brand == "ATTENDS":
                fam = "ATTENDS SLIP"
            elif brand == "FORMA-CARE":
                fam = "FORMA-CARE SLIP"
            elif brand == "AMD":
                fam = "AMD SLIP"
            else:
                fam = f"{brand} PÜKSMÄHE"

            ml_bucket = cls._diaper_ml_bucket(volume_ml, tier_str, drops, combo_code)
            v_tokens = []
            if combo_code:
                v_tokens.append(combo_code)
            elif size:
                v_tokens.append(size)
            if level_code and not combo_code:
                v_tokens.append(level_code)
            v_tokens.append(ml_bucket)
            return fam, " + ".join(v_tokens) if v_tokens else "STANDARD", "Suurus + imavus/tase (püksmähkmed -> 09.30.24.30–57)"

        # --- 15. SUURED VORMIMÄHKMED JA INKONTINENTSISIDEMED (09.30.24.11 - .28) ---
        if brand in cls.INCO_BRANDS or any(w in raw_up for w in [
            "INKONTINENTSI", "URIINIPIDAM", "VORMMÄHE", "MÄHE", "MÄHKMED", "SIDEMED", "TILKA"
        ]):
            is_large_shaped = (
                (volume_ml and volume_ml >= 1200)
                or any(w in raw_up for w in ["VORMMÄHE", "SAN SENI", "MOLICARE FORM", "EXPERT FORM", "COMFORT PLUS", "COMFORT EXTRA", "COMFORT SUPER", "COMFORT MAXI"])
                or (level_code and any(level_code.startswith(p) for p in ["SAN 5", "SAN 6", "SAN 7", "SAN 8", "SAN 9", "SAN 10", "SAN 11"]))
            )
            if is_large_shaped:
                if brand == "TENA":
                    fam = "TENA COMFORT (VORMMÄHE)"
                elif brand == "ABENA":
                    fam = "ABENA SAN (VORMMÄHE 5-11)"
                elif brand == "SENI":
                    fam = "SAN SENI (VORMMÄHE)"
                elif brand == "MOLICARE":
                    fam = "MOLICARE FORM (VORMMÄHE)"
                else:
                    fam = f"{brand} VORMMÄHE"
                ml_b = cls._shaped_pad_ml_bucket(volume_ml, level_code, tier_str, drops)
                v_parts = [p for p in [level_code or tier_str, ml_b] if p]
                return fam, " + ".join(v_parts), "Imavus ml / tase (suured vormmähkmed -> 09.30.24.25–28)"

            if gender == "MEESTE":
                fam = f"{brand} MEN (MEESTE SIDE)"
                ml_b = cls._men_pad_ml_bucket(volume_ml, level_code, drops)
                v_parts = [p for p in [level_code or (f"{int(drops) if drops and drops.is_integer() else drops} TILKA" if drops else tier_str), ml_b] if p]
                return fam, " + ".join(v_parts) if v_parts else ml_b, "Sugu (meeste) + imavus/tase (09.30.24.11–13)"

            # Women's / light-to-medium incontinence pads (09.30.24.14 - .17)
            if brand == "TENA":
                fam = "TENA COMFORT MINI" if "COMFORT" in raw_up else "TENA LADY / DISCREET"
            elif brand == "MOLICARE":
                fam = "MOLICARE PAD LADY"
            elif brand == "SENI":
                fam = "SENI LADY"
            elif brand == "ABENA":
                fam = "ABENA SAN (1-4)" if "SAN" in raw_up else "ABENA LIGHT"
            elif brand in ("ONTEX iD", "LILLE"):
                fam = "ID / LILLE LIGHT"
            elif brand == "FORMA-CARE":
                fam = "FORMA-CARE WOMAN"
            else:
                fam = f"{brand} NAISTE SIDE"

            ml_b = cls._women_pad_ml_bucket(volume_ml, drops, level_code, tier_str)
            v_parts = []
            if drops:
                v_parts.append(f"{int(drops) if drops.is_integer() else drops} TILKA")
            elif level_code:
                v_parts.append(level_code)
            elif tier_str:
                v_parts.append(tier_str)
            v_parts.append(ml_b)
            return fam, " + ".join(v_parts), "Imavus ml / tilgad / tase (naiste sidemed -> 09.30.24.14–17)"

        # --- 16. LIIKUMIS-, TUALETI- JA PESEMISABIVAHENDID ---
        if any(w in raw_up for w in ["RULAATOR", "TUGIRAAM"]):
            fam = f"{brand} RULAATOR / TUGIRAAM" if brand != "MUU BRÄND" else "RULAATOR / TUGIRAAM"
            sub = "4-RATTALINE RULAATOR" if any(w in raw_up for w in ["RULAATOR", "4-R", "4 RATTALINE", "4 - RATTALINE"]) else "TUGIRAAM"
            return fam, sub, "Tootetüüp + rataste arv (12.06.03 / 12.06.06)"
        if any(w in raw_up for w in ["KÜÜNARKARK", "KÜÜNARKEPP", "KARK"]):
            fam = f"{brand} KARK" if brand != "MUU BRÄND" else "KARK"
            sub = "KAENLAALUNE KARK" if ("KAENLA" in raw_up or "ASHLEY" in raw_up or "12.03.12" in raw_up) else "KÜÜNARKARK"
            return fam, sub, "Tootetüüp (küünarkargud 12.03.06 vs kaenlaalused 12.03.12)"
        if "KEPP" in raw_up:
            fam = f"{brand} KÄIMISKEPP" if brand != "MUU BRÄND" else "KÄIMISKEPP"
            if any(w in raw_up for w in ["VALGE KEPP", "PIMEDATE", "RNIB", "TELESKOOPKEPP"]):
                return fam, "VALGE KEPP (NÄGEMISABIVAHEND)", "Tootetüüp (valged kepid -> 12.39.03)"
            sub = "MITME PUNKTIGA KEPP" if any(w in raw_up for w in ["3-P", "4-P", "KOLME", "NELJA", "HARK"]) else "TAVALINE KÄIMISKEPP"
            return fam, sub, "Tootetüüp (käimiskepid 12.03.03 vs 12.03.16)"
        if any(w in raw_up for w in ["POTITOOL", "WC TOOL", "WC/DUSHITOOL", "POTIKÕRGENDUS", "WC KÕRGENDUS", "DUŠITOOL", "DUSHIISTE", "VANNITOOL", "VANNILAUD", "TUGIKÄEPIDE"]):
            if "POTIKÕRGENDUS" in raw_up or "WC KÕRGENDUS" in raw_up:
                return f"{brand} POTIKÕRGENDUS", "POTIKÕRGENDUS", "Tootetüüp (potikõrgendused -> 09.12.15)"
            if "POTITOOL" in raw_up or "WC TOOL" in raw_up or "COMMODE" in raw_up:
                return f"{brand} POTITOOL", "POTITOOL", "Tootetüüp (potitoolid -> 09.12.03.01)"
            if "TUGIKÄEPIDE" in raw_up:
                return f"{brand} TUGIKÄEPIDE", "TUGIKÄEPIDE", "Tootetüüp (käsipuud ja tugikäepidemed -> 18.18.06)"
            return f"{brand} DUŠI-/VANNIABIVAHEND", norm, "Tootetüüp (pesemisabivahendid -> 09.33.03)"
        if any(w in raw_up for w in ["SUKAJALGATÕMBAJA", "SOKIJALGATÕMBAJA", "SOKI JALGATÕMBAJA"]):
            return f"{brand} RIIETUMISABIVAHEND", "SUKA-/SOKIJALGATÕMBAJA", "Tootetüüp (riietumisabivahendid -> 09.09.03)"
        if "HAARATS" in raw_up:
            if "PABERI" in raw_up or "TORKEL" in raw_up:
                return f"{brand} TUALETIABIVAHEND", "WC PABERI HAARATS", "Tootetüüp (tualeti hügieeniabivahendid -> 09.12.27)"
            return f"{brand} HAARATS", "HAARATS", "Tootetüüp (haaratsid -> 24.21.03)"
        if "LAMATIST" in raw_up and "MADRATS" in raw_up:
            sub_m = "KOMPRESSORIGA MADRATS" if ("KOMPRESSOR" in raw_up or "PIUMA" in raw_up) else "VAHTMADRATS"
            return f"{brand} LAMATISTEVASTANE MADRATS", sub_m, "Tootetüüp (lamatisi ennetavad madratsid -> 04.33.06.01–02)"

        return f"{brand} MUU TOODE", norm, "Konkreetne mudelinimetus"

    @staticmethod
    def _pants_ml_bucket(volume_ml: Optional[int], drops: Optional[float], combo_code: Optional[str], tier_str: Optional[str]) -> str:
        if volume_ml:
            if volume_ml < 1400:
                return "<1400ML"
            if volume_ml < 1700:
                return "1400-1699ML"
            return ">=1700ML"
        if combo_code:
            lvl = combo_code[-1]
            if lvl == "0":
                return "<1400ML"
            if lvl == "1":
                return "1400-1699ML"
            if lvl in ("2", "3", "4", "8"):
                return ">=1700ML"
        if drops:
            if drops <= 5:
                return "<1400ML"
            if drops >= 6:
                return ">=1700ML"
        if tier_str:
            if any(t in tier_str for t in ["MAXI", "SUPER"]):
                return ">=1700ML"
            if any(t in tier_str for t in ["EXTRA", "PLUS", "CLASSIC"]):
                return "1400-1699ML"
            if "NORMAL" in tier_str:
                return "<1400ML"
        return "MAHT TÄPSUSTAMATA"

    @staticmethod
    def _diaper_ml_bucket(volume_ml: Optional[int], tier_str: Optional[str], drops: Optional[float], combo_code: Optional[str]) -> str:
        if volume_ml:
            if volume_ml < 1900:
                return "<1900ML"
            if volume_ml < 2500:
                return "1900-2499ML"
            if volume_ml < 3000:
                return "2500-2999ML"
            if volume_ml < 3700:
                return "3000-3699ML"
            return ">=3700ML"
        if combo_code:
            if combo_code == "M1":
                return "1900-2499ML"
            if combo_code == "M2":
                return "2500-2999ML"
            if combo_code in ("M3", "M4", "L2", "L3", "XL2"):
                return "3000-3699ML"
            if combo_code in ("L4", "XL4", "M10", "L10", "XL10"):
                return ">=3700ML"
        if tier_str:
            if any(t in tier_str for t in ["ULTIMA", "QUATRO"]):
                return ">=3700ML"
            if any(t in tier_str for t in ["MAXI", "TRIO"]):
                return "3000-3699ML"
            if "SUPER" in tier_str:
                return "2500-2999ML"
            if "PLUS" in tier_str:
                return "1900-2499ML"
        return "MAHT TÄPSUSTAMATA"

    @staticmethod
    def _shaped_pad_ml_bucket(volume_ml: Optional[int], level_code: Optional[str], tier_str: Optional[str], drops: Optional[float]) -> str:
        if volume_ml:
            if volume_ml < 1600:
                return "1200-1599ML"
            if volume_ml < 2100:
                return "1600-2099ML"
            if volume_ml < 2600:
                return "2100-2599ML"
            if volume_ml >= 3000:
                return ">=3000ML"
            return "2600-2999ML"
        if level_code == "SAN 5" or level_code == "SAN 6 BASIC":
            return "1200-1999ML"
        if level_code == "SAN 6":
            return "2000-2499ML"
        if level_code in ("SAN 7", "SAN 8", "SAN 9"):
            return "2100-2599ML"
        if level_code in ("SAN 10", "SAN 11"):
            return ">=2600ML"
        return ">=1200ML"

    @staticmethod
    def _men_pad_ml_bucket(volume_ml: Optional[int], level_code: Optional[str], drops: Optional[float]) -> str:
        if volume_ml:
            if volume_ml < 400:
                return "<400ML"
            if volume_ml < 600:
                return "400-599ML"
            return ">=600ML"
        if level_code in ("LEVEL 0", "LEVEL 1"):
            return "<400ML"
        if level_code == "LEVEL 2":
            return "400-599ML"
        if level_code in ("LEVEL 3", "LEVEL 4"):
            return ">=600ML"
        if drops:
            if drops <= 3:
                return "<400ML"
            if drops == 4:
                return "400-599ML"
            if drops >= 5:
                return ">=600ML"
        return "MEESTE SIDE"

    @staticmethod
    def _women_pad_ml_bucket(volume_ml: Optional[int], drops: Optional[float], level_code: Optional[str], tier_str: Optional[str]) -> str:
        if volume_ml:
            if volume_ml < 300:
                return "201-299ML"
            if volume_ml < 600:
                return "300-599ML"
            if volume_ml < 1000:
                return "600-999ML"
            return "1000-1199ML"
        if drops:
            if drops <= 1.5:
                return "201-299ML"
            if drops in (2.0, 2.5, 3.0, 3.5):
                return "300-599ML"
            if drops in (4.0, 4.5):
                return "600-999ML"
            if drops >= 5.0:
                return "1000-1199ML"
        if level_code in ("SAN 1", "SAN 1A", "NR 1"):
            return "201-299ML"
        if level_code in ("SAN 2", "SAN 3", "SAN 3A", "NR 2", "SOFT 2", "SOFT 2 NORMAL", "SOFT 3 NORMAL"):
            return "300-599ML"
        if level_code in ("SAN 4", "NR 3", "NR 4", "SOFT 3 EXTRA", "SOFT 4", "SOFT 5"):
            return "600-999ML"
        if tier_str == "EXTRA":
            return "300-599ML"
        return "NAISTE SIDE"
