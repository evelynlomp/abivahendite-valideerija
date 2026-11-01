"""Toote tuvastamise agent (Product Identification Agent).

Eesmärk:
Tuvastada tarnija spetsiifilisest nimetusest reaalne ametlik toode, selle tootja,
omadused, tõendusmaterjal ja usaldusskoor ENNE riiklikku klassifitseerimist ja valideerimist.
Peamiseks allikaks on püsiv SQLite tooteregister (tooteregister).
"""

import re
from typing import Dict, Any, List, Optional
from rapidfuzz import fuzz

from src.normalizer import clean_text, normalize_name
from src.product_registry import MANUFACTURER_CATALOGUE
from src.product_registry_db import get_product_registry_db, ProductRegistryDB


class ProductIdentificationAgent:
    """
    Toote tuvastamise agent:
    1. Otsib toote tõendeid (evidence)
    2. Otsib tootja informatsiooni (manufacturer info)
    3. Otsib tarnijate ja tootjate kataloogidest (tooteregister)
    4. Võrdleb toote omadusi (maht ml, tilgad, tase, suurus, sihtgrupp)
    5. Toodab ühe või mitu kandidaattoodet (candidate products)
    6. Arvutab usaldusskoori (confidence score)
    7. Põhjendab arutluskäiku (reasoning)
    """

    def __init__(self, registry: Optional[List[Dict[str, Any]]] = None, registry_db: Optional[ProductRegistryDB] = None):
        self.registry_db = registry_db or get_product_registry_db()
        db_prods = self.registry_db.get_all_products()
        if registry:
            self.registry = registry
        elif db_prods:
            self.registry = db_prods
        else:
            self.registry = MANUFACTURER_CATALOGUE

    def extract_features(self, raw_name: str) -> Dict[str, Any]:
        """
        Eraldab nimetusest tootja, tootesarja, mahu ml, tilgad, taseme, suuruse ja pakendi.
        """
        text = clean_text(raw_name)

        features: Dict[str, Any] = {
            "raw": raw_name,
            "normalized": normalize_name(raw_name),
            "brand": None,
            "line": None,
            "level": None,
            "volume_ml": None,
            "drops": None,
            "size": None,
            "package_count": None,
            "gender": None
        }

        # 1. Tuvasta maht ml (nt 340ML, 600 ML, 800ML)
        vol_match = re.search(r"\b(\d{2,4})\s*ML\b", text, re.IGNORECASE)
        if vol_match:
            features["volume_ml"] = int(vol_match.group(1))

        # 2. Tuvasta pakendi suurus (nt N28, N30, 14TK)
        pkg_match = re.search(r"\bN\s*(\d+)\b", text, re.IGNORECASE)
        if pkg_match:
            features["package_count"] = int(pkg_match.group(1))
        else:
            pkg_tk = re.search(r"\b(\d+)\s*(TK|PCS|PK)\b", text, re.IGNORECASE)
            if pkg_tk:
                features["package_count"] = int(pkg_tk.group(1))

        # 3. Tuvasta tilkade arv (nt 4 TILKA, 6 DROPS)
        drop_match = re.search(r"\b(\d+)\s*(TILKA?|DROPS?)\b", text, re.IGNORECASE)
        if drop_match:
            features["drops"] = int(drop_match.group(1))
        else:
            dec_drop = re.search(r"\b(\d+)[,\.]5\s*(TILKA?|DROPS?)\b", text, re.IGNORECASE)
            if dec_drop:
                features["drops"] = int(dec_drop.group(1))

        # 4. Tuvasta toote tase/number (nt SAN 4, PAD 4, M3)
        combo_match = re.search(r"\b(?:SAN|PAD|ABRI-SAN|LEVEL|NR)\s*(\d+)\b", text, re.IGNORECASE)
        if combo_match:
            features["level"] = int(combo_match.group(1))
        else:
            size_num_match = re.search(r"\b(XXS|XS|S|M|L|XL|XXL|XXXL)(\d)\b", text, re.IGNORECASE)
            if size_num_match:
                features["size"] = size_num_match.group(1).upper()
                features["level"] = int(size_num_match.group(2))
            else:
                num_match = re.search(r"\b([1-9])\b", text)
                if num_match and not features["drops"]:
                    features["level"] = int(num_match.group(1))

        # 5. Tuvasta suurus (XS, S, M, L, XL, XXL)
        if not features["size"]:
            size_match = re.search(r"\b(XXS|XS|S|M|L|XL|XXL|XXXL)\b", text, re.IGNORECASE)
            if size_match:
                features["size"] = size_match.group(1).upper()

        # 6. Tuvasta sugu (LADY, MEN)
        if re.search(r"\bLADY\b", text, re.IGNORECASE):
            features["gender"] = "Naistele"
        elif re.search(r"\bMEN\b", text, re.IGNORECASE):
            features["gender"] = "Meestele"

        # 7. Tuvasta tuntud brändid
        known_brands = {
            "ABENA": "ABENA",
            "ABRI": "ABENA",
            "BAMBO": "ABENA",
            "MOLICARE": "MOLICARE",
            "HARTMANN": "MOLICARE",
            "MENALIND": "MOLICARE",
            "LILLE": "LILLE",
            "ONTEX": "LILLE",
            "ID": "LILLE",
            "TENA": "TENA",
            "ESSITY": "TENA",
            "SENI": "SENI",
            "TZMO": "SENI",
            "ATTENDS": "ATTENDS",
            "MEDI": "MEDI",
            "MEDIVEN": "MEDI",
            "SIGVARIS": "SIGVARIS",
            "VERMEIREN": "VERMEIREN",
            "ETAC": "ETAC",
            "REBOTEC": "REBOTEC",
            "INVACARE": "INVACARE",
            "DIETZ": "DIETZ",
            "BEURER": "BEURER",
            "BAUERFEIND": "BAUERFEIND",
            "THUASNE": "THUASNE",
            "BORT": "BORT",
            "ORLIMAN": "ORLIMAN",
            "SWERECO": "SWERECO",
            "CRISTALLO": "CRISTALLO",
            "ERGODYNAMIC": "ERGODYNAMIC",
            "FORMA-CARE": "FORMA-CARE",
            "FORMA CARE": "FORMA-CARE",
            "FORMA": "FORMA-CARE",
            "SENSILIND": "SENSILIND"
        }
        for token, brand_key in known_brands.items():
            if re.search(r"\b" + re.escape(token) + r"\b", text, re.IGNORECASE):
                features["brand"] = brand_key
                break

        return features

    def identify_product(self, raw_name: str) -> Dict[str, Any]:
        """
        Teostab täieliku toote tuvastuse:
        1. Kontrollib O(1) kiirusega täpset alias-vastavust SQLite tooteregistrist
        2. Kui täpset vastet pole, teostab brändi ja atribuutide põhjal kaalutud otsingu
        3. Arvutab usaldusskoori ja koostab arutluskäigu tõenditega
        """
        features = self.extract_features(raw_name)
        norm_name = features["normalized"]

        # Kiire O(1) alias-kontroll tooteregistris
        if self.registry_db:
            exact = self.registry_db.find_exact_alias(raw_name)
            if exact:
                reasoning = (
                    f"Tarnija nimetus '{raw_name}' leiti täpse vastena tooteregistrist: "
                    f"tootja {exact['manufacturer']} ametlik toode '{exact['official_name']}' "
                    f"(Kategooria: {exact.get('category_type')}). Allikas: {exact.get('source_supplier')}."
                )
                evidence = [
                    f"Täpne vastavus tooteregistri aliasele või ametlikule tootenimele '{exact['official_name']}'.",
                    f"Tootja: {exact['manufacturer']} | Allikad: {exact.get('source_supplier')}"
                ]
                
                same_brand = self.registry_db.get_by_brand(exact['brand'])
                alternatives = []
                for p in same_brand:
                    if p['official_name'] != exact['official_name']:
                        alternatives.append({
                            "official_product": p["official_name"],
                            "confidence_score": 0.85,
                            "reason": f"Sama sarja alternatiiv ({p.get('absorption_ml')} ml)" if p.get("absorption_ml") else "Alternatiivne toode"
                        })
                        if len(alternatives) >= 3:
                            break

                return {
                    "identified": True,
                    "official_product": exact["official_name"],
                    "full_name": exact.get("full_name", exact["official_name"]),
                    "manufacturer": exact["manufacturer"],
                    "confidence_score": 1.0,
                    "suggested_iso": exact.get("suggested_iso"),
                    "suggested_statutory_name": exact.get("suggested_statutory_name"),
                    "evidence_sources": evidence,
                    "alternative_matches": alternatives,
                    "reasoning": reasoning,
                    "features": features
                }

        candidate_pool = self.registry
        if features["brand"] and self.registry_db:
            brand_prods = self.registry_db.get_by_brand(features["brand"])
            if brand_prods:
                candidate_pool = brand_prods

        candidates = []

        for prod in candidate_pool:
            brand_score = 0.0
            line_score = 0.0
            param_score = 0.0
            evidence_points = []

            # 1. Brändi vastavus
            prod_brand = prod["brand"].upper()
            if features["brand"] == prod_brand:
                brand_score = 1.0
                evidence_points.append(f"Tootja bränd '{prod_brand}' kattub (Tootja: {prod['manufacturer']}).")
            elif prod_brand in norm_name:
                brand_score = 0.9
                evidence_points.append(f"Tootja bränd '{prod_brand}' leidub tootenimes.")
            else:
                brand_score = 0.0

            # 2. Tootesarja ja kanooniliste aliase'te vastavus
            best_alias_score = 0.0
            aliases = prod.get("aliases", [])
            if not aliases:
                aliases = [prod.get("official_name", "")]

            for alias in aliases:
                norm_alias = normalize_name(alias)
                s_sort = fuzz.token_sort_ratio(norm_name, norm_alias)
                s_set = fuzz.token_set_ratio(norm_name, norm_alias)
                s_comb = max(s_sort, s_set)
                if s_comb > best_alias_score:
                    best_alias_score = s_comb

            line_score = best_alias_score / 100.0
            if line_score > 0.6:
                p_line = prod.get('product_line') or prod.get('product_family') or prod['official_name']
                evidence_points.append(f"Tootesarja '{p_line}' sarnasusskoor: {int(line_score*100)}%.")

            # 3. Spetsiifiliste parameetrite võrdlus (maht, tilgad, tase, suurus)
            param_matches = 0
            param_checks = 0

            # Maht ml
            prod_ml = prod.get("absorption_ml") or prod.get("ml_capacity")
            if features["volume_ml"] and prod_ml:
                param_checks += 1
                if features["volume_ml"] == prod_ml:
                    param_matches += 1
                    evidence_points.append(f"Täpne mahu kattuvus: {features['volume_ml']} ml.")
                elif abs(features["volume_ml"] - prod_ml) <= 50:
                    param_matches += 0.8
                    evidence_points.append(f"Lähedane mahu kattuvus: {features['volume_ml']} ml vs {prod_ml} ml.")

            # Tase / Number (nt Abena San 4)
            if features["level"] is not None:
                param_checks += 1
                prod_num = re.search(r"\b(\d+)\b", prod["official_name"])
                if prod_num and int(prod_num.group(1)) == features["level"]:
                    param_matches += 1
                    evidence_points.append(f"Tooteseeria tase/number klapib: Tase {features['level']}.")
                else:
                    param_matches -= 0.3

            # Tilgad (nt Molicare 4 tilka)
            prod_drops = prod.get("drops") or prod.get("drop_rating")
            if features["drops"] is not None and prod_drops is not None:
                param_checks += 1
                if features["drops"] == prod_drops:
                    param_matches += 1
                    evidence_points.append(f"Tilgasüsteemi imavusaste klapib: {features['drops']} tilka.")
                else:
                    param_matches -= 0.3

            # Suurus (nt M, L)
            prod_size = prod.get("size")
            if features["size"] and prod_size:
                param_checks += 1
                if features["size"] == prod_size:
                    param_matches += 1
                    evidence_points.append(f"Toote suurus klapib: {features['size']}.")
                else:
                    param_matches -= 0.5

            if param_checks > 0:
                param_score = max(0.0, min(1.0, param_matches / param_checks))
            else:
                param_score = 0.5

            # Kaalutud koguskoor
            if brand_score > 0:
                total_confidence = (brand_score * 0.35) + (line_score * 0.40) + (param_score * 0.25)
            else:
                total_confidence = line_score * 0.5

            candidates.append({
                "official_product": prod["official_name"],
                "full_name": prod.get("full_name", prod["official_name"]),
                "manufacturer": prod["manufacturer"],
                "product_line": prod.get("product_line") or prod.get("product_family"),
                "confidence_score": round(min(1.0, max(0.0, total_confidence)), 3),
                "category_type": prod.get("category_type") or prod.get("product_type", ""),
                "absorption_ml": prod_ml,
                "suggested_iso": prod.get("suggested_iso"),
                "suggested_statutory_name": prod.get("suggested_statutory_name"),
                "evidence_sources": evidence_points + ([prod.get("evidence_notes")] if prod.get("evidence_notes") else []),
                "source_supplier": prod.get("source_supplier"),
                "source_url": prod.get("source_url")
            })

        candidates.sort(key=lambda x: x["confidence_score"], reverse=True)
        best = candidates[0] if candidates else None

        if best and best["confidence_score"] >= 0.70:
            supp_str = f" Allikad: {best.get('source_supplier')}." if best.get("source_supplier") else ""
            reasoning = (
                f"Tarnija nimetus '{raw_name}' tuvastati tootja {best['manufacturer']} tootena "
                f"'{best['official_product']}'. Tuvastatud omadused: {best['category_type']}"
            )
            if best.get("absorption_ml"):
                reasoning += f", imavusmaht {best['absorption_ml']} ml"
            reasoning += f".{supp_str}"

            alternatives = [
                {
                    "official_product": c["official_product"],
                    "confidence_score": c["confidence_score"],
                    "reason": f"Sama tootja alternatiiv ({c.get('absorption_ml', '')} ml)" if c.get("absorption_ml") else "Alternatiivne toode"
                }
                for c in candidates[1:4] if c["confidence_score"] >= 0.40
            ]

            return {
                "identified": True,
                "official_product": best["official_product"],
                "full_name": best["full_name"],
                "manufacturer": best["manufacturer"],
                "confidence_score": best["confidence_score"],
                "suggested_iso": best.get("suggested_iso"),
                "suggested_statutory_name": best.get("suggested_statutory_name"),
                "evidence_sources": [e for e in best["evidence_sources"] if e],
                "alternative_matches": alternatives,
                "reasoning": reasoning,
                "features": features
            }
        else:
            top_score = best["confidence_score"] if best else 0.0
            return {
                "identified": False,
                "official_product": None,
                "full_name": None,
                "manufacturer": None,
                "confidence_score": round(top_score, 3),
                "suggested_iso": best.get("suggested_iso") if best else None,
                "suggested_statutory_name": best.get("suggested_statutory_name") if best else None,
                "evidence_sources": ["Toote tõendid ja tootja tunnused ei andnud piisavat usaldusväärsust."],
                "alternative_matches": [
                    {"official_product": c["official_product"], "confidence_score": c["confidence_score"]}
                    for c in candidates[:3]
                ],
                "reasoning": f"Nimetusest '{raw_name}' ei õnnestunud usaldusväärselt tuvastada tootjat ega ametlikku toodet.",
                "features": features
            }
