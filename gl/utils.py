
import re
from typing import Tuple, Optional, Dict, Any
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

MONTH_INDICES = {v: k for k, v in MONTHS.items()}
LOCATIONS = ["Ware", "Hby", "Abdn"]
POSITIONS = ["Staff", "Employer"]
TAGS = ["AP", "AR", "GL", "PS", "PR"]
TAG_INDEX = 50
ALL = "All"

BR1 = "1BRKIN"
BR2 = "2BRKIN"

# How far into a line the amount will start at for credits
# This assumes the line has been stripped first
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
            loc = loc.replace("Ware", "Warehouse").upper()

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


def extract_amt(line: str, mul: Optional[int]=None) -> Tuple[Decimal, bool]:
    """
    Extract the amount from a line.

    Also returns a boolean indicating whether the amount is ambiguous.
    Ambiguity is determined by checking if the amount stretches to
    or past the CREDIT_INDEX, and if are non-whitespace characters
    that are "pushing" the amount to that point.

    The existence of these characters gives me a headache.
    """

    if mul is None:
        mul = 1 if len(line) < CREDIT_INDEX else -1

    assert mul in [-1, 1]

    cand = line.split()[-1].replace(',', '')
    if len(line) > CREDIT_INDEX:
        return Decimal(re.findall(r"\d+\.\d\d", cand)[0]) * mul, True
    elif re.fullmatch(r"\d+\.\d\d", cand):
        return Decimal(cand) * mul, False
    elif re.match(r"\d+\.\d\d", cand):
        # Interesting
        print(f"Very interesting, {cand}")
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
TDBIZ = "TD Business Investor Account"
USCHEQ = "US $ Chequing Account"
USEXCH = "US $ Account Exchange"
ACCREC = "Accounts Receivalbe"
GSTINC = "GST Input Credit"
INVENT = "Inventory"
PREPAY = "Prepaid"
ACCPAY = "Accounts Payable"
ACCPAYC = "Accounts Payable-Consignment"
USACCP = "US Accounts Payable"
CPPPAY = "CPP Payable-{pos}"
EIPAY = "EI Payable-{pos}"
PTPAY = "Payroll Tax Payable"
GSTPAY = "GST Payable"
PSTPAY = "PST Payable"
CORTPAY = "Corporate Taxes Payable"
DTSHR = "Due to Shareholder"
SALESH = "Sales - Hornby St."
SALESA = "Sales - Abdn"
SALESW = "Sale of Warehouse"
INTERI = "Interest Income"
PSTCOM = "PST comm"
COGSOL = "Cost of Goods Sold"
COGSBI = "COGS - Broken item w/o"
COGSMI = "COGS - Missing item w/o"
CASHSO = "Cash Short/Over"
REPMAI = "Repair & Maintenance"
SECAL = "Security/Alarm"
SECALH = "Security/Alarm-Hby"
STORSU = "Store Supplis"
TELE = "Telephone"
TELEH = "Telephone-Hby"
TELEW = "Telephone-Ware"
WAGESG = "Wages-Gal"
WAGESA = "Wages-Aberdeen"
ACC = "Accounting"
BANKCH = "Bank Charges"
PROPT = "Property Tax"
LEGAL = "Legal"
OFFICE = "Office"
STRATA = "Strata Fee"
UTIL = "Utilities"

GENERICS = [
    CCAOUT, TDBIZ, USCHEQ, USEXCH, ACCREC, GSTINC, PREPAY,
    ACCPAY, ACCPAYC, USACCP, CPPPAY, EIPAY, PTPAY, GSTPAY,
    PSTPAY, CORTPAY, DTSHR, SALESH, SALESA, SALESW, INTERI,
    PSTCOM, COGSOL, CASHSO, REPMAI, SECAL, SECALH, STORSU,
    TELE, TELEH, TELEW, WAGESG, WAGESA, ACC, BANKCH, PROPT,
    LEGAL, OFFICE, STRATA, UTIL
]

generics_adapted = []
for genera in GENERICS:
    if "{pos}" in genera:
        for pos in POSITIONS:
            generics_adapted.append(genera.format(pos=pos))
    elif "{loc}" in genera:
        for loc in LOCATIONS:
            generics_adapted.append(genera.format(loc=loc))
    else:
        generics_adapted.append(genera)

GENERICS = generics_adapted


# =============================================================================
# Transaction class, for storing information in a consistent manner

@dataclass
class Transaction:
    date: str
    identifier: str
    amt: Decimal
    tag: str
    ambiguous: bool = False
    desc: str = ""

    def __str__(self) -> str:
        d, i, a = self.date, self.identifier, self.amt
        t, a, desc = self.tag, self.ambiguous, self.desc
        return f"{d}||{i}||{a}||{t}||{a}||{desc}"

    def __eq__(self, other) -> bool:
        return self.date == other.date and self.identifier == other.identifier
    
    def __neg__(self) -> "Transaction":
        return Transaction(
            self.date, self.identifier, -self.amt,
            self.tag, self.ambiguous, self.desc
        )
    
    def __mul__(self, other: float) -> "Transaction":
        return Transaction(
            self.date, self.identifier, self.amt * other,
            self.tag, self.ambiguous, self.desc
        )
    
    def __rmul__(self, other: float) -> "Transaction":
        return self * other
    
    def __hash__(self) -> int:
        return hash((self.date, self.identifier))
    
    @property
    def debit(self) -> Decimal:
        """
        Return the debit amount.
        """

        return self.amt if self.amt > 0 else 0
    
    @property
    def credit(self) -> Decimal:
        """
        Return the credit amount.
        """

        return -self.amt if self.amt < 0 else 0
    
    def to_datetime(self) -> datetime:
        """
        Convert the date to a datetime object.
        """

        return datetime.strptime(self.date, "%m/%d/%y")
    
    def to_json(self) -> Dict[str, Any]:
        """
        Convert the transaction to a JSON serializable object.
        """

        return {
            "date": self.date,
            "identifier": self.identifier,
            "amt": str(self.amt),
            "tag": self.tag,
            "ambiguous": self.ambiguous,
            "desc": self.desc
        }
    
    def to_excel_json(self) -> Dict[str, Any]:
        """
        Convert the transaction to a JSON serializable object,
        but without the ambiguous tag.
        """

        return {
            "date": self.date,
            "identifier": self.identifier,
            "amt": str(self.amt),
            "tag": self.tag,
            "desc": self.desc,
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
