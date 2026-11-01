"""Tuvastus- ja usaldusskoorimootor (Matching Engine).

Töövoog:
1. Normaliseerib toote nimetuse.
2. Teadmistebaasi lookup (kui toode on varem kinnitatud).
3. Kui toode puudub teadmistebaasist -> käivitab TOOTETUVASTUSE AGENDI (Product Identification Agent):
   - Otsib toote tõendeid (evidence)
   - Otsib tootja infot (manufacturer info)
   - Otsib tootekataloogidest
   - Võrdleb omadusi (maht ml, tilgad, tase, suurus)
   - Arvutab usaldusskoori ja esitab arutluskäigu (reasoning)
4. Seob tuvastatud toote Sotsiaalministeeriumi ametliku klassifikaatoriga.
5. Suunab valideerimisse ja spetsialisti ülevaatusse.
"""

from typing import Dict, Any, Optional, List

from src.normalizer import normalize_name
from src.knowledge_base import KnowledgeBase
from src.classifier import MinistryClassifier
from src.product_agent import ProductIdentificationAgent


class ProductMatcher:
    """
    Juhib toote tuvastamist ja sidumist Sotsiaalministeeriumi klassifikaatoriga.
    """

    def __init__(
        self,
        classifier: Optional[MinistryClassifier] = None,
        knowledge_base: Optional[KnowledgeBase] = None,
        review_threshold: float = 0.45,
        catalog: Optional[Any] = None,
        product_agent: Optional[ProductIdentificationAgent] = None,
        **kwargs
    ):
        self.classifier = classifier or catalog
        self.kb = knowledge_base
        self.review_threshold = review_threshold
        self.product_agent = product_agent or ProductIdentificationAgent()

    def match(self, raw_name: str) -> Dict[str, Any]:
        """
        Teostab toote tuvastuse ja klassifitseerimise.
        """
        normalized = normalize_name(raw_name)

        if not normalized:
            return {
                "algne_nimetus": raw_name,
                "normaliseeritud_nimetus": "",
                "in_kb": False,
                "kb_id": None,
                "official_product": None,
                "ametlik_toode": None,
                "iso_kood": None,
                "maarusejargne_nimetus": None,
                "usaldusskoor": 0.0,
                "confidence_score": 0.0,
                "allikas": "Tühi sisend",
                "evidence_sources": [],
                "alternative_matches": [],
                "reasoning": "Sisend oli tühi.",
                "kandidaadid": []
            }

        # 1. SAMM: Otsing Teadmistebaasist (Kinnitatud aliaste otsing)
        if self.kb:
            kb_match = self.kb.lookup(raw_name=raw_name, normalized_name=normalized)
            if kb_match:
                official_prod = kb_match["ametlik_toode"]
                iso_code = kb_match.get("iso_kood")
                statutory_name = kb_match.get("maarusejargne_nimetus")
                manufacturer = None
                category_type = None

                # TÕEALLIKAS: Laadi toote kanoonilised andmed tooteregistrist
                if self.product_agent and hasattr(self.product_agent, "registry_db") and self.product_agent.registry_db:
                    prod_obj = self.product_agent.registry_db.find_exact_alias(official_prod)
                    if prod_obj:
                        iso_code = prod_obj.get("suggested_iso") or iso_code
                        statutory_name = prod_obj.get("suggested_statutory_name") or statutory_name
                        manufacturer = prod_obj.get("manufacturer")
                        category_type = prod_obj.get("category_type")

                # TÕEALLIKAS: Sünkroniseeri ametliku määrusejärgse nimetusega määrusest nr 74
                if self.classifier and iso_code:
                    official_record = self.classifier.get_by_iso(iso_code)
                    if official_record:
                        statutory_name = official_record["maarusejargne_nimetus"]

                return {
                    "algne_nimetus": raw_name,
                    "normaliseeritud_nimetus": normalized,
                    "in_kb": True,
                    "kb_id": kb_match["id"],
                    "official_product": official_prod,
                    "ametlik_toode": official_prod,
                    "manufacturer": manufacturer,
                    "category_type": category_type,
                    "iso_kood": iso_code,
                    "maarusejargne_nimetus": statutory_name,
                    "soovituslik_iso": iso_code,
                    "soovituslik_nimetus": statutory_name,
                    "usaldusskoor": float(kb_match["usaldustase"]),
                    "confidence_score": float(kb_match["usaldustase"]),
                    "kinnituste_arv": kb_match.get("kinnituste_arv", 1),
                    "allikas": "Kinnitatud tootealias",
                    "evidence_sources": [
                        f"Spetsialisti kinnitatud tootealias ({kb_match.get('kinnituste_arv', 1)} korda).",
                        f"Kanooniline toode: '{official_prod}'. Ametlik klassifikatsioon pärineb tõeallikast."
                    ],
                    "alternative_matches": [],
                    "reasoning": f"Kirjapilt '{raw_name}' on kinnitatud alias ametlikule tootele '{official_prod}'. Tõeallika ametlik ISO: '{iso_code}'.",
                    "kandidaadid": []
                }

        # 2. SAMM: TOOTETUVASTUSE AGENT (Product Identification Agent)
        ident_res = self.product_agent.identify_product(raw_name)

        if ident_res["identified"]:
            official_prod = ident_res["official_product"]
            conf_score = ident_res["confidence_score"]
            suggested_iso = ident_res["suggested_iso"]
            suggested_stat = ident_res["suggested_statutory_name"]

            # Kontrollime Sotsiaalministeeriumi klassifikaatorist üle
            if self.classifier and suggested_iso:
                official_rec = self.classifier.get_by_iso(suggested_iso)
                if official_rec:
                    suggested_stat = official_rec["maarusejargne_nimetus"]

            return {
                "algne_nimetus": raw_name,
                "normaliseeritud_nimetus": normalized,
                "in_kb": False,
                "kb_id": None,
                "official_product": official_prod,
                "ametlik_toode": official_prod,
                "full_name": ident_res.get("full_name"),
                "manufacturer": ident_res.get("manufacturer"),
                "soovituslik_iso": suggested_iso,
                "iso_kood": suggested_iso,
                "soovituslik_nimetus": suggested_stat,
                "maarusejargne_nimetus": suggested_stat,
                "usaldusskoor": conf_score,
                "confidence_score": conf_score,
                "allikas": "Tootetuvastuse agent",
                "evidence_sources": ident_res.get("evidence_sources", []),
                "alternative_matches": ident_res.get("alternative_matches", []),
                "reasoning": ident_res.get("reasoning", ""),
                "kandidaadid": [
                    {
                        "iso_kood": suggested_iso,
                        "maarusejargne_nimetus": suggested_stat,
                        "skoor": conf_score
                    }
                ]
            }

        # 3. SAMM: Kui toodet ei õnnestunud tuvastada
        return {
            "algne_nimetus": raw_name,
            "normaliseeritud_nimetus": normalized,
            "in_kb": False,
            "kb_id": None,
            "official_product": None,
            "ametlik_toode": None,
            "soovituslik_iso": ident_res.get("suggested_iso"),
            "soovituslik_nimetus": ident_res.get("suggested_statutory_name"),
            "usaldusskoor": ident_res.get("confidence_score", 0.0),
            "confidence_score": ident_res.get("confidence_score", 0.0),
            "allikas": "Tundmatu toode",
            "evidence_sources": ident_res.get("evidence_sources", []),
            "alternative_matches": ident_res.get("alternative_matches", []),
            "reasoning": ident_res.get("reasoning", "Toote tuvastamine ebaõnnestus."),
            "kandidaadid": []
        }
