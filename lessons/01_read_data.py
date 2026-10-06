"""第一课：读取教学数据，核对明细、订单和金额；不是生产清洗程序。"""

import csv
from decimal import Decimal
from pathlib import Path

sample_path = Path(__file__).resolve().parents[1] / "data" / "teaching_sample.csv"
with sample_path.open(encoding="utf-8", newline="") as file:
    rows = list(csv.DictReader(file))

purchase_invoices = set()
customers = set()
positive_amount = Decimal("0")
cancellation_amount = Decimal("0")

def calculate_amount(row):
    quantity = int(row["Quantity"])
    unit_price = Decimal(row["UnitPrice"])
    amount = quantity * unit_price
    return quantity, unit_price, amount

for row in rows:
    invoice = row["InvoiceNo"]
    quantity, unit_price, amount = calculate_amount(row)
    print(f"明细 {invoice} / {row['StockCode']}：{quantity} × {unit_price} = {amount:.2f}")

    # 本课样本约定：C 开头表示取消记录，其余为有效购买。
    if invoice.startswith("C"):
        cancellation_amount += amount
    else:
        purchase_invoices.add(invoice)
        positive_amount += amount

    if row["CustomerID"]:
        customers.add(row["CustomerID"])

print(f"\n明细行数：{len(rows)}")
print(f"购买发票数：{len(purchase_invoices)}")
print(f"已知客户数：{len(customers)}")
print(f"购买金额：{positive_amount:.2f}")
print(f"取消金额（有符号）：{cancellation_amount:.2f}")
print(f"净额：{positive_amount + cancellation_amount:.2f}")
