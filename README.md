# Valideer — Abivahendite andmete kontroll

Valideer on spetsialiseeritud lahendus sotsiaal- ja tervishoiuvaldkonna abivahendite tehinguridade automaatseks kontrolliks ja vigade tuvastamiseks tuhandete ridadega failides (Excel, CSV) vastavalt **Sotsiaalministeeriumi määrusele nr 74**.

GitHub repositoorium: **https://github.com/evelynlomp/abivahendite-valideerija**

---

## Tõeallika otsustusmudel ja põhiprintsiibid

Rakenduse äriloogika ja soovituste esitus tugineb neljaastmelisele hierarhilisele tõeallika mudelile:

```
[Arverida / Esitatud sisend]
        ↓
[Tuvastatud ametlik toode] (Tooteregister: 4 115 kanoonilist toodet)
        ↓
[Ametlikud andmed tõeallikast] (Sotsiaalkindlustusameti määrus nr 74 alates 01.10.2026: 250 ISO koodi ja täielikud reeglid)
        ↓
[Leitud lahknevus ja soovitus] (Võrdlus tõeallika ja arvel esitatu vahel)
```

1. **Excel ei ole tõeallikas**:
   - Esitatud tootenimi ja koodid on arvel esitatud sisend.
   - Süsteem tuvastab sisendi põhjal **ametliku toote**, mis seotakse **riikliku klassifikaatoriga (Määrus nr 74)**.
   - Ametlik ISO-kood, määrusejärgne nimetus ja piirangud pärinevad **eranditult tõeallikatest**.
   - Süsteem võib kasutaja kinnitustest õppida tootenime kirjutusvariante (aliaseid), kuid **ei õpi ega muuda kunagi riikliku määruse tõde**.

2. **1:1 determinism (Üks toode = Täpselt üks ISO kood)**:
   - Iga toode vastab registris eranditult ainult **ühele** ametlikule ISO koodile ja määrusejärgsele nimetusele.

3. **Määruse sisuliste kitsenduste automaatkontroll (`RestrictionEngine`)**:
   - Kontrollib Sotsiaalministeeriumi määruse nr 74 loetelu veergude **C** (*kitsendused*) ja **M** (*abistav kirjeldus*) välistusi:
     - `09.21.18` (Nahakaitsevahendid): AINULT tsinkoksiidi baasil tooted (mitte-tsink kreemid blokeeritakse).
     - `09.21.06` (Nahapesemisvahendid): Dušigeelid, šampoonid ja seebid on välistatud.
     - `18.30.15` (Teisaldatavad kaldteed): Lävepaku kaldteed on välistatud.
     - `04.33.06.01` (Lamatiste ennetamise madratsid): Standardsed poroloonmadratsid on välistatud.
     - `18.03.15` (Voodilauad): Öökapid ja voodikapid on välistatud.
     - `09.33.03` (Vanni- ja dušitoolid): Vannitõstukid ja -astmed on välistatud.
     - `04.48.08.02` (Hingamistreeninguseadmed): Üldised treeningseadmed on välistatud.
     - `09.33.30.01` (Niisutatud rätikud): Alkoholi- ja lõhnavabad tooted.

4. **Andmeprivaatsus**:
   - Valideeritavaid faile kettale ega välisserveritesse ei salvestata; töötlemine toimub sessioonimälus.

---

## Kasutajaliides & Valideer Disainisüsteem 1.0

Kasutajaliides järgib **Valideer Disainisüsteem 1.0** (Dark Mode, WCAG 2.2 AA) põhimõtteid:
- **Tüpograafia**: `IBM Plex Sans` (tekstid ja pealkirjad) ja `IBM Plex Mono` (koodid, mõõdikud, ISO-numbrid).
- **Semantiline värvipalett**:
  - Roheline (`#2EC4B6` / `#22C55E`): Korras, vastavuses.
  - Merevaik / kollane (`#F59E0B`): Vajab tähelepanu / spetsialisti otsust.
  - Punane (`#EF4444`): Kriitiline probleem / välistatud abivahend.
  - Primaarne aktsent (`#66C7B8`): Nupud, fookus, aktiivsed olekud.
- **Kahetasemeline infoarhitektuur**:
  - **Töölaud**: Faili laadimine, valideerimine, lahendamist vajavate kirjete ülevaade, 2-tasemelise Exceli raporti allalaadimine.
  - **Registrid ja haldus**: Tooteregister (4 115 toodet), Riiklik klassifikaator (Määrus nr 74), Kinnitatud reeglid ja süsteemiinfo.

---

## Projekti failistruktuur

```
valideer/
├── app.py                           # Peamine Streamlit veebirakendus
├── pyproject.toml                   # Projekti seadistus ja sõltuvused (uv)
├── uv.lock                          # Lukustatud sõltuvuste versioonid
├── README.md                        # Projekti dokumentatsioon
│
├── src/                             # Põhirakenduse moodulid
│   ├── classifier.py                # Sotsiaalministeeriumi klassifikaatori haldur (Määrus nr 74)
│   ├── knowledge_base.py            # Kinnitatud reeglite ja aliaste haldus (SQLite)
│   ├── matcher.py                   # Mitmeastmeline toote ja koodi vastavuse tuvastaja
│   ├── normalizer.py                # Teksti, nimetuste ja ISO-koodide normaliseerija
│   ├── product_agent.py             # Toote tuvastamise agent ja argumenteeritud selgitused
│   ├── product_registry.py          # Baaskataloogi konstandid ja tootjate spetsifikatsioonid
│   ├── product_registry_db.py       # Tooteregistri andmebaasikiht (SQLite)
│   ├── report.py                    # Kahetasemelise Exceli raporti genereerija
│   ├── restriction_engine.py        # Määruse nr 74 sisuliste kitsenduste reeglimootor
│   └── validator.py                 # Valideerimise põhireeglimootor (7 staatust)
│
├── data/                            # Püsivad andmefailid ja tõeallikad
│   ├── valideer.db                  # Ühtne SQLite andmebaas (tooteregister, klassifikaator, reeglid)
│   ├── naidis_sisend_vigadega.xlsx  # Demofail vigaste tehinguridadega testimiseks
│   ├── Abivahendite_otsimootor_al.01.10.2026.xlsx # SKA ametlik loetelu ja otsimootori reeglid (tõeallikas)
│   └── Abivahendite_otsimootor_al.01.10.2026.xlsb # SKA ametlik loetelu binaarformaat
│
├── assets/                          # Disainisüsteemi visuaalsed varad
│   ├── valideer-logo-flat.svg       # Ametlik lame vektorlogo
│   ├── valideer-favicon-flat.svg    # Vektorfavicon
│   ├── valideer_icon.png            # PNG ikoon
│   └── icons/                       # 21 semantilist SVG ikooni
│
├── scripts/                         # Haldus-, sünkroonimis- ja auditiskriptid
│   ├── cleanup_registry.py          # Registri duplikaatide puhastamine ja kanooniline liitmine
│   ├── extract_suppliers.py         # Eesti 5 tarnija tootekataloogide sünkroniseerimine
│   ├── audit_volume_ranges.py       # Imavusmahtude vahemike vastavuskontroll
│   ├── audit_ml_registry.py         # Registri ml-mahtude ja ISO koodide audit
│   ├── test_restrictions.py         # Kitsenduste mootori testid
│   └── verify_restriction_integration.py # Kitsenduste integratsioonitestid
│
└── tests/                           # Automaattestid
    └── test_valideer.py             # Agendi, normaliseerimise ja valideerimisahela testid
```

---

## Kahetasemeline Exceli raport

Valideerimise järgselt eksporditav Exceli raport on jaotatud kaheks selgeks leheks:

1. **Spetsialisti raport** (Põhivaade):
   - Sisaldab ainult otsuse tegemiseks vajalikku infot:
     - Arvel esitatud tootenimi ja koodid
     - Valideerimise staatus (Vastab, Vale ISO, Vale määrusejärgne nimetus, Ei vasta määruse kitsendusele jne)
     - Tõeallikast tuvastatud ametlik toode ja ametlik ISO kood
     - Selge tegevussoovitus (nt *"Asendada ISO 09.30.24.16 -> 09.30.24.15"*)
     - Lahknevuse selgitus arusaadavas keeles
2. **Tehniline audit** (Ekspertvaade):
   - Sisaldab täielikku auditijälge:
     - Tuvastamise usaldusskoor (Confidence score)
     - Tuvastusviis (Reegel, Täpne vaste, Mudel)
     - Tõendite allikad (kataloogid, veebiviited)
     - Alternatiivsed kandidaadid
     - Normaliseeritud stringid ja tehniline põhjendus

---

## Paigaldamine ja käivitamine

Projekt on täielikult iseseisev ja ei vaja väliseid andmebaasiserevereid ega API-võtmeid või keskkonnamuutujaid. Kõik vajalikud tõeallikad sisalduvad kaasasolevas SQLite baasis (`data/valideer.db`).

### Nõuded
- Python 3.10 kuni 3.14 (soovituslik: Python 3.11 või 3.12)
- Git

### Variant A: Standardne Python `pip` ja `requirements.txt` (sobib igasse keskkonda ja pilve)
```bash
# 1. Klooni repositoorium
git clone https://github.com/evelynlomp/abivahendite-valideerija.git
cd abivahendite-valideerija

# 2. Loo ja aktiveeri virtuaalkeskkond
python -m venv .venv

# Windows:
.\.venv\Scripts\activate
# Linux / macOS:
source .venv/bin/activate

# 3. Paigalda sõltuvused
pip install -r requirements.txt

# 4. Käivita veebiliides
streamlit run app.py
```

### Variant B: Kiire käivitus `uv` abil
```bash
git clone https://github.com/evelynlomp/abivahendite-valideerija.git
cd abivahendite-valideerija

# Sünkroniseeri sõltuvused ja käivita
uv sync
uv run streamlit run app.py
```

Veebirakendus avaneb aadressil **http://localhost:8501**.

### Testide käivitamine
```bash
# Tuvastamisagendi, normaliseerimise ja ahela testid
python tests/test_valideer.py

# Määruse kitsenduste mootori testid
python scripts/test_restrictions.py
python scripts/verify_restriction_integration.py
```
