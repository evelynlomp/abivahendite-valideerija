import sys
sys.path.insert(0, '.')
from src.classifier import MinistryClassifier
from src.knowledge_base import KnowledgeBase
from src.product_agent import ProductIdentificationAgent
from src.matcher import ProductMatcher
from src.validator import Validator
from src.product_registry_db import ProductRegistryDB

reg_db = ProductRegistryDB('data/valideer.db')
cl = MinistryClassifier('data/valideer.db')
kb = KnowledgeBase('data/valideer.db')
agent = ProductIdentificationAgent(registry_db=reg_db)
matcher = ProductMatcher(classifier=cl, knowledge_base=kb, product_agent=agent)
validator = Validator(matcher=matcher)

test_cases = [
    # 1. Normaalne toode
    {
        "name": "ABENA SAN 4",
        "iso": "09.30.24.16",
        "stat": "inkontinentsisidemed naistele 600 - 999 ml",
        "expected_status": Validator.STATUS_MATCH
    },
    # 2. Tsinkoksiidi nõude rikkumine (ISO 09.21.18 alla esitatud tsinkoksiidita kreem)
    {
        "name": "Seni Care kaitsekreem arginiiniga 200ml",
        "iso": "09.21.18",
        "stat": "nahakaitsevahendid",
        "expected_status": Validator.STATUS_RESTRICTION
    },
    # 3. Tsinkoksiidiga toode (ISO 09.21.18)
    {
        "name": "Abena tsinksalv 100ml",
        "iso": "09.21.18",
        "stat": "nahakaitsevahendid",
        "expected_status": Validator.STATUS_MATCH
    },
    # 4. Dušigeel ISO 09.21.06 all (otsene välistus)
    {
        "name": "Tena dušigeel 500ml",
        "iso": "09.21.06",
        "stat": "nahapesemisvahendid",
        "expected_status": Validator.STATUS_RESTRICTION
    },
    # 5. Lävepaku kaldtee ISO 18.30.15 all (otsene välistus)
    {
        "name": "Kaldtee lävepakule 4 cm alumiinium",
        "iso": "18.30.15",
        "stat": "kaasaskantavad kaldteed",
        "expected_status": Validator.STATUS_RESTRICTION
    },
    # 6. Standardne poroloonmadrats ISO 04.33.06.01 all (otsene välistus)
    {
        "name": "Standardne poroloonmadrats 90x200",
        "iso": "04.33.06.01",
        "stat": "püsiva survejaotusega lamatisi ennetavad madratsid",
        "expected_status": Validator.STATUS_RESTRICTION
    }
]

print("=== VERIFYING RESTRICTION INTEGRATION ===")
all_ok = True
for tc in test_cases:
    res = validator.validate_row(tc['name'], tc['iso'], tc['stat'], row_index=1)
    status = res['Valideerimise staatus']
    passed = (status == tc['expected_status'])
    print(f"[{'PASS' if passed else 'FAIL'}] {tc['name']} ({tc['iso']})")
    print(f"       Staatus: {status} (Oodati: {tc['expected_status']})")
    print(f"       Selgitus: {res['Selgitus'][:100]}...")
    if not passed:
        all_ok = False

print("\nResult:", "ALL TESTS PASSED!" if all_ok else "SOME TESTS FAILED!")
