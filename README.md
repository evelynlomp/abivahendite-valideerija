# Valideer — Abivahendite andmete kontroll & Õppiv teadmistebaas

Valideer on spetsialiseeritud lahendus sotsiaal- ja tervishoiuvaldkonna abivahendite tehinguridade automaatseks kontrolliks ja vigade tuvastamiseks tuhandete ridadega Exceli failides.

GitHub repositoorium: **https://github.com/evelynlomp/abivahendite-valideerija**

---

## Põhiprintsiibid

1. **1:1 determinism (Üks toode = Täpselt üks ISO kood)**:
   - Iga toode registris vastab eranditult ainult **ühele** ametlikule ISO koodile ja määrusejärgsele nimetusele. Mitmele koodile vastavust ei lubata.
2. **Määruse sisuliste kitsenduste automaatkontroll (RestrictionEngine)**:
   - Sotsiaalministeeriumi määruse nr 74 loetelu veerg **C** (*"Abivahendi täpsustus või abivahendi grupi kitsendus"*) ja veerg **M** (*"Abistav kirjeldus, millise funktsioonipiirangu või terviseprobleemi korral abivahend sobib..."*).
   - Tööriist kontrollib toote füüsikalis-keemilisi omadusi, koostist ja ametlikke välistusi (nt tsinkoksiidi kohustus nahakaitsevahendites, dušigeelide välistus, lävepaku kaldteede välistus, standardse poroloonmadratsi välistus).
   - Kuna arveridadel puuduvad patsiendi meditsiinilised terviseandmed (nt Bradeni skaala punktid, diagnoosid), keskendub süsteem **toote enda reaalsetele omadustele ja spetsifikatsioonile**.
3. **Andmeprivaatsus**:
   - Valideeritavaid Exceli faile ja tehinguridu kettale ega välisserveritesse ei salvestata; töötlemine toimub sessioonimälus.

---

## Peamised funktsionaalsused

1. **Määruse kitsenduste mootor (`src/restriction_engine.py`)**:
   - Kontrollib määruse tehnilisi ja sisulisi piiranguid:
     - `09.21.18` (Nahakaitsevahendid): AINULT tsinkoksiidi baasil tooted. Muud kreemid/õlid blokeeritakse.
     - `09.21.06` (Nahapesemisvahendid): Dušigeelid, šampoonid ja seebid on määrusega välistatud.
     - `18.30.15` (Teisaldatavad kaldteed): Lävepaku kaldteed ei kuulu hüvitamisele.
     - `04.33.06.01` (Lamatiste ennetamise madratsid): Standardsed poroloonmadratsid on välistatud.
     - `18.03.15` (Voodilauad): Öökapid ja voodikapid on välistatud.
     - `09.33.03` (Vanni- ja dušitoolid): Vannitõstukid ja -astmed on välistatud.
     - `04.48.08.02` (Hingamistreeninguseadmed): Üldised treeninguseadmed on välistatud.
     - `09.33.30.01` (Niisutatud rätikud): Alkoholi- ja lõhnavabad tooted.
     - `22.12.12` (Ekraanilugemistarkvara ja skannerid): Tavaprinterid on välistatud.
     - `06.30.03` (Parukad): Juuksepikkus ei tohi ületada 40 cm.

2. **Arukas nimenormaliseerija (`src/normalizer.py`)**:
   - Eemaldab pakendikoodid (`N30`, `14TK`, `10X30`).
   - Eemaldab redundantsed tilga- ja imavussõnad (`4 TILKA` -> säilitab numbri `4`).
   - Puhastab apteegispetsiifilised lisad (`SOODUSTUSEGA`, sulgudes koodid).
   - Tulemus: `MOLICARE PAD 4`, `MOLICARE PAD 4 TILKA`, `MOLICARE PAD LADY 4` ja `MOLICARE PAD 4 N30` koonduvad samale kanoonilisele tootele.

3. **Mitmeastmeline tuvastus ja usaldusskoor (`src/matcher.py`)**:
   - **Aste 1: Teadmistebaas** (kui ametnik on varem seose kinnitanud -> usaldus 0.95–1.0).
   - **Aste 2: Ametlik kataloog (täpne vaste)** -> usaldus 1.0.
   - **Aste 3: RapidFuzz sarnasuse otsing** (Token Sort / Token Set Ratio).

4. **Reeglimootor ja 7 valideerimise staatust (`src/validator.py`)**:
   - ✅ **Vastab**: toode, ISO-kood ja määrusejärgne nimetus klapivad ning vastavad kitsendustele.
   - 🛑 **Ei vasta määruse kitsendusele**: toode rikub määruse veergude C või M tingimust/välistust.
   - ⚠️ **Vale ISO**: toode ja määrusejärgne nimetus klapivad, kuid ISO-kood on vale.
   - ⚠️ **Vale määrusejärgne nimetus**: toode ja ISO klapivad, kuid määrusejärgne nimetus on vale.
   - ❌ **Vale ISO ja määrusejärgne nimetus**: kumbki ei vasta toote ametlikele andmetele.
   - ❓ **Tundmatu toode**: sarnasusskoor alla lävendi (< 50%).
   - 🔍 **Vajab käsitsi kontrolli**: toode on sarnane (50% – 85%), kuid vajab spetsialisti kinnitust.

5. **Õppiv teadmistebaas (`src/knowledge_base.py`)**:
   - SQLite andmebaas (`data/knowledge_base.db`).
   - Salvestab spetsialisti kinnitatud erandid ja õpitud seosed.

6. **Interaktiivne veebiliides (`app.py`)**:
   - Exceli lohistamine (`drag & drop`) või näidisfaili laadimine 1 klikiga.
   - Reaalajas mõõdikud (sh eraldi mõõdik määruse kitsenduste rikkumistele).
   - Filtreeritav ja värvikoodidega tulemuste tabel koos selgitustega.
   - **Spetsialisti ülevaatuse järjekord (Review Queue)**.
   - Valideerimistulemustega rikastatud Exceli allalaadimine.

---

## Käivitamine

Rakendus töötab lokaalselt aadressil:
**http://localhost:8501**

Käsitsi käivitamiseks:
```bash
cd "C:\Users\evely\.gemini\antigravity\scratch\valideer"
.\.venv\Scripts\streamlit run app.py
```

Testide käivitamiseks:
```bash
.\.venv\Scripts\python scripts/test_restrictions.py
.\.venv\Scripts\python scripts/verify_restriction_integration.py
```
