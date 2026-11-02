with open("src/product_registry_db.py", "r", encoding="utf-8") as f:
    text = f.read()

print("Does product_registry_db handle lainer or cros?")
print("lainer in code:", "lainer" in text.lower())
print("cros in code:", "cros" in text.lower())
