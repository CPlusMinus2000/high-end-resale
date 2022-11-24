
import pandas as pd
import pyperclip

from collections import namedtuple
from decimal import Decimal


StockItem = namedtuple("StockItem", [
    "number", "description", "quantity",
    "location", "price", "total", "value", "equal"
])

def is_stock_line(line):
    if not line.strip() or not line.split():
        return False
    
    s = line.split()[0]
    if '-' not in s or s != s.upper():
        return False
    
    last = s.split('-')[1][-4:]
    return len(s) <= 9 and (last.isdigit() or last.isalpha())


if __name__ == "__main__":
    with open("cougar_data/stock_value.txt", 'r') as f:
        stock_lines = f.readlines()

    i = prev = 0
    wrong = []
    stock_items = []
    while i < len(stock_lines):
        if is_stock_line(stock_lines[i]):
            l = stock_lines[i]
            m = stock_lines[i + 1].replace(".0000", " ", 1)
            m = m.replace('(', '-').replace(')', ' ')
            number = l.split()[0]
            description = l[10:l.index("FIFO")].strip()
            location = m.split()[0]
            quantity = int(m.split()[1])
            price = round(Decimal(m.split()[2]), 2)
            value = round(Decimal(m.split()[3].replace(',', '')), 2)
            equal = "YES"
            if value != quantity * price:
                wrong.append((i, description))
                equal = "NO"

            stock_items.append(StockItem(
                number, description, quantity,
                location, price, quantity * price, value, equal
            ))

            # Safety check
            if 2 < i - prev < 5:
                raise ValueError("Something wrong at line {}".format(i))
            
            prev = i

        i += 2


    # convert to dataframe
    df = pd.DataFrame(stock_items)
    df.head()


    # Convert to csv string and copy to clipboard
    pyperclip.copy(df.to_csv(sep='\t', index=False))
