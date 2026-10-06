from pathlib import Path

import pandas as pd

from retail_rules import build_staging_data


project_root = Path(__file__).resolve().parents[1]
data_path = project_root / "data" / "raw" / "Online Retail.xlsx"
staging_dir = project_root / "data" / "staging"
output_path = staging_dir / "online_retail_staging.csv"

print("正在读取原始数据……")
data = pd.read_excel(data_path, engine="openpyxl")
data = build_staging_data(data)

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
