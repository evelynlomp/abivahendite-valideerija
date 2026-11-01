"""Genereerib realistliku igakuise test-Exceli kasutaja näidiste põhjal."""

import os
import pandas as pd


def generate_sample_data():
    os.makedirs("data", exist_ok=True)

    test_rows = [
        # Kasutaja näidis 1: ABENA SAN 4
        {
            "Rea ID": 1,
            "Abivahendi nimetus": "ABENA SAN 4",
            "ISO kood": "09.30.24.16",
            "Määrusejärgne nimetus": "inkontinentsisidemed naistele 600 - 999 ml",
            "Märkused": "Kasutaja näidis: Abena San 4 (800 ml)"
        },
        # Kasutaja näidis 2: MOLICARE PAD 4 TILKA N30
        {
            "Rea ID": 2,
            "Abivahendi nimetus": "MOLICARE PAD 4 TILKA N30",
            "ISO kood": "09.30.24.16",
            "Määrusejärgne nimetus": "inkontinentsisidemed naistele 600 - 999 ml",
            "Märkused": "Kasutaja näidis: MoliCare Pad 4 (Hartmann, 4 tilka / 865 ml)"
        },
        # Kasutaja näidis 3: LILLE SUPREME LIGHT NORMAL 340ML N28
        {
            "Rea ID": 3,
            "Abivahendi nimetus": "LILLE SUPREME LIGHT NORMAL 340ML N28",
            "ISO kood": "09.30.24.15",
            "Määrusejärgne nimetus": "inkontinentsisidemed naistele 300 - 599 ml",
            "Märkused": "Kasutaja näidis: Lille Supreme Light Normal (Ontex, 340 ml)"
        },
        # Näidis 4: Sama toode ilma pakendita
        {
            "Rea ID": 4,
            "Abivahendi nimetus": "MOLICARE PAD LADY 4",
            "ISO kood": "09.30.24.16",
            "Määrusejärgne nimetus": "inkontinentsisidemed naistele 600 - 999 ml",
            "Märkused": "Sama toote teine kirjapilt"
        },
        # Näidis 5: Vale ISO (Lille tootele on pandud kargu kood)
        {
            "Rea ID": 5,
            "Abivahendi nimetus": "LILLE SUPREME LIGHT NORMAL 340ML",
            "ISO kood": "12.03.06",
            "Määrusejärgne nimetus": "inkontinentsisidemed naistele 300 - 599 ml",
            "Märkused": "Vale ISO kood"
        },
        # Näidis 6: Vale määrusejärgne nimetus
        {
            "Rea ID": 6,
            "Abivahendi nimetus": "ABENA SAN 4",
            "ISO kood": "09.30.24.16",
            "Määrusejärgne nimetus": "rulaatorid",
            "Märkused": "Vale määrusejärgne nimetus"
        },
        # Näidis 7: Mõlemad valed
        {
            "Rea ID": 7,
            "Abivahendi nimetus": "MOLICARE PAD 4",
            "ISO kood": "99.99.99",
            "Määrusejärgne nimetus": "Vale määrus",
            "Märkused": "Mõlemad valed"
        },
        # Näidis 8: Tundmatu toode
        {
            "Rea ID": 8,
            "Abivahendi nimetus": "TUNDMATU ELEKTROONILINE SEADE XYZ-999",
            "ISO kood": "01.01.01",
            "Määrusejärgne nimetus": "Tundmatu kirje",
            "Märkused": "Toode, mida agent ei suuda tuvastada"
        }
    ]

    df_test = pd.DataFrame(test_rows)
    test_path = "data/naidis_sisend_vigadega.xlsx"
    df_test.to_excel(test_path, index=False)
    print(f"Loodud uuendatud test-fail: {test_path}")


if __name__ == "__main__":
    generate_sample_data()
