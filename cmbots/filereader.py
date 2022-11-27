
from typing import List
from constants import Entry, ATTRS

import pandas as pd

def read_excel(filename: str) -> List[Entry]:
    entries: List[Entry] = []
    dfs = pd.read_excel(filename, sheet_name=None)
    for sheet_name, df in dfs.items():
        df = df.astype(str)
        titles = list(df.iloc[0])
        indices = {
            attr: titles.index(value) + 1
            for attr, value in ATTRS.items()
        }

        indices["price"] = titles.index("Cost") + 3
        qindex = titles.index("Abdn") + 1
        for row in df.itertuples():
            print(row)
            if row[indices["index"]] not in ["nan", "#"]:
                if row[qindex + 1] == "nan" or row[qindex] == "X":
                    entry = Entry()
                    for attr, index in indices.items():
                        entry[attr] = row[index]

                    q = row[qindex] if row[qindex].isnumeric() else "1"
                    entry["quantity"] = q
                    entry["location"] = "ABDN"
                    entries.append(entry)

                if row[qindex + 1] != "nan":
                    entry = Entry()
                    for attr, index in indices.items():
                        entry[attr] = row[index]

                    q = "1" if row[qindex + 1] == "X" else row[qindex + 1]
                    entry["quantity"] = q
                    entry["location"] = "HBY"
                    entries.append(entry)
    
    return entries