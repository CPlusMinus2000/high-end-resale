# %%
from decimal import Decimal
from glob import glob
from collections import namedtuple, defaultdict
from datetime import datetime

import pandas as pd


MONTHS = [
    "Jan", "Feb", "March", "April", "May", "June",
    "July", "Aug", "Sept", "Oct", "Nov", "Dec"
]

# %%
def is_inventory(s):
    """
    Checks if a piece of text holds an inventory item.
    """

    return s.isdigit() or \
        s.startswith("CC") and s[2:].isdigit() or \
        s.startswith("CN") and s[2:].isdigit()

# %%
# Define a relevant money class and namedtuple

class Money:
    def __init__(self, amt=0):
        if isinstance(amt, str):
            amt = amt.replace(",", "").replace("$", "")
        elif isinstance(amt, type(None)):
            amt = 0
        
        self.amt = Decimal(amt)
    
    def __eq__(self, other):
        return self.amt == other.amt
    
    def __lt__(self, other):
        return self.amt < other.amt
    
    def __gt__(self, other):
        return self.amt > other.amt
    
    def __str__(self):
        if self.amt < 0:
            return f"-${-self.amt:,.2f}"
        
        return "{:,.2f}".format(self.amt)
    
    def __repr__(self):
        return str(self)
    
    def __hash__(self):
        return hash(self.amt)
    
    def __neg__(self):
        return Money(-self.amt)
    
    def __add__(self, other):
        return Money(self.amt + other.amt)
    
    def __sub__(self, other):
        return Money(abs(self.amt - other.amt))
    
    def __mul__(self, other):
        return Money(self.amt * other)
    
    def __truediv__(self, other):
        return Money(self.amt / other)


InventoryItem = namedtuple(
    "InventoryItem",
    [
        "cn_number", "cn_date", "linestock", "description",
        "location", "quantity", "price", "status", "stat_date"
    ]
)

InvoiceItem = namedtuple(
    "InvoiceItem",
    ["invoice_number", "mult", "cn_number", "inv_date", "amt"]
)

if __name__ == "__main__":
    # %%
    # Parse the CN, if it exists
    both = True

    cnfiles = glob("cougar_data/*CN*.txt")
    if len(cnfiles) >= 1:
        cnfile = cnfiles[0]
        with open(cnfile, "r") as f:
            cn = f.read()

        month = next(
            (m for m in MONTHS if m in cnfile),
            None
        )

        # %%
        cn_items, i = [], 0
        cn_lines = cn.splitlines()
        while i < len(cn_lines):
            contents = [t for t in cn_lines[i].split(' ') if t]
            if contents and is_inventory(contents[0]):
                cn_number = cn_lines[i][:10].strip()
                cn_date = datetime.strptime(cn_lines[i][11:21], "%m/%d/%Y").date()
                linestock = cn_lines[i][22:31].strip()
                description = cn_lines[i][34:45].strip()

                location = cn_lines[i][45:56].strip()
                quantity = int(cn_lines[i][56:60].strip())
                price = Money(cn_lines[i][60:68].strip())
                status = cn_lines[i][69:77].strip()
                stat_date = datetime.strptime(
                    cn_lines[i][78:88], "%m/%d/%Y").date()

                i += 1
                while i < len(cn_lines) and \
                    cn_lines[i].startswith(' ' * 21) and \
                    "show line" not in cn_lines[i]:
                    
                    description += cn_lines[i].strip()
                    i += 1
                
                cn_items.append(InventoryItem(
                    cn_number, str(cn_date), linestock, description,
                    location, quantity, str(price), status, str(stat_date)
                ))

            else:
                i += 1

        # %%
        df = pd.DataFrame(cn_items, columns=InventoryItem._fields)
        df = df.set_index("cn_number")
        df.to_excel(f"cougar_data/{month}_items.xlsx", freeze_panes=(1, 0))
    
    else:
        both = False

    # %%
    # Now parse the CC

    ccfiles = glob("cougar_data/*CC*.txt")
    if len(ccfiles) >= 1:
        ccfile = ccfiles[0]
        with open(ccfile, "r") as f:
            cc = f.read()
        
        month = next(
            (m for m in MONTHS if m in ccfile),
            None
        )

        invoices = []
        for line in cc.splitlines():
            if line.strip().startswith("Invoice"):
                contents = line.split('/')
                invoice_number = contents[0].strip().split()[-1]
                cn_number = contents[1].strip()
                mult = 'X' if len(contents[2]) > 2 else ''
                ind = next(
                    i for i, t in enumerate(contents)
                    if len(t) == 2
                )

                inv_date = datetime.strptime(
                    line.split('/')[ind] + line.split('/')[ind + 1], "%d%Y%m"
                ).date()

                amt = Money(contents[-1].split('$')[-1])
                invoices.append(InvoiceItem(
                    invoice_number, mult, cn_number, str(inv_date), str(amt)
                ))

        df = pd.DataFrame(invoices, columns=InventoryItem._fields)
        df = df.set_index("invoice_number")
        df.to_excel(f"cougar_data/{month}_invoices.xlsx", freeze_panes=(1, 0))
    
    else:
        both = False

    # Compare the daily totals for the CN and CC

    if both:
        cn_dict, cc_dict = defaultdict(Money), defaultdict(Money)
        for item in cn_items:
            cn_dict[item.stat_date] += Money(item.price) * item.quantity

        for item in invoices:
            cc_dict[item.inv_date] += Money(item.amt)

        dates = sorted(cn_dict.keys() | cc_dict.keys())
        cn_list, cc_list, diff_list = [], [], []
        for d in dates:
            cn_list.append(cn_dict.get(d))
            cc_list.append(cc_dict.get(d))
            cnd = Money() if cn_dict.get(d) is None else cn_dict.get(d)
            ccd = Money() if cc_dict.get(d) is None else cc_dict.get(d)
            diff_list.append(cnd - ccd)

        # Turn the lists into a dataframe
        df = pd.DataFrame(
            {
                "CN": cn_list,
                "CC": cc_list,
                "Diff": diff_list
            }, index=dates
        )

        df.to_excel(f"cougar_data/{month}_totals.xlsx")
