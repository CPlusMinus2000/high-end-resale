
from typing import List
from constants import Entry, ATTRS

import pandas as pd


def read_excel(filename: str, mode: str='i') -> List[Entry]:
    """
    Reads an Excel document of a very specific format
    (must contain the column headers contained in ATTRS)
    and compiles it into a list of Entry objects, which are returned.

    Mode represents the reading mode, which is important for small details.
    'i': Inventory mode, could possibly have two locations per row
    'b': Barcode mode, only one location per row
    """

    assert mode in ['i', 'b']

    entries: List[Entry] = []
    dfs = pd.read_excel(filename, sheet_name=None)
    for _, df in dfs.items():
        df = df.astype(str)
        titles = list(df.iloc[0])
        if any([t not in titles for t in ATTRS.values()]):
            missing = [t for t in ATTRS.values() if t not in titles]
            raise ValueError(
                "Excel sheet is missing the columns: " + ", ".join(missing)
            )

        indices = {
            attr: titles.index(value) + 1
            for attr, value in ATTRS.items()
        }

        indices["price"] = titles.index("Cost") + 3
        qindex = titles.index("Abdn") + 1
        for row in df.itertuples():
            if row[indices["index"]] not in ["nan", "#"]:
                count = 0
                mode_check = row[qindex + 1] == "nan" if mode == 'b' else True
                if mode_check or row[qindex] in ['x', 'X']:
                    entry = Entry()
                    for attr, index in indices.items():
                        entry[attr] = row[index]

                    # q = row[qindex] if row[qindex].isnumeric() else "1"
                    # entry["quantity"] = q
                    entry["location"] = "ABDN"
                    entries.append(entry)
                    count += 1

                mode_check = row[qindex] == "nan" if mode == 'b' else True
                if row[qindex + 1] != "nan" and mode_check:
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
