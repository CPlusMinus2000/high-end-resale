
import pyautogui
import time

from platform import platform
from constants import *

if "Windows" in platform():
    from pywinauto.keyboard import send_keys


# Just check to see if we can click on the bullet
open_network()
locate_and_click(c("select.png"))