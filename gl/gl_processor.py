from datetime import datetime, timedelta
from utils import *
from typing import Dict, List, Callable
from tqdm import tqdm, trange

import json
import itertools
import pandas as pd
import argparse


class GLProcessor:
    def __init__(self, filename: str, yr: Optional[int]=None):
        self.filename = filename
        with open(filename, "r") as f:
            self.report = f.read()

        self.pages = [p.strip() for p in self.report.split("\n" * 7)]
        self.pagelines: List[List[str]] = [
            [l.strip() for l in p.splitlines()] for p in self.pages
        ]
        self.raw_pagelines = [[l for l in p.splitlines()] for p in self.pages]

        self.page = 0
        self.line = 0
        self.headers: Dict[str, Callable[[], None]] = {
            CFLOAT: self.process_cash_float,
            PURCH: lambda: self.process_inventory_like(PURCH),
            INVENT: lambda: self.process_inventory_like(INVENT),
            COGSBI: lambda: self.process_cogs(COGSBI),
            COGSMI: lambda: self.process_cogs(COGSMI),
            DTSHR: self.process_due_to_shareholder,
            STOPUR: lambda: self.process_inventory_like(STOPUR),
        } | {h: lambda h=h: self.process_generic(h) for h in GENERICS}
        self.header_numbers: Dict[str, str] = {}

        for key, func in self.headers.copy().items():
            if "{loc}" in key:
                for loc in LOCATIONS:
                    k = key.format(loc=loc)

                    def f(loc=loc, func=func):
                        func(location=loc)

                    self.headers[k] = f

                del self.headers[key]
            elif "{pos}" in key:
                for pos in POSITIONS:
                    k = key.format(pos=pos)

                    def f(pos=pos, func=func):
                        func(position=pos)

                    self.headers[k] = f

        self.transactions: Dict[str, List[Transaction]] = {
            h: [] for h in self.headers
        }

        z = Decimal(0)
        self.monthly_totals = {
            h: {m: [z, z] for m in MONTHS} for h in self.headers
        }

        self.balances: Dict[str, List[Decimal]] = {}
        self.balance_forwards: Dict[str, List[Transaction]] = {}
        self.valid: Dict[str, Dict[str, List[bool]]] = {
            h: {} for h in self.headers
        }

        self.totals = tuple()
        self.yr = yr

    def save(self, filename: Optional[str] = None) -> None:
        """
        Save the processed GL report to a file.
        """

        if not filename:
            filename = self.filename.replace(".txt", "_processed.json")

        t = {
            h: [transaction.to_json() for transaction in self.transactions[h]]
            for h in self.transactions
        }

        results = {
            "Transactions": t,
            "Monthly Totals": self.monthly_totals,
            "Balance Forward": self.balances,
            "Valid": self.valid,
        }

        with open(filename, "w") as f:
            json.dump(results, f, indent=4, default=float)

    def process_cash_float(self, location) -> None:
        """
        Process a single cash float entry.
        """

        p, l = self.page, self.line
        if not is_entry(self.pagelines[p][l]):
            raise ValueError(f"Line {l} of page {p + 1} is not an entry.")

        dt = self.pagelines[p][l][:8]
        iden = self.pagelines[p][l][8:16]
        amt, amb = extract_amt(self.pagelines[p][l])

        # For some reason these lines always have "GL" or "AP" in them,
        # near the end of the line, so we can use this
        # to determine where the description stops
        tag = extract_tag(self.pagelines[p][l])
        desc = self.pagelines[p][l][16:].split(tag)[0].strip()

        header = CFLOAT.format(loc=location)
        self.transactions[header].append(
            Transaction(dt, iden, amt, tag, amb, desc)
        )

        self.line += 2

    def process_inventory_like(self, header: str) -> None:
        """
        Process a single inventory-like entry.

        Inventory entries suck because sometimes they're just random items
        and sometimes they're regular Point of Sale entries.
        Gotta check for both.
        """

        p, l = self.page, self.line
        if not is_entry(self.pagelines[p][l]):
            raise ValueError(f"Line {l} of page {p + 1} is not an entry.")

        dt = self.pagelines[p][l][:8]
        amt, amb = None, None
        iden, tag = "", ""
        skip = 2

        # Inventory lines are weird.
        t = extract_tag(self.pagelines[p][l])
        if t == "PS":
            # Only shows up in Inventory, not in Purchases
            iden = self.pagelines[p][l][8:PS_INDEX]
            desc = self.pagelines[p][l][PS_INDEX:].split("PS")[0].strip()
            amt, amb = extract_amt(self.pagelines[p][l])
            tag = "PS"
        elif t == "AP":
            iden = self.pagelines[p][l][8:20]
            desc = self.pagelines[p][l][20:].split("AP")[0].strip()
            desc += ", " + self.pagelines[p][l + 1].strip()
            amt, amb = extract_amt(self.pagelines[p][l])
            tag = "AP"
        elif t == "GL":
            # Only shows up in Purchases, not in Inventory
            iden = self.pagelines[p][l][8:15]
            desc = self.pagelines[p][l][15:].split("GL")[0].strip()
            amt, amb = extract_amt(self.pagelines[p][l])
            tag = "GL"
        elif t is None:
            if re.search(r"TC: \dCNIN", self.pagelines[p][l]):
                # This is a CNIN entry, and can be ignored.
                self.line += 1
                return

            iden = self.pagelines[p][l][8:15]
            tag = location(self.pagelines[p][l], uppercase=True)
            desc = self.pagelines[p][l][15:].split(tag)[0].strip()
            g = self.pagelines[p][l].replace(BR1, " ")
            g = g.replace(BR2, " " * len(BR2))

            amt, amb = extract_amt(g)
            skip = 1
        else:
            # Huh?
            raise ValueError(f"Line {l} of page {p + 1} is not recognized.")

        self.transactions[header].append(
            Transaction(dt, iden, amt, tag, amb, desc)
        )

        # So apparently, sometimes the desc can just be non-existent?
        # In this case, the transaction only spans one line, so set skip to 1.
        if desc == "":
            skip = 1

        self.line += skip

    def process_cogs(self, header: str) -> None:
        """
        Process a single COGS entry.

        COGS entries suck because sometimes they're just random items
        and sometimes they're regular Point of Sale entries.
        Gotta check for both.
        """

        p, l = self.page, self.line
        if not is_entry(self.pagelines[p][l]):
            raise ValueError(f"Line {l} of page {p + 1} is not an entry.")

        dt = self.pagelines[p][l][:8]
        amt, amb = None, None
        iden = ""
        skip = 2

        # Inventory lines are weird.
        tag = extract_tag(self.pagelines[p][l])
        if tag == "PS":
            iden = self.pagelines[p][l][8:PS_INDEX]
            desc = self.pagelines[p][l][PS_INDEX:].split("PS")[0].strip()
            amt, amb = extract_amt(self.pagelines[p][l])
        elif tag == "AP":
            iden = self.pagelines[p][l][8:20]
            desc = self.pagelines[p][l][20:].split("AP")[0].strip()
            desc += ", " + self.pagelines[p][l + 1].strip()
            amt, amb = extract_amt(self.pagelines[p][l])
        elif tag == "GL":
            iden = self.pagelines[p][l][8:17]
            desc = self.pagelines[p][l][17:].split("GL")[0].strip()
            amt, amb = extract_amt(self.pagelines[p][l])
        elif tag is None:
            iden = self.pagelines[p][l][8:15]
            tag = location(self.pagelines[p][l], uppercase=True)
            desc = self.pagelines[p][l][15:].split(tag)[0].strip()
            g = self.pagelines[p][l].replace(BR2, " ")
            g = g.replace(BR1, " " * len(BR1))

            amt, amb = extract_amt(g)
            skip = 1
        else:
            # Huh?
            raise ValueError(f"Line {l} of page {p + 1} is not recognized.")

        self.transactions[header].append(
            Transaction(dt, iden, amt, tag, amb, desc)
        )

        self.line += skip

    def process_due_to_shareholder(self) -> None:
        p, l = self.page, self.line
        if not is_entry(self.pagelines[p][l]):
            raise ValueError(f"Line {l} of page {p + 1} is not an entry.")

        dt = self.pagelines[p][l][:8]
        amt, amb = None, None
        iden, tag = "", extract_tag(self.pagelines[p][l])
        skip = 2
        if l + 1 < len(self.pagelines[p]) and is_entry(
            self.pagelines[p][l + 1]
        ):

            skip = 1

        tag_dict = {
            "GL": 16,
            "AP": 20,
        }

        if tag is not None:
            ind = tag_dict[tag]
            iden = self.pagelines[p][l][8:ind]
            desc = self.pagelines[p][l][ind:].split(tag)[0].strip()
            amt, amb = extract_amt(self.pagelines[p][l])
            if skip == 2:
                desc += ", " + self.pagelines[p][l + 1].strip()
        else:
            iden = self.pagelines[p][l][8:15]
            tag = location(self.pagelines[p][l], uppercase=True)
            desc = self.pagelines[p][l][15:].split(tag)[0].strip()
            g = self.pagelines[p][l].replace(SH2, " ")
            g = g.replace(SH1, " " * len(SH1))

            amt, amb = extract_amt(g)
            skip = 1

        self.transactions[DTSHR].append(
            Transaction(dt, iden, amt, tag, amb, desc)
        )

        self.line += skip

    def process_generic(self, header) -> None:
        """
        Process a generic entry.
        """

        p, l = self.page, self.line
        if not is_entry(self.pagelines[p][l]):
            raise ValueError(f"Line {l} of page {p + 1} is not an entry.")

        dt = self.pagelines[p][l][:8]
        amt, amb = extract_amt(self.pagelines[p][l])
        iden = ""
        tag = extract_tag(self.pagelines[p][l])
        skip = 2
        if l + 1 < len(self.pagelines[p]) and is_entry(
            self.pagelines[p][l + 1]
        ) and num_spaces_at_start(self.raw_pagelines[p][l + 1]) < 2:
            skip = 1

        # Generic lines typically have two letters in them somewhere
        # that give us some information about how the entry is recorded.
        # These are AP, AR, PS, and GL. We can use this to determine where
        # the description stops, and also other formatting information.
        if extract_tag(self.pagelines[p][l]) == "AP":
            iden = self.pagelines[p][l][8:20]
            desc = self.pagelines[p][l][20:].split("AP")[0].strip()
            if skip == 2:
                desc += ", " + self.pagelines[p][l + 1].strip()

        elif extract_tag(self.pagelines[p][l]) == "AR":
            iden = self.pagelines[p][l][8:15]
            desc = self.pagelines[p][l][15:].split("AR")[0].strip()
        elif extract_tag(self.pagelines[p][l]) == "GL":
            ind = PS_INDEX if self.pagelines[p][l][8].isdigit() else 16
            iden = self.pagelines[p][l][8:ind]
            desc = self.pagelines[p][l][ind:].split("GL")[0].strip()
        elif extract_tag(self.pagelines[p][l]) == "PS":
            if OVERSHORT in self.pagelines[p][l]:
                iden = OVERSHORT
                n = self.pagelines[p][l].find(OVERSHORT) + len(OVERSHORT)
                desc = self.pagelines[p][l][n:].split("PS")[0].strip()
            else:
                iden = self.pagelines[p][l][8:PS_INDEX]
                desc = self.pagelines[p][l][PS_INDEX:].split("PS")[0].strip()

        elif extract_tag(self.pagelines[p][l]) == "PR":
            iden = self.pagelines[p][l][8:15]
            desc = self.pagelines[p][l][15:].split("PR")[0].strip()
            if skip == 2:
                desc += ", " + self.pagelines[p][l + 1].strip()

        elif "IN" in self.pagelines[p][l].split()[-1]:
            if re.search(r"TC: \dCNIN", self.pagelines[p][l]):
                # This is a CNIN entry, and can be ignored.
                self.line += 1
                return

            iden = self.pagelines[p][l][8:15]
            tag = location(self.pagelines[p][l], uppercase=True)
            desc = self.pagelines[p][l][15:].split(tag)[0].strip()
            g = self.pagelines[p][l].replace(BR1, " ")
            g = g.replace(BR2, " " * len(BR2))

            amt, amb = extract_amt(g)
            skip = 1
        else:
            print("Line: " + self.pagelines[p][l])
            raise ValueError(f"Line {l} of page {p + 1} has an unknown tag.")

        self.transactions[header].append(
            Transaction(dt, iden, amt, tag, amb, desc)
        )

        self.line += skip

    def validate(self) -> None:
        """
        Validates the processed GL report by comparing the
        transaction amounts to the known monthly totals,
        storing the results of comparison in self.valid.
        """

        for header in self.transactions:
            calculations = {month: [0, 0] for month in MONTHS}
            header_total = [0, 0]
            for transaction in self.transactions[header]:
                m = MONTH_INDICES[transaction.to_datetime().month]
                calculations[m][0] += transaction.debit
                calculations[m][1] += transaction.credit

            for month in MONTHS:
                header_total[0] += self.monthly_totals[header][month][0]
                header_total[1] += self.monthly_totals[header][month][1]
                if calculations[month] == self.monthly_totals[header][month]:
                    self.valid[header][month] = True
                elif header == INVENT:
                    t_diff = calculations[month][0] - calculations[month][1]
                    m_diff = (
                        self.monthly_totals[header][month][0]
                        - self.monthly_totals[header][month][1]
                    )
                    self.valid[header][month] = t_diff == m_diff
                else:
                    self.valid[header][month] = False

            self.valid[header][ALL] = (
                self.balances[header] == header_total
            )

        # Also check the totals over all headers
        debs = sum(self.balances[h][0] for h in self.balances)
        creds = sum(self.balances[h][1] for h in self.balances)
        print((debs, creds), self.totals)
        self.valid[ALL] = (debs, creds) == self.totals

    @property
    def all_valid(self) -> bool:
        """
        Checks whether all entries are valid.
        """

        valid = True
        for header in self.valid:
            if header == ALL:
                continue

            valid = valid and all(self.valid[header][m] for m in MONTHS)

        valid = valid and all(
            self.valid[h][ALL] for h in self.valid if h != ALL
        )
        valid = valid and self.valid[ALL]

        return valid

    def disambiguate(self, header: str, month: str) -> None:
        """
        Attempts to use ambiguity values in transactions to
        disambiguate between debit and credit entries,
        where the values cannot be determined from indentation.
        To do this, it loops through all possible permutations
        of entries and compares them against the monthly totals,
        saving the disambiguated results once identified.

        NOTE: This procedure assumes that there is one and only one
        correct permutation that matches the monthly totals.
        This is unlikely to be true in general, but I have no idea
        how to solve the general problem with the knowledge I am
        in possession of.
        """

        deb = Decimal(self.monthly_totals[header][month][0])
        cred = Decimal(self.monthly_totals[header][month][1])
        if not self.valid[header][month]:
            # How many ambiguous values are there?
            amb_indices = [
                i
                for i, v in enumerate(self.transactions[header])
                if v.to_datetime().month == MONTHS[month] and v.ambiguous
            ]

            for t in self.transactions[header]:
                if t.to_datetime().month == MONTHS[month] and not t.ambiguous:
                    deb -= t.debit
                    cred -= t.credit

            n = len(amb_indices)
            ambs = [self.transactions[header][i] for i in amb_indices]
            perms = itertools.product([-1, 1], repeat=n)
            for perm in tqdm(perms, total=2**n):
                ambs_copy = ambs.copy()
                for i, v in enumerate(perm):
                    ambs_copy[i] *= v

                tdeb = sum(t.debit for t in ambs_copy)
                tcred = sum(t.credit for t in ambs_copy)
                if (tdeb == deb and tcred == cred) or (
                    header == INVENT and tdeb - tcred == deb - cred
                ):
                    self.valid[header][month] = True
                    for j, t in enumerate(ambs_copy):
                        self.transactions[header][amb_indices[j]] = t

                    break
            else:
                tlen = len(self.transactions[header])
                amts = [abs(float(t.amt)) for t in ambs]
                raise ValueError(
                    f"Could not disambiguate {header} for {month}. "
                    f"The correct totals are {deb} and {cred}, "
                    f"but the calculated totals are {tdeb} and {tcred}. "
                    f"There are {tlen} transactions in total, "
                    f"and the ambiguous amounts are: {amts}."
                )

    def line_loop(self) -> None:
        """
        Iterate over the lines of a page, and add entries accordingly.
        """

        self.line = 8
        p = self.page
        while self.line < len(self.pagelines[p]):
            x = self.pagelines[p][self.line].split(" " * 10)[0]
            if x == "Totals for Report":
                self.line += 2
                self.totals = extract_balances(self.pagelines[p][self.line])
                return

            num, header = x.split(" " * 4)
            if header is None:
                return
            elif header not in self.header_numbers:
                self.header_numbers[header] = num

            self.line += 2
            while self.line < len(self.pagelines[p]):
                if is_entry(self.pagelines[p][self.line]):
                    self.headers[header]()
                elif totfor(self.pagelines[p][self.line]):
                    month = extract_month(self.pagelines[p][self.line])
                    deb, cred = extract_totals(self.pagelines[p][self.line])
                    self.monthly_totals[header][month][0] += deb
                    self.monthly_totals[header][month][1] += cred
                    self.line += 1
                elif balfor(self.pagelines[p][self.line]):
                    self.line += 1
                    deb, cred = extract_balances(self.pagelines[p][self.line])
                    op, clos = extract_balance_forwards(
                        self.pagelines[p][self.line]
                    )

                    opt = Transaction(
                        f"01/01/{self.yr % 100}",
                        "",
                        op,
                        "",
                        desc="Balance Forward"
                    )

                    clost = Transaction(
                        f"12/31/{self.yr % 100}",
                        "",
                        clos,
                        "",
                        desc="Ending Balance"
                    )

                    self.balances[header] = [deb, cred]
                    self.balance_forwards[header] = [opt, clost]
                    self.line += 2
                    break
                else:
                    # ???
                    raise ValueError(
                        f"Line {self.line} of page {self.page + 1}, "
                        f"{self.pagelines[p][self.line]}, "
                        "is not recognized."
                    )

    def process(self) -> None:
        """
        Process the GL report.
        """

        for p in trange(len(self.pagelines)):
            self.page = p
            self.line_loop()

        # Drop all headers with no transactions
        self.transactions = {
            k: v for k, v in self.transactions.items() if len(v) > 0
        }

        self.valid = {
            k: v for k, v in self.valid.items() if k in self.transactions
        }

        for h in self.transactions:
            print(f"{h}: {len(self.transactions[h])} transactions")
            print(f"Balance Forward: {self.balances[h]}" + "\n")

        self.validate()
        self.save()
        if not self.all_valid:
            for h in self.transactions:
                for m in MONTHS:
                    if not self.valid[h][m]:
                        print(f"Disambiguating {h} for {m}")
                        self.disambiguate(h, m)

        print(self.all_valid)
        self.save()
        print("Done.")

    def save_to_excel(self, filename: Optional[str] = None) -> None:
        """
        Save the processed GL report to an Excel file.
        """

        if filename is None:
            filename = self.filename.replace(".txt", ".xlsx")

        header_order = sorted(
            self.transactions.keys(),
            key=lambda x: float(self.header_numbers[x])
        )

        with pd.ExcelWriter(filename) as writer:
            for header in header_order:
                opt, clost = self.balance_forwards[header]
                trs = [opt] + self.transactions[header] + [clost]
                df = pd.DataFrame([t.to_excel_json() for t in trs])
                # safe_header = header.replace("/", "-")
                safe_header = self.header_numbers[header]
                df.to_excel(writer, sheet_name=safe_header, index=False)
            
            # Combine all transactions into a single sheet
            full_list = []
            for header in header_order:
                num = self.header_numbers[header]
                for transaction in self.transactions[header]:
                    full_list.append(transaction.to_excel_json(header=num))

            df = pd.DataFrame(full_list)
            df.to_excel(writer, sheet_name="Summary", index=False)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Process a GL report.")
    parser.add_argument(
        "filename",
        type=str,
        help="The filename of the GL report to process."
    )

    args = parser.parse_args()
    fname = args.filename
    yr = int(re.search(r"\d{4}", fname).group(0))

    g = GLProcessor(fname, yr)
    try:
        g.process()
    except Exception:
        print(g.pagelines[g.page][g.line], g.page + 1, g.line)
        raise

    g.save_to_excel()
