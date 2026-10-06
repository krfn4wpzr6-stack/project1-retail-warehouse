from pathlib import Path

import pandas as pd


project_root = Path(__file__).resolve().parents[1]
data_path = project_root / "data" / "raw" / "Online Retail.xlsx"

print("正在读取数据……")
data = pd.read_excel(data_path, engine="openpyxl")

# Excel 第一行是表头，所以第一条数据位于第 2 行。
data.insert(0, "source_row_number", range(2, len(data) + 2))

business_columns = [
    "InvoiceNo",
    "StockCode",
    "Description",
    "Quantity",
    "InvoiceDate",
    "UnitPrice",
    "CustomerID",
    "Country",
]

# 只标记同一组数据中第二次及以后出现的记录。
extra_duplicate_mask = data.duplicated(
    subset=business_columns,
    keep="first",
)

# 标记所有参与重复的记录，包括第一次出现的记录。
all_duplicate_mask = data.duplicated(
    subset=business_columns,
    keep=False,
)

all_duplicate_rows = data.loc[all_duplicate_mask]

# 每种重复内容只保留一条，用于统计重复模式数量。
duplicate_patterns = all_duplicate_rows.drop_duplicates(
    subset=business_columns
)

group_sizes = (
    all_duplicate_rows
    .groupby(business_columns, dropna=False)
    .size()
    .sort_values(ascending=False)
)

extra_amount = (
    data.loc[extra_duplicate_mask, "Quantity"]
    * data.loc[extra_duplicate_mask, "UnitPrice"]
).sum()

print("\n额外重复行数：")
print(extra_duplicate_mask.sum())

print("\n所有参与重复的行数：")
print(all_duplicate_mask.sum())

print("\n不同的重复模式数量：")
print(len(duplicate_patterns))

print("\n最大的完全相同记录组：")
print(group_sizes.head(10))

print("\n前 20 条参与重复的记录：")
display_columns = [
    "source_row_number",
    "InvoiceNo",
    "StockCode",
    "Description",
    "Quantity",
    "InvoiceDate",
    "UnitPrice",
    "CustomerID",
]

print(
    all_duplicate_rows[display_columns]
    .head(20)
    .to_string(index=False)
)

print("\n如果删除额外重复行，金额变化量：")
print(round(extra_amount, 2))

assert all_duplicate_mask.sum() >= extra_duplicate_mask.sum()