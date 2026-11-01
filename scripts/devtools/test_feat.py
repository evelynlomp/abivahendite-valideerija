from scripts.extract_suppliers import extract_product_features
import json
import sys

sys.stdout.reconfigure(encoding='utf-8')

text = "Abena San 4, 42x20 cm, 800 ml N30"
feat = extract_product_features(text, "")
print("Features for", text)
for k, v in feat.items():
    print(f"  {k}: {v}")
