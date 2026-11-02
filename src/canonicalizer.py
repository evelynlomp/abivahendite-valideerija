"""
Toodete kanoniseerimise, deduplitseerimise ja tõendite koondamise moodul.

Võtab veebiallikatest (e-poed, hinnakirjad) leitud toormaterjali ja:
1. Tuvastab samad tooted erinevate kirjapiltide, mudelitähiste (miniRITE, R, BTE, CCL, suurused) ja poodide lõikes.
2. Moodustab ühe kanoonilise tooteüksuse (nt 'OTICON INTENT').
3. Säilitab kanoonilise toote juures:
   - Kõik leitud aliasnimed ja variatsioonid
   - Kõik allikad ja e-poodide lingid
   - Tootja ja brändi
   - Toote pildid
   - Kirjeldused ja spetsifikatsioonid (tõendid)
   - Leitud hinnad (täishind, piirhind, omaosalus, hinnavahemik)
4. Hindab ametliku määruse nr 74 ISO vastavust kanoonilisel tasemel.
5. Võimaldab kasutajale kuvada iga toodet täpselt üks kord koos kõigi tõenditega.
"""

import re
from dataclasses import dataclass, field, asdict
from typing import List, Dict, Any, Optional, Tuple, Set


@dataclass
class CanonicalProduct:
    canonical_id: str
    canonical_name: str
    brand: str
    manufacturer: str
    category: str
    aliases: List[str] = field(default_factory=list)
    sources: List[Dict[str, Any]] = field(default_factory=list)
    prices: List[Dict[str, Any]] = field(default_factory=list)
    price_range_str: str = "Täpsustamisel"
    images: List[str] = field(default_factory=list)
    descriptions: List[str] = field(default_factory=list)
    matching_isos: List[Tuple[str, str, str]] = field(default_factory=list)
    confidence: str = "MÄÄRAMATA"
    status_rationale: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class ProductCanonicalizer:
    """Kanoniseerimismootor ja tõendite agregaator."""

    def __init__(self):
        pass

    @staticmethod
    def clean_title(title: str) -> str:
        """Eemaldab HTML leivapuru ja liigsed tühikud."""
        if not title:
            return ""
        if "»" in title:
            title = title.split("»")[0].strip()
        # Eemalda mitmekordsed tühikud
        return re.sub(r"\s+", " ", title).strip()

    def resolve_canonical_identity(self, raw_name: str, brand_hint: str = "") -> Tuple[str, str, str, str]:
        """
        Tuvastab toote kanoonilise nime, brändi, tootja ja üldkategooria.
        Tagastab: (canonical_name, brand, manufacturer, category)
        """
        clean = self.clean_title(raw_name)
        n_up = clean.upper()

        # --- 1. OTICON KUULMISABIVAHENDID ---
        if "OTICON" in n_up or "INTENT" in n_up or "REAL" in n_up or "XCEED" in n_up or "ZEAL" in n_up or "VERIT" in n_up:
            mfg = "Demant A/S (Taani)"
            brand = "Oticon"
            cat = "Kuulmisabivahendid"

            if "CROS" in n_up:
                return "OTICON CROS", brand, mfg, "Kuulmisabivahendid (CROS süsteem)"
            if "INTENT" in n_up:
                return "OTICON INTENT", brand, mfg, cat
            if "REAL" in n_up:
                return "OTICON REAL", brand, mfg, cat
            if "OWN" in n_up:
                return "OTICON OWN", brand, mfg, "Kuulmisabivahendid (kõrvasisesed)"
            if "JET" in n_up:
                return "OTICON JET", brand, mfg, cat
            if "ZEAL" in n_up:
                return "OTICON ZEAL", brand, mfg, cat
            if "VERIT" in n_up:
                return "OTICON VERIT", brand, mfg, cat
            if "XCEED PLAY" in n_up or ("XCEED" in n_up and "PLAY" in n_up):
                return "OTICON XCEED PLAY", brand, mfg, "Kuulmisabivahendid (lapsed / ülisuur võimsus)"
            if "XCEED" in n_up:
                return "OTICON XCEED", brand, mfg, "Kuulmisabivahendid (ülisuur võimsus)"
            if "PLAY" in n_up:
                return "OTICON PLAY", brand, mfg, "Kuulmisabivahendid (lapsed)"
            if "SAFELINE" in n_up:
                return "OTICON SAFELINE KAELAPAEL", brand, mfg, "Kuuldeaparaadi tarvikud"
            if "TV ADAPTER" in n_up:
                return "OTICON TV ADAPTER", brand, mfg, "Kuuldeaparaadi tarvikud"
            if "PROWAX" in n_up:
                return "OTICON PROWAX FILTRID", brand, mfg, "Kuuldeaparaadi hooldustarvikud"
            if "NOWAX" in n_up:
                return "OTICON NOWAX FILTRID", brand, mfg, "Kuuldeaparaadi hooldustarvikud"
            if "WAXSTOP" in n_up:
                return "OTICON WAXSTOP FILTRID", brand, mfg, "Kuuldeaparaadi hooldustarvikud"
            if "O-CAP" in n_up or "T-CAP" in n_up:
                return "OTICON MIKROFONI FILTRID (O-CAP / T-CAP)", brand, mfg, "Kuuldeaparaadi hooldustarvikud"
            if "DOOM" in n_up or "MINIFIT" in n_up:
                return "OTICON MINIFIT DOOMID", brand, mfg, "Kuuldeaparaadi otsakud"
            if "OTSAK" in n_up:
                return "OTICON STANDARDOTSAKUD", brand, mfg, "Kuuldeaparaadi otsakud"

        # --- 2. PATAREID ---
        if "PATAREI" in n_up and any(c in n_up for c in ["10", "13", "312", "675"]):
            return "KUULDEAPARAADI TSINK-ÕHK PATAREID (10/13/312/675)", "Määramata", "Määramata", "Kuulmisabivahendite toiteallikad"

        # --- 3. OTTOBOCK PROTEESILAINERID ---
        if "OTTOBOCK" in n_up or "GALEO" in n_up or "SKEO" in n_up:
            mfg = "Ottobock SE & Co. KGaA (Saksamaa)"
            brand = "Ottobock"
            if "GALEO" in n_up:
                return "OTTOBOCK GALEO", brand, mfg, "Proteesi sisevoodrid (lainerid sääreproteesile)"
            if "SKEO" in n_up:
                # Eristame anatoomilise taseme järgi, kui on märgitud
                if any(w in n_up for w in ["(TF)", " TF", "REIE"]):
                    return "OTTOBOCK SKEO (TF)", brand, mfg, "Proteesi sisevoodrid (lainerid reieproteesile)"
                elif any(w in n_up for w in ["(TT)", " TT", "SÄÄRE"]):
                    return "OTTOBOCK SKEO (TT)", brand, mfg, "Proteesi sisevoodrid (lainerid sääreproteesile)"
                return "OTTOBOCK SKEO", brand, mfg, "Proteesi sisevoodrid (lainerid)"

        # --- 4. ÖSSUR PROTEESILAINERID ---
        if "ÖSSUR" in n_up or "OSSUR" in n_up or "ICEROSS" in n_up:
            mfg = "Össur hf (Island)"
            brand = "Össur"
            if "SEAL-IN X5" in n_up:
                return "ÖSSUR ICEROSS SEAL-IN X5", brand, mfg, "Proteesi sisevoodrid (lainerid)"
            if "SEAL-IN X" in n_up:
                return "ÖSSUR ICEROSS SEAL-IN X", brand, mfg, "Proteesi sisevoodrid (lainerid)"
            if "DERMO" in n_up:
                return "ÖSSUR ICEROSS DERMO", brand, mfg, "Proteesi sisevoodrid (lainerid sääreproteesile)"
            if "COMFORT" in n_up:
                return "ÖSSUR ICEROSS COMFORT", brand, mfg, "Proteesi sisevoodrid (lainerid sääreproteesile)"
            if "TRANSFEMORAL" in n_up:
                return "ÖSSUR ICEROSS TRANSFEMORAL", brand, mfg, "Proteesi sisevoodrid (lainerid reieproteesile)"
            if "UPPER-X" in n_up or "KÄE" in n_up:
                return "ÖSSUR ICEROSS UPPER-X", brand, mfg, "Proteesi sisevoodrid (lainerid ülajäsemeproteesile)"
            return "ÖSSUR ICEROSS", brand, mfg, "Proteesi sisevoodrid (lainerid)"

        # --- 5. JOBST KOMPRESSIOONTOOTED ---
        if "JOBST" in n_up:
            mfg = "Essity Hygiene and Health AB (Rootsi)"
            brand = "JOBST"
            cat = "Ravikompressioontooted"
            if "AMBITION" in n_up or "FORMEN" in n_up:
                return "JOBST FORMEN AMBITION", brand, mfg, cat
            if "ULTRA SHEER" in n_up or "ULTRASHEER" in n_up:
                return "JOBST ULTRA SHEER", brand, mfg, cat
            if "OPAQUE" in n_up:
                return "JOBST OPAQUE", brand, mfg, cat
            return "JOBST RAVIKOMPRESSIOON", brand, mfg, cat

        # --- 6. COMPRITEX KOMPRESSIOONTOOTED ---
        if "COMPRITEX" in n_up:
            mfg = "Vannini Medica S.r.l. (Itaalia)"
            brand = "CompriTex"
            cat = "Ravikompressioontooted"
            if "TROMBI" in n_up:
                return "COMPRITEX TROMBIENNETUS", brand, mfg, cat
            return "COMPRITEX MEDITSIINILISED KOMPRESSIOONSUKAD", brand, mfg, cat

        # --- 7. RESMED (Tervisekassa uneapnoe meditsiiniseadmed) ---
        if "RESMED" in n_up or "AIRFIT" in n_up or "AIRMINI" in n_up or "AIR10" in n_up or "AIR11" in n_up:
            mfg = "ResMed Inc. (USA/Austraalia)"
            brand = "ResMed"
            cat = "Uneapnoe seadmed ja tarvikud (Tervisekassa)"
            if "AIRFIT F20" in n_up:
                return "RESMED AIRFIT F20 TÄISNÄOMASK", brand, mfg, cat
            if "AIRFIT F30" in n_up:
                return "RESMED AIRFIT F30 TÄISNÄOMASK", brand, mfg, cat
            if "AIRMINI" in n_up:
                return "RESMED AIRMINI AUTO-CPAP SEADE JA TARVIKUD", brand, mfg, cat
            if "AIR10" in n_up or "S9" in n_up:
                return "RESMED AIR10 STANDARD- JA HÜPOALLERGEENSED FILTRID", brand, mfg, cat
            if "AIR11" in n_up:
                return "RESMED AIR11 STANDARD- JA HÜPOALLERGEENSED FILTRID", brand, mfg, cat
            if "MÄLUKAART" in n_up or "MALUKAART" in n_up:
                return "RESMED AIR SD-MÄLUKAART", brand, mfg, cat
            return "RESMED UNEAPNOE SEADMED JA TARVIKUD", brand, mfg, cat

        # --- 8. PÜRDOX (Tervisekassa tarvikud) ---
        if "PÜRDOX" in n_up or "PURDOUX" in n_up:
            mfg = "Pürdoux Health"
            brand = "Pürdoux"
            cat = "CPAP hooldustarvikud (Tervisekassa)"
            if "SEEP" in n_up:
                return "PÜRDOX CPAP MASKI JA VOOLIKU SEEP", brand, mfg, cat
            if "LAPID" in n_up or "PUHASTUSLAPID" in n_up:
                return "PÜRDOX CPAP PUHASTUSLAPID", brand, mfg, cat
            if "HARI" in n_up or "VOOLIKUHARI" in n_up:
                return "PÜRDOX CPAP VOOLIKUHARI", brand, mfg, cat
            return "PÜRDOX CPAP HOOLDUSTARVIKUD", brand, mfg, cat

        # --- 9. HYDRO-TRACH ---
        if "HYDRO-TRACH" in n_up or "TRAHEANIISUTI" in n_up or "TRAHHEANIISUTI" in n_up:
            return "HYDRO-TRACH T MK II TRAHHEANIISUTI", "Hydro-Trach", "Intersurgical Ltd (Ühendkuningriik)", "Hingamisteede filtrid ja niisutid"

        # --- 10. ORTOOSID (DJO / DonJoy / Aircast / Ortoosikeskus) ---
        mfg_djo = "DJO, LLC / Enovis (USA)"
        if "WALKER" in n_up:
            return "AIRCAST WALKER HÜPPELIIGESE ORTOOS-SAABAS", "Aircast", mfg_djo, "Hüppeliigese- ja jalaortoosid"
        if "DRYTEX" in n_up:
            return "DONJOY DRYTEX PÕLVEORTOOS", "DonJoy", mfg_djo, "Põlveortoosid"
        if "X-ACT" in n_up:
            return "DONJOY X-ACT PIKENDATAV PÕLVEORTOOS", "DonJoy", mfg_djo, "Põlveortoosid"
        if "GENUFORCE" in n_up:
            return "DONJOY GENUFORCE PÕLVEORTOOS", "DonJoy", mfg_djo, "Põlveortoosid"
        if "REACTION" in n_up:
            return "DONJOY REACTION PÕLVEORTOOS", "DonJoy", mfg_djo, "Põlveortoosid"
        if "LEGEND" in n_up:
            return "DONJOY LEGEND PÕLVEORTOOS", "DonJoy", mfg_djo, "Põlveortoosid"
        if "TRU-PULL" in n_up:
            return "DONJOY TRU-PULL LITE PÕLVEORTOOS", "DonJoy", mfg_djo, "Põlveortoosid"
        if "ACTISTRAP" in n_up:
            return "DONJOY ACTISTRAP SELJAORTOOS", "DonJoy", mfg_djo, "Seljaortoosid"
        if "CONFORSTRAP" in n_up:
            return "DONJOY CONFORSTRAP SELJAORTOOS", "DonJoy", mfg_djo, "Seljaortoosid"
        if "IMMOSTRAP" in n_up:
            return "DONJOY IMMOSTRAP SELJAORTOOS", "DonJoy", mfg_djo, "Seljaortoosid"
        if "TLSO" in n_up:
            return "DJO TLSO LÜLISAMBAORTOOS", "DJO", mfg_djo, "Lülisamba- ja seljaortoosid"
        if "FOOT-UP" in n_up:
            return "ÖSSUR FOOT-UP RIPPUVA LABAJALA ORTOOS", "Össur", "Össur hf (Island)", "Jala- ja hüppeliigeseortoosid"
        if "COTEX" in n_up:
            return "COTEX PATELLA PÕLVEORTOOS", "Määramata", "Määramata", "Põlveortoosid"
        if "QUICKFIT" in n_up:
            return "QUICKFIT LIIGENDITEGA PÕLVEORTOOS", "Määramata", "Määramata", "Põlveortoosid"
        if "POL'AX" in n_up:
            return "POL'AX PÖIDLAORTOOS", "Määramata", "Määramata", "Käe- ja randmeortoosid"
        if "ERGOFORM" in n_up:
            return "ERGOFORM PÖIDLAORTOOS", "Määramata", "Määramata", "Käe- ja randmeortoosid"
        if "MANEX OPUS" in n_up:
            return "MANEX OPUS RANDMEORTOOS", "Määramata", "Määramata", "Käe- ja randmeortoosid"

        # --- 11. HOOLDUS- JA LIIKUMISABIVAHENDID ---
        if "BODYGUARD" in n_up:
            return "BODYGUARD IMAV ALUSPESU", "Scabo", "Scabo Medical", "Imavad tooted ja pidamatuspesu"
        if "FARGO" in n_up:
            return "RULAATOR FARGO", "Fargo", "Meyra / MDH", "Liikumisabivahendid (rulaatorid)"
        if "JAGUAR" in n_up:
            return "RULAATOR JAGUAR", "Jaguar", "Määramata", "Liikumisabivahendid (rulaatorid)"
        if "TIMO" in n_up:
            return "PESEMISRAAM TIMO", "Timo", "Määramata", "Hügieeni- ja pesemisabivahendid"
        if "JÄÄOTSIK" in n_up or "JAAOTSIK" in n_up:
            return "KARGU JA KEPI JÄÄOTSIKUD", "Kid-Man", "Määramata", "Liikumisabivahendite lisatarvikud"
        if "GEHWOL" in n_up:
            return "GEHWOL SILIKOONIST VARBAKAITSED", "Gehwol", "Eduard Gerlach GmbH (Saksamaa)", "Jalahoolduse jaemüügitooted"
        if "MOLICARE" in n_up:
            return "MOLICARE SKIN HOOLDUSVAHT", "Molicare", "Paul Hartmann AG (Saksamaa)", "Nahahooldustooted"
        if "EVERCARE" in n_up:
            return "EVERCARE KAITSEMASKID", "Evercare", "OneMed Group", "Isikukaitsevahendid"
        if "FRESCO" in n_up:
            return "FRESCO GEELPADJAD", "Fresco", "Määramata", "Rõhu ümberjaotuse geelpadjad"
        if "SIRM" in n_up:
            return "RATASTEL RUUMISIRM", "Määramata", "Määramata", "Kliiniku ja hooldekodu sisustus"
        if "RAVIMIPOOLITAJA" in n_up:
            return "RAVIMIPOOLITAJA/PURUSTAJA 3IN1", "Määramata", "Määramata", "Igapäevaelu abivahendid"

        # Vaikimisi
        return clean.upper(), brand_hint or "Määramata", "Määramata", "Muu kategooria"

    def evaluate_canonical_iso(self, canonical_name: str, category: str) -> Tuple[List[Tuple[str, str, str]], str, str]:
        """
        Hindab kanoonilise toote ametlikku ISO vastavust Sotsiaalkaitseministri määruse nr 74 alusel.
        Tagastab: (matching_isos, confidence, status_rationale)
        """
        c_up = canonical_name.upper()
        matching_isos = []

        # 1. Kuulmisabivahendid
        if "OTICON CROS" in c_up:
            matching_isos.append((
                "22.06.15.05",
                "teise kõrva heli ülekande süsteemid (CROS)",
                "Standardne CROS heliülekandesüsteem ühepoolse kurtuse korral"
            ))
            return matching_isos, "KÕRGE KINDLUS", "Otsene 1:1 vaste määruse nr 74 koodile 22.06.15.05."

        if any(w in c_up for w in ["OTICON INTENT", "OTICON REAL", "OTICON ZEAL", "OTICON VERIT", "OTICON JET", "OTICON XCEED"]):
            matching_isos.append((
                "22.06.15.01",
                "kõrvatagused kuulmisabivahendid - aktiivsusgrupp I",
                "Baastaseme digitaalne kõrvatagune kuuldeaparaat"
            ))
            matching_isos.append((
                "22.06.15.02",
                "kõrvatagused kuulmisabivahendid - aktiivsusgrupp II",
                "Kõrgema taseme digitaalne kõrvatagune kuuldeaparaat"
            ))
            return matching_isos, "ÜLEVAATUST VAJAV (MITU ISO-D)", "Kuulub määrusesse nr 74, kuid konkreetne ISO sõltub patsiendi arstlikust aktiivsusgrupist (I vs II)."

        if "OTICON OWN" in c_up:
            matching_isos.append(("22.06.12.01", "kõrvasisesed kuulmisabivahendid - aktiivsusgrupp I", "Kõrvasisene aparaat, aktiivsusgrupp I"))
            matching_isos.append(("22.06.12.02", "kõrvasisesed kuulmisabivahendid - aktiivsusgrupp II", "Kõrvasisene aparaat, aktiivsusgrupp II"))
            return matching_isos, "ÜLEVAATUST VAJAV (MITU ISO-D)", "Kohandatav kõrvasisene (ITE/ITC/CIC) mudel, ISO sõltub aktiivsusgrupist I vs II."

        if "OTICON PLAY" in c_up or "OTICON XCEED PLAY" in c_up:
            matching_isos.append(("22.06.15.03", "kõrvatagused kuulmisabivahendid - lapsed", "Spetsiaalne laste kõrvatagune kuulmisabivahend"))
            return matching_isos, "KÕRGE KINDLUS", "Lastele mõeldud mudel, otsene vaste määruse koodile 22.06.15.03."

        # 2. Proteesilainerid
        if "OTTOBOCK GALEO" in c_up:
            matching_isos.append(("06.24.41.07", "proteesi sisevoodrid (lainerid) sääreproteesidele", "Transtibiaalsed (TT) silikoonlainerid (6Y92, 6Y93, 6Y95)"))
            return matching_isos, "KÕRGE KINDLUS", "Kõik Galeo mudelid on säärelainerid (TT), otsene vaste koodile 06.24.41.07."

        if "OTTOBOCK SKEO" in c_up:
            if "(TF)" in c_up:
                matching_isos.append(("06.24.41.08", "proteesi sisevoodrid (lainerid) põlve- ja reieproteesidele", "Reie lainer (6Y80, 6Y85, 6Y87, 6Y88, 6Y110)"))
                return matching_isos, "KÕRGE KINDLUS", "Otsene vaste reielaineri koodile 06.24.41.08."
            elif "(TT)" in c_up:
                matching_isos.append(("06.24.41.07", "proteesi sisevoodrid (lainerid) sääreproteesidele", "Sääre lainer (6Y75)"))
                return matching_isos, "KÕRGE KINDLUS", "Otsene vaste säärelaineri koodile 06.24.41.07."
            else:
                matching_isos.append(("06.24.41.07", "proteesi sisevoodrid (lainerid) sääreproteesidele", "Skeo TT mudelid"))
                matching_isos.append(("06.24.41.08", "proteesi sisevoodrid (lainerid) põlve- ja reieproteesidele", "Skeo TF mudelid"))
                return matching_isos, "KÕRGE KINDLUS", "Skeo sarjas on nii sääre- kui reielainerid, ISO valitakse mudelikoodi (TT vs TF) järgi."

        if "ÖSSUR ICEROSS" in c_up:
            if "UPPER-X" in c_up:
                matching_isos.append(("06.18.00.02", "proteesi sisevoodrid (lainerid) ülajäsemeproteesile", "Käeproteesi lainer"))
                return matching_isos, "KÕRGE KINDLUS", "Otsene vaste ülajäsemelaineri koodile 06.18.00.02."
            if "TRANSFEMORAL" in c_up:
                matching_isos.append(("06.24.41.08", "proteesi sisevoodrid (lainerid) põlve- ja reieproteesidele", "Reielainer (TF)"))
                return matching_isos, "KÕRGE KINDLUS", "Otsene vaste reielaineri koodile 06.24.41.08."
            if "DERMO" in c_up or "COMFORT" in c_up:
                matching_isos.append(("06.24.41.07", "proteesi sisevoodrid (lainerid) sääreproteesidele", "Säärelainer (TT)"))
                return matching_isos, "KÕRGE KINDLUS", "Otsene vaste säärelaineri koodile 06.24.41.07."
            if "SEAL-IN X" in c_up or "SEAL-IN X5" in c_up:
                matching_isos.append(("06.24.41.07", "proteesi sisevoodrid (lainerid) sääreproteesidele", "TT mudelid"))
                matching_isos.append(("06.24.41.08", "proteesi sisevoodrid (lainerid) põlve- ja reieproteesidele", "TF mudelid"))
                return matching_isos, "KÕRGE KINDLUS", "Seal-in X seeria katab nii sääre (TT) kui reie (TF) amputatsiooni."

        # 3. Tervisekassa seadmed
        if any(w in c_up for w in ["RESMED", "PÜRDOX", "PURDOUX", "HYDRO-TRACH", "FRESCO"]):
            matching_isos.append(("TERVISEKASSA", "Tervisekassa meditsiiniseadmete loetelu (CPAP/hingamisteraapia)", "Kompenseerib Eesti Tervisekassa, mitte SKA"))
            return matching_isos, "TERVISEKASSA MEDITSIINISEADE", "Kuulub Tervisekassa, mitte Sotsiaalkindlustusameti hüvitussüsteemi."

        # 4. Liikumisabivahendid
        if "RULAATOR FARGO" in c_up or "RULAATOR JAGUAR" in c_up:
            matching_isos.append(("12.06.06", "neljarattalised käimistoolid / rulaatorid", "Standardne rulaator"))
            return matching_isos, "KÕRGE KINDLUS", "Otsene vaste määruse nr 74 rulaatorite koodile 12.06.06."

        if "TIMO" in c_up:
            matching_isos.append(("09.33.12", "vanni-, duši- ja mähkimislauad", "Hüdrauliline pesemisraam"))
            return matching_isos, "KÕRGE KINDLUS", "Vaste hügieeni pesemisraamide koodile 09.33.12."

        # 5. Määrusevälised ortoosid ja kompressioontooted (Tervisekassa pädevus)
        if any(w in c_up for w in ["JOBST", "COMPRITEX", "WALKER", "DRYTEX", "X-ACT", "GENUFORCE", "ACTISTRAP", "IMMOSTRAP", "FOOT-UP", "TLSO"]):
            matching_isos.append(("TERVISEKASSA / MEDITSIINISEADE", "Ortoosid ja ravisukad (Tervisekassa loetelu)", "Põhiortoose ja kompressioontooteid hüvitab Eestis Tervisekassa"))
            return matching_isos, "TERVISEKASSA MEDITSIINISEADE", "SKA määrus nr 74 ei sisalda standardseid liigeseortoose ega ravisukki (hüvitatakse Tervisekassa kaudu)."

        # 6. Jaekaubad ja hooldustarvikud
        return [], "MÄÄRUSEVÄLINE / JAEKAUP", "Ei kuulu riiklikult hüvitatavate abivahendite loetellu (jaemüügikaup, tarvik või kliiniku inventar)."

    def process_raw_items(self, raw_items: List[Dict[str, Any]]) -> List[CanonicalProduct]:
        """
        Kogub toormaterjali kirjed, rühmitab need kanoonilisteks toodeteks ning
        seob juurde kõik aliased, allikad, pildid, hinnad ja tõendid.
        """
        grouped = {}

        for item in raw_items:
            raw_name = item.get("raw_name") or item.get("official_product_name") or ""
            brand_hint = item.get("brand") or item.get("brand_hint") or ""
            mfg_hint = item.get("manufacturer") or item.get("mfg_hint") or ""
            source_url = item.get("source") or item.get("source_url") or ""
            source_name = item.get("source_name") or item.get("source_supplier") or ""
            img_url = item.get("image") or item.get("image_url") or ""
            price_val = item.get("price")
            desc = item.get("description") or ""

            c_name, c_brand, c_mfg, c_cat = self.resolve_canonical_identity(raw_name, brand_hint)
            c_id = "CP-" + re.sub(r"[^A-Z0-9]+", "-", c_name.upper()).strip("-")

            if c_id not in grouped:
                iso_matches, conf, rationale = self.evaluate_canonical_iso(c_name, c_cat)
                grouped[c_id] = CanonicalProduct(
                    canonical_id=c_id,
                    canonical_name=c_name,
                    brand=c_brand if c_brand != "Määramata" else (brand_hint or "Määramata"),
                    manufacturer=c_mfg if c_mfg != "Määramata" else (mfg_hint or "Määramata"),
                    category=c_cat,
                    aliases=[],
                    sources=[],
                    prices=[],
                    price_range_str="Täpsustamisel",
                    images=[],
                    descriptions=[],
                    matching_isos=iso_matches,
                    confidence=conf,
                    status_rationale=rationale
                )

            cp = grouped[c_id]

            # 1. Aliased (toore nime lisamine)
            clean_raw = self.clean_title(raw_name)
            if clean_raw and clean_raw not in cp.aliases:
                cp.aliases.append(clean_raw)

            # 2. Allikad
            if source_url and not any(s["url"] == source_url for s in cp.sources):
                cp.sources.append({
                    "source_name": source_name,
                    "url": source_url
                })

            # 3. Hinnad
            if price_val:
                cp.prices.append({
                    "price": price_val,
                    "source": source_name
                })

            # 4. Pildid
            if img_url and img_url not in cp.images:
                cp.images.append(img_url)

            # 5. Kirjeldused
            if desc and desc not in cp.descriptions:
                cp.descriptions.append(desc)

        # Arvuta hinnavahemikud ja sorteeri aliased
        canonical_list = list(grouped.values())
        for cp in canonical_list:
            cp.aliases.sort()
            if cp.prices:
                num_prices = []
                for p in cp.prices:
                    val = p.get("price")
                    if isinstance(val, (int, float)):
                        num_prices.append(val)
                    elif isinstance(val, str):
                        # Puhasta numbriline osa
                        m = re.search(r"(\d+[\.,]?\d*)", val)
                        if m:
                            try:
                                num_prices.append(float(m.group(1).replace(",", ".")))
                            except ValueError:
                                pass
                if num_prices:
                    min_p, max_p = min(num_prices), max(num_prices)
                    if min_p == max_p:
                        cp.price_range_str = f"{min_p:.2f} €"
                    else:
                        cp.price_range_str = f"{min_p:.2f} – {max_p:.2f} €"
            elif "400.00" in cp.canonical_name or "OTTOBOCK" in cp.canonical_name or "ÖSSUR" in cp.canonical_name:
                cp.price_range_str = "400.00 € (piirhind: 360.00 €)"

        return canonical_list
