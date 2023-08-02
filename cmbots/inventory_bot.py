import time
import os
import re
import pyautogui
import telegram_send
import pyperclip

from platform import platform
from modules.constants import p, c, locate_and_click, Entry, open_network, \
    ImageNotFoundError
from modules.filereader import read_excel

if "Windows" in platform():
    from pywinauto.keyboard import send_keys
else:
    send_keys = lambda t: pyautogui.write(t, interval=0.05)


# So here's how the bot is going to need to work
# Step 1: Read the Excel sheet
# Do this by opening every page in the spreadsheet using pandas
# and then read row by row to assemble a list of entries

xls = os.path.exists(c("stock.xls"))
xlsx = os.path.exists(c("stock.xlsx"))

if not (xls or xlsx):
    pyautogui.alert(
        "Please save the stock spreadsheet in the folder bot_data "
        "with the name stock.xls or stock.xlsx. and try again."
    )
    exit()

name = "stock.xls" if xls else "stock.xlsx"
try:
    entries = read_excel(c(name))
except ValueError as e:
    pyautogui.alert(str(e))
    exit()

if not entries:
    pyautogui.alert("No entries found in the spreadsheet.")
    exit()

print(entries)

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
        "Please copy the signs information "
        "and save it in the folder bot_data/ as signs.txt."
    )
    exit()

try:
    with open(c("signs.txt"), 'r') as f:
        signs = f.read().strip().split("\n\n")
except UnicodeDecodeError as e:
    if "codec can't decode byte 0x93" in str(e):
        with open(c("signs.txt"), 'r', encoding="latin-1") as f:
            signs = f.read().strip()

        signs = signs.replace("0x93", '"').replace('?', '" ')
        signs = signs.split("\n\n")
    else:
        pyautogui.alert(
            "The signs file looks weird... I can't read it! :("
        )
        raise e

signs_map = {}
for s in signs:
    lines = s.splitlines()
    i = re.search(r"\d+", lines[0]).group(0)
    t = '\n'.join(lines[1:])
    signs_map[i] = t.split("   ")[0].strip()

requested = set()
for entry in entries:
    if entry.index in signs_map:
        # Check that the price is contained in the text
        if entry.price not in signs_map[entry.index].replace(',', ''):
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

                    entry.price = new_price.replace(',', '')

                elif res == "OK":
                    entry.price = guess.replace(',', '')

                else:
                    exit()

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

    elif entry.index not in requested:
        print(f"No sign data for {entry.index}")
        res = pyautogui.confirm(
            text=f"No sign data for {entry.index}. Continue?",
            title="CougarBot"
        )

        if res == "Cancel":
            exit()

        requested.add(entry.index)
        continue

print(entries[0])

# Step 3: Open Cougar Mountain through Remote Desktop and (optionally)
# locate the right places to click on the screen to insert text and save
# Alternatively, use human supervision to find the right values

from modules.constants import enter_maintenance

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
        for _ in range(5):
            try:
                locate_and_click(p("number.png"))
                break
            except pyautogui.ImageNotFoundException as e:
                time.sleep(0.5)
        
        else:
            raise e

    send_keys(entry.code + "{TAB}")
    tabs = 5
    on_hand = pyautogui.locateOnScreen(p("on_hand.png"))
    if on_hand is None:
        first = False
        tabs -= 1

    # Enter the location and description
    if first:
        tabs -= 2
        send_keys(entry.location + "{TAB 2}I1{TAB %d}" % tabs)
    else:
        send_keys(entry.location + "{TAB %d}" % tabs)

    # Now try to find the notes box. If it is not on screen,
    # then there must be a duplicate
    time.sleep(1)
    dup = pyautogui.locateOnScreen(p("notes.png"))
    if dup is None:
        # Duplicate detected.
        locate_and_click(p("cancel.png"))
        enter_maintenance()
        return False

    pyperclip.copy(entry.description)
    send_keys("^v")
    consign_grey = pyautogui.locateOnScreen(p("consignment_grey.png"))
    if entry.cnor.strip() not in ["nan", ''] and consign_grey is not None:
        send_keys("{TAB}" + entry.cnor)
        try:
            locate_and_click(p("serialized.png"))
        except ImageNotFoundError:
            # Looks like this consignment item is already in the system
            locate_and_click(p("cancel.png"))
            locate_and_click(p("no.png"))
            locate_and_click(p("file.png"))
            locate_and_click(p("main_menu.png"))
            enter_maintenance()
            return False

        locate_and_click(p("consignment.png"), pos='r')
        send_keys("{TAB 2}" + entry.cost)
    elif entry.cnor in ["nan", '']:
        send_keys("{TAB}{BACK}")

    locate_and_click(p("breaklist.png"), pos="br", stretch=3)
    send_keys(entry.price + "{TAB}")

    # lc = pyautogui.locateOnScreen(p("last_cost.png"))
    # pyautogui.click(lc.left + lc.width + 2, lc.top + 0.5 * lc.height)
    locate_and_click(p("last_cost.png"), pos='r', stretch=2)
    send_keys(entry.cost + "{TAB}")

    locate_and_click(p("sales.png"))
    locate_and_click(p("storing.png"), pos='r', stretch=2)
    send_keys(entry.price + "{TAB}")

    locate_and_click(p("notes.png"))
    pyperclip.copy(entry.notes)
    send_keys("^v")

    locate_and_click(p("save.png"))
    time.sleep(2)

    with open("finished.txt", 'a') as f:
        f.write(entry.code + "\n")

    return True


if not os.path.exists("finished.txt"):
    with open("finished.txt", "w") as f:
        f.write("")

try:
    open_network()
    enter_maintenance()
    with open("finished.txt", "r") as f:
        finished = f.readlines()

    already_entered = []
    first = True
    for i, entry in enumerate(entries):
        if entry.code not in finished:
            if not enter_stock(entry, first=first):
                already_entered.append(entry)
                first = True
            else:
                first = False

except ImageNotFoundError as e:
    pyautogui.alert(f"Could not find {e}!")
    exit()

# Step 5: Send a Telegram message to Mom when the program is done
codes = '\n'.join([e.code for e in already_entered])
message = (
    f"Finished entering {len(entries) - len(already_entered)} entries"
    f" into Cougar Mountain. {len(already_entered)} duplicates found:"
    f"\n{codes}"
)
telegram_send.send(messages=[message])

# Step 6: Profit
