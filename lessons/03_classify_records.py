from pathlib import Path

import pandas as pd


project_root = Path(__file__).resolve().parents[1]
data_path = project_root / "data" / "raw" / "Online Retail.xlsx"


def classify_record(row):
    invoice = str(row["InvoiceNo"]).upper()

    if invoice.startswith("C"):
        return "customer_cancellation"

    if row["Quantity"] < 0:
        return "inventory_adjustment_candidate"

    if row["UnitPrice"] <= 0:
        return "nonpositive_price_candidate"

    if pd.isna(row["CustomerID"]):
        return "unknown_customer_purchase"

    return "regular_purchase"


print("正在读取数据……")
data = pd.read_excel(data_path, engine="openpyxl")

data["record_type"] = data.apply(classify_record, axis=1)

type_counts = data["record_type"].value_counts()

print("\n各类记录数量：")
print(type_counts)

print("\n分类总数：")
print(type_counts.sum())

assert type_counts.sum() == len(data)