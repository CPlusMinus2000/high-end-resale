
import time
from typing import Dict

import pandas as pd
from collections import namedtuple

import pyautogui
import textract
import tkinter as tk

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

# Step 3.5: Scan through the find menu to see if any of the codes
# are already in the system. If so, prompt for a new code using tkinter.

# Step 4: Loop through the entries and insert the data into the system,
# checking during insertion that the index number does not already exist
# either by looking for greyed out text or checking the find menu

# Step 5: Send a Telegram message to Mom when the program is done

# Step 6: Profit