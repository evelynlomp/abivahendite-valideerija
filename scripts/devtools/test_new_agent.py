from src.product_agent import ProductIdentificationAgent
import sys

sys.stdout.reconfigure(encoding='utf-8')

agent = ProductIdentificationAgent()
print(f"Agent loaded registry with {len(agent.registry)} products.")

test_inputs = [
    "ABENA SAN 4",
    "MOLICARE PAD 4 TILKA N30",
    "LILLE SUPREME LIGHT NORMAL 340ML N28",
    "ABENA PANTS M3",
    "MOLICARE MOBILE 6 TILKA M",
    "Kompressioonsukad CCL2 medi Mediven Plus",
    "Tundmatu toode 999"
]

for inp in test_inputs:
    res = agent.identify_product(inp)
    print(f"\n==========================================")
    print(f"INPUT: {inp}")
    print(f"  Identified: {res['identified']}")
    print(f"  Official: {res['official_product']}")
    print(f"  Manufacturer: {res['manufacturer']}")
    print(f"  Confidence: {res['confidence_score']}")
    print(f"  Evidence: {res['evidence_sources'][:2]}")
    print(f"  Reasoning: {res['reasoning']}")
