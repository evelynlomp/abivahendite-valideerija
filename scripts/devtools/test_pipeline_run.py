import pandas as pd
import sys
from src.matcher import ProductMatcher
from src.classifier import MinistryClassifier
from src.knowledge_base import KnowledgeBase
from src.product_agent import ProductIdentificationAgent
from src.validator import Validator

sys.stdout.reconfigure(encoding='utf-8')

cl = MinistryClassifier('data/valideer.db')
kb = KnowledgeBase('data/valideer.db')
pa = ProductIdentificationAgent()
matcher = ProductMatcher(classifier=cl, knowledge_base=kb, product_agent=pa)
validator = Validator(matcher=matcher)

df = pd.read_excel('data/naidis_sisend_vigadega.xlsx')
print(f"Validating sample file ({len(df)} rows):")

for idx, row in df.iterrows():
    name = row['Abivahendi nimetus']
    iso = row['ISO kood']
    stat = row['Määrusejärgne nimetus']
    res = validator.validate_row(name, iso, stat, row_index=idx+1)
    print(f"\nRida {res['Rida']}: {name}")
    print(f"  Ametlik toode: {res['Tuvastatud ametlik toode']}")
    print(f"  Tootja: {res['Tootja']}")
    print(f"  Valideerimise staatus: {res['Valideerimise staatus']}")
    print(f"  Usaldusskoor: {res['Usaldusskoor']}")
    print(f"  Ametlik ISO: {res['Ametlik ISO kood']} (Excelis: {res['ISO kood (Excel)']})")
    print(f"  Tuvastuse allikas: {res['Tuvastuse allikas']}")
