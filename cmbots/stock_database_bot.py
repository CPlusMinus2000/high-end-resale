import time
import os
import pyautogui
import telegram_send
import pyperclip
import pandas as pd

from platform import platform
from modules.constants import p, c, locate_and_click, Entry, EntryTuple, \
    open_network, ImageNotFoundError, enter_maintenance

if "Windows" in platform():
    from pywinauto.keyboard import send_keys
else:
    send_keys = lambda t: pyautogui.write(t, interval=0.05)


REFRESH = True

# Step 1: Log into Cougar Mountain
try:
    open_network()
    enter_maintenance()
except ImageNotFoundError:
    pyautogui.alert(
        "Please make sure the RDP window is open and try again."
    )
    exit()

# Step 1.5: Read the Excel file to see what codes
# we have already scraped
found = set()
data = pd.DataFrame()
if not REFRESH and os.path.exists("bot_data/stock_database.xlsx"):
    sheets = pd.read_excel("bot_data/stock_database.xlsx", sheet_name=None)
    for sheetname, df in sheets.items():
        df = df.astype(str)
        found.update(df["Code"].values)

    data = pd.concat(sheets.values())
elif not REFRESH:
    pyautogui.alert(
        "Please save the stock spreadsheet in the folder bot_data "
        "with the name stock_database.xlsx."
    )
    exit()

initial = len(found)
ordered = sorted(found)

# Step 2: Enter the find menu
try:
    locate_and_click(p("find.png"))
    locate_and_click(p("select2.png"))
    
    while True:
        locate_and_click(p("edit.png"))
        locate_and_click(p("save.png"), wait=3)
        send_keys("^c")
        code = pyperclip.paste()
        if code <= ordered[0]:
            break
        elif code in found:
            locate_and_click(p("right.png"))
            continue
        else:
            found.add(code)
            ordered.append(code)

        send_keys("{TAB}^c")
        location = pyperclip.paste()
        send_keys("{TAB}")
        locate_and_click(p("edit.png"))
        send_keys("{TAB}^c")
        description = pyperclip.paste()

        locate_and_click(p("breaklist.png"), pos="br", stretch=3)
        send_keys("^c")
        price = pyperclip.paste()[:-2]

        locate_and_click(p("notes_small.png"))
        # Hold Shift, click on the corner
        locate_and_click(p("down.png"), pos="tl")
        corner = pyautogui.locate(p("corner.png"))
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
        entry = EntryTuple(code, location, description, price, notes)
        data = data.append(entry._asdict(), ignore_index=True)

        # Advance!
        locate_and_click(p("right.png"))

except ImageNotFoundError as e:
    pyautogui.alert(f"Could not find image {e}!")
    raise


# Step 3: Save the data
data.to_excel("bot_data/stock_database.xlsx", index=False)

# Step 4: Send Mom a Telegram message
message = (
    f"Found {len(found) - initial} new items in the stock database. "
    f"Total: {len(found)}"
)
telegram_send.send(messages=[message])