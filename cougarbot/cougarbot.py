
import time
from typing import Dict

import pandas as pd
from collections import namedtuple

import pyautogui
import textract
from pywinauto.keyboard import send_keys

Entry = namedtuple(
    "Entry",
    [
        "index", "code", "description", "location",
        "cost", "price", "notes"
    ]
)

# So here's how the bot is going to need to work
# Step 1: Read the Excel sheet
# Do this by opening every page in the spreadsheet using pandas
# and then read row by row to assemble a list of entries

entry_dict: Dict[int, Entry] = {}

# Step 2: Read the Word document containing the sign data to extract notes.
# Do this by opening the Word document and then reading the text
# using textract, then read the notes by splitting on double newlines
# and add each note to the entry with the corresponding index number
# Also, check that the prices match up

# Step 3: Open Cougar Mountain through Remote Desktop and (optionally)
# locate the right places to click on the screen to insert text and save
# Alternatively, use human supervision to find the right values

def locate_and_click(image: str, wait: int=1) -> None:
    icon = pyautogui.locateOnScreen(image)
    pyautogui.moveTo(icon)
    time.sleep(0.3)
    pyautogui.click()
    time.sleep(wait)

def enter_maintenance():
    steps = [
        "cougarbot_data/" + i for i in [
            "network.png",
            "stock.png",
            "stock_maintenance.png"
        ]
    ]

    for step in steps:
        locate_and_click(step, 1)

locate_and_click("cougarbot_data/network.png")
list_box = pyautogui.locateOnScreen("cougarbot_data/number.png")
print(list_box)
pyautogui.click(list_box)
time.sleep(0.5)
send_keys("123")



# Step 3.5: Scan through the find menu to see if any of the codes
# are already in the system. If so, prompt for a new code using tkinter.

# Step 4: Loop through the entries and insert the data into the system,
# checking during insertion that the index number does not already exist
# either by looking for greyed out text or checking the find menu

# Step 5: Send a Telegram message to Mom when the program is done

# Step 6: Profit
