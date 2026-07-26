"""
Build the annotation workbook.

A CSV is the wrong format to hand to someone: Excel in a French locale expects a
semicolon, guesses the encoding, and turns accented text into mojibake. This writes an
.xlsx instead, with the trajectory ids already filled in, a dropdown restricted to the
valid labels, and the task text alongside each row so the annotator can keep their place
without switching windows.

    python make_sheet.py
"""
import json
import os

from openpyxl import Workbook
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.utils import get_column_letter
from openpyxl.worksheet.datavalidation import DataValidation

HERE = os.path.dirname(os.path.abspath(__file__))
LABELS = ["S", "F1a", "F1b", "F2", "F3", "F4", "F5", "F6", "F7"]
GLOSS = {
    "S": "genuine success",
    "F1a": "called a tool that does not exist",
    "F1b": "called an existing but unfit tool",
    "F2": "well-formed argument containing an invented value, not reused as the pivot",
    "F3": "residual: wrong or incomplete answer from mishandled information",
    "F4": "repeats an equivalent step without progress",
    "F5": "stops, or answers empty, before finishing",
    "F6": "final answer contradicts a value the agent itself produced",
    "F7": "fabricated value used as the pivot of the final result",
}

rows = [json.loads(l) for l in open(os.path.join(HERE, "sample_blind.jsonl"),
                                    encoding="utf-8") if l.strip()]

wb = Workbook()

# ---------------------------------------------------------------- sheet 1: the grid
ws = wb.active
ws.title = "annotations"
head = ["id", "label", "confidence", "notes", "task (for reference)", "steps"]
ws.append(head)
for c in range(1, len(head) + 1):
    cell = ws.cell(row=1, column=c)
    cell.font = Font(bold=True)
    cell.fill = PatternFill("solid", fgColor="DDE6F0")
ws.freeze_panes = "A2"

for r in rows:
    ws.append([r["id"], "", "", "", r["task"], len(r["trajectory"])])

dv = DataValidation(type="list", formula1='"' + ",".join(LABELS) + '"',
                    allow_blank=True, showDropDown=False)
dv.error = "Use one of: " + ", ".join(LABELS)
dv.errorTitle = "Not a valid label"
dv.prompt = "Pick the category of the FIRST observable fault, or S."
dv.promptTitle = "Label"
ws.add_data_validation(dv)
dv.add(f"B2:B{len(rows) + 1}")

dvc = DataValidation(type="list", formula1='"1,2,3"', allow_blank=True, showDropDown=False)
dvc.prompt = "1 unsure, 2 fairly sure, 3 certain. Optional."
dvc.promptTitle = "Confidence"
ws.add_data_validation(dvc)
dvc.add(f"C2:C{len(rows) + 1}")

for col, w in zip("ABCDEF", (10, 10, 12, 46, 60, 8)):
    ws.column_dimensions[col].width = w
for row in ws.iter_rows(min_row=2, max_row=len(rows) + 1):
    row[4].alignment = Alignment(wrap_text=True, vertical="top")
    row[3].alignment = Alignment(wrap_text=True, vertical="top")

# ---------------------------------------------------------------- sheet 2: the codebook
cb = wb.create_sheet("codebook")
cb.append(["Apply the checks IN THIS ORDER and stop at the first one that fires."])
cb.append(["The label is the FIRST observable fault, not the state the trajectory ends in."])
cb.append([])
cb.append(["order", "label", "meaning"])
for c in range(1, 4):
    cb.cell(row=4, column=c).font = Font(bold=True)
for n, l in enumerate(LABELS[1:], 1):
    cb.append([n, l, GLOSS[l]])
cb.append(["", "S", GLOSS["S"]])
cb.append([])
cb.append(["For F3 you may add a sub-code in the notes column, if it is clear:"])
cb.append(["", "F3a", "wrong calculation over values that were retrieved correctly"])
cb.append(["", "F3b", "the fact was present but the agent queried the wrong key"])
cb.append(["", "F3c", "partial answer, or an answer not grounded in what was retrieved"])
cb.append([])
cb.append(["Do not try to guess the other annotator's label. Disagreement is the "
           "informative outcome."])
cb.append(["Work alone, and do not discuss individual items until this sheet is returned."])
for col, w in zip("ABC", (8, 10, 96)):
    cb.column_dimensions[col].width = w
cb["A1"].font = Font(bold=True)

out = os.path.join(HERE, "annotations_annotator2.xlsx")
wb.save(out)
print(f"written: {os.path.basename(out)}  ({len(rows)} rows, dropdown on B and C)")
