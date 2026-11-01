import pandas as pd
from src.classifier import MinistryClassifier
from src.knowledge_base import KnowledgeBase
from src.product_agent import ProductIdentificationAgent
from src.matcher import ProductMatcher
from src.validator import Validator

df = pd.read_excel('data/naidis_sisend_vigadega.xlsx')
c = MinistryClassifier()
kb = KnowledgeBase()
pa = ProductIdentificationAgent()
m = ProductMatcher(classifier=c, knowledge_base=kb, product_agent=pa)
v = Validator(matcher=m)

res_df, col_info = v.validate_dataframe(df)
for idx, r in res_df.iterrows():
    print(f"Rida {idx+1}: {r['Abivahendi nimetus']} -> Staatus: {r['Valideerimise staatus']}, Usaldus: {r['Usaldusskoor']}, Allikas: {r['Tuvastuse allikas']}")
