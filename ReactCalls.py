from flask import Flask, jsonify, request
from flask_cors import CORS
import os
import BankStatementReader
import pandas as pd

app = Flask(__name__)
CORS(app)

AVAILABLE_BANKS = ["HSBC"]
UPLOAD_FOLDER = "./uploads"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)


@app.route("/banks", methods=["GET"])
def get_banks():
  return jsonify({"banks": AVAILABLE_BANKS})


@app.route("/upload", methods=["POST"])
def upload_file():
  uploaded_file = request.files.get("file")
  bank = request.form.get("bank")
  if not uploaded_file:
    return jsonify({"error": "No file uploaded"}), 400

  # Save file to disk
  file_path = os.path.join(UPLOAD_FOLDER, uploaded_file.filename)
  uploaded_file.save(file_path)

  # Extract text and transactions
  if bank == "HSBC":
    return hsbc(file_path)


def hsbc(file_path):
  try:
    pages = BankStatementReader.extract_text(file_path)
    transactions, csv_name = BankStatementReader.extract_transactions(pages)
  except Exception as e:
    return jsonify({"error": f"Failed to parse file: {str(e)}"}), 500

  income, outgoings = [], []

  for t in transactions:
    if not t:
      continue
    if t["type"] == "IN":
      income.append([t["date"], t["desc"], t["paid_in"], t["add_info"]])
    else:
      outgoings.append([t["date"], t["desc"], t["tx_type"], t["cheque_number"], t["paid_out"]])

  # Create CSVs
  income = pd.DataFrame(income, columns=["Date", "Description", "Payed In", "Additional Info"]).to_csv(index=False) if income else ""
  outcome = pd.DataFrame(outgoings, columns=["Date", "Description", "Type", "Cheque Number", "Payed Out"]).to_csv(index=False) if outgoings else ""

  os.remove(file_path)

  return jsonify({"income": income, "outgoing": outcome})


if __name__ == "__main__":
  app.run(debug=True)
