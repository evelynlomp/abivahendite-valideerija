with open("src/product_registry_db.py", "r", encoding="utf-8") as f:
    text = f.read()

for i, line in enumerate(text.split("\n")):
    if "cros" in line.lower():
        print(f"Line {i+1}: {line}")
