
import os
import pyautogui
import time
from dataclasses import dataclass

CONVERT = ("+", "^", "%", "(", ")")
NETWORKS = ["networks/" + f for f in os.listdir("bot_data/images/networks")]


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


class ImageNotFoundError(Exception):
    pass


ATTRS = {
    "index": "#",
    "code": "Stock#",
    "description": "Description",
    "quantity": "Qty.",
    "price": "Sell Price",
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
        if pyautogui.locateOnScreen(p(network)) is not None:
            pyautogui.click(p(network))
            return

    raise Exception("Could not find network icon")


POSITIONS = {
    'c': (0.5, 0.5, 0, 0),
    't': (0.5, 0, 0, -1),
    'b': (0.5, 1, 0, 1),
    'l': (0, 0.5, -1, 0),
    'r': (1, 0.5, 1, 0),
    'tl': (0, 0, -1, -1),
    'tr': (1, 0, 1, -1),
    'bl': (0, 1, -1, 1),
    'br': (1, 1, 1, 1)
}


def locate_and_click(
    image: str,
    wait: float = 0.5,
    pos: str = 'c',
    stretch: int = 0
) -> None:
    """
    Locate the image on the screen and click it.

    :param image: The image to locate
    :param wait: The amount of time to wait after clicking
    :param pos: The position to click. 
    'c' for center, 't' for top, 'b' for bottom, 'l' for left, 'r' for right
    Vertical and horizontal positions can be combined, e.g. 'tl' for top left
    :param stretch: The amount of pixels past the pos to click
    Useful when you need to click just outside the bounding box of an image
    """

    assert pos in ('c', 't', 'b', 'l', 'r', 'tl', 'tr', 'bl', 'br')

    icon = pyautogui.locateOnScreen(image)
    if icon is None:
        raise ImageNotFoundError(f"{image}")
    
    x, y = icon.left, icon.top
    w, h = icon.width, icon.height
    x, y = x + w * POSITIONS[pos][0], y + h * POSITIONS[pos][1]
    x, y = x + POSITIONS[pos][2] * stretch, y + POSITIONS[pos][3] * stretch

    pyautogui.moveTo(x, y)
    time.sleep(0.2)
    pyautogui.click()
    time.sleep(wait)
