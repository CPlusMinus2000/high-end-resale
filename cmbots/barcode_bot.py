
import pyautogui
import time

from platform import platform
from constants import *

if "Windows" in platform():
    from pywinauto.keyboard import send_keys


# Step 1: Read the Excel file


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


open_network()
enter_stock_labels()


# Just check to see if we can click on the bullet
locate_and_click(c("select.png"))