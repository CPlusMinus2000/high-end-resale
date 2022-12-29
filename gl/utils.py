
import re
from typing import Tuple, Optional
from dataclasses import dataclass
from decimal import Decimal
from datetime import datetime

MONTHS = {
    "January": 1,
    "February": 2,
    "March": 3,
    "April": 4,
    "May": 5,
    "June": 6,
    "July": 7,
    "August": 8,
    "September": 9,
    "October": 10,
    "November": 11,
    "December": 12
}

LOCATIONS = ["Ware", "Hby", "Abdn"]
TAGS = ["AP", "AR", "GL"]
TAG_INDEX = 50
CREDIT_INDEX = 74

# =============================================================================
# Basic utility functions

def location(line: str, uppercase: bool=False) -> Optional[str]:
    """
    Is the line a location line?
    If so, return the location.
    """

    for loc in LOCATIONS:
        if uppercase:
            loc = loc.upper()

        if loc in line:
            return loc
    
    return None


def extract_month(line: str) -> Optional[str]:
    """
    Is the line a month line?
    If so, return the month.
    """

    for month in MONTHS:
        if month in line:
            return month
    
    return None


def balfor(line: str) -> bool:
    """
    Is the line a balance forward line?
    """

    return line.strip().startswith("Balance Forward")


def extract_balances(line: str) -> Tuple[Decimal]:
    """
    Extract the balances from a balance forward line.
    Index 0 is debits, index 1 is credits.
    """

    line = line.replace(',', '')
    return (
        Decimal(re.findall(r"\d+\.\d\d", line)[1]),
        Decimal(re.findall(r"\d+\.\d\d", line)[2])
    )


def totfor(line: str) -> Optional[str]:
    """
    Is the line a totals for line?
    If so, return the month.
    """

    for month in MONTHS:
        if month in line:
            return month
    
    return None


def extract_totals(line: str) -> Tuple[Decimal]:
    """
    Extract the totals from a totals line.
    Index 0 is debits, index 1 is credits.
    """

    line = line.replace(',', '')
    return (
        Decimal(re.findall(r"\d+\.\d\d", line)[0]),
        Decimal(re.findall(r"\d+\.\d\d", line)[1])
    )


def is_entry(line: str) -> bool:
    """
    Is the line an entry?
    """

    return re.match(r"^\d{2}/\d{2}/\d{2}", line.strip()) is not None


def extract_tag(line: str) -> Optional[str]:
    """
    Extract the tag from an entry line.
    """

    for tag in TAGS:
        if tag in line[TAG_INDEX:]:
            return tag
    
    return None


def extract_amt(line: str) -> Tuple[Decimal, bool]:
    """
    Extract the amount from a line.

    Also returns a boolean indicating whether the amount is ambiguous.
    Ambiguity is determined by checking if the amount stretches to
    or past the CREDIT_INDEX, and if are non-whitespace characters
    that are "pushing" the amount to that point.

    The existence of these characters gives me a headache.
    """

    mul = 1 if len(line) < CREDIT_INDEX else -1
    cand = line.split()[-1].replace(',', '')
    if len(line) > CREDIT_INDEX:
        return Decimal(re.findall(r"\d+\.\d\d", cand)[0]) * mul, True
    elif re.match(r"\d+\.\d\d", cand):
        return Decimal(cand) * mul, False
    elif re.search(r"\d+\.\d\d", cand) and mul == 1:
        amt = Decimal(re.findall(r"\d+\.\d\d", cand)[0]) * mul
        return Decimal(amt) * mul, False
    else:
        amt = Decimal(re.findall(r"\d+\.\d\d", cand)[0]) * mul
        return amt, True


# =============================================================================
# Headers

CFLOAT = "Cash Float-{loc}"
CCAOUT = "Cash chequing account-Out"


# =============================================================================
# Transaction class, for storing information in a consistent manner

@dataclass
class Transaction:
    date: str
    identifier: str
    amt: Decimal
    ambiguous: bool = False
    desc: str = ""

    def __str__(self):
        return f"{self.date}||{self.identifier}||{self.amt}||{self.desc}"
    
    def __eq__(self, other):
        return self.date == other.date and self.identifier == other.identifier
    
    def __hash__(self):
        return hash((self.date, self.identifier))
    
    def to_datetime(self):
        """
        Convert the date to a datetime object.
        """

        return datetime.strptime(self.date, "%m/%d/%y")
    
    def to_json(self):
        """
        Convert the transaction to a JSON serializable object.
        """

        return {
            "date": self.date,
            "identifier": self.identifier,
            "amt": str(self.amt),
            "ambiguous": self.ambiguous,
            "desc": self.desc
        }


# =============================================================================
# Testing

if __name__ == "__main__":
    credit = "01/22/22AP0642100006CellJan22phone bills          AP                409.23"
    debit = "01/15/22AP0640700001Void ck#11256                 AP           800.00"
    ambiguous = "02/27/22APR22-06Record Abdn landlord Fairchild security deposit paGL16,849.58"
    large = "08/26/22OCT22-04Record cash deposit after sell of WarehouseGL  1,456,501.91"
    not_amb = "02/27/22APR22-07Record Hornby landlord 815 Hornby security depGL7,342.66"

    assert is_entry(credit)
    assert is_entry(debit)
    assert is_entry(ambiguous)
    assert is_entry(large)
    assert is_entry(not_amb)

    assert extract_amt(credit) == (Decimal("-409.23"), False)
    assert extract_amt(debit) == (Decimal("800.00"), False)
    assert extract_amt(ambiguous) == (Decimal("-16849.58"), True)
    assert extract_amt(large) == (Decimal("-1456501.91"), True)
    assert extract_amt(not_amb) == (Decimal("7342.66"), False)
