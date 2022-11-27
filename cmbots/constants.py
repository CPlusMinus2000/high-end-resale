
import os
import pyautogui
import time
from dataclasses import dataclass

CONVERT = ("+", "^", "%", "(", ")")
NETWORKS = ["networks/" + f for f in os.listdir("bot_data/networks")]


@dataclass
class Entry:
    index: str = ""
    code: str = ""
    description: str = ""
    cnor: str = ""
    location: str = ""
    quantity: str = ""
    cost: str = ""
    price: str = ""
    notes: str = ""

    def __getitem__(self, key):
        return getattr(self, key)

    def __setitem__(self, key, value):
        setattr(self, key, value)


ATTRS = {
    "index": "#",
    "code": "Stock#",
    "description": "Description",
    "quantity": "Qty.",
    "cost": "Cost",
    "cnor": "Cnor"
}


def c(f: str) -> str:
    """
    Short utility function for formatting file paths
    """

    return f"bot_data/{f}"


def p(f: str) -> str:
    """
    Short utility function for formatting image file paths
    """

    return f"bot_data/images/{f}"


def open_network() -> None:
    """
    Launch the remote desktop application by clicking on the icon.
    The exact icon image is finicky, so try a few different ones.
    """

    for network in NETWORKS:
        if pyautogui.locateOnScreen(c(network)) is not None:
            pyautogui.click(c(network))
            return

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
