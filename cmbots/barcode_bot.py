
import pyautogui
import time
import os

from platform import platform
from constants import c, locate_and_click, open_network, Entry
from filereader import read_excel

if "Windows" in platform():
    from pywinauto.keyboard import send_keys


# Step 1: Read the Excel file
if not os.path.exists(c("barcode.xlsx")):
    pyautogui.alert(
        "Please save the stock spreadsheet in the folder bot_data "
        "with the name barcode.xlsx."
    )
    exit()

entries = read_excel(c("barcode.xlsx"))
print(entries)

# Step 2: Open the RDP window and enter the barcode menu


def enter_stock_labels() -> None:
    """
    Use locate_and_click to enter the stock maintenance screen.
    """

    steps = [
        c(i) for i in [
            "file.png", "inventory.png",
            "reports.png", "stock_labels.png"
        ]
    ]

    if pyautogui.locateOnScreen(c("in_stock_labels.png")) is not None:
        # Menu is visible, but can't enter numbers. Exit.
        locate_and_click(c("file.png"))
        locate_and_click(c("exit.png"))
        if pyautogui.locateOnScreen(c("information.png")) is not None:
            # Made edits, have to cancel
            locate_and_click(c("no.png"))

    for step in steps:
        locate_and_click(step)

def setup() -> None:
    """
    Perform some setup tasks before entering the data.
    """
    
    pic = pyautogui.locateOnScreen(c("process_in.png"))
    if pic is not None:
        pyautogui.click(pic.left + pic.width, pic.top + pic.height // 2)
    
    send_keys("{TAB}I1")
    locate_and_click(c("barcode_on.png"))
    locate_and_click(c("select.png"))


open_network()
enter_stock_labels()
setup()

# Step 3: Enter the data into the system
def print_barcode(entry: Entry) -> None:
    """
    Print the barcode for the given entry.
    """
    
    sn = pyautogui.locateOnScreen(c("stock_number.png"))
    pyautogui.click(sn.left + sn.width + 2, sn.top + sn.height // 2)
    send_keys(entry.code + "{TAB}" + entry.code)