
import pyautogui
import time
import os

from platform import platform
from modules.constants import p, c, locate_and_click, open_network, Entry, \
    ImageNotFoundError
from modules.filereader import read_excel

if "Windows" in platform():
    from pywinauto.keyboard import send_keys
else:
    from pyautogui import typewrite as send_keys


# Step 1: Read the Excel file
xls = os.path.exists(c("barcode.xls"))
xlsx = os.path.exists(c("barcode.xlsx"))


if not xls or xlsx:
    pyautogui.alert(
        "Please save the stock spreadsheet in the folder bot_data "
        "with the name barcode.xls or barcode.xlsx."
    )
    exit()

name = "barcode.xls" if xls else "barcode.xlsx"
try:
    entries = read_excel(c(name), mode='b')
except ValueError as e:
    pyautogui.alert(str(e))
    exit()

print(entries)

# Step 2: Open the RDP window and enter the barcode menu


def enter_stock_labels() -> None:
    """
    Use locate_and_click to enter the stock maintenance screen.
    """

    steps = [
        p(i) for i in [
            "file.png", "inventory.png",
            "reports.png", "stock_labels.png"
        ]
    ]

    if pyautogui.locateOnScreen(p("in_stock_labels.png")) is not None:
        # Menu is visible, but can't enter numbers. Exit.
        locate_and_click(p("file.png"))
        locate_and_click(p("exit.png"))
        if pyautogui.locateOnScreen(p("information.png")) is not None:
            # Made edits, have to cancel
            locate_and_click(p("no.png"))

    for step in steps:
        locate_and_click(step)


def setup() -> None:
    """
    Perform some setup tasks before entering the data.
    """

    locate_and_click(p("process_in.png"), pos='r')
    send_keys("{TAB}I1")
    locate_and_click(p("barcode_on.png"))
    locate_and_click(p("select.png"))


try:
    open_network()
    enter_stock_labels()
    setup()
except ImageNotFoundError as e:
    pyautogui.alert(f"Image not found: {e}")
    exit()


# Step 3: Enter the data into the system
def print_barcode(entry: Entry) -> None:
    """
    Print the barcode for the given entry.
    """

    locate_and_click(p("stock_number.png"), pos='r', stretch=2)
    send_keys(entry.code + "{TAB}" + entry.code)
    time.sleep(0.1)
    send_keys("{TAB 5}" + entry.location + "{TAB}" + entry.location)

    # Since the printer can only handle two-digit numbers,
    # use some funny logic to print the right number of labels.
    quant = int(entry.quantity)
    while quant > 0:
        amt_to_print = str(min(quant, 99))
        locate_and_click(p("quantity.png"), pos='r', stretch=2)
        send_keys(amt_to_print)
        locate_and_click(p("ok.png"))
        time.sleep(5 + 0.3 * int(amt_to_print))
        quant -= int(amt_to_print)

    with open("finished_barcodes.txt", 'a') as f:
        f.write(entry.code + '\n')


if not os.path.exists("finished_barcodes.txt"):
    with open("finished_barcodes.txt", "w") as f:
        f.write("")

with open("finished_barcodes.txt", "r") as f:
    finished = f.readlines()
    entries = [e for e in entries if e.code not in finished]

try:
    for i, entry in enumerate(entries):
        print_barcode(entry)
        if pyautogui.locateOnScreen(p("in_stock_labels.png")) is None:
            locate_and_click(p("file.png"))
            locate_and_click(p("inventory.png"))
except ImageNotFoundError as e:
    pyautogui.alert(f"Image not found: {e}")
    exit()
