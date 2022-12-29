
from datetime import datetime
from utils import *
from typing import Dict, List, Callable

import json


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
            CCAOUT: lambda: self.process_generic(CCAOUT)
        }

        for key, func in self.headers.copy().items():
            if "{loc}" in key:
                for loc in LOCATIONS:
                    k = key.format(loc=loc)
                    def f(loc=loc, func=func):
                        print(loc)
                        func(location=loc)

                    self.headers[k] = f

                del self.headers[key]

        self.transactions: Dict[str, List[Transaction]] = {
            h: [] for h in self.headers
        }

        z = Decimal(0)
        self.monthly_totals = {
            h: {m: [z, z] for m in MONTHS}
            for h in self.headers
        }
    
        self.balance_forward: Dict[str, List[Decimal]] = {}
    

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
            "Balance Forward": self.balance_forward
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
            Transaction(dt, iden, amt, amb, desc)
        )

        self.line += 2
    

    def process_generic(self, header) -> None:
        """
        Process a generic entry.
        """

        p, l = self.page, self.line
        if not is_entry(self.pagelines[p][l]):
            raise ValueError(f"Line {l} of page {p} is not an entry.")
        
        dt = self.pagelines[p][l][:8]
        iden = self.pagelines[p][l][8:20]
        amt, amb = extract_amt(self.pagelines[p][l])

        # Generic lines typically have two letters in them somewhere
        # that give us some information about how the entry is recorded.
        # These are AP, AR, and GL. We can use this to determine where
        # the description stops, and also other formatting information.
        if extract_tag(self.pagelines[p][l]) == "AP":
            desc = self.pagelines[p][l][20:].split("AP")[0].strip()
            desc += ', ' + self.pagelines[p][l + 1].strip()

        self.transactions[header].append(
            Transaction(dt, iden, amt, amb, desc)
        )

        self.line += 2
    
    
    def line_loop(self) -> None:
        """
        Iterate over the lines of a page, and add entries accordingly.
        """

        self.line = 8
        p = self.page
        while self.line < len(self.pagelines[p]):
            print(self.pagelines[p][self.line])
            header = next(
                h for h in self.headers
                if h in self.pagelines[p][self.line]
            )

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

            # At the end of every page, save the current results
            self.save()

        for h in self.headers:
            print(f"{h}: {len(self.transactions[h])} transactions")
            print(f"Debits: {self.monthly_totals[h][0]}")
            print(f"Credits: {self.monthly_totals[h][1]}")
            print(f"Balance Forward: {self.balance_forward[h]}")
            print()

        print("Done.")


if __name__ == "__main__":
    yr = datetime.now().year
    fname = f"GL{yr}.txt"
    GLProcessor(fname).process()
