"""第二课：读取 UCI Online Retail 原始文件并生成第一份数据调查报告。"""

from pathlib import Path

import pandas as pd


project_root = Path(__file__).resolve().parents[1]
data_path = project_root / "data" / "raw" / "Online Retail.xlsx"
report_path = project_root / "reports" / "02_data_profile.txt"

expected_columns = [
    "InvoiceNo",
    "StockCode",
    "Description",
    "Quantity",
    "InvoiceDate",
    "UnitPrice",
    "CustomerID",
    "Country",
]


def format_counts(title, counts):
    """把每个字段的计数整理成便于阅读的多行文本。"""
    lines = [title]
    for column, count in counts.items():
        lines.append(f"  {column}: {count}")
    return lines


print("正在读取原始 Excel，首次运行通常需要几十秒……")
data = pd.read_excel(data_path, engine="openpyxl")
print("\n前 5 行数据：")
print(data.head())

print("\n各字段类型：")
print(data.dtypes)

# 先确认我们读到的是预期文件，而不是名称相同的其他表格。
assert list(data.columns) == expected_columns, "字段与预期不一致"
assert len(data) == 541_909, "明细行数与 UCI 公布值不一致"

invoice_text = data["InvoiceNo"].astype(str).str.upper()
missing_counts = data.isna().sum()

report_lines = [
    "UCI Online Retail 数据调查报告",
    "",
    f"明细行数: {len(data)}",
    f"字段数: {len(data.columns)}",
    f"最早交易时间: {data['InvoiceDate'].min()}",
    f"最晚交易时间: {data['InvoiceDate'].max()}",
    f"不同发票号数量: {data['InvoiceNo'].nunique()}",
    f"已知客户数量: {data['CustomerID'].nunique(dropna=True)}",
    f"C 开头取消明细数: {invoice_text.str.startswith('C').sum()}",
    f"负数量明细数: {(data['Quantity'] < 0).sum()}",
    f"非正单价明细数: {(data['UnitPrice'] <= 0).sum()}",
    f"完全重复明细数: {data.duplicated().sum()}",
    "",
]
report_lines.extend(format_counts("各字段缺失数量:", missing_counts))

report = "\n".join(report_lines)
print(report)

report_path.parent.mkdir(parents=True, exist_ok=True)
report_path.write_text(report + "\n", encoding="utf-8")
print(f"\n报告已保存到: {report_path}")
invoice_text = data["InvoiceNo"].astype(str).str.upper()

negative_quantity = data["Quantity"] < 0
cancellation = invoice_text.str.startswith("C")

print("\n负数量且是 C 开头：")
print((negative_quantity & cancellation).sum())

print("\n负数量但不是 C 开头：")
print((negative_quantity & ~cancellation).sum())

print("\nC 开头但数量不是负数：")
print((cancellation & ~negative_quantity).sum())
non_cancel_negative = data.loc[
    negative_quantity & ~cancellation,
    [
        "InvoiceNo",
        "StockCode",
        "Description",
        "Quantity",
        "UnitPrice",
        "CustomerID",
    ],
]

print("\n负数量但非取消的前 10 行：")
print(non_cancel_negative.head(10))

print("\n最常见的描述：")
print(
    non_cancel_negative["Description"]
    .value_counts(dropna=False)
    .head(15)
)