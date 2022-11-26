
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