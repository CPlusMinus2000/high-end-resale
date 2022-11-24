
import time
from typing import List

import pandas as pd
from dataclasses import dataclass

import pyautogui
import textract
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

# Step 2: Read the Word document containing the sign data to extract notes.
# Do this by opening the Word document and then reading the text
# using textract, then read the notes by splitting on double newlines
# and add each note to the entry with the corresponding index number
# Also, check that the prices match up

# Step 3: Open Cougar Mountain through Remote Desktop and (optionally)
# locate the right places to click on the screen to insert text and save
# Alternatively, use human supervision to find the right values

def c(f: str) -> str:
    return f"cougarbot_data/{f}"

def locate_and_click(image: str, wait: int=1) -> None:
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

def enter_stock(entry: Entry) -> None:
    """
    Enter the data from an entry into the Cougar Mountain system.
    """

    # Enter the stock number
    locate_and_click(c("stock_number.png"))
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
    send_keys(entry.location + "{TAB}")
    send_keys(entry.description + "{TAB}")

    bl = pyautogui.locateOnScreen(c("breaklist.png"))
    if bl is None:
        raise ValueError("Could not find breaklist")

    pyautogui.click(bl.left + bl.width, bl.top + bl.height + 3)
    time.sleep(0.3)
    send_keys(entry.price + "{TAB}")

# locate_and_click("cougarbot_data/network.png")
# list_box = pyautogui.locateOnScreen("cougarbot_data/number.png")
# print(list_box)
# pyautogui.click(list_box)
# time.sleep(0.5)
# send_keys("123")

enter_stock(entries[0])

# Step 3.5: Scan through the find menu to see if any of the codes
# are already in the system. If so, prompt for a new code using tkinter.

# Step 4: Loop through the entries and insert the data into the system,
# checking during insertion that the index number does not already exist
# either by looking for greyed out text or checking the find menu

# Step 5: Send a Telegram message to Mom when the program is done

# Step 6: Profit
