import json

with open("data/scanned_candidates_report.json", "r", encoding="utf-8") as f:
    d = json.load(f)

s = d["summary"]
c = d["by_confidence"]

lines = []
lines.append("# Tootekataloogi laiendamise vahearuanne (Avalike allikate analüüs)")
lines.append("\n> [!IMPORTANT]")
lines.append("> **Käesolev raport on koostatud enne andmebaasi muudatuste tegemist.** Ühtegi toodet ei ole tooteregistrisse automaatselt lisatud ega klassifikaatoreid muudetud. Avalikud veebiallikad ei ole õiguslikud tõeallikad ning need ei tohi muuta ISO koode, määrusejärgseid nimetusi ega sotsiaalkaitseministri määruse nr 74 piiranguid.")
lines.append("")

lines.append("## 1. Koondstatistika ja ülevaade\n")
lines.append("| Näitaja | Väärtus | Selgitus |")
lines.append("| :--- | :--- | :--- |")
lines.append(f"| **Analüüsitud unikaalseid tooteid** | **{s['total_analyzed']}** | Tuvastatud 5 avalikust veebiallikast pärast esmast deduplitseerimist |")
lines.append(f"| **Uusi tootekandidaate kokku** | **{s['new_candidates_count']}** | Tooteid, mis ei leidu hetkel tooteregistris (4 115 toodet) |")
lines.append(f"| ├─ **Kõrge kindlusega kandidaadid** | **{s['high_confidence_count']}** | Selge 1:1 vastavus määruse nr 74 konkreetsele ISO koodile |")
lines.append(f"| ├─ **Ülevaatust vajavad (Mitu ISO-d)** | **{s['multi_iso_review_count']}** | Toode kuulub määruse alla, kuid sobib mitmele ISO koodile (laps vs täiskasvanu, aktiivsusgrupp I vs II) |")
lines.append(f"| └─ **Madala kindlusega kandidaadid** | **{s['low_confidence_count']}** | Tervisekassa meditsiiniseadmed ({s['tervisekassa_count']}) või määruse-välised jaekaubad ({s['non_ska_retail_count']}) |")
lines.append(f"| **Uusi tootjaid avastatud** | **{s['new_manufacturers_count']}** | Tuvastatud tootjatehaste ja korporatsioonide nimed |")
lines.append(f"| **Uusi kaubamärke/brände** | **{s['new_brands_count']}** | Tootesarjad ja brändinimed |")
lines.append(f"| **Võimalikke duplikaate** | **{s['duplicates_count']}** | Tooted, mis on registris juba 100% nime vastega olemas |")
lines.append(f"| **Võimalikke aliasnimesid** | **{s['aliases_count']}** | Sarnasus olemasolevate kirjetega >85% (soovitatav lisada aliastena) |")
lines.append(f"| **Käsitsi kontrolli vajavaid kirjeid** | **{s['manual_review_total']}** | Mitme ISO-ga tooted + Tervisekassa seadmed + loetelu-välised kaubad |")
lines.append("")

lines.append("## 2. Uued tootjad ja brändid\n")
lines.append("### Uued tootjad (10 tk)")
for m in s["new_manufacturers"]:
    lines.append(f"- **{m}**")
lines.append("\n### Uued kaubamärgid ja brändid (12 tk)")
for b in s["new_brands"]:
    lines.append(f"- **{b}**")
lines.append("")

lines.append("## 3. Ülevaatust vajavad kandidaadid (Mitu võimalikku ISO-d)\n")
lines.append("> [!WARNING]")
lines.append("> Vastavalt juhisele ei ole nendele toodetele tehtud automaatset ISO valikut. Klassifikatsioon sõltub patsiendi vanusest (täiskasvanu vs laps) ja arsti poolt määratud aktiivsusgrupist (I vs II).\n")
lines.append("| Tootenimi | Tootja | Kaubamärk | Allikas | Võimalikud ISO klassid | Põhjendus ja alternatiivid |")
lines.append("| :--- | :--- | :--- | :--- | :--- | :--- |")
for it in c["ÜLEVAATUST VAJAV (MITU ISO-D)"]:
    isos = "<br>".join([f"`{x[0]}`: {x[1]}" for x in it["matching_isos"]])
    lines.append(f"| **{it['raw_name']}** | {it['manufacturer']} | {it['brand']} | [{it['source_name']}]({it['source']}) | {isos} | {it['status_desc']} |")
lines.append("")

lines.append("## 4. Kõrge kindlusega tootekandidaadid (71 tk)\n")
lines.append("> [!NOTE]")
lines.append("> Need tooted omavad selget 1:1 vastavust sotsiaalkaitseministri määruse nr 74 konkreetse ISO koodiga.\n")
lines.append("| Tootenimi | Tootja | Allikas | Kategooria | Hinnanguline ISO | Määrusejärgne nimetus | Põhjendus |")
lines.append("| :--- | :--- | :--- | :--- | :--- | :--- | :--- |")
for it in c["KÕRGE KINDLUS"]:
    iso_k = it["matching_isos"][0][0]
    iso_n = it["matching_isos"][0][1]
    lines.append(f"| **{it['raw_name']}** | {it['manufacturer']} | [{it['source_name']}]({it['source']}) | {it['category']} | `{iso_k}` | {iso_n} | {it['matching_isos'][0][2]} |")
lines.append("")

lines.append("## 5. Madala kindlusega kandidaadid (51 tk)\n")
lines.append("### 5.1. Tervisekassa hüvitatavad meditsiiniseadmed (22 tk)\n")
lines.append("> [!CAUTION]")
lines.append("> **Ei kuulu SKA määruse nr 74 loetellu!** Allikas `meditsiiniseadmed.ee` pakub uneapnoe CPAP seadmeid, maske ja trahheostoomifiltreid, mida hüvitab Eestis Tervisekassa (ravikindlustuse seaduse alusel), mitte Sotsiaalkindlustusamet. Neid ei tohiks lisada SKA valideerimise põhikataloogi, välja arvatud juhul, kui soovitakse eraldi Tervisekassa seadmete registrit.\n")
lines.append("| Tootenimi | Tootja | Bränd | Allikas | Rahastav asutus | Staatus |")
lines.append("| :--- | :--- | :--- | :--- | :--- | :--- |")
for it in c["MADAL KINDLUS (TERVISEKASSA)"]:
    lines.append(f"| **{it['raw_name']}** | {it['manufacturer']} | {it['brand']} | [{it['source_name']}]({it['source']}) | **Eesti Tervisekassa** | Ei vasta SKA määrusele nr 74 |")
lines.append("")

lines.append("### 5.2. Määruse-välised jaekaubad ja hooldusvahendid (29 tk)\n")
lines.append("> [!NOTE]")
lines.append("> Apteegi jaemüügitooted, kosmeetika, desinfitseerimisvahendid, kliiniku sisustus ja mittemeditsiinilised lisad, mis ei ole riikliku soodustusega abivahendid.\n")
lines.append("| Tootenimi | Tootja / Allikas | Esialgne kategooria | Põhjus, miks ISO puudub |")
lines.append("| :--- | :--- | :--- | :--- |")
for it in c["MADAL KINDLUS"]:
    lines.append(f"| **{it['raw_name']}** | {it['source_name']} | {it['category']} | {it['status_desc']} |")
lines.append("")

lines.append("## 6. Duplikaadid ja võimalikud aliased\n")
lines.append("### Duplikaadid olemasolevas registris (1 tk)")
lines.append("| Skaneeritud toode | Olemasolev toode registris | Registri ID | Hinnang |")
lines.append("| :--- | :--- | :--- | :--- |")
for it in c["DUPLIKAAT"]:
    lines.append(f"| **{it['raw_name']}** | {it['status_desc']} | - | 100% nime kattuvus |")
lines.append("")

lines.append("### Võimalikud aliasnimed (3 tk)")
lines.append("| Skaneeritud toode | Sarnane toode registris | Sarnasuse määr | Soovitus |")
lines.append("| :--- | :--- | :--- | :--- |")
for it in c["VÕIMALIK ALIAS"]:
    lines.append(f"| **{it['raw_name']}** | {it['best_candidate'][1]} (ID: {it['best_candidate'][0]}) | {it['best_ratio']:.1f}% | Lisada olemasolevale tootele täiendava aliasena |")
lines.append("")

lines.append("## 7. Soovituslikud tegevussammud enne importi\n")
lines.append("1. **Kinnitada Kõrge kindlusega tooted (71 tk):** Need võib pärast heakskiitu importida otse tooteregistrisse koos vastavate tootjate ja brändidega.")
lines.append("2. **Otsustada Oticoni kuuldeaparaatide jaotus (11 tk):** Spetsialistil tuleb määrata, kas mudelid (nt Oticon Intent, Real, Own) registreeritakse baasmudelina (Aktiivsusgrupp I: `22.06.15.01`) või mitme eraldi kirjena (nt 'Oticon Intent - Aktiivsusgrupp I' ja 'Oticon Intent - Aktiivsusgrupp II').")
lines.append("3. **Kinnitada Tervisekassa toodete välistamine (22 tk):** Jätta ResMed CPAP ja Intersurgical filtrid SKA tooteregistrist välja, kuna need kuuluvad Tervisekassa süsteemi.")
lines.append("4. **Kinnitada aliaste sidumine (3 tk):** Lisada alternatiivsed nimed olemasolevate kirjete veergu `aliases`.")

full_md = "\n".join(lines)
with open("data/vahearuanne_gen.md", "w", encoding="utf-8") as f:
    f.write(full_md)

print("Report built successfully! Length:", len(full_md))
