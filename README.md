# Valideer — Abivahendite andmete kontroll ja otsustustugi

**Valideer** on spetsialiseeritud otsustustoe- ja valideerimissüsteem sotsiaal- ja tervishoiuvaldkonna abivahendite tehinguridade automaatseks kontrolliks (Excel `.xlsx`/`.xls`, `.csv`) vastavalt **Sotsiaalministeeriumi määrusele nr 74**.

GitHub repositoorium: **https://github.com/evelynlomp/abivahendite-valideerija**

---

## 1. Arhitektuur ja kahetasemeline otsustusmudel

Rakenduse tuvastus- ja valideerimisloogika töötab mitmetasemelise tõeallika mudelina (`ProductMatcher` $\rightarrow$ `Validator`):

```
[Arverida / Esitatud sisend (tootenimi, ISO, rühmanimetus)]
        │
        ├──► 1A. Kinnitatud teadmistebaas (KnowledgeBase: 881 AUTO_LEARN teadmist + 1 031 aliast)
        │
        ├──► 1B. Kahetasemeline variandireegel (VariantClassifier: Tooteperekond + Variant → 413 reeglit)
        │
        ├──► 2.  Tootetuvastuse agent (ProductIdentificationAgent: 3 413 toodet tooteregistris)
        │
        └──► 3.  Sotsiaalministeeriumi määrus nr 74 (MinistryClassifier: 250 ISO koodi + RestrictionEngine)
                        ↓
        [Valideerimise otsus + kahe-leheline Exceli raport (Spetsialisti raport + Tehniline audit)]
```

### Põhiprintsiibid
1. **Kahetasemeline mudel (`FAMILY_VARIANT_RULE`)**:
   - **Tase A — Tooteperekond (`product_family`)**: nt `TENA PANTS MAXI`, `MOLICARE PAD LADY`, `SENI ACTIVE TRIO`, `TENA BED PLUS`.
   - **Tase B — Klassifitseeritav variant (`classifiable_variant`)**: suurus (`XS`–`XXL`), imavus (`ml`), tilkade arv (`1`–`10 tilka`), mõõt (`40x60`, `60x90`, `80x180`), sugu (`MEN`/`LADY`) ja vanusegrupp (`JUNIOR`).
   - Pakenditunnused (`N30`, `30tk`, koodisabad `*09.30.24.95`) eemaldatakse normaliseerimisel, kuid semantilised mõõdud ja mahud säilitatakse.
2. **Määruse sisuliste kitsenduste automaatkontroll (`RestrictionEngine`)**:
   - Kontrollib Sotsiaalministeeriumi määruse nr 74 veergude **C** (*kitsendused*) ja **M** (*abistav kirjeldus*) nõudeid:
     - `09.21.18` (*nahakaitsevahendid*): lubatud ainult tsinkoksiidi baasil tooted.
     - `09.21.06` (*nahapesemisvahendid*): tavalised dušigeelid, šampoonid ja seebid on välistatud.
     - `09.33.30.01` (*niisutatud salvrätid*): alkoholi- ja lõhnavabad rätikud.
     - `18.30.15` (*kaasaskantavad kaldteed*), `04.33.06.01` (*lamatisi ennetavad madratsid*), `18.03.15` (*voodilauad*), `09.33.03` (*vanni- ja dušitoolid*).
3. **Andmeprivaatsus**:
   - Üleslaetavaid tehingufaile töödeldakse ainult sessioonimälus; välistesse pilveteenustesse ega API-desse andmeid ei saadeta.

---

## 2. Kasutajaliides (TEDI / TEHIK Disainisüsteem — Dark Mode)

Rakendus sisaldab kolme töökeskkonda:
1. **Valideerimise töölaud**:
   - Igakuise tehingufaili (`.xlsx`, `.xls`, `.csv`) üleslaadimine või kohene testimine näidisfailiga (`Proovi näidisfailiga`).
   - Automaatne valideerimine, filtreerimine staatuste kaupa, üksikrea inspektori vaade, spetsialisti kinnitused teadmistebaasi ja 2-lehelise Exceli raporti eksport.
2. **Kandidaattoodete töölaud**:
   - Kanooniliste kandidaattoodete (`data/canonical_products.json`) läbivaatus, ISO vastavuse kinnitamine või ümberklassifitseerimine koos otsuste ajalooga.
3. **Registrid ja haldus**:
   - Ülevaade ja otsing: **Tooteregister** (`3 413` toodet), **Riiklik klassifikaator (Määrus nr 74)** (`250` ISO koodi) ja **Õppiv teadmistebaas** (`881` kinnitatud kirjet, `413` variandireeglit).

---

## 3. Projekti kaustastruktuur (Release Candidate)

```
valideer/
├── app.py                           # Peamine Streamlit veebirakendus (3 töölauda)
├── pyproject.toml                   # Projekti konfiguratsioon ja sõltuvused (uv / PEP 621)
├── requirements.txt                 # Tootmissõltuvused (pip)
├── uv.lock                          # Lukustatud sõltuvuste versioonid
├── .python-version                  # Soovituslik Pythoni versioon
├── .gitignore                       # Git välistusreeglid
├── README.md                        # Projekti dokumentatsioon
│
├── .streamlit/
│   └── config.toml                  # Streamliti serveri ja TEDI tumeda teema seadistus
│
├── src/                             # Rakenduse tuumikmoodulid
│   ├── __init__.py
│   ├── normalizer.py                # Nimetuste, mõõtude, ISO koodide ja rühmanimetuste normaliseerija
│   ├── variant_classifier.py        # Kahetasemeline mudel (Tooteperekond + Variant -> ISO)
│   ├── classifier.py                # Määruse nr 74 klassifikaatori mootor (O(1) vahemäluga)
│   ├── knowledge_base.py            # Teadmistebaasi, variandireeglite, aliaste ja auditi SQLite kiht
│   ├── product_agent.py             # Tootetuvastuse agent (täpne alias + kaalutud parameetriotsing)
│   ├── product_registry.py          # Kureeritud tootjate baaskataloog (MANUFACTURER_CATALOGUE)
│   ├── product_registry_db.py       # SQLite tooteregistri liides ja määruse nr 74 ISO tuletusreeglid
│   ├── matcher.py                   # Mitmetasemeline tuvastusmootor (KB -> Variandireegel -> Agent)
│   ├── restriction_engine.py        # Määruse nr 74 Tulp C ja Tulp M kitsenduste reeglimootor
│   ├── validator.py                 # Tehinguridade vastavuskontrolli mootor
│   ├── report.py                    # Kahetasemelise Exceli raporti ja TEDI märgendite generaator
│   ├── tedi_table.py                # TEDI disainisüsteemi HTML-tabelite renderdaja
│   └── canonical_learning.py        # Kandidaattoodete kinnitamise ja õppimise teenus
│
├── data/                            # Püsivad tõeallikad ja näidisandmed
│   ├── valideer.db                  # Ühtne SQLite andmebaas (klassifikaator, register, KB, variandireeglid)
│   ├── canonical_products.json      # Kandidaattoodete töölaua kanooniline kataloog
│   ├── Abivahendite_otsimootor_al.01.10.2026.xlsx # Määruse nr 74 ametlik algtabel
│   └── naidis_sisend_vigadega.xlsx  # Demofail vigaste tehinguridadega testimiseks
│
├── assets/                          # Kasutajaliidese käitusaja stiilid ja graafika
│   ├── tedi-dark.css                # TEDI disainisüsteemi Dark Mode stiilileht
│   ├── valideer-logo-flat.svg       # Rakenduse vektorlogo
│   ├── valideer-favicon-flat.svg    # Vektorfavicon
│   └── valideer_icon.png            # Lehe ikoon
│
├── scripts/                         # Haldusskriptid (pööratav teadmiste import ja rollback)
│   ├── import_auto_learn.py         # AUTO_LEARN teadmiste ja variandireeglite auditeeritud import
│   └── rollback_auto_learn.py       # AUTO_LEARN impordi täielik tagasivõtmine (rollback)
│
└── tests/                           # Automaattestid
    ├── test_valideer.py             # Normaliseerija, agendi, KB, variandireeglite ja valideerija testid
    └── test_canonical_learning.py   # Kandidaattoodete õppimisteenuse ühiktestid
```

---

## 4. Paigaldamine ja käivitamine nullist

Projekt on täielikult iseseisev ega vaja väliseid andmebaasiservereid ega API-võtmeid. Kõik tõeallikad sisalduvad failis `data/valideer.db`.

### Eeldused
- **Python 3.10 – 3.14** (soovituslik Python 3.11 või 3.12)
- **Git**

### Variant A: Standardne `venv` + `pip`
```bash
# 1. Klooni repositoorium
git clone https://github.com/evelynlomp/abivahendite-valideerija.git
cd abivahendite-valideerija

# 2. Loo ja aktiveeri virtuaalkeskkond
python -m venv .venv

# Windows (PowerShell):
.\.venv\Scripts\Activate.ps1
# Linux / macOS:
source .venv/bin/activate

# 3. Paigalda sõltuvused
pip install -r requirements.txt

# 4. Käivita rakendus
streamlit run app.py
```

### Variant B: Kiire käivitus `uv` paketihalduriga
```bash
git clone https://github.com/evelynlomp/abivahendite-valideerija.git
cd abivahendite-valideerija

uv sync
uv run streamlit run app.py
```

Rakendus avaneb brauseris aadressil **http://localhost:8501**.

---

## 5. Automaattestide ja haldusskriptide käivitamine

### Kõigi automaattestide käivitamine
```bash
# Käivitab kõik ühik- ja integratsioonitestid (9 testi: test_valideer.py + test_canonical_learning.py)
python -m unittest discover -s tests -v
```

### Teadmistebaasi `AUTO_LEARN` impordi tagasivõtmine (Rollback)
Kui on vaja `AUTO_LEARN` import (`batch_id`) tagasi võtta:
```bash
# 1. Partii-põhine tagasivõtmine (kustutab ainult konkreetse impordipartii kirjed)
python scripts/rollback_auto_learn.py --mode batch

# 2. Täielik impordieelse SQLite varukoopia taastamine
python scripts/rollback_auto_learn.py --mode backup
```
