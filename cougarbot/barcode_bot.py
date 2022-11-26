
import pyautogui
import time

from platform import platform
from constants import *

if "Windows" in platform():
    from pywinauto.keyboard import send_keys


