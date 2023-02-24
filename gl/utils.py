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
    "December": 12,
}

MONTH_INDICES = {v: k for k, v in MONTHS.items()}
LOCATIONS = ["Ware", "Hby", "Abdn"]
POSITIONS = ["Staff", "Employer"]
TAGS = ["AP", "AR", "GL", "PS", "PR"]
TAG_INDEX = 50
ALL = "All"

BR1 = "1BRKIN"
BR2 = "2BRKIN"
SH1 = "1SHIN"
SH2 = "2SHIN"
OVERSHORT = "OVER/SHORT"

# How far into a line the amount will start at for credits
# This assumes the line has been stripped first
CREDIT_INDEX = 74

# What index are the ends of PS (Point of Sale) IDs located at?
# Sometimes it's 16, sometimes it's 17. Shove it in a constant.
PS_INDEX = 16

# =============================================================================
# Basic utility functions


def location(line: str, uppercase: bool = False) -> Optional[str]:
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
    Index 1 is debits, index 2 is credits.
    """

    line = line.replace(",", "")
    return (
        Decimal(re.findall(r"\d+\.\d\d", line)[1]),
        Decimal(re.findall(r"\d+\.\d\d", line)[2]),
    )


def extract_balance_forwards(line: str) -> Tuple[Decimal]:
    """
    Extract the opening and closing balances from a balance forward line.
    If we take all the numbers out of the line (for example using regex),
    index 0 is the opening balance and index 4 is the closing balance.
    However, there's a slight complication: the number can be positive or
    negative, and the sign can only be determined by examining the characters
    immediately after the amount. "CR" is credit (negative) and "DR" is debit
    (positive).

    There's probably a way to identify the DR/CR, but I'm just
    going to go with first- and last-based indexing. Easy.
    """

    muls = {"DR": 1, "CR": -1}

    line = line.replace(',', '')
    amts = re.findall(r"\d+\.\d\d", line)
    drcr = re.findall("[CD]R", line)
    opening = Decimal(amts[0])
    if opening != 0:
        opening *= muls[drcr[0]]
    
    closing = Decimal(amts[4])
    if closing != 0:
        closing *= muls[drcr[-1]]

    return opening, closing


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

    line = line.replace(",", "")
    return (
        Decimal(re.findall(r"\d+\.\d\d", line)[0]),
        Decimal(re.findall(r"\d+\.\d\d", line)[1]),
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


def extract_amt(line: str, mul: Optional[int] = None) -> Tuple[Decimal, bool]:
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

    cand = line.split()[-1].replace(",", "")
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
CCAIN = "Cash Chequing Account-In"
CCAOUT = "Cash chequing account-Out"
TDBIZ = "TD Business Investor Account"
CCSA = "Coastal Capital Saving Account"
CCM = "Coastal Capital Membership"
USCHEQ = "US $ Chequing Account"
USEXCH = "US $ Account Exchange"
ARCLR = "AR Clearing"
ACCREC = "Accounts Receivalbe"
GSTINC = "GST Input Credit"
PURCH = "Purchases"
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
ACC = "Accounting"
ADVP = "Advertising & Promotion"
APPR = "Appraisal"
BANKCH = "Bank Charges"
BUTRP = "Business Travel/Parking"
COGSOL = "Cost of Goods Sold"
COGSBI = "COGS - Broken item w/o"
COGSMI = "COGS - Missing item w/o"
COGSA = "COGS - Abdn"
COGSBC = "COGS - Boxes & Chains"
COGSBCA = "COGS -Boxes & Chains-Abdn"
COMPNM = "Computer/Network Maintenance"
COSTMI = "Cost of Misc items"
CASHSO = "Cash Short/Over"
CASHOSA = "Cash Over/Short-Abdn"
CASHOSH = "Cash Over/Short-HBY"
CCCOMA = "Credit Card Commissions-Abdn"
CCCOMH = "Credit Card Commissions-Hby"
COMHAD = "Computer Hardware"
DUESF = "Dues & Fees"
ENTERT = "Entertainment"
FURNE = "Furniture & Equipment"
GOODW = "Goodwill"
INSUR = "Insurance"
INCTAX = "Income Taxes"
LEGAL = "Legal"
OFFICE = "Office"
POLIRE = "Polishing & Repair"
PROPT = "Property Tax"
RENTA = "Rent-Abdn"
RENTH = "Rent-Hby"
REPMAI = "Repair & Maintenance"
SABOCA = "Sales Boxes & Chains - Abdn"
SABOCH = "Sales Boxes & Chains - HBY"
SMITEM = "Sales-Misc. Items"
SALESD = "Sales Discount"
SECAL = "Security/Alarm"
SECALH = "Security/Alarm-Hby"
SPECO = "Special Order"
STORSU = "Store Supplis"
STRATA = "Strata Fee"
TELE = "Telephone"
TELEA = "Telephone-Abdn"
TELEH = "Telephone-Hby"
TELEW = "Telephone-Ware"
UTIL = "Utilities"
UTILA = "Utilities-Abdn"
WAGES = "Wages"
WAGESG = "Wages-Gal"
WAGESA = "Wages-Abdn"
WAGESAL = "Wages-Aberdeen"
WAGESH = "Wages-HBY"

GENERICS = [
    CCAIN,
    CCAOUT,
    TDBIZ,
    CCSA,
    CCM,
    USCHEQ,
    USEXCH,
    ARCLR,
    ACCREC,
    GSTINC,
    PREPAY,
    ACCPAY,
    ACCPAYC,
    USACCP,
    CPPPAY,
    EIPAY,
    PTPAY,
    GSTPAY,
    PSTPAY,
    CORTPAY,
    SALESH,
    SALESA,
    SALESW,
    INTERI,
    PSTCOM,
    COGSOL,
    COGSA,
    COGSBC,
    COGSBCA,
    COMPNM,
    COSTMI,
    CASHSO,
    CASHOSA,
    CASHOSH,
    CCCOMA,
    CCCOMH,
    COMHAD,
    DUESF,
    ENTERT,
    FURNE,
    GOODW,
    INCTAX,
    INSUR,
    POLIRE,
    RENTA,
    RENTH,
    REPMAI,
    SABOCA,
    SABOCH,
    SMITEM,
    SALESD,
    SECAL,
    SECALH,
    SPECO,
    STORSU,
    TELE,
    TELEA,
    TELEH,
    TELEW,
    WAGES,
    WAGESA,
    WAGESAL,
    WAGESG,
    WAGESH,
    ACC,
    ADVP,
    APPR,
    BANKCH,
    BUTRP,
    PROPT,
    LEGAL,
    OFFICE,
    STRATA,
    UTIL,
    UTILA,
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

    def __eq__(self, other: "Transaction") -> bool:
        return self.date == other.date and self.identifier == other.identifier

    def __neg__(self) -> "Transaction":
        return Transaction(
            self.date,
            self.identifier,
            -self.amt,
            self.tag,
            self.ambiguous,
            self.desc,
        )

    def __mul__(self, other: float) -> "Transaction":
        return Transaction(
            self.date,
            self.identifier,
            self.amt * other,
            self.tag,
            self.ambiguous,
            self.desc,
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

    def to_json(self) -> Dict[str, str]:
        """
        Convert the transaction to a JSON serializable object.
        """

        return {
            "date": self.date,
            "identifier": self.identifier,
            "amt": str(self.amt),
            "tag": self.tag,
            "ambiguous": self.ambiguous,
            "desc": self.desc,
        }

    def to_excel_json(self, header: Optional[str]=None) -> Dict[str, Any]:
        """
        Convert the transaction to a JSON serializable object,
        but without the ambiguous tag.

        If header is given, it will be used as the first key.
        """

        d = {} if header is None else { "account": header }

        return d | {
            "date": self.date,
            "identifier": self.identifier,
            "debit": "" if self.credit > 0 else float(self.debit),
            "credit": "" if self.credit == 0 else float(self.credit),
            "tag": self.tag,
            "desc": self.desc,
        }


# =============================================================================
# Testing

if __name__ == "__main__":
    credit = "01/22/22AP0642100006CellJan22phone bills          AP                409.23"
    debit = (
        "01/15/22AP0640700001Void ck#11256                 AP           800.00"
    )
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
