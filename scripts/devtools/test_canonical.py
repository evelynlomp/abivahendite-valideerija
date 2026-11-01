import re

def make_canonical_name(brand, product_family, level, drops, size, ml_capacity, title):
    canon_parts = []
    if brand and brand != "MÄÄRAMATA":
        canon_parts.append(brand.upper())
        if product_family:
            fam_clean = re.sub(r'^\s*' + re.escape(brand) + r'\s*', '', product_family, flags=re.I).strip()
            if fam_clean:
                canon_parts.append(fam_clean.upper())
    elif product_family:
        canon_parts.append(product_family.upper())
        
    if level is not None:
        canon_parts.append(str(level))
    elif drops is not None:
        canon_parts.append(f"{drops} TILKA")
        
    if size:
        canon_parts.append(size.upper())
        
    if ml_capacity and not level and not drops:
        canon_parts.append(f"{ml_capacity}ML")
        
    name = " ".join(canon_parts).strip()
    return name

test_cases = [
    ("ABENA", "Abena San", 4, None, None, 800, "Vormmähkmed Abena San 4 800ml"),
    ("MOLICARE", "MoliCare Pad", 4, 4, None, 865, "Molicare Pad 4 tilka"),
    ("TENA", "Tena Pants", None, None, "M", 1400, "Tena Pants Normal M"),
    ("LILLE", "Lille Supreme Light", None, None, None, 340, "Lille Supreme Light Normal 340ml N28"),
    ("SENI", "Seni Lady", 3, 3, None, 400, "Seni Lady Extra 3 tilka"),
]

for tc in test_cases:
    print(tc[6], "->", make_canonical_name(*tc[:6], tc[6]))
