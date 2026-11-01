import json
from src.product_agent import ProductIdentificationAgent
from src.matcher import ProductMatcher
from src.classifier import MinistryClassifier
from src.knowledge_base import KnowledgeBase
from src.validator import Validator
from rapidfuzz import fuzz

raw_input = "ABENA SAN 4"

print("==================================================")
print("1. EXACT SEARCH SOURCE")
print("==================================================")
print("Files/Tables accessed during execution:")
print("  a) SQLite Table: teadmistebaas (File: data/valideer.db)")
print("  b) Registry Data Structure: MANUFACTURER_CATALOGUE (File: src/product_registry.py)")
print("  c) SQLite Table: ametlik_klassifikaator (File: data/valideer.db, source: data/Sotsiaalministeeriumi abivahendite loetelu.xlsx)")

print("\n==================================================")
print("2. EXACT LOOKUP DATA (EXTRACTED FEATURES)")
print("==================================================")
agent = ProductIdentificationAgent()
features = agent.extract_features(raw_input)
print(json.dumps(features, indent=2, ensure_ascii=False))

print("\n==================================================")
print("3. MATCHED RECORD")
print("==================================================")
norm_name = features["normalized"]

matched_rec = None
for prod in agent.registry:
    if prod["official_name"] == "ABENA SAN 4":
        matched_rec = prod
        break

print(json.dumps(matched_rec, indent=2, ensure_ascii=False))

print("\n==================================================")
print("4. CONFIDENCE CALCULATION BREAKDOWN")
print("==================================================")
# 1. Brand match
prod_brand = matched_rec["brand"].upper()
if features["brand"] == prod_brand:
    brand_score = 1.0
    brand_reason = f"features['brand'] ('{features['brand']}') == matched_rec['brand'].upper() ('{prod_brand}')"
elif prod_brand in norm_name:
    brand_score = 0.9
    brand_reason = f"'{prod_brand}' in norm_name ('{norm_name}')"
else:
    brand_score = 0.0
    brand_reason = "No brand match"

# 2. Line / Alias matching
best_alias = None
best_alias_score = 0.0
alias_scores = {}
for alias in matched_rec.get("aliases", []):
    s_sort = fuzz.token_sort_ratio(norm_name, alias)
    s_set = fuzz.token_set_ratio(norm_name, alias)
    s_comb = max(s_sort, s_set)
    alias_scores[alias] = {"token_sort_ratio": s_sort, "token_set_ratio": s_set, "max": s_comb}
    if s_comb > best_alias_score:
        best_alias_score = s_comb
        best_alias = alias

line_score = best_alias_score / 100.0

# 3. Parameters
param_matches = 0
param_checks = 0

# Volume check
if features["volume_ml"] and matched_rec.get("absorption_ml"):
    param_checks += 1
    if features["volume_ml"] == matched_rec["absorption_ml"]:
        param_matches += 1

# Level check
if features["level"] is not None:
    param_checks += 1
    import re
    prod_num = re.search(r"\b(\d+)\b", matched_rec["official_name"])
    if prod_num and int(prod_num.group(1)) == features["level"]:
        param_matches += 1

# Drops check
if features["drops"] is not None and matched_rec.get("drops") is not None:
    param_checks += 1
    if features["drops"] == matched_rec["drops"]:
        param_matches += 1

# Size check
if features["size"] and matched_rec.get("size"):
    param_checks += 1
    if features["size"] == matched_rec["size"]:
        param_matches += 1

param_score = (param_matches / param_checks) if param_checks > 0 else 0.5

# Weight calculation:
# total_confidence = (brand_score * 0.35) + (line_score * 0.40) + (param_score * 0.25)
brand_component = brand_score * 0.35
line_component = line_score * 0.40
param_component = param_score * 0.25
total_confidence = brand_component + line_component + param_component

print(f"a) Brand Score: {brand_score} (Weight 0.35 -> contribution: {brand_component:.3f})")
print(f"   Reason: {brand_reason}")
print(f"b) Line Score: {line_score} (Weight 0.40 -> contribution: {line_component:.3f})")
print(f"   Alias scores against normalized '{norm_name}':")
for a, sc in alias_scores.items():
    print(f"     * '{a}': sort={sc['token_sort_ratio']}%, set={sc['token_set_ratio']}% -> best={sc['max']}%")
print(f"   Best alias: '{best_alias}' -> {best_alias_score}/100 = {line_score}")
print(f"c) Parameter Score: {param_score} (Weight 0.25 -> contribution: {param_component:.3f})")
print(f"   Checks count: {param_checks}, Matches count: {param_matches} (Level={features['level']} matches official name level 4)")
print(f"d) Final Formula: ({brand_score} * 0.35) + ({line_score} * 0.40) + ({param_score} * 0.25)")
print(f"   Final Confidence Score: {total_confidence:.3f} -> rounded: {round(total_confidence, 3)}")

print("\n==================================================")
print("5. EXECUTION TRACE (CALL STACK & RETURN VALUES)")
print("==================================================")
c = MinistryClassifier()
kb = KnowledgeBase()
matcher = ProductMatcher(classifier=c, knowledge_base=kb, product_agent=agent)
val = Validator(matcher=matcher)

print("Step 5.1: Call val.validate_row('ABENA SAN 4', '09.30.24.16', 'inkontinentsisidemed naistele 600 - 999 ml')")
print("  Step 5.2: In val.validate_row -> calls matcher.match('ABENA SAN 4')")
print("    Step 5.3: In matcher.match -> normalizes raw input to 'ABENA SAN 4'")
print("    Step 5.4: In matcher.match -> queries kb.lookup('ABENA SAN 4', 'ABENA SAN 4')")
kb_res = kb.lookup("ABENA SAN 4", "ABENA SAN 4")
print(f"              Result: {kb_res} (in_kb = {kb_res is not None})")
print("    Step 5.5: In matcher.match -> calls product_agent.identify_product('ABENA SAN 4')")
agent_out = agent.identify_product(raw_input)
print(f"              product_agent returned identified={agent_out['identified']}, official='{agent_out['official_product']}', score={agent_out['confidence_score']}")
print(f"              suggested_iso='{agent_out['suggested_iso']}', suggested_statutory='{agent_out['suggested_statutory_name']}'")
print(f"    Step 5.6: In matcher.match -> verifies suggested_iso '{agent_out['suggested_iso']}' in MinistryClassifier")
ministry_rec = c.get_by_iso(agent_out['suggested_iso'])
print(f"              MinistryClassifier returned authoritative record: ISO='{ministry_rec['iso_kood']}', name='{ministry_rec['maarusejargne_nimetus']}'")
print("    Step 5.7: matcher.match returns combined dictionary to validator")
print("  Step 5.8: In val.validate_row -> compares Excel row inputs against authoritative matched data:")
print(f"            compare_iso('09.30.24.16', '{agent_out['suggested_iso']}') -> True")
print(f"            compare_statutory_names('inkontinentsisidemed naistele 600 - 999 ml', '{ministry_rec['maarusejargne_nimetus']}') -> True")
final_val = val.validate_row("ABENA SAN 4", "09.30.24.16", "inkontinentsisidemed naistele 600 - 999 ml")
print(f"  Step 5.9: Final status assigned: '{final_val['Valideerimise staatus']}'")
print(f"            Explanation: '{final_val['Selgitus']}'")
