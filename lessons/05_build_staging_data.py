from pathlib import Path

import pandas as pd


project_root = Path(__file__).resolve().parents[1]
data_path = project_root / "data" / "raw" / "Online Retail.xlsx"
staging_dir = project_root / "data" / "staging"
output_path = staging_dir / "online_retail_staging.csv"

print("正在读取原始数据……")
data = pd.read_excel(data_path, engine="openpyxl")

original_columns = list(data.columns)

# 记录原始 Excel 行号，便于以后追查问题。
data.insert(0, "source_row_number", range(2, len(data) + 2))

invoice_text = data["InvoiceNo"].astype(str).str.upper()

# 每个标记独立存在，同一行可以同时满足多个条件。
data["is_customer_cancellation"] = invoice_text.str.startswith("C")
data["is_negative_quantity"] = data["Quantity"] < 0
data["is_nonpositive_price"] = data["UnitPrice"] <= 0
data["is_missing_customer"] = data["CustomerID"].isna()
data["is_missing_description"] = data["Description"].isna()

# 必须只检查原始字段，因为 source_row_number 本身永远不会重复。
data["is_exact_duplicate_extra"] = data.duplicated(
    subset=original_columns,
    keep="first",
)

data["line_amount"] = data["Quantity"] * data["UnitPrice"]

# 客户编号本质上是整数，Int64 同时允许存在缺失值。
data["CustomerID"] = data["CustomerID"].astype("Int64")

# 先设置默认类型。
data["record_type"] = "regular_purchase"

# 后执行的规则优先级更高。
data.loc[
    data["is_missing_customer"],
    "record_type",
] = "unknown_customer_purchase"

data.loc[
    data["is_nonpositive_price"],
    "record_type",
] = "nonpositive_price_candidate"

data.loc[
    data["is_negative_quantity"],
    "record_type",
] = "inventory_adjustment_candidate"

data.loc[
    data["is_customer_cancellation"],
    "record_type",
] = "customer_cancellation"

# 创建 staging 文件夹并保存结果。
staging_dir.mkdir(parents=True, exist_ok=True)
data.to_csv(output_path, index=False, encoding="utf-8-sig")

print("\n主要记录类型：")
print(data["record_type"].value_counts())

print("\n独立质量标记：")
print("取消记录：", data["is_customer_cancellation"].sum())
print("负数量记录：", data["is_negative_quantity"].sum())
print("非正价格记录：", data["is_nonpositive_price"].sum())
print("客户编号缺失：", data["is_missing_customer"].sum())
print("商品描述缺失：", data["is_missing_description"].sum())
print("额外重复记录：", data["is_exact_duplicate_extra"].sum())

print("\n暂不删除任何记录。")
print("暂存层行数：", len(data))
print("文件已保存到：", output_path)

# 自动检查关键结果。
assert len(data) == 541909
assert data["source_row_number"].is_unique
assert data["record_type"].isna().sum() == 0
assert data["is_exact_duplicate_extra"].sum() == 5268