import time
import os
import pyautogui
import telegram_send
import pyperclip
import pandas as pd

from platform import platform
from modules.constants import p, locate_and_click, EntryTuple, \
    open_network, ImageNotFoundError, enter_maintenance

if "Windows" in platform():
    from pywinauto.keyboard import send_keys
else:
    send_keys = lambda t: pyautogui.write(t, interval=0.05)


def is_code(tag: str) -> bool:
    if len(tag.split('-')) != 2:
        return False

    left, right = tag.split('-')
    return 1 <= len(left) <= 4 and 2 <= len(right) <= 4


def send_message(found_len: int, initial: int):
    message = (
        f"Found {found_len - initial} new items in the stock database. "
        f"Total: {found_len} items have been recorded."
    )
    telegram_send.send(messages=[message])


REFRESH = False

# Step 1: Log into Cougar Mountain
try:
    open_network()
    res = enter_maintenance(mode='s')
    time.sleep(1)
except ImageNotFoundError:
    pyautogui.alert("Please make sure the RDP window is open and try again.")
    exit()

# Step 1.5: Read the Excel file to see what codes
# we have already scraped
found = set()
data = pd.DataFrame()
if not REFRESH and os.path.exists("bot_data/stock_database.xlsx"):
    sheets = pd.read_excel("bot_data/stock_database.xlsx", sheet_name=None)
    for sheetname, df in sheets.items():
        df = df.astype(str)
        found.update(zip(df["code"].values, df["location"].values))

    data = pd.concat(sheets.values())

initial = len(found)
ordered = sorted(found)
counter = 0
entries = []

# Step 2: Enter the find menu
try:
    if not res:
        locate_and_click(p("find.png"))
        if initial > 0:
            send_keys(ordered[-1][0])

        locate_and_click(p("select2.png"), wait=1)

    prev = ""
    while True:
        counter += 1
        locate_and_click(p("edit.png"))
        locate_and_click(p("save.png"), wait=2)
        for tries in range(5):
            send_keys("^c")
            code = pyperclip.paste()
            if is_code(code):
                break
        else:
            # sus...
            code = "CODE-FAIL"
        
        send_keys("{TAB}^c", pause=0.1)
        location = pyperclip.paste()
        send_keys("{TAB}")
        time.sleep(1)
        if ordered and prev > ordered[0][0] and code <= ordered[0][0]:
            # Managed to loop all the way around. Impressive effort. Done!
            break
        elif (code, location) in found:
            locate_and_click(p("right.png"))
            continue
        else:
            found.add((code, location))
            ordered.append((code, location))

        prev = code
        locate_and_click(p("edit.png"))
        if pyautogui.locateOnScreen(p("grey1.png")) is not None:
            send_keys("^c")
        else:
            send_keys("{TAB}^c")

        description = pyperclip.paste()

        locate_and_click(p("sales.png"))
        locate_and_click(p("storing.png"), pos='r', stretch=2)
        send_keys("^c")
        price = pyperclip.paste()

        locate_and_click(p("notes_small.png"))
        # Hold Shift, click on the corner
        try:
            locate_and_click(p("down.png"), pos="tl")
        except ImageNotFoundError:
            locate_and_click(p("down_black.png"), pos="tl")

        corner = pyautogui.locateOnScreen(p("corner.png"))
        if corner is None:
            # Empty note, cursor is getting in the way
            notes = ""
        else:
            pyautogui.dragTo(
                corner.left + corner.width,
                corner.top + corner.height,
                duration=1,
                tween=pyautogui.easeInOutQuad,
                button="left"
            )

            send_keys("^c")
            notes = pyperclip.paste()
    
        # Save the data
        entry = EntryTuple(code, description, location, price, notes)
        entries.append(entry._asdict())

        # Advance!
        locate_and_click(p("right.png"))
        if pyautogui.locateOnScreen(p("information.png")) is not None:
            locate_and_click(p("no.png"))

        # Every 20 new entries, save the results
        if len(entries) % 20 == 0:
            data_temp = pd.concat([data, pd.DataFrame.from_records(entries)])
            data_temp.to_excel("bot_data/stock_database.xlsx", index=False)

except ImageNotFoundError as e:
    pyautogui.alert(f"Could not find image {e}!")
except Exception as e:
    pyautogui.alert(f"An error occurred: {e}")
    raise
finally:
    if entries:
        data = pd.concat([data, pd.DataFrame.from_records(entries)])
        data.to_excel("bot_data/stock_database.xlsx", index=False)
        send_message(len(found), initial)
