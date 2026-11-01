import sqlite3
import pandas as pd
import sys
import os

sys.path.insert(0, '.')
from src.classifier import MinistryClassifier
from src.knowledge_base import KnowledgeBase
from src.product_agent import ProductIdentificationAgent
from src.matcher import ProductMatcher
from src.validator import Validator
from src.product_registry_db import ProductRegistryDB

# 1. Test dataset consisting of all reported validation cases + sample file cases
rows_to_validate = [
    # The 9 cases from User's validation report
    {"name": "TENA Comfort Mini Extra 566 ml", "iso": "09.30.24.15", "stat": "inkontinentsisidemed naistele 300 - 599 ml", "desc": "User Report 1"},
    {"name": "TENA Comfort Mini Super 905 ml", "iso": "09.30.24.16", "stat": "inkontinentsisidemed naistele 600 - 999 ml", "desc": "User Report 2"},
    {"name": "Abena San 1A 250 ml", "iso": "09.30.24.14", "stat": "inkontinentsisidemed naistele 201- 299 ml", "desc": "User Report 3"},
    {"name": "Sensilind Lady Normal 340 ml", "iso": "09.30.24.15", "stat": "inkontinentsisidemed naistele 300 - 599 ml", "desc": "User Report 4"},
    {"name": "MoliCare Pad Lady 1.5 tilka 267 ml", "iso": "09.30.24.14", "stat": "inkontinentsisidemed naistele 201- 299 ml", "desc": "User Report 5"},
    {"name": "forma-care woman EXTRA 500 ml", "iso": "09.30.24.15", "stat": "inkontinentsisidemed naistele 300 - 599 ml", "desc": "User Report Task 5"},
    {"name": "forma-care woman SUPER 933 ml", "iso": "09.30.24.16", "stat": "inkontinentsisidemed naistele 600 - 999 ml", "desc": "User Report Task 5"},
    {"name": "Attends Soft 5 liimiribaga 990 ml", "iso": "09.30.24.16", "stat": "inkontinentsisidemed naistele 600 - 999 ml", "desc": "User Report Task 6"},
    {"name": "TENA Comfort Mini Plus 310 ml", "iso": "09.30.24.15", "stat": "inkontinentsisidemed naistele 300 - 599 ml", "desc": "User Report Task 3"},
    # The standard sample dataset
    {"name": "ABENA SAN 4", "iso": "09.30.24.16", "stat": "inkontinentsisidemed naistele 600 - 999 ml", "desc": "Sample 1"},
    {"name": "MOLICARE PAD 4 TILKA N30", "iso": "09.30.24.16", "stat": "inkontinentsisidemed naistele 600 - 999 ml", "desc": "Sample 2"},
    {"name": "LILLE SUPREME LIGHT NORMAL 340ML N28", "iso": "09.30.24.15", "stat": "inkontinentsisidemed naistele 300 - 599 ml", "desc": "Sample 3"},
    {"name": "MOLICARE PAD LADY 4", "iso": "09.30.24.16", "stat": "inkontinentsisidemed naistele 600 - 999 ml", "desc": "Sample 4"},
    {"name": "LILLE SUPREME LIGHT NORMAL 340ML", "iso": "12.03.06", "stat": "inkontinentsisidemed naistele 300 - 599 ml", "desc": "Sample 5 (Wrong ISO)"},
    {"name": "ABENA SAN 4", "iso": "09.30.24.16", "stat": "rulaatorid", "desc": "Sample 6 (Wrong Stat)"},
    {"name": "MOLICARE PAD 4", "iso": "99.99.99", "stat": "Vale määrus", "desc": "Sample 7 (Both wrong)"},
    {"name": "TUNDMATU ELEKTROONILINE SEADE XYZ-999", "iso": "01.01.01", "stat": "Tundmatu kirje", "desc": "Sample 8 (Unknown)"}
]

# Run AFTER (Current system)
reg_db = ProductRegistryDB('data/valideer.db')
cl = MinistryClassifier('data/valideer.db')
kb = KnowledgeBase('data/valideer.db')
agent = ProductIdentificationAgent(registry_db=reg_db)
matcher = ProductMatcher(classifier=cl, knowledge_base=kb, product_agent=agent)
val = Validator(matcher=matcher)

results_after = []
for idx, r in enumerate(rows_to_validate):
    res = val.validate_row(r['name'], r['iso'], r['stat'], row_index=idx+1)
    results_after.append(res)

df_after = pd.DataFrame(results_after)
counts_after = df_after['Valideerimise staatus'].value_counts().to_dict()

print("=== CURRENT RESULTS (AFTER) ===")
print(f"Total rows: {len(df_after)}")
for k, v in counts_after.items():
    print(f"  {k}: {v}")

# Now let's calculate the BEFORE results based on the User's Validation Report
# In the Before state:
# - Rows 1-5 & 9 (TENA Mini Extra, Mini Super, Mini Plus, Abena San 1A, Sensilind Lady, MoliCare 1.5) failed with Wrong ISO and statutory classification (Vale mõlemad / Vale ISO)
# - Rows 6-8 (forma-care Extra, forma-care Super, Attends Soft 5) failed as "Tundmatu toode"
# - Row 10-13: Valid (4)
# - Row 14: Vale ISO (1)
# - Row 15: Vale määrusejärgne nimetus (1)
# - Row 16: Vale mõlemad (1)
# - Row 17: Tundmatu toode (1)

before_counts = {
    Validator.STATUS_MATCH: 4,                      # Valid rows
    Validator.STATUS_WRONG_ISO: 1,                  # Wrong ISO
    Validator.STATUS_WRONG_NAME: 1,                 # Wrong statutory
    Validator.STATUS_WRONG_BOTH: 7,                 # 1 sample + 6 failed report items
    Validator.STATUS_REVIEW: 0,                     # Manual review
    Validator.STATUS_UNKNOWN: 4                     # 1 sample + 2 forma-care + 1 Attends
}

after_counts = {
    Validator.STATUS_MATCH: counts_after.get(Validator.STATUS_MATCH, 0),
    Validator.STATUS_WRONG_ISO: counts_after.get(Validator.STATUS_WRONG_ISO, 0),
    Validator.STATUS_WRONG_NAME: counts_after.get(Validator.STATUS_WRONG_NAME, 0),
    Validator.STATUS_WRONG_BOTH: counts_after.get(Validator.STATUS_WRONG_BOTH, 0),
    Validator.STATUS_REVIEW: counts_after.get(Validator.STATUS_REVIEW, 0),
    Validator.STATUS_UNKNOWN: counts_after.get(Validator.STATUS_UNKNOWN, 0),
}

total = len(rows_to_validate)
print("\n" + "="*70)
print(f"{'Metrika':<35} | {'Enne (Before)':<14} | {'Pärast (After)':<14} | {'Muutus':<10}")
print("="*70)
print(f"{'Total rows':<35} | {total:<14} | {total:<14} | 0%")

metrics = [
    ("Valid rows (Vastab)", Validator.STATUS_MATCH),
    ("Wrong ISO (Vale ISO)", Validator.STATUS_WRONG_ISO),
    ("Wrong statutory (Vale nimetus)", Validator.STATUS_WRONG_NAME),
    ("Wrong both (Mõlemad valed)", Validator.STATUS_WRONG_BOTH),
    ("Manual review (Vajab kontrolli)", Validator.STATUS_REVIEW),
    ("Unknown products (Tundmatu)", Validator.STATUS_UNKNOWN)
]

for label, key in metrics:
    b = before_counts.get(key, 0)
    a = after_counts.get(key, 0)
    diff = a - b
    if b == 0:
        pct = f"+{a}" if a > 0 else "0%"
    else:
        change_pct = ((a - b) / b) * 100
        pct = f"{change_pct:+.1f}%"
    print(f"{label:<35} | {b:<12} | {a:<12} | {pct:<10}")

print("="*60)

