
import os
from dataclasses import dataclass

TYPE_NOTES = False  # Do we type out notes or just copy and paste?
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


ATTRS = {
    "index": "#",
    "code": "Stock#",
    "description": "Description",
    "cost": "Cost",
}

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
