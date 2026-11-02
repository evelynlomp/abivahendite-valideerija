with open("src/product_registry_db.py", "r", encoding="utf-8") as f:
    text = f.read()

print("product_registry_db.py length:", len(text))
lines = text.split("\n")
print("\n".join(lines[:80]))
