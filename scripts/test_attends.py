import sys
sys.path.insert(0, '.')
from src.classifier import MinistryClassifier
from src.knowledge_base import KnowledgeBase
from src.product_agent import ProductIdentificationAgent
from src.matcher import ProductMatcher
from src.validator import Validator

cl = MinistryClassifier('data/valideer.db')
kb = KnowledgeBase('data/valideer.db')
agent = ProductIdentificationAgent()
matcher = ProductMatcher(classifier=cl, knowledge_base=kb, product_agent=agent)
val = Validator(matcher=matcher)

raw_name = "Attends Soft 5 liimiribaga 990 ml"
ident_res = agent.identify_product(raw_name)
print("=== AGENT IDENTIFICATION ===")
for k, v in ident_res.items():
    print(f"  {k}: {v}")

print("\n=== MATCHER RESULT ===")
m_res = matcher.match(raw_name)
for k, v in m_res.items():
    print(f"  {k}: {v}")

print("\n=== VALIDATOR RESULT ===")
v_res = val.validate_row(excel_name=raw_name, excel_iso="09.30.24.16", excel_statutory_name="inkontinentsisidemed naistele 600 - 999 ml", row_index=1)
for k, v in v_res.items():
    print(f"  {k}: {v}")
