import sys
sys.path.insert(0, '.')
from src.classifier import MinistryClassifier
from src.knowledge_base import KnowledgeBase
from src.product_agent import ProductIdentificationAgent
from src.matcher import ProductMatcher
from src.validator import Validator
from src.product_registry_db import ProductRegistryDB

# Force fresh reload of registry
reg_db = ProductRegistryDB()
cl = MinistryClassifier('data/valideer.db')
kb = KnowledgeBase('data/valideer.db')
agent = ProductIdentificationAgent(registry_db=reg_db)
matcher = ProductMatcher(classifier=cl, knowledge_base=kb, product_agent=agent)
val = Validator(matcher=matcher)

test_suite = [
    ("TENA Comfort Mini Extra 566 ml", "09.30.24.15", "inkontinentsisidemed naistele 300 - 599 ml"),
    ("TENA Comfort Mini Super 905 ml", "09.30.24.16", "inkontinentsisidemed naistele 600 - 999 ml"),
    ("TENA Comfort Mini Plus 310 ml", "09.30.24.15", "inkontinentsisidemed naistele 300 - 599 ml"),
    ("Abena San 1A 250 ml", "09.30.24.14", "inkontinentsisidemed naistele 201- 299 ml"),
    ("Sensilind Lady Normal 340 ml", "09.30.24.15", "inkontinentsisidemed naistele 300 - 599 ml"),
    ("MoliCare Pad Lady 1.5 tilka 267 ml", "09.30.24.14", "inkontinentsisidemed naistele 201- 299 ml"),
    ("forma-care woman EXTRA 500 ml", "09.30.24.15", "inkontinentsisidemed naistele 300 - 599 ml"),
    ("forma-care woman SUPER 933 ml", "09.30.24.16", "inkontinentsisidemed naistele 600 - 999 ml"),
    ("Attends Soft 5 liimiribaga 990 ml", "09.30.24.16", "inkontinentsisidemed naistele 600 - 999 ml")
]

all_passed = True
for name, exp_iso, exp_stat in test_suite:
    res = val.validate_row(excel_name=name, excel_iso=exp_iso, excel_statutory_name=exp_stat, row_index=1)
    status = res['Valideerimise staatus']
    matched_prod = res['Tuvastatud ametlik toode']
    matched_iso = res['Ametlik ISO kood']
    conf = res['Usaldusskoor']
    
    passed = (status == Validator.STATUS_MATCH and matched_iso == exp_iso)
    print(f"[{'PASS' if passed else 'FAIL'}] {name}")
    print(f"       -> Status: {status} | Product: {matched_prod} | ISO: {matched_iso} | Conf: {conf}")
    if not passed:
        all_passed = False
        print(f"       -> Expected ISO: {exp_iso} | Explanation: {res['Selgitus']}")

print(f"\n>>> Total Test Suite Result: {'ALL PASSED (100%)' if all_passed else 'FAILURES DETECTED'}")
