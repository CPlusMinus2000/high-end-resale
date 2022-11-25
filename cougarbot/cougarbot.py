
import time
from typing import List

import pandas as pd
from dataclasses import dataclass

import pyautogui
from platform import platform

if "Windows" in platform():
    from pywinauto.keyboard import send_keys


@dataclass
class Entry:
    index: str = ""
    code: str = ""
    description: str = ""
    location: str = ""
    quantity: str = ""
    cost: str = ""
    price: str = ""
    notes: str = ""

    def __getitem__(self, key):
        return getattr(self, key)
    
    def __setitem__(self, key, value):
        setattr(self, key, value)

attrs = {
    "index": '#',
    "code": "Stock#",
    "description": "Description",
    "cost": "Cost",
}

# So here's how the bot is going to need to work
# Step 1: Read the Excel sheet
# Do this by opening every page in the spreadsheet using pandas
# and then read row by row to assemble a list of entries

entries: List[Entry] = []
dfs = pd.read_excel("cougarbot_data/stock.xls", sheet_name=None)
for sheet_name, df in dfs.items():
    df = df.astype(str)
    titles = list(df.iloc[0])
    indices = {
        attr: titles.index(value) + 1 for attr, value in attrs.items()
    }

    indices["price"] = titles.index("Cost") + 3
    qindex = titles.index("Abdn") + 1
    for row in df.itertuples():
        if row[indices["index"]] not in ["nan", '#']:
            if row[qindex + 1] == "nan" or row[qindex] == 'X':
                entry = Entry()
                for attr, index in indices.items():
                    entry[attr] = row[index]

                q = row[qindex] if row[qindex].isnumeric() else '1'
                entry["quantity"] = q
                entry["location"] = "ABDN"
                entries.append(entry)

            if row[qindex + 1] != "nan":
                entry = Entry()
                for attr, index in indices.items():
                    entry[attr] = row[index]

                q = '1' if row[qindex + 1] == 'X' else row[qindex + 1]
                entry["quantity"] = q
                entry["location"] = "HBY"
                entries.append(entry)

print(entries[0])

# Step 2: Read the Word document containing the sign data to extract notes.
# Do this by opening the Word document and then reading the text
# using textract, then read the notes by splitting on double newlines
# and add each note to the entry with the corresponding index number
# Also, check that the prices match up

with open("cougarbot_data/signs.txt", 'r') as f:
    signs = f.read().split("\n\n")

signs_map = {}
for s in signs:
    i, t = s.splitlines()
    for part in i.split(" & "):
        signs_map[part.strip('.')] = t.split("   ")[0].strip()

for entry in entries:
    if entry.index in signs_map:
        # Check that the price is contained in the text
        if entry.price not in signs_map[entry.index]:
            print(f"Price mismatch for {entry.index}")
            continue

        entry.notes = signs_map[entry.index]

    else:
        print(f"No sign data for {entry.index}")
        continue

print(entries[0])

# Step 3: Open Cougar Mountain through Remote Desktop and (optionally)
# locate the right places to click on the screen to insert text and save
# Alternatively, use human supervision to find the right values

def c(f: str) -> str:
    return f"cougarbot_data/{f}"

def locate_and_click(image: str, wait: float=0.5) -> None:
    icon = pyautogui.locateOnScreen(image)
    if icon is None:
        raise ValueError(f"Could not find {image}")

    pyautogui.moveTo(icon)
    time.sleep(0.3)
    pyautogui.click()
    time.sleep(wait)

def enter_maintenance() -> None:
    steps = [
        "cougarbot_data/" + i for i in [
            "network.png",
            "stock.png",
            "stock_maintenance.png"
        ]
    ]

    for step in steps:
        locate_and_click(step, 1)

# Step 4: Loop through the entries and insert the data into the system,
# checking during insertion that the index number does not already exist
# either by looking for greyed out text or checking the find menu

def enter_stock(entry: Entry) -> None:
    """
    Enter the data from an entry into the Cougar Mountain system.
    """

    # Enter the stock number
    locate_and_click(c("number.png"))
    send_keys(entry.code + "{TAB}")

    # If the stock number is already in the system, then looking for
    # location.png should fail. If this happens, then alert the user
    # (or in this case just print a failure message and exit)
    try:
        locate_and_click(c("location.png"))
    except ValueError:
        print(f"Stock number {entry.code} already in system")
        raise

    # Enter the location and description
    send_keys(entry.location + "{TAB 2}I1{TAB 3}")
    send_keys(entry.description + "{TAB}")

    bl = pyautogui.locateOnScreen(c("breaklist.png"))
    if bl is None:
        raise ValueError("Could not find breaklist")

    pyautogui.click(bl.left + bl.width, bl.top + bl.height + 3)
    time.sleep(0.3)
    send_keys(entry.price + "{TAB}")

    locate_and_click(c("last_cost.png"))
    send_keys(entry.cost + "{TAB}")

    locate_and_click(c("sales.png"))
    locate_and_click(c("storing.png"))
    send_keys(entry.price + "{TAB}")

    locate_and_click(c("notes.png"))

locate_and_click(c("network.png"))
enter_stock(entries[0])

# Step 5: Send a Telegram message to Mom when the program is done

# Step 6: Profit
