
from typing import List
from constants import Entry, ATTRS

import pandas as pd


def read_excel(filename: str) -> List[Entry]:
    """
    Reads an Excel document of a very specific format
    (must contain the column headers contained in ATTRS)
    and compiles it into a list of Entry objects, which are returned.
    """

    entries: List[Entry] = []
    dfs = pd.read_excel(filename, sheet_name=None)
    for _, df in dfs.items():
        df = df.astype(str)
        titles = list(df.iloc[0])
        indices = {
            attr: titles.index(value) + 1
            for attr, value in ATTRS.items()
        }

        indices["price"] = titles.index("Cost") + 3
        qindex = titles.index("Abdn") + 1
        for row in df.itertuples():
            if row[indices["index"]] not in ["nan", "#"]:
                count = 0
                if row[qindex + 1] == "nan" or row[qindex] in ['x', 'X']:
                    entry = Entry()
                    for attr, index in indices.items():
                        entry[attr] = row[index]

                    # q = row[qindex] if row[qindex].isnumeric() else "1"
                    # entry["quantity"] = q
                    entry["location"] = "ABDN"
                    entries.append(entry)
                    count += 1

                if row[qindex + 1] != "nan" and row[qindex] == "nan":
                    entry = Entry()
                    for attr, index in indices.items():
                        entry[attr] = row[index]

                    # q = "1" if row[qindex + 1] == "X" else row[qindex + 1]
                    # entry["quantity"] = q
                    entry["location"] = "HBY"
                    entries.append(entry)
                    count += 1

                if count == 0:
                    # Row was ignored?
                    raise ValueError(
                        f"Unused row with index {row[indices['index']]}"
                    )

    return entries
