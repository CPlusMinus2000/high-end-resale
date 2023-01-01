
from datetime import datetime, timedelta
from utils import *
from typing import Dict, List, Callable
from tqdm import tqdm

import json
import itertools


class GLProcessor:
    def __init__(self, filename: str):
        self.filename = filename
        with open(filename, 'r') as f:
            self.report = f.read()

        self.pages = [p.strip() for p in self.report.split('\n' * 7)]
        self.pagelines = [
            [
                l.strip() for l in p.splitlines()
            ]
            for p in self.pages
        ]

        self.page = 0
        self.line = 0
        self.headers: Dict[str, Callable[[], None]] = {
            CFLOAT: self.process_cash_float,
            INVENT: self.process_inventory
        } | {
            h: lambda h=h: self.process_generic(h)
            for h in GENERICS
        }

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
            h: {m: [z, z] for m in MONTHS}
            for h in self.headers
        }
    
        self.balance_forward: Dict[str, List[Decimal]] = {}
        self.valid: Dict[str, Dict[str, List[bool]]] = {
            h: {} for h in self.headers
        }
    

    def save(self, filename: Optional[str]=None) -> None:
        """
        Save the processed GL report to a file.
        """

        if not filename:
            filename = self.filename.replace(".txt", "_processed.json")
        
        t = {
            h: [
                transaction.to_json()
                for transaction in self.transactions[h]
            ]
            for h in self.transactions
        }

        results = {
            "Transactions": t,
            "Monthly Totals": self.monthly_totals,
            "Balance Forward": self.balance_forward,
            "Valid": self.valid
        }

        with open(filename, 'w') as f:
            json.dump(results, f, indent=4, default=float)

    
    def process_cash_float(self, location) -> None:
        """
        Process a single cash float entry.
        """

        p, l = self.page, self.line
        if not is_entry(self.pagelines[p][l]):
            raise ValueError(f"Line {l} of page {p} is not an entry.")
        
        dt = self.pagelines[p][l][:8]
        iden = self.pagelines[p][l][8:16]
        amt, amb = extract_amt(self.pagelines[p][l])

        # For some reason these lines always have "GL" in them,
        # near the end of the line, so we can use this
        # to determine where the description stops
        desc = self.pagelines[p][l][16:].split("GL")[0].strip()

        header = CFLOAT.format(loc=location)
        self.transactions[header].append(
            Transaction(dt, iden, amt, "GL", amb, desc)
        )

        self.line += 2
    

    def process_inventory(self) -> None:
        """
        Process a single inventory entry.

        Inventory entries suck because sometimes they're just random items
        and sometimes they're regular Point of Sale entries.
        Gotta check for both.
        """

        p, l = self.page, self.line
        if not is_entry(self.pagelines[p][l]):
            raise ValueError(f"Line {l} of page {p} is not an entry.")
        
        dt = self.pagelines[p][l][:8]
        amt, amb = None, None
        iden, tag = "", ""
        skip = 2

        # Inventory lines are weird.
        t = extract_tag(self.pagelines[p][l])
        if t == "PS":
            iden = self.pagelines[p][l][8:17]
            desc = self.pagelines[p][l][17:].split("PS")[0].strip()
            amt, amb = extract_amt(self.pagelines[p][l])
            tag = "PS"
        elif t == "AP":
            iden = self.pagelines[p][l][8:20]
            desc = self.pagelines[p][l][20:].split("AP")[0].strip()
            desc += ', ' + self.pagelines[p][l + 1].strip()
            amt, amb = extract_amt(self.pagelines[p][l])
            tag = "AP"
        elif t == "GL":
            iden = self.pagelines[p][l][8:17]
            desc = self.pagelines[p][l][17:].split("GL")[0].strip()
            amt, amb = extract_amt(self.pagelines[p][l])
            tag = "GL"
        elif t is None:
            iden = self.pagelines[p][l][8:15]
            tag = location(self.pagelines[p][l], uppercase=True)
            desc = self.pagelines[p][l][15:].split(tag)[0].strip()
            g = self.pagelines[p][l].replace(
                BR1, ' ').replace(BR2, ' ' * len(BR2))

            amt, amb = extract_amt(g)
            skip = 1
        else:
            # Huh?
            raise ValueError(f"Line {l} of page {p} is not recognized.")

        self.transactions[INVENT].append(
            Transaction(dt, iden, amt, tag, amb, desc)
        )

        self.line += skip
    

    def process_generic(self, header) -> None:
        """
        Process a generic entry.
        """

        p, l = self.page, self.line
        if not is_entry(self.pagelines[p][l]):
            raise ValueError(f"Line {l} of page {p} is not an entry.")
        
        dt = self.pagelines[p][l][:8]
        amt, amb = extract_amt(self.pagelines[p][l])
        iden = tag = ""

        # Generic lines typically have two letters in them somewhere
        # that give us some information about how the entry is recorded.
        # These are AP, AR, and GL. We can use this to determine where
        # the description stops, and also other formatting information.
        if extract_tag(self.pagelines[p][l]) == "AP":
            iden = self.pagelines[p][l][8:20]
            desc = self.pagelines[p][l][20:].split("AP")[0].strip()
            desc += ', ' + self.pagelines[p][l + 1].strip()
            tag = "AP"
        elif extract_tag(self.pagelines[p][l]) == "AR":
            iden = self.pagelines[p][l][8:15]
            desc = self.pagelines[p][l][15:].split("AR")[0].strip()
            tag = "AR"
        elif extract_tag(self.pagelines[p][l]) == "GL":
            iden = self.pagelines[p][l][8:16]
            desc = self.pagelines[p][l][16:].split("GL")[0].strip()
            tag = "GL"
        elif extract_tag(self.pagelines[p][l]) == "PS":
            iden = self.pagelines[p][l][8:17]
            desc = self.pagelines[p][l][17:].split("PS")[0].strip()
            tag = "PS"
        elif extract_tag(self.pagelines[p][l]) == "PR":
            iden = self.pagelines[p][l][8:15]
            desc = self.pagelines[p][l][15:].split("PR")[0].strip()
            desc += ', ' + self.pagelines[p][l + 1].strip()
            tag = "PR"
        else:
            print("Line: " + self.pagelines[p][l])
            raise ValueError(f"Line {l} of page {p} has an unknown tag.")

        self.transactions[header].append(
            Transaction(dt, iden, amt, tag, amb, desc)
        )

        self.line += 2
    

    def validate(self) -> None:
        """
        Validates the processed GL report by comparing the
        transaction amounts to the known monthly totals,
        storing the results of comparison in self.valid.
        """

        for header in self.transactions:
            calculations = {month: [0, 0] for month in MONTHS}
            for transaction in self.transactions[header]:
                m = MONTH_INDICES[transaction.to_datetime().month]
                calculations[m][0] += transaction.debit
                calculations[m][1] += transaction.credit
            
            for month in MONTHS:
                if calculations[month] == self.monthly_totals[header][month]:
                    self.valid[header][month] = True
                else:
                    self.valid[header][month] = False
    

    def all_valid(self) -> bool:
        """
        Checks whether all entries are valid.
        """

        valid = True
        for header in self.valid:
            for month in self.valid[header]:
                valid = valid and self.valid[header][month]

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
                i for i, v in enumerate(self.transactions[header])
                if v.to_datetime().month == MONTHS[month]
                and v.ambiguous
            ]

            for t in self.transactions[header]:
                if t.to_datetime().month == MONTHS[month] and \
                    not t.ambiguous:

                    deb -= t.debit
                    cred -= t.credit
            
            print(deb, cred)
            n = len(amb_indices)
            ambs = [self.transactions[header][i] for i in amb_indices]
            perms = list(itertools.product([-1, 1], repeat=n))
            for perm in tqdm(perms):
                for i, v in enumerate(perm):
                    ambs[i] *= v
                
                tdeb = sum(t.debit for t in ambs)
                tcred = sum(t.credit for t in ambs)
                if tdeb == deb and tcred == cred:
                    self.valid[header][month] = True
                    for j, t in enumerate(ambs):
                        self.transactions[header][amb_indices[j]] = t

                    break
            else:
                raise ValueError(
                    f"Could not disambiguate {header} for {month}."
                )


    def line_loop(self) -> None:
        """
        Iterate over the lines of a page, and add entries accordingly.
        """

        self.line = 8
        p = self.page
        while self.line < len(self.pagelines[p]):
            print(self.pagelines[p][self.line])
            header = next(
                (
                    h for h in self.headers
                    if h in self.pagelines[p][self.line]
                ), None
            )

            if header is None:
                return

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
                    self.balance_forward[header] = [deb, cred]
                    self.line += 2
                    break
                else:
                    # ???
                    raise ValueError(
                        f"Line {self.line} of page {self.page} "
                        "is not recognized."
                    )
        
    
    def process(self) -> None:
        """
        Process the GL report.
        """

        for p in range(len(self.pagelines)):
            self.page = p
            self.line_loop()

        for h in self.transactions:
            print(f"{h}: {len(self.transactions[h])} transactions")
            print(f"Balance Forward: {self.balance_forward[h]}" + "\n")

        self.validate()
        self.save()
        print(self.all_valid())
        if not self.all_valid():
            for h in self.transactions:
                for m in MONTHS:
                    if not self.valid[h][m]:
                        print(f"Disambiguating {h} for {m}")
                        self.disambiguate(h, m)
                        print(self.valid[h][m])
                        print()

        self.save()
        print("Done.")


if __name__ == "__main__":
    yr = (datetime.now() - timedelta(days=60)).year
    fname = f"GL{yr}.txt"
    GLProcessor(fname).process()
