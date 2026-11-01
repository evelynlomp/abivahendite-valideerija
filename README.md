# Valideer — Abivahendite andmete kontroll & õppiv teadmistebaas

Valideer on spetsialiseeritud lahendus sotsiaal- ja tervishoiuvaldkonna abivahendite tehinguridade automaatseks kontrolliks ja vigade tuvastamiseks tuhandete ridadega Exceli failides.

## Peamised funktsionaalsused

1. **Arukas nimenormaliseerija (`src/normalizer.py`)**:
   - Eemaldab pakendikoodid (`N30`, `14TK`, `10X30`).
   - Eemaldab redundantsed tilga- ja imavussõnad (`4 TILKA` -> säilitab numbri `4`).
   - Puhastab apteegispetsiifilised lisad (`SOODUSTUSEGA`, sulgudes koodid).
   - Tulemus: `MOLICARE PAD 4`, `MOLICARE PAD 4 TILKA`, `MOLICARE PAD LADY 4` ja `MOLICARE PAD 4 N30` koonduvad samale kanoonilisele tootele.

2. **Mitmeastmeline tuvastus ja usaldusskoor (`src/matcher.py`)**:
   - **Aste 1: Teadmistebaas** (kui ametnik on varem seose kinnitanud -> usaldus 0.95-1.0).
   - **Aste 2: Ametlik kataloog (täpne vaste)** -> usaldus 1.0.
   - **Aste 3: RapidFuzz sarnasuse otsing** (Token Sort / Token Set Ratio).

3. **Reeglimootor ja 6 valideerimise staatust (`src/validator.py`)**:
   - ✅ **Vastab**: toode, ISO-kood ja määrusejärgne nimetus on ametliku loeteluga kooskõlas.
   - ⚠️ **Vale ISO**: toode ja määrusejärgne nimetus klapivad, kuid ISO-kood on vale.
   - ⚠️ **Vale määrusejärgne nimetus**: toode ja ISO klapivad, kuid määrusejärgne nimetus on vale.
   - ❌ **Vale ISO ja määrusejärgne nimetus**: kumbki ei vasta tuvastatud toote ametlikele andmetele.
   - ❓ **Tundmatu toode**: sarnasusskoor alla lävendi (< 50%).
   - 🔍 **Vajab käsitsi kontrolli**: toode on sarnane (50% - 85%), kuid vajab ametniku kinnitust.

4. **Õppiv teadmistebaas (`src/knowledge_base.py`)**:
   - SQLite andmebaas (`data/knowledge_base.db`).
   - Säilitab: `algne_nimetus`, `normaliseeritud_nimetus`, `ametlik_toode`, `iso_kood`, `maarusejargne_nimetus`, `kinnituste_arv`, `usaldustase`, `viimane_valideerimine`.
   - Iga kinnitusega suureneb usaldustase asümptootiliselt: $1.0 - \frac{0.15}{\text{kinnituste\_arv}}$.
   - **Privaatsusreegel:** Töödeldud Exceli ridu kettale ei salvestata, säilitatakse ainult kinnitatud seosed.

5. **Interaktiivne veebiliides (`app.py`)**:
   - Exceli lohistamine (`drag & drop`) või näidisfaili laadimine 1 klikiga.
   - Reaalajas mõõdikud ja graafikud.
   - Filtreeritav ja värvikoodidega tulemuste tabel.
   - **Ametniku ülevaatuse järjekord (Review Queue)**: võimalus valida ja kinnitada tundmatuid või kahtlasi ridu, mis uuendab koheselt teadmistebaasi.
   - Tulemustega rikastatud Exceli allalaadimine.

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
.\.venv\Scripts\python tests\test_valideer.py
```
