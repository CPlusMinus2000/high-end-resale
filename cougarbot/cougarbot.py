import time
import os
import pandas as pd
import pyautogui
import telegram_send
import pyperclip

from typing import List
from dataclasses import dataclass
from platform import platform
from dotenv import load_dotenv

load_dotenv()

if "Windows" in platform():
    from pywinauto.keyboard import send_keys


CONVERT = ("+", "^", "%", "(", ")")
NETWORKS = ["networks/" + f for f in os.listdir("cougarbot_data/networks")]


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
    "index": "#",
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
    indices = {attr: titles.index(value) + 1 for attr, value in attrs.items()}

    indices["price"] = titles.index("Cost") + 3
    qindex = titles.index("Abdn") + 1
    for row in df.itertuples():
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


with open("cougarbot_data/signs.txt", "r") as f:
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


def c(f: str) -> str:
    """
    Short utility function for formatting file paths
    """

    return f"cougarbot_data/{f}"


def open_network() -> None:
    """
    Launch the remote desktop application by clicking on the icon.
    The exact icon image is finicky, so try a few different ones.
    """

    for network in NETWORKS:
        if pyautogui.locateOnScreen(c(network)) is not None:
            pyautogui.click(c(network))
            break
    
    raise Exception("Could not find network icon")


def locate_and_click(image: str, wait: float = 0.5) -> None:
    """
    Locate the image on the screen and click it
    """

    icon = pyautogui.locateOnScreen(image)
    if icon is None:
        raise ValueError(f"Could not find {image}")

    pyautogui.moveTo(icon)
    time.sleep(0.2)
    pyautogui.click()
    time.sleep(wait)


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

    if pyautogui.locateOnScreen(c("number.png")) is not None:
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
    lc = pyautogui.locateOnScreen(c("last_cost.png"))
    if lc is None:
        # Duplicate detected.
        # TODO: Set the bot to exit and re-enter maintenance, and continue
        # raise ValueError("Already in system")
        locate_and_click(c("cancel.png"))
        enter_maintenance()
        return False

    send_keys(entry.description + "{TAB}")

    bl = pyautogui.locateOnScreen(c("breaklist.png"))
    pyautogui.click(bl.left + bl.width, bl.top + bl.height + 3)
    time.sleep(0.3)
    send_keys(entry.price + "{TAB}")

    locate_and_click(c("last_cost.png"))
    send_keys(entry.cost + "{TAB}")

    locate_and_click(c("sales.png"))
    stor = pyautogui.locateOnScreen(c("storing.png"))
    pyautogui.click(stor.left + stor.width + 2, stor.top + 0.5 * stor.height)
    send_keys(entry.price + "{TAB}")

    locate_and_click(c("notes.png"))
    # send_keys(entry.notes, with_spaces=True)
    pyperclip.copy(entry.notes)
    send_keys("^v")

    locate_and_click(c("save.png"))
    time.sleep(2)

    with open(c("finished.txt"), "a") as f:
        f.write(entry.code + "\n")

    return True


if not os.path.exists(c("finished.txt")):
    with open(c("finished.txt"), "w") as f:
        f.write("")

open_network()
enter_maintenance()
with open(c("finished.txt"), "r") as f:
    finished = f.readlines()

print(finished)
already_entered = []
for i, entry in enumerate(entries):
    if entry.code not in finished:
        if not enter_stock(entry, first=i == 0):
            already_entered.append(entry)

print(*[e.code for e in already_entered], sep='\n')

# Step 5: Send a Telegram message to Mom when the program is done
# telegram_send.send(messages=["CougarBot is done!"])

# Step 6: Profit
