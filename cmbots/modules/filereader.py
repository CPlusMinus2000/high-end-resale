
from typing import List
from modules.constants import Entry, ATTRS

import pandas as pd


def read_excel(filename: str, mode: str='i') -> List[Entry]:
    """
    Reads an Excel document of a very specific format
    (must contain the column headers contained in ATTRS)
    and compiles it into a list of Entry objects, which are returned.

    Mode represents the reading mode, which is important for small details.
    'i': Inventory mode, could possibly have two locations per row
    'b': Barcode mode, only one location per row

    I'll take this moment to elaborate a bit more on the different modes
    because it's probably pretty confusing. In Inventory Mode, the different
    locations might both be populated, and the convention is as follows:
     - No location data given -> put an entry in Abdn.
     - Otherwise, follow the location data given. Abdn, Hby, both.
       *EXCEPT, even if only Hby is ticked, we put an entry in Abdn anyway.
        This is maybe bizarre behaviour but it makes things more convenient.
    In barcode mode, however, location is less important. In fact, I used
    to think there was some semblance of importance, but the current
    method (subject to change) is to default to Abdn for everything.
    The logic may get a little hard to follow though as I leave old and dead
    code lying around waiting to be used or killed off.
    """

    assert mode in ['i', 'b']

    entries: List[Entry] = []
    dfs = pd.read_excel(filename, sheet_name=None)
    for sheetname, df in dfs.items():
        if not sheetname[0].isdigit():
            continue

        df = df.astype(str)
        consignor = df.columns[8]

        while 'Box' not in df.columns:
            df.columns = df.iloc[0]
            df = df[1:]

        titles = list(df.iloc[0])
        print(f"{titles=}")
        if any([t not in titles for t in ATTRS.values()]):
            missing = [t for t in ATTRS.values() if t not in titles]
            cols = list(df.columns)
            for m in missing:
                if m in cols and m not in titles:
                    titles[cols.index(m)] = m

            missing = [m for m in missing if m not in titles]
            if missing:
                raise ValueError(
                    "Excel sheet is missing the columns: " + ", ".join(missing)
                )

        indices = {
            attr: titles.index(value) + 1
            for attr, value in ATTRS.items()
        }

        qindex = titles.index("Abdn") + 1
        for row in df.itertuples():
            if row[indices["index"]] not in ["nan", "#"]:
                count = 0
                mode_check = True # Right now, ABDN is always used
                if mode_check or row[qindex] in ['x', 'X']:
                    entry = Entry()
                    for attr, index in indices.items():
                        entry[attr] = row[index]

                    # q = row[qindex] if row[qindex].isnumeric() else "1"
                    # entry["quantity"] = q
                    entry["location"] = "ABDN"
                    if entry["cnor"] != "nan" and entry["cnor"].strip():
                        entry["cnor"] = consignors

                    entries.append(entry)
                    count += 1

                mode_check = mode != 'b'
                if row[qindex + 1] != "nan" and mode_check:
                    entry = Entry()
                    for attr, index in indices.items():
                        entry[attr] = row[index]

                    # q = "1" if row[qindex + 1] == "X" else row[qindex + 1]
                    # entry["quantity"] = q
                    entry["location"] = "HBY"
                    if entry["cnor"] != "nan" and entry["cnor"].strip():
                        entry["cnor"] = consignor

                    entries.append(entry)
                    count += 1

                if count == 0:
                    # Row was ignored?
                    raise ValueError(
                        f"Unused row with index {row[indices['index']]}"
                    )

    for entry in entries:
        entry["cost"] = entry["cost"].replace(',', '')
        entry["price"] = entry["price"].replace(',', '')

    return entries
