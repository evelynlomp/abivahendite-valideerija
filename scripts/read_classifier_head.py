with open("src/classifier.py", "r", encoding="utf-8") as f:
    text = f.read()

print("classifier.py length:", len(text))
lines = text.split("\n")
print("\n".join(lines[:60]))
