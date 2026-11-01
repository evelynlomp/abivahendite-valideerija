import pandas as pd
df = pd.read_excel('data/naidis_sisend_vigadega.xlsx')
for idx, r in df.iterrows():
    print(f"Row {idx+1}: {r['Abivahendi nimetus']} | ISO: {r['ISO kood']} | Stat: {r['Määrusejärgne nimetus']}")
