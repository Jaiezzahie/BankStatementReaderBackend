import re
import pdfplumber
import pandas as pd
import os
from datetime import datetime

DATE_PATTERN = re.compile(r"^(\d{2} \w{3} \d{2})\s+(.*)$")


def save_to_csvs(transactions_list, prefix):
  script_dir = os.path.dirname(os.path.abspath(__file__))  # folder of Main.py
  income, outgoings = [], []

  for t in transactions_list:
    if t is None:
      continue
    if t["type"] == "IN":
      income.append([t["date"], t["desc"], t["paid_in"], t["add_info"]])
    else:
      outgoings.append([t["date"], t["desc"], t["tx_type"], t["cheque_number"], t["paid_out"]])

  if income:
    pd.DataFrame(income, columns=["Date", "Description", "Payed In", "Additional Info"]).to_csv(
      os.path.join(script_dir, f"{prefix}INCOME.csv"), index=False
    )
  if outgoings:
    pd.DataFrame(outgoings, columns=["Date", "Description", "Type", "Cheque Number", "Payed Out"]).to_csv(
      os.path.join(script_dir, f"{prefix}OUTGOING.csv"), index=False
    )
  print(f"✅ CSVs saved in {script_dir}")


def extract_text(path):
  with pdfplumber.open(path) as pdf:
    page_list = ""
    for page in pdf.pages:
      text = page.extract_text()
      if not text:
        continue
      page_list += text
    return page_list


def extract_amount_from_parts(parts):
  numbers = []
  for p in parts:
    try:
      numbers.append(float(p.replace(",", "")))
    except ValueError:
      continue
  if not numbers:
    return None
  # If there are multiple numbers, pick the second-to-last; else the last
  return numbers[-2] if len(numbers) > 1 else numbers[-1]


def credit_transaction(current_date, line, next_line, parts):
  desc = line[2:].strip()
  add_info, amount = "", None
  if not next_line.startswith("SO") and not next_line.startswith("CR") and not next_line.startswith("DD") and not next_line.startswith("CHQ"):
    next_parts = next_line.strip().split()

    if next_parts:
      amount = extract_amount_from_parts(next_parts)
      if amount is not None:
        # Remove the number from add_info
        add_info = " ".join(p for p in next_parts if p.replace(",", "").replace(".", "").isdigit() == False)
      else:
        desc += " " + next_line.strip()
  else:
    amount = extract_amount_from_parts(parts)
    desc_parts = [p for p in parts[1:] if p.replace(",", "").replace(".", "").isdigit() == False]
    desc = " ".join(desc_parts)

  transaction = {
    "type": "IN",
    "date": current_date,
    "desc": desc,
    "add_info": add_info,
    "paid_in": amount,
    "paid_out": None
  }
  return transaction


def direct_debit_transaction(current_date, parts):
  amount = extract_amount_from_parts(parts)

  desc_parts = [p for p in parts[1:] if p.replace(",", "").replace(".", "").isdigit() == False]
  desc = " ".join(desc_parts)

  transaction = {
    "type": "OUT",
    "date": current_date,
    "desc": desc,
    "tx_type": "DD",
    "cheque_number": None,
    "paid_in": None,
    "paid_out": amount
  }

  return transaction


def standing_order_transaction(current_date, line, next_line, parts):
  desc = line[2:].strip()
  add_info, amount = "", None
  if not next_line.startswith("SO") and not next_line.startswith("CR") and not next_line.startswith("DD") and not next_line.startswith("CHQ"):
    next_parts = next_line.strip().split()

    if next_parts:
      amount = extract_amount_from_parts(next_parts)
      if amount is not None:
        # Remove the number from add_info
        add_info = " ".join(p for p in next_parts if p.replace(",", "").replace(".", "").isdigit() == False)
      else:
        desc += " " + next_line.strip()
  else:
    amount = extract_amount_from_parts(parts)
    desc_parts = [p for p in parts[1:] if p.replace(",", "").replace(".", "").isdigit() == False]
    desc = " ".join(desc_parts)

  transaction = {
    "type": "OUT",
    "date": current_date,
    "desc": desc + " " + add_info,
    "tx_type": "SO",
    "cheque_number": None,
    "paid_in": None,
    "paid_out": amount
  }

  return transaction


def cheque_transaction(current_date, parts):
  transaction = {
    "type": "OUT",
    "date": current_date,
    "desc": None,
    "tx_type": "CHQ",
    "cheque_number": parts[1],
    "paid_in": None,
    "paid_out": parts[2]
  }

  return transaction


def parse_transaction_line(line, next_line, current_date):
  transaction = None
  line = line.strip()
  parts = line.split()

  if not parts:
    return None

  if line.startswith("CR"):
    transaction = credit_transaction(current_date, line, next_line, parts)
  elif line.startswith("DD"):
    transaction = direct_debit_transaction(current_date, parts)
  elif line.startswith("SO"):
    transaction = standing_order_transaction(current_date, line, next_line, parts)
  elif line.startswith("CHQ"):
    transaction = cheque_transaction(current_date, parts)

  return transaction


def extract_transactions(text):
  transactions_list = []
  month_abbr, year_abbr = None, None
  current_date = None

  lines = text.splitlines()
  i = 0
  while i < len(lines):
    line = lines[i].strip()
    if "BALANCEBROUGHTFORWARD" in line or "BALANCECARRIEDFORWARD" in line:
      i += 1
      continue
    match = DATE_PATTERN.match(line)
    next_line = lines[i + 1] if i + 1 < len(lines) else None

    if match:
      date_str, rest = match.groups()
      try:
        dt = datetime.strptime(date_str, "%d %b %y")
      except ValueError:
        i += 1
        continue
      current_date = dt.day
      month_abbr = dt.strftime("%b").upper()
      year_abbr = dt.strftime("%y")

      transactions_list.append(parse_transaction_line(rest, next_line, current_date))
    elif current_date is not None:
      transactions_list.append(parse_transaction_line(line, next_line, current_date))

    i += 1

  prefix = f"{month_abbr}{year_abbr}" if month_abbr and year_abbr else "STATEMENT"
  return transactions_list, prefix


if __name__ == "__main__":
  pdf_path = input("Enter the path to the bank statement PDF: ").strip().strip('"').strip("'")
  if not os.path.exists(pdf_path):
    print("❌ File not found")
  else:
    pages = extract_text(pdf_path)
    transactions, csv_name = extract_transactions(pages)
    print(transactions)
    if transactions:
      save_to_csvs(transactions, csv_name)
    else:
      print("⚠️ No transactions found")
