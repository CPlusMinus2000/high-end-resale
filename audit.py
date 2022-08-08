# %%
from decimal import Decimal
from glob import glob
from collections import namedtuple
from datetime import datetime
from typing import Optional

import pandas as pd
import re

# %%
# Define useful containers

CashIn = namedtuple(
    "CashIn",
    [
        "Transaction_Date", "Reference", "Description",
        "Application", "Debit", "Credit"
    ]
)

CashOut = namedtuple(
    "CashOut",
    [
        "Transaction_Date", "Reference", "Description", "Application",
        "Payee", "Emp", "Invoice_Number", "Cheque_Number", "Debit", "Credit"
    ]
)

# %%
def is_inline(line: str) -> bool:
    """
    Determines if a line contains cash in information.
    """

    return line[:2].isdigit() and \
        line[3:5].isdigit() and \
        line[6:8].isdigit() and \
        line[8:16].isdigit()

def outline(line: str) -> Optional[str]:
    """
    Determines if a line contains cash out information.
    If it does, determines if it is of type AP or PR.
    """

    if line[:2].isdigit() and \
        line[3:5].isdigit() and \
        line[6:8].isdigit():

        return line[8:10]
    else:
        return None


if __name__ == "__main__":
    # %%
    # Read the files

    infile = glob("*[Cc][Aa][Ss][Hh] [Ii][Nn]*.txt")[0]
    with open(infile, 'r') as f:
        cash_in = f.readlines()

    outfile = glob("*[Cc][Aa][Ss][Hh] [Oo][Uu][Tt]*.txt")[0]
    with open(outfile, 'r') as f:
        cash_out = f.readlines()

    # %%
    # Process the Cash In
    cash_in_list = []
    for line in cash_in:
        line = line.strip()
        if is_inline(line):
            trans_date = datetime.strptime(line[:8], "%m/%d/%y").date()
            reference, description = line[8:16], line[16:40].strip()
            ind = next(i for i in range(40, 2000) if not line[i].isspace())
            application = line[ind:ind + 8].strip()

            # Calculate the amount of whitespace to the next non-whitespace char
            start = next(i for i in range(ind, 2000) if line[i].isspace()) - 1
            end = next(i for i in range(start + 1, 2000) if not line[i].isspace())
            amount = Decimal(line[end:].strip().replace(',', ''))
            debit = amount if end - start <= 12 else ""
            credit = amount if end - start > 12 else ""
        
            cash_in_list.append(CashIn(
                trans_date, reference, description,
                application, debit, credit
            ))
        
        elif "OVER/SHORTOver/Short" in line:
            trans_date = datetime.strptime(line[:8], "%m/%d/%y").date()
            reference, description = None, line[8:40].strip()
            ind = next(i for i in range(40, 2000) if not line[i].isspace())
            application = line[ind:ind + 8].strip()

            # Calculate the amount of whitespace to the next non-whitespace char
            start = next(i for i in range(ind, 2000) if line[i].isspace()) - 1
            end = next(i for i in range(start + 1, 2000) if not line[i].isspace())
            amount = Decimal(line[end:].strip().replace(',', ''))
            debit = amount if end - start <= 12 else ""
            credit = amount if end - start > 12 else ""
        
            cash_in_list.append(CashIn(
                trans_date, reference, description,
                application, debit, credit
            ))

    # %%
    df = pd.DataFrame(cash_in_list, columns=CashIn._fields)
    df = df.rename(columns={"Transaction_Date": "Date"})
    df = df.set_index("Date")
    df.to_excel("cash_in.xlsx", freeze_panes=(1, 0))

    # %%
    # Now the Cash Out
    cash_out_list, i = [], 0
    while i < len(cash_out):
        line = cash_out[i].strip()
        if outline(line) == "AP":
            trans_date = datetime.strptime(line[:8], "%m/%d/%y").date()
            reference, description = line[8:20], line[20:50].strip()
            ind = next(i for i in range(50, 2000) if not line[i].isspace())
            application = line[ind:ind + 8].strip()

            # Calculate the amount of whitespace to the next non-whitespace char
            start = next(i for i in range(ind, 2000) if line[i].isspace()) - 1
            end = next(i for i in range(start + 1, 2000) if not line[i].isspace())
            amount = Decimal(line[end:].strip().replace(',', ''))
            debit = amount if end - start <= 10 else ""
            credit = amount if end - start > 10 else ""

            # Also grab some info from the next line
            i += 1
            line_info = cash_out[i].strip().split(" / ")
            payee, invoice_number, cheque_number = line_info[0], None, line_info[-1]
            if len(line_info) > 2:
                invoice_number = line_info[1]
            
            cash_out_list.append(CashOut(
                trans_date, reference, description, application,
                payee, None, invoice_number, cheque_number, debit, credit
            ))
        
        elif outline(line) == "PR":
            trans_date = datetime.strptime(line[:8], "%m/%d/%y").date()
            reference, description = line[8:15], line[16:50].strip()
            ind = next(i for i in range(50, 2000) if not line[i].isspace())
            application = line[ind:ind + 8].strip()

            # Calculate the amount of whitespace to the next non-whitespace char
            start = next(i for i in range(ind, 2000) if line[i].isspace()) - 1
            end = next(i for i in range(start + 1, 2000) if not line[i].isspace())
            amount = Decimal(line[end:].strip().replace(',', ''))
            debit = amount if end - start <= 10 else ""
            credit = amount if end - start > 10 else ""

            # Also grab some info from the next line
            i += 1
            cheque_number = re.search("Ck# ([0-9]+)", cash_out[i].strip()).group(1)
            emp_number = re.search("Emp: ([0-9]+)", cash_out[i].strip()).group(1)
            
            cash_out_list.append(CashOut(
                trans_date, reference, description, application,
                None, emp_number, None, cheque_number, debit, credit
            ))
        
        i += 1

    # %%
    df = pd.DataFrame(cash_out_list, columns=CashOut._fields)
    df = df.rename(columns={
        "Transaction_Date": "Date",
        "Cheque_Number": "Ck #",
        "Invoice_Number": "Inv #",
        "Emp": "Emp #"
    })
    df = df.set_index("Date")
    df.to_excel("cash_out.xlsx", freeze_panes=(1, 0))
