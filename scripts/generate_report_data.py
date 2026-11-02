import json
from scan_external_sources import results, new_mfgs, new_brands

by_conf = {}
for r in results:
    conf = r['confidence']
    by_conf.setdefault(conf, []).append(r)

print('=== KATEGOORIATE JAOTUS ===')
for k, v in by_conf.items():
    print(f"{k}: {len(v)}")

print('\n=== ÜLEVAATUST VAJAV (MITU ISO-D) ===')
for r in by_conf.get('ÜLEVAATUST VAJAV (MITU ISO-D)', []):
    isos = ', '.join([x[0] for x in r['matching_isos']])
    print(f"- {r['raw_name']} | Bränd: {r['brand']} | Tootja: {r['manufacturer']} | Allikas: {r['source_name']} | ISO-d: {isos}")

print('\n=== DUPLIKAADID JA ALIASED ===')
for r in by_conf.get('DUPLIKAAT', []):
    print(f"DUPLIKAAT: {r['raw_name']} -> {r['status_desc']}")
for r in by_conf.get('VÕIMALIK ALIAS', []):
    print(f"ALIAS: {r['raw_name']} -> {r['status_desc']}")

# Salvestame ka JSON faili detailseks raportiks
with open("data/scanned_candidates_report.json", "w", encoding="utf-8") as f:
    json.dump({
        "summary": {
            "total_analyzed": len(results),
            "new_candidates_count": len([r for r in results if r["confidence"] in ("KÕRGE KINDLUS", "ÜLEVAATUST VAJAV (MITU ISO-D)", "MADAL KINDLUS", "MADAL KINDLUS (TERVISEKASSA)")]),
            "high_confidence_count": len(by_conf.get("KÕRGE KINDLUS", [])),
            "multi_iso_review_count": len(by_conf.get("ÜLEVAATUST VAJAV (MITU ISO-D)", [])),
            "low_confidence_count": len(by_conf.get("MADAL KINDLUS", [])) + len(by_conf.get("MADAL KINDLUS (TERVISEKASSA)", [])),
            "new_manufacturers_count": len(new_mfgs),
            "new_manufacturers": list(new_mfgs),
            "new_brands_count": len(new_brands),
            "new_brands": list(new_brands),
            "duplicates_count": len(by_conf.get("DUPLIKAAT", [])),
            "aliases_count": len(by_conf.get("VÕIMALIK ALIAS", [])),
            "manual_review_total": len(by_conf.get("ÜLEVAATUST VAJAV (MITU ISO-D)", [])) + len(by_conf.get("MADAL KINDLUS", [])) + len(by_conf.get("MADAL KINDLUS (TERVISEKASSA)", []))
        },
        "results": results
    }, f, ensure_ascii=False, indent=2)

print("\nRaport salvestatud: data/scanned_candidates_report.json")
