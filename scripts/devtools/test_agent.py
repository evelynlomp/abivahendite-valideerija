from src.product_agent import ProductIdentificationAgent

agent = ProductIdentificationAgent()
examples = [
    "ABENA SAN 4",
    "MOLICARE PAD 4 TILKA N30",
    "LILLE SUPREME LIGHT NORMAL 340ML N28"
]

for ex in examples:
    res = agent.identify_product(ex)
    print("=" * 60)
    print("Input:", ex)
    print("Official Product:", res.get("official_product"))
    print("Confidence Score:", res.get("confidence_score"))
    print("Manufacturer:", res.get("manufacturer"))
    print("Suggested ISO:", f"{res.get('suggested_iso')} - {res.get('suggested_statutory_name')}")
    print("Evidence Sources:")
    for ev in res.get("evidence_sources", []):
        print(f"  * {ev}")
    print("Reasoning:", res.get("reasoning"))
    print("Alternative Matches:", res.get("alternative_matches"))
