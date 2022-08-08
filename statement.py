
import pyperclip as pyp


reduc = [
    "OTT PAY", "Fido", "Telus", "CRA Payroll",
    "Transfer", "FDL", "PROVINCE OF BC", "CRA GST"
]

def reduc_replace(row):
    for red in reduc:
        if red in row[1]:
            row[1] = red
            return

def zero_empty(cell):
    return to_num(cell) if cell else 0

def to_num(cell):
    return float(cell.replace(',', ''))

def add_digits(cell):
    if '.' not in cell:
        cell += ".00"
    
    return cell

def num_index(desc: str):
    i, found = 0, False
    while desc[i].isdigit() or not found:
        found = found or desc[i].isdigit()
        i += 1
    
    return i

if __name__ == "__main__":
    s = pyp.paste()
    cells = [r.split('\t') for r in s.splitlines()]

    new_cells = [cells[0][1:]]
    new_cells[0][2] = "Fund In"
    new_cells[0].insert(3, "Fund Out")

    bal = to_num(cells[-1][-1]) - to_num(cells[-1][-2])

    new_cells.append([
        "", "Beginning Balance", "", "", f'{bal:,}'
    ])

    extra_cells = []
    for row in cells[1:]:
        extra_cells.append([row[1], row[2],
            add_digits(row[3]) if to_num(row[3]) > 0 else "",
            add_digits(row[3][1:]) if to_num(row[3]) < 0 else "",
            0
        ])

    extra_cells.sort(key=lambda x: x[1])
    new_bal = bal
    for row in extra_cells:
        if "Cheque Cheque" in row[1]:
            row[1] = row[1][7:num_index(row[1])]
        elif any(r in row[1] for r in reduc):
            reduc_replace(row)
        elif "Direct Deposit" in row[1] or "MRCH" in row[1]:
            row[1] = row[1].split()[2]
        
        new_bal = round(new_bal + zero_empty(row[2]) - zero_empty(row[3]), 2)
        row[4] = f'{new_bal:,}'

    new_cells.extend(extra_cells)
    final = '\n'.join([
        '\t'.join(row) for row in new_cells
    ])

    pyp.copy(final)
