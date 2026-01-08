import re
import pdfplumber
import pandas as pd
import os
from datetime import datetime

DATE_PATTERN = re.compile(r"^(\d{2} \w{3} \d{4})$")


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


def extract_data(path):
  with pdfplumber.open(path) as pdf:
    page_list = []
    for page in pdf.pages:
      text = page.extract_table()
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


def purchase_transaction(details, current_date, amount):
  transaction = {
    "type": "OUT",
    "date": current_date,
    "desc": details.split("\n")[0],
    "tx_type": "Purchase",
    "cheque_number": None,
    "paid_in": None,
    "paid_out": amount
  }
  return transaction


def transfer_transaction(details, current_date, amount):
  transaction = {
    "type": "OUT",
    "date": current_date,
    "desc": details.split("\n")[0],
    "tx_type": "Transfer",
    "cheque_number": None,
    "paid_in": None,
    "paid_out": amount
  }
  return transaction



def direct_debit_transaction(details, current_date, amount):
  transaction = {
    "type": "OUT",
    "date": current_date,
    "desc": details.split("\n")[0],
    "tx_type": "Direct Debit",
    "cheque_number": None,
    "paid_in": None,
    "paid_out": amount
  }
  return transaction



def payment_transaction(details, current_date, amount):
  transaction = {
    "type": "IN",
    "date": current_date,
    "desc": details.split("\n")[0],
    "add_info": None,
    "paid_in": amount,
    "paid_out": None
  }
  return transaction


def parse_transaction_line(transaction, current_date):
  formatted_transaction = None
  details = transaction[1]
  amount = transaction[2].replace("£", "").replace("-", "").replace("+", "")

  if "Purchase" in details:
    formatted_transaction = purchase_transaction(details, current_date, amount)
  elif "Transfer" in details:
    formatted_transaction = transfer_transaction(details, current_date, amount)
  elif "Payment" in details:
    formatted_transaction = payment_transaction(details, current_date, amount)
  elif "Direct Debit" in details:
    formatted_transaction = direct_debit_transaction(details, current_date, amount)

  return formatted_transaction


def extract_transactions(unformatted_transactions):
  transactions_list = []
  month_abbr, year_abbr = None, None

  for transaction in unformatted_transactions:
    dt = datetime.strptime(transaction[0], "%d %b %Y")

    month_abbr = dt.strftime("%b").upper()
    year_abbr = dt.strftime("%y")

    transactions_list.append(parse_transaction_line(transaction, dt.day))

  prefix = f"{month_abbr}{year_abbr}" if month_abbr and year_abbr else "STATEMENT"
  return transactions_list, prefix


if __name__ == "__main__":
  pdf_path = input("Enter the path to the bank statement PDF: ").strip().strip('"').strip("'")
  if not os.path.exists(pdf_path):
    print("❌ File not found")
  else:
    pages = extract_data(pdf_path)
    transactions, csv_name = extract_transactions(pages)
    if transactions:
      save_to_csvs(transactions, csv_name)
    else:
      print("⚠️ No transactions found")
