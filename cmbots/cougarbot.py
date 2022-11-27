import time
import os
import pandas as pd
import pyautogui
import telegram_send
import pyperclip

from typing import List
from platform import platform
from constants import *
from filereader import read_excel

if "Windows" in platform():
    from pywinauto.keyboard import send_keys


# So here's how the bot is going to need to work
# Step 1: Read the Excel sheet
# Do this by opening every page in the spreadsheet using pandas
# and then read row by row to assemble a list of entries

if not os.path.exists(c("stock.xls")):
    pyautogui.alert(
        "Please save the stock spreadsheet in the folder bot_data "
        "with the name stock.xls."
    )
    exit()

entries = read_excel(c("stock.xls"))
print(entries[1])

# Step 2: Read the Word document containing the sign data to extract notes.
# Do this by opening the Word document and then reading the text
# using textract, then read the notes by splitting on double newlines
# and add each note to the entry with the corresponding index number
# Also, check that the prices match up


def locate_price(sentence: str) -> str:
    for word in sentence.split():
        if "$" in word:
            return word[word.index("$") + 1:]

    return ""

if not os.path.exists(c("signs.txt")):
    pyautogui.alert(
        "Please open the signs document "
        "and save it in the folder bot_data/ as signs.txt."
    )
    exit()

with open(c("signs.txt"), "r") as f:
    signs = f.read().split("\n\n")

signs_map = {}
for s in signs:
    i, t = s.splitlines()
    for part in i.split(" & "):
        signs_map[part.strip(".")] = t.split("   ")[0].strip()

for entry in entries:
    if entry.index in signs_map:
        # Check that the price is contained in the text
        if entry.price not in signs_map[entry.index]:
            print(f"Price mismatch for {entry.index}")
            guess = locate_price(signs_map[entry.index])
            if guess != "":
                res = pyautogui.confirm(
                    f"Price mismatch for {entry.index} with "
                    f'sign text "{signs_map[entry.index]}". '
                    f"Is the price {guess}? "
                    "Click OK to accept, "
                    "or Cancel to keep the existing price. "
                    "If you would like to enter in a new price, "
                    'click "New Price".',
                    buttons=["OK", "Cancel", "New Price"],
                )

                if res == "New Price":
                    new_price = pyautogui.prompt("Please enter the new price:")
                    if new_price is None:
                        pass

                    entry.price = new_price

                elif res == "OK":
                    entry.price = guess

            else:
                # This probably shouldn't be happening, but we can check it
                res = pyautogui.confirm(
                    f"The sign for {entry.index} does not contain a price. "
                    "Please check the sign and enter in the price manually."
                    "Click OK to continue, or Cancel to stop the program.",
                )

                if res == "Cancel":
                    exit()

        entry.notes = signs_map[entry.index]
        if TYPE_NOTES:
            for c in CONVERT:
                entry.notes = entry.notes.replace(c, "{" + c + "}")

    else:
        print(f"No sign data for {entry.index}")
        res = pyautogui.confirm(
            text=f"No sign data for {entry.index}. Continue?",
            title="CougarBot"
        )

        if res == "Cancel":
            exit()

        continue

print(entries[0])

# Step 3: Open Cougar Mountain through Remote Desktop and (optionally)
# locate the right places to click on the screen to insert text and save
# Alternatively, use human supervision to find the right values


def enter_maintenance() -> None:
    """
    Use locate_and_click to enter the stock maintenance screen.
    """

    steps = [
        c(i) for i in [
            "file.png", "inventory.png",
            "stock.png", "stock_maintenance.png"
        ]
    ]

    if pyautogui.locateOnScreen(c("information.png")) is not None:
        locate_and_click(c("no.png"))
    elif pyautogui.locateOnScreen(c("number.png")) is not None:
        # Already ready to start entering
        return
    elif pyautogui.locateOnScreen(c("stock.png")) is None:
        # Regular, no modifications
        pass
    elif pyautogui.locateOnScreen(c("in_stock.png")) is None:
        # Menu is not visible. Enter maintenance mode
        steps = steps[2:]
    else:
        # Menu is visible, but can't enter numbers. Exit.
        locate_and_click(c("file.png"))
        locate_and_click(c("exit.png"))
        if pyautogui.locateOnScreen(c("information.png")) is not None:
            # Made edits, have to cancel
            locate_and_click(c("no.png"))

    for step in steps:
        locate_and_click(step)


# Step 4: Loop through the entries and insert the data into the system,
# checking during insertion that the index number does not already exist
# either by looking for greyed out text or checking the find menu


def enter_stock(entry: Entry, first=False) -> bool:
    """
    Enter the data from an entry into the Cougar Mountain system.

    Returns True if the entry was successfully entered, False otherwise.
    """

    # Enter the stock number
    if first:
        locate_and_click(c("number.png"))

    send_keys(entry.code + "{TAB}")

    # Enter the location and description
    if first:
        send_keys(entry.location + "{TAB 2}I1{TAB 3}")
    else:
        send_keys(entry.location + "{TAB 5}")

    # Now try to find the last cost box. If it is not on screen,
    # then there must be a duplicate
    dup = pyautogui.locateOnScreen(c("notes.png"))
    if dup is None:
        # Duplicate detected.
        locate_and_click(c("cancel.png"))
        enter_maintenance()
        return False

    send_keys(entry.description + "{TAB}")
    if entry.cnor != "nan":
        send_keys(entry.cnor)
        locate_and_click(c("serialized.png"))
        con = pyautogui.locateOnScreen(c("consignment.png"))
        if con is not None:
            pyautogui.click(con.left + con.width, con.top + 0.5 * con.height)
        else:
            pyautogui.alert("Could not find consignment button!")
            exit()
        
        send_keys("{TAB 2}" + entry.cost)

    bl = pyautogui.locateOnScreen(c("breaklist.png"))
    pyautogui.click(bl.left + bl.width, bl.top + bl.height + 3)
    time.sleep(0.3)
    send_keys(entry.price + "{TAB}")

    lc = pyautogui.locateOnScreen(c("last_cost.png"))
    pyautogui.click(lc.left + lc.width + 2, lc.top + 0.5 * lc.height)
    send_keys(entry.cost + "{TAB}")

    locate_and_click(c("sales.png"))
    stor = pyautogui.locateOnScreen(c("storing.png"))
    pyautogui.click(stor.left + stor.width + 2, stor.top + 0.5 * stor.height)
    send_keys(entry.price + "{TAB}")

    locate_and_click(c("notes.png"))
    if TYPE_NOTES:
        send_keys(entry.notes, with_spaces=True)
    else:
        pyperclip.copy(entry.notes)
        send_keys("^v")

    locate_and_click(c("save.png"))
    time.sleep(2)

    with open("finished.txt", "a") as f:
        f.write(entry.code + "\n")

    return True


if not os.path.exists("finished.txt"):
    with open("finished.txt", "w") as f:
        f.write("")

open_network()
enter_maintenance()
with open("finished.txt", "r") as f:
    finished = f.readlines()

print(finished)
already_entered = []
first = True
for i, entry in enumerate(entries):
    if entry.code not in finished:
        if not enter_stock(entry, first=first):
            already_entered.append(entry)
            first = True
        else:
            first = False

print(*[e.code for e in already_entered], sep='\n')
with open("already_entered.txt", "w") as f:
    f.write("\n".join([e.code for e in already_entered]))

# Step 5: Send a Telegram message to Mom when the program is done
codes = '\n'.join([e.code for e in already_entered])
message = (
    f"Finished entering {len(entries) - len(already_entered)} entries"
    f" into Cougar Mountain. {len(already_entered)} duplicates found:"
    f"\n{codes}"
)
telegram_send.send(messages=[message])

# Step 6: Profit
